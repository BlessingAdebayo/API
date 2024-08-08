import logging
import time
import typing
from datetime import datetime, timezone
from decimal import Decimal
from functools import partial
from typing import Callable, Optional, Tuple, Union

from hexbytes import HexBytes

from trading_api import EnvVar, get_env, get_env_force
from trading_api.algorithm.lock import create_algorithm_transaction, get_lock_symbol
from trading_api.algorithm.models.algorithm import (
    Algorithm,
    AlgorithmIsLocked,
    AlgorithmTransaction,
    AlgorithmWasLocked,
    NewAlgorithmLock,
    TradingContractVersion,
)
from trading_api.algorithm.models.crypto import ChainId
from trading_api.algorithm.models.trade import (
    BlockChainError,
    BuyTrade,
    BuyTradeV2,
    InsufficientFunds,
    MultiTokenTrade,
    SellTradeV2,
    StatusRequest,
    Trade,
    TradeRequestResponse,
    TradeStatus,
    TradeType,
    TradingTransaction,
)
from trading_api.algorithm.repositories.algorithm import AlgorithmRepository
from trading_api.algorithm.repositories.lock import AlgorithmLockRepository
from trading_api.algorithm.repositories.nonce import NonceRepository
from trading_api.algorithm.repositories.transaction import TransactionRepository
from trading_api.algorithm.services.kms import KeyManagementService
from trading_api.algorithm.services.web3 import Web3Provider
from trading_api.algorithm.status import check_trade_status

logger = logging.getLogger(__name__)

MAX_TRIES = 3


def handle_trade_request(
    trade_request: Trade,
    algorithm: Algorithm,
    lock_repository: AlgorithmLockRepository,
    web3_provider: Web3Provider,
    km_service: KeyManagementService,
    trading_transaction_repository: TransactionRepository,
    algorithm_repository: AlgorithmRepository,
    nonce_repository: NonceRepository,
) -> TradeRequestResponse:
    algorithm_lock = retrieve_lock(
        lock_repository,
        trade_request,
        web3_provider,
        trading_transaction_repository=trading_transaction_repository,
        algorithm_repository=algorithm_repository,
    )
    if isinstance(algorithm_lock, AlgorithmWasLocked):
        return algorithm_lock

    trade_type = get_trade_type(trade_request)

    try:
        if not is_trade_possible(trade_request, algorithm, web3_provider):
            return handle_blockchain_error(
                ValueError("Trade is not possible with the values provided."), lock_repository, trade_request
            )
    except ValueError as error:
        return handle_blockchain_error(error, lock_repository, trade_request)

    web3_nonce = get_web3_nonce(algorithm, web3_provider)
    nonce_counter = nonce_repository.get_nonce(trade=trade_request, web3_nonce=web3_nonce)

    make_trade_callable = partial(
        send_trade_to_blockchain,
        algorithm=algorithm,
        web3_provider=web3_provider,
        km_service=km_service,
        nonce_counter=nonce_counter,
    )

    try:
        lock, nonce = make_trade(trade_request, make_trade_callable, lock_repository, trading_transaction_repository)

        return lock
    except ValueError as error:
        logger.warning(
            f"Error sending trade to blockchain. trade-type:{trade_type.value} {trade_request.json()=}  {error=}",
            exc_info=True,
        )

        nonce_repository.reset_nonce(trade=trade_request)

        return handle_blockchain_error(error, lock_repository, trade_request)


def get_web3_nonce(algorithm: Algorithm, web3_provider: Web3Provider):
    w3 = web3_provider.get_web3(chain=algorithm.chain_id)
    return int(w3.eth.get_transaction_count(algorithm.controller_wallet_address))


def is_multi_token_trade(trade: Trade) -> bool:
    return isinstance(trade, (BuyTradeV2, SellTradeV2))


def is_trade_possible(trade: Trade, algorithm: Algorithm, web3_provider: Web3Provider) -> bool:
    if not is_multi_token_trade(trade):
        return True

    trading_contract_tools = web3_provider.get_trading_contract_tools(algorithm=algorithm)
    trading_check_function = get_trading_check_function(trade, trading_contract_tools)

    try:
        check_result = trading_check_function(algorithm.trading_contract_address, trade.symbol).call()  # type: ignore
        logger.info(f"is_trade_possible: {check_result=} {trade=} {algorithm.trading_contract_address=}")
        return bool(check_result)
    except Exception as e:
        logger.warning(
            f"Error checking validity of blockchain trade. contract-address=:{algorithm.trading_contract_address} symbol={trade.symbol} {e=}",  # type: ignore
            exc_info=True,
        )
        raise ValueError from e


