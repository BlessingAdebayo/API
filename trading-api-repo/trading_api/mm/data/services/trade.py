import logging
import math
from decimal import Decimal
from typing import List

from hexbytes import HexBytes
from web3 import Web3
from web3.contract import Contract, ContractFunction
from web3.exceptions import TransactionNotFound
from web3.types import Nonce, Wei

from mm.domain.exceptions import BlockchainError
from mm.domain.models import (
    Amounts,
    ChainId,
    ContractAddress,
    KeyAddressPair,
    Release,
    SignedTransaction,
    Slippage,
    Stake,
    Swap,
    Trade,
    TradeType,
    Transaction,
    TransactionHash,
    TransactionHashes,
    TransactionStatus,
)
from mm.domain.services import TransactionService, Web3Provider

logger = logging.getLogger(__name__)


class StubTransactionService(TransactionService):
    def __init__(self, hashes: TransactionHashes = None):
        self.hashes = hashes or []
        self.transactions: List[SignedTransaction] = []

    def create_trade_transaction(self, pair: KeyAddressPair, trade: Trade) -> Transaction:
        pass

    def create_swap_transaction(self, pair: KeyAddressPair, swap: Swap) -> Transaction:
        pass

    def create_stake_in_liquidity_maker_transaction(self, pair: KeyAddressPair, stake: Stake) -> Transaction:
        pass

    def create_release_for_transaction(self, pair: KeyAddressPair, release: Release) -> Transaction:
        pass

    def send(self, transaction: SignedTransaction) -> TransactionHash:
        self.transactions.append(transaction)

        return TransactionHash(self.hashes.pop())

    def get_status(self, hash: TransactionHash, chain: ChainId) -> TransactionStatus:
        return TransactionStatus.TRANSACTION_SUCCESSFUL


