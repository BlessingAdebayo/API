import asyncio
import logging
from datetime import datetime, timezone
from typing import Tuple

from hexbytes import HexBytes
from web3 import Web3
from web3.exceptions import TimeExhausted, TransactionNotFound
from web3.types import TxReceipt

from trading_api import EnvVar, get_env_force
from trading_api.algorithm.models.algorithm import AlgorithmId
from trading_api.algorithm.models.crypto import TransactionHash
from trading_api.algorithm.models.trade import (
    StatusRequest,
    Trade,
    TradeFailedResponse,
    TradeInProgressOrNotFoundResponse,
    TradeStatus,
    TradeStatusResponse,
    TradeSuccessfulResponse,
)
from trading_api.algorithm.repositories.algorithm import AlgorithmRepository
from trading_api.algorithm.repositories.nonce import NonceRepository
from trading_api.algorithm.repositories.transaction import TransactionRepository
from trading_api.algorithm.services.web3 import Web3Provider
from trading_api.core.container import Container

logger = logging.getLogger(__name__)


async def handle_status_request(
    request: StatusRequest,
    web3_provider: Web3Provider,
    trading_transaction_repository: TransactionRepository,
    algorithm_repository: AlgorithmRepository,
) -> TradeStatusResponse:
    trade_status: TradeStatus = check_trade_status(request, web3_provider, algorithm_repository=algorithm_repository)
    trading_transaction_repository.update_transaction_status(
        request.transaction_hash, trade_status, datetime.now(timezone.utc)
    )

    if trade_status == TradeStatus.TRADE_IN_PROGRESS_OR_NOT_FOUND:
        return TradeInProgressOrNotFoundResponse()
    elif trade_status == TradeStatus.TRADE_FAILED:
        return TradeFailedResponse()
    elif trade_status == TradeStatus.TRADE_SUCCESSFUL:
        return TradeSuccessfulResponse()
    else:
        raise ValueError(f"TradeStatus {trade_status=} is not an implemented response.")


def check_trade_status(
    request: StatusRequest, web3_provider: Web3Provider, algorithm_repository: AlgorithmRepository
) -> TradeStatus:
    try:
        return retrieve_trade_status(request, web3_provider, algorithm_repository=algorithm_repository)
    except TransactionNotFound:
        logger.info(f"Couldn't find transaction receipt for {request.transaction_hash=}")

        return TradeStatus.TRADE_IN_PROGRESS_OR_NOT_FOUND
    except TimeExhausted:
        logger.info(f"Couldn't find transaction receipt for {request.transaction_hash=}")

        return TradeStatus.TRADE_IN_PROGRESS_OR_NOT_FOUND


def retrieve_trade_status(
    request: StatusRequest, web3_provider: Web3Provider, algorithm_repository: AlgorithmRepository
) -> TradeStatus:
    logger.info(f"Retrieving transaction status for {request.transaction_hash=}")
    receipt = _get_receipt(request, web3_provider, algorithm_repository=algorithm_repository)
    logger.info(f"Retrieved transaction receipt. {request.transaction_hash=} {receipt=}")

    if receipt["status"] == 1:
        return TradeStatus.TRADE_SUCCESSFUL

    return TradeStatus.TRADE_FAILED


def _get_receipt(
    request: StatusRequest, web3_provider: Web3Provider, algorithm_repository: AlgorithmRepository
) -> TxReceipt:
    algorithm = algorithm_repository.get_algorithm(request.algorithm_id.public_address)
    if algorithm is None:
        raise ValueError(f"Failed to retrieve algorithm for request, algorithm-id:[{request.algorithm_id}].")

    if request.timeout_in_seconds == 0:
        return _get_transaction_receipt(request.transaction_hash, web3_provider.get_web3(algorithm.chain_id))

    return _wait_for_transaction_receipt(
        request.transaction_hash, request.timeout_in_seconds, web3_provider.get_web3(algorithm.chain_id)
    )


def _wait_for_transaction_receipt(transaction: TransactionHash, timeout_in_seconds: int, w3: Web3) -> TxReceipt:
    return w3.eth.wait_for_transaction_receipt(HexBytes(transaction.value), timeout=timeout_in_seconds)


def _get_transaction_receipt(transaction: TransactionHash, w3: Web3) -> TxReceipt:
    return w3.eth.get_transaction_receipt(HexBytes(transaction.value))


async def background_task_check_tx_status(
    trade: Trade, algorithm_id: AlgorithmId, transaction_hash: TransactionHash, container: Container
):
    response = None
    try:
        for attempt_nr in range(7):
            try:
                done, response = await retrieve_status_attempt(algorithm_id, attempt_nr, container, transaction_hash)
                if done:
                    logger.info(f"Successfully retrieved trade status. {algorithm_id=} {transaction_hash=} {response=}")
                    return
            except Exception as e:
                logger.warning(
                    f"Error retrieving trade status. {algorithm_id=} {transaction_hash=} {e=}", exc_info=True
                )

        logger.critical(f"Was not successful in retrieving trade status. {algorithm_id=} {transaction_hash=}")
    finally:
        # Reset the algorithm_nonce if the tx was not successful
        if not isinstance(response, TradeSuccessfulResponse):
            await reset_algorithm_nonce(trade=trade, container=container)


async def reset_algorithm_nonce(trade: Trade, container: Container):
    nonce_repository: NonceRepository = container[NonceRepository]
    nonce_repository.reset_nonce(trade=trade)


async def retrieve_status_attempt(
    algorithm_id: AlgorithmId, attempt_nr: int, container: Container, transaction_hash: TransactionHash
) -> Tuple[bool, TradeStatusResponse]:
    response = await handle_status_request(
        request=StatusRequest(algorithm_id=algorithm_id, transaction_hash=transaction_hash, timeout_in_seconds=0),
        web3_provider=container[Web3Provider],
        trading_transaction_repository=container[TransactionRepository],
        algorithm_repository=container[AlgorithmRepository],
    )

    if isinstance(response, TradeInProgressOrNotFoundResponse):
        sleep_time = int(get_env_force(EnvVar.TASK_CHECK_TX_STATUS_SLEEP_TIME, "5"))
        wait_time_it = sleep_time * pow(2, attempt_nr)  # exponential back off
        logger.info(
            f"Tried to retrieve trade status, sleeping for {wait_time_it} seconds and trying again. {algorithm_id=} {transaction_hash=}"
        )
        await asyncio.sleep(wait_time_it)
        return False, response

    return True, response