def make_trade(
    trade: Trade,
    make_trade_callable: Callable[[Trade], Tuple[AlgorithmTransaction, int]],
    lock_repository: AlgorithmLockRepository,
    trading_transaction_repository: TransactionRepository,
) -> Tuple[AlgorithmIsLocked, int]:
    algorithm_transaction, nonce = make_trade_callable(trade)
    algorithm_is_locked = lock_repository.persist_algorithm_transaction(
        algorithm_transaction, symbol=get_lock_symbol(trade)
    )

    trading_transaction = TradingTransaction(
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        transaction_hash=algorithm_transaction.transaction_hash.value,
        trading_contract_address=trade.algorithm_id.public_address,
        slippage_amount=Decimal(trade.slippage.amount),
        relative_amount=Decimal(trade.relative_amount),
        symbol=trade.symbol if isinstance(trade, (BuyTradeV2, SellTradeV2)) else None,
        status=TradeStatus.TRADE_IN_PROGRESS_OR_NOT_FOUND,
        trade_type=get_trade_type(trade),
    )
    trading_transaction_repository.persist_transaction(trading_transaction)

    return algorithm_is_locked, nonce


def handle_blockchain_error(error: ValueError, lock_repository: AlgorithmLockRepository, trade: Trade):
    error_str = str(error)
    lock_repository.remove_algorithm_lock(algorithm_id=trade.algorithm_id, symbol=get_lock_symbol(trade))
    if "Not enough funds to trade" in error_str:
        return InsufficientFunds(algorithm_id=trade.algorithm_id)

    return BlockChainError(algorithm_id=trade.algorithm_id, error=error_str)


def retrieve_lock(
    lock_repository: AlgorithmLockRepository,
    trade: Trade,
    web3_provider: Web3Provider,
    trading_transaction_repository: TransactionRepository,
    algorithm_repository: AlgorithmRepository,
) -> Union[NewAlgorithmLock, AlgorithmWasLocked]:
    algorithm_lock = lock_repository.get_algorithm_lock(trade.algorithm_id, get_lock_symbol(trade))

    # There is already a lock on this algorithm.
    if isinstance(algorithm_lock, AlgorithmWasLocked):
        algorithm_lock = check_transaction_status_for_lock(
            algorithm_lock=algorithm_lock,
            lock_repository=lock_repository,
            trade=trade,
            web3_provider=web3_provider,
            trading_transaction_repository=trading_transaction_repository,
            algorithm_repository=algorithm_repository,
        )

    if isinstance(algorithm_lock, AlgorithmWasLocked):
        logger.info(f"Trading call stopped. Transaction is still in progress. {algorithm_lock=}")

    return algorithm_lock


def check_transaction_status_for_lock(
    algorithm_lock: AlgorithmWasLocked,
    lock_repository: AlgorithmLockRepository,
    trade: Trade,
    web3_provider: Web3Provider,
    trading_transaction_repository: TransactionRepository,
    algorithm_repository: AlgorithmRepository,
) -> Union[NewAlgorithmLock, AlgorithmWasLocked]:
    # Exceptional case -- shouldn't happen:
    if algorithm_lock.transaction_hash is None:
        return algorithm_lock

    status_request = StatusRequest(
        algorithm_id=trade.algorithm_id,
        transaction_hash=algorithm_lock.transaction_hash,
        timeout_in_seconds=0,
    )
    trade_status = check_trade_status(
        request=status_request, web3_provider=web3_provider, algorithm_repository=algorithm_repository
    )

    if trade_status == trade_status.TRADE_IN_PROGRESS_OR_NOT_FOUND:
        return algorithm_lock

    # Remove the lock since the transaction is 'finished'.
    assert trade_status in (trade_status.TRADE_FAILED, trade_status.TRADE_SUCCESSFUL)

    # Update our trading transaction record
    trading_transaction_repository.update_transaction_status(
        transaction_hash=algorithm_lock.transaction_hash,
        trade_status=trade_status,
        timestamp=datetime.now(timezone.utc),
    )

    lock_repository.remove_algorithm_lock(algorithm_id=trade.algorithm_id, symbol=get_lock_symbol(trade))

    # Try to retrieve a new lock, this could still be an AlgorithmWasLocked,
    # if we have a concurrent request, this is very much an edge case.
    return lock_repository.get_algorithm_lock(algorithm_id=trade.algorithm_id, symbol=get_lock_symbol(trade))


def get_trading_check_function(trade: Trade, trading_contract_tools):
    if get_trade_type(trade) == TradeType.BUY:
        return trading_contract_tools.functions.buyCheck

    return trading_contract_tools.functions.sellCheck


def get_trading_function(trade: Trade, trading_contract):
    if get_trade_type(trade) == TradeType.BUY:
        return trading_contract.functions.buy

    return trading_contract.functions.sell