class BlockchainTransactionService(TransactionService):
    estimated_gas_factor = 20
    estimated_gas_price_factor = 1.2

    def __init__(self, web3: Web3Provider):
        self.web3 = web3

    def create_trade_transaction(self, pair: KeyAddressPair, trade: Trade) -> Transaction:
        logger.info(f"Building transaction: {pair=} {trade=})")
        try:
            w3 = self.web3.get_web3(pair.chain)

            contract = get_contract(self.web3, pair.contract, pair.chain)

            tx_func = get_trading_function(trade, contract)
            tx_args = (
                _to_wei(w3, trade.amounts),
                trade.addresses,
                _to_raw_amount(trade.slippage),
                trade.exchange.value,
            )
            tx = tx_func(*tx_args).buildTransaction(
                {
                    "gas": Wei(self.estimated_gas_factor * w3.eth.estimate_gas({})),
                    "gasPrice": Wei(int(self.estimated_gas_price_factor * w3.eth.gas_price)),
                    "nonce": Nonce(w3.eth.get_transaction_count(pair.wallet)),
                }
            )

        except Exception as e:
            logger.error(e)
            raise BlockchainError.from_trade(trade)

        logger.info(f"Built transaction: {tx=}, {tx_args=})")

        return Transaction(tx)

    def create_swap_transaction(self, pair: KeyAddressPair, swap: Swap) -> Transaction:
        logger.info(f"Building transaction: {pair=} {swap=})")
        try:
            w3 = self.web3.get_web3(pair.chain)

            contract = get_contract(self.web3, pair.contract, pair.chain)

            tx_func = get_swapping_function(contract)
            tx_args = (
                _to_wei(w3, swap.amounts),
                swap.addresses,
                swap.seller,
                swap.exchange.value,
            )
            tx = tx_func(*tx_args).buildTransaction(
                {
                    "gas": Wei(self.estimated_gas_factor * w3.eth.estimate_gas({})),
                    "gasPrice": Wei(int(self.estimated_gas_price_factor * w3.eth.gas_price)),
                    "nonce": Nonce(w3.eth.get_transaction_count(pair.wallet)),
                }
            )

        except Exception as e:
            logger.error(e)
            raise BlockchainError.from_swap(swap)

        logger.info(f"Built transaction: {tx=}, {tx_args=})")

        return Transaction(tx)

    def create_stake_in_liquidity_maker_transaction(self, pair: KeyAddressPair, stake: Stake) -> Transaction:
        logger.info(f"Building transaction: {pair=} {stake=})")
        try:
            w3 = self.web3.get_web3(pair.chain)

            contract = get_contract(self.web3, pair.contract, pair.chain)

            tx_func = get_staking_function(contract)
            tx_args = (
                _to_wei(w3, stake.amounts_base),
                stake.addresses_base,
                _to_wei(w3, stake.amounts_paired),
                stake.addresses_paired,
                _to_raw_amount(stake.slippage),
                stake.exchange.value,
            )
            tx = tx_func(*tx_args).buildTransaction(
                {
                    "gas": Wei(self.estimated_gas_factor * w3.eth.estimate_gas({})),
                    "gasPrice": Wei(int(self.estimated_gas_price_factor * w3.eth.gas_price)),
                    "nonce": Nonce(w3.eth.get_transaction_count(pair.wallet)),
                }
            )

        except Exception as e:
            logger.error(e)
            raise BlockchainError.from_stake(stake)

        logger.info(f"Built transaction: {tx=}, {tx_args=})")

        return Transaction(tx)

    def create_release_for_transaction(self, pair: KeyAddressPair, release: Release) -> Transaction:
        logger.info(f"Building transaction: {pair=} {release=})")

        try:
            w3 = self.web3.get_web3(pair.chain)

            contract = get_contract(self.web3, pair.contract, pair.chain)

            tx_func = get_release_for_function(contract)
            tx_args = (release.addresses,)
            tx = tx_func(*tx_args).buildTransaction(
                {
                    "gas": Wei(self.estimated_gas_factor * w3.eth.estimate_gas({})),
                    "gasPrice": Wei(int(self.estimated_gas_price_factor * w3.eth.gas_price)),
                    "nonce": Nonce(w3.eth.get_transaction_count(pair.wallet)),
                }
            )

        except Exception as e:
            logger.error(e)
            raise BlockchainError.from_release(release)

        logger.info(f"Built transaction: {tx=}, {tx_args=})")

        return Transaction(tx)

    def send(self, transaction: SignedTransaction) -> TransactionHash:
        logger.info(f"Sending transaction to blockchain {transaction=})")
        try:
            w3 = self.web3.get_web3(chain=transaction.chain)

            tx_hash = w3.eth.send_raw_transaction(transaction.eth.rawTransaction).hex()

        except Exception as e:
            logger.error(e)
            raise BlockchainError.from_exception(e)

        logger.info(f"Sent transaction to blockchain {tx_hash=})")

        return TransactionHash(tx_hash)

    def get_status(self, hash: TransactionHash, chain: ChainId) -> TransactionStatus:
        logger.info(f"Retrieving transaction status from blockchain {hash=} {chain=})")
        try:
            w3 = self.web3.get_web3(chain=chain)

            tx_receipt = w3.eth.get_transaction_receipt(HexBytes(hash))

        except TransactionNotFound as e:
            logger.info(e)
            return TransactionStatus.TRANSACTION_IN_PROGRESS
        except Exception as e:
            logger.error(e)
            raise BlockchainError.from_transaction_receipt(hash)

        logger.info(f"Retrieved transaction status from blockchain {tx_receipt=})")

        if tx_receipt["status"] == 0:
            return TransactionStatus.TRANSACTION_FAILED

        return TransactionStatus.TRANSACTION_SUCCESSFUL


def _to_wei(w3: Web3, amounts: Amounts) -> list[Wei]:
    return [w3.toWei(amount, unit="ether") for amount in amounts]


def _to_raw_amount(slippage: Slippage, prec: int = 18) -> int:
    return int(Decimal(math.pow(10, prec)) * slippage)


def get_contract(web3: Web3Provider, contract_address: ContractAddress, chain: ChainId) -> Contract:
    return web3.get_contract(contract_address, chain)


def get_trading_function(trade: Trade, contract: Contract) -> ContractFunction:
    if trade.type == TradeType.BUY:
        return contract.functions.buy

    return contract.functions.sell


def get_swapping_function(contract: Contract) -> ContractFunction:
    return contract.functions.swap


def get_staking_function(contract: Contract) -> ContractFunction:
    return contract.functions.stakeInLiquidityMaker


def get_release_for_function(contract: Contract) -> ContractFunction:
    return contract.functions.releaseFor