def get_trade_type(trade: Trade) -> TradeType:
    if isinstance(trade, (BuyTrade, BuyTradeV2)):
        return TradeType.BUY

    return TradeType.SELL


def estimated_gas_factor_for_chain(chain_id: ChainId) -> Decimal:
    factors = {
        ChainId.RTN: Decimal(get_env_force(EnvVar.ESTIMATED_GAS_FACTOR_RTN, "20")),
        ChainId.BSC: Decimal(get_env_force(EnvVar.ESTIMATED_GAS_FACTOR_BSC, "10")),
    }

    return factors.get(chain_id, Decimal(get_env_force(EnvVar.ESTIMATED_GAS_FACTOR, "15")))


def estimated_gas_price_factor_for_chain(chain_id: ChainId) -> Decimal:
    factors = {
        ChainId.RTN: Decimal(get_env_force(EnvVar.ESTIMATED_GAS_PRICE_FACTOR_RTN, "1")),
        ChainId.BSC: Decimal(get_env_force(EnvVar.ESTIMATED_GAS_PRICE_FACTOR_BSC, "1")),
    }

    return factors.get(chain_id, Decimal(get_env_force(EnvVar.ESTIMATED_GAS_PRICE_FACTOR, "1")))


@typing.no_type_check
def send_trade_to_blockchain(
    trade: Trade,
    algorithm: Algorithm,
    web3_provider: Web3Provider,
    km_service: KeyManagementService,
    nonce_counter: Optional[int],
    try_number: int = 1,
    estimated_gas_factor: Optional[Decimal] = None,
    estimated_gas_price_factor: Optional[Decimal] = None,
) -> Tuple[AlgorithmTransaction, int]:
    if estimated_gas_factor is None:
        estimated_gas_factor = estimated_gas_factor_for_chain(algorithm.chain_id)
    if estimated_gas_price_factor is None:
        estimated_gas_price_factor = estimated_gas_price_factor_for_chain(algorithm.chain_id)

    w3 = web3_provider.get_web3(chain=algorithm.chain_id)
    unit = get_env(EnvVar.UNIT, "ether")

    nonce = int(w3.eth.get_transaction_count(algorithm.controller_wallet_address))
    if nonce_counter is not None and nonce_counter > nonce:
        nonce = nonce_counter

    transaction = {
        "gas": int(estimated_gas_factor * w3.eth.estimate_gas({})),
        "gasPrice": int(estimated_gas_price_factor * w3.eth.gas_price),
        "nonce": nonce,
    }

    trading_contract = web3_provider.get_trading_contract(algorithm=algorithm)
    trading_function = get_trading_function(trade, trading_contract)

    if Decimal(algorithm.trading_contract.version.value) >= Decimal(TradingContractVersion.V2_0):
        txn = trading_function(
            w3.toWei(trade.relative_amount, unit=unit),
            int(trade.slippage.raw_amount),
            trade.symbol,
        ).buildTransaction(transaction)
    else:
        txn = trading_function(
            w3.toWei(trade.relative_amount, unit=unit),
            int(trade.slippage.raw_amount),
        ).buildTransaction(transaction)

    signed_txn = km_service.sign_transaction(
        transaction=txn, address=algorithm.controller_wallet_address, chain=algorithm.chain_id
    )
    logger.info(f"Sending trade to blockchain, trade-type:{get_trade_type(trade).value} {trade=} {txn=}.")
    try:
        transaction_hash: str = w3.eth.send_raw_transaction(signed_txn.rawTransaction).hex()
    except ValueError as e:
        error_str = str(e)
        if try_number >= MAX_TRIES:
            raise e
        if not any(m in error_str for m in ["replacement transaction underpriced", "nonce too low"]):
            raise e

        logger.warning(
            f"[RETRYING] Error sending trade to blockchain. {try_number=} {nonce=} trade-type:{get_trade_type(trade).value} {trade.json()=} {transaction=} {e=}",
            exc_info=True,
        )
        # if try_number == 1:
        #     estimated_gas_factor = estimated_gas_factor * Decimal("1.50")  # Add 50%.

        # Trying again
        # We don't make a replacement transaction, instead we try to make another transaction
        return send_trade_to_blockchain(
            trade=trade,
            algorithm=algorithm,
            web3_provider=web3_provider,
            km_service=km_service,
            try_number=try_number + 1,
            nonce_counter=nonce_counter,
            estimated_gas_factor=estimated_gas_factor,
        )

    logger.info(
        f"Trade on blockchain done. trade-type:{get_trade_type(trade).value} {algorithm.controller_wallet_address=} {transaction_hash=}, {str(transaction)=}."
    )

    return create_algorithm_transaction(trade.algorithm_id, HexBytes(transaction_hash)), nonce
