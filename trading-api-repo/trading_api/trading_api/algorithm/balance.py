import logging
import math
from decimal import Decimal

from eth_typing import ChecksumAddress
from web3.contract import Contract

from trading_api.algorithm.models.algorithm import Algorithm
from trading_api.algorithm.models.balance import (
    AlgorithmBalance,
    AlgorithmBalanceResponse,
    AlgorithmBalanceV2,
    RelativeAmount,
    TotalSupply,
)
from trading_api.algorithm.models.trade import BlockChainError
from trading_api.algorithm.services.web3 import Web3Provider

logger = logging.getLogger(__name__)

BC_INT_OFFSET = int(math.pow(10, 18))
BC_INT_OFFSET_FMT = ".18f"


def handle_balance_request(algorithm: Algorithm, w3: Web3Provider) -> AlgorithmBalanceResponse:
    contract = w3.get_trading_contract(algorithm=algorithm)
    try:
        supply, ratio = _get_algorithm_balance(contract), _get_balance_ratio(contract)
    except Exception as e:
        return handle_blockchain_error(e, algorithm.trading_contract_address)

    return AlgorithmBalance(supply=supply, ratio=ratio)


def handle_balance_request_v2(algorithm: Algorithm, w3: Web3Provider) -> AlgorithmBalanceResponse:
    contract = w3.get_trading_contract(algorithm=algorithm)
    try:
        supply = _get_algorithm_balance(contract)
    except Exception as e:
        return handle_blockchain_error(e, algorithm.trading_contract_address)

    return AlgorithmBalanceV2(supply=supply)


def handle_blockchain_error(error: Exception, trading_contract_address: ChecksumAddress) -> BlockChainError:
    logger.error(f"Error requesting balance. {trading_contract_address=}  {error=}")

    return BlockChainError(algorithm_id={"public_address": trading_contract_address})


def _get_algorithm_balance(contract: Contract) -> TotalSupply:
    amount = contract.functions.getTotalSupply().call()
    return TotalSupply(amount=amount)


def _get_balance_ratio(contract: Contract) -> RelativeAmount:
    amount = Decimal(contract.functions.getRatioPairedToken().call()) / BC_INT_OFFSET
    return RelativeAmount(amount=f"{amount:{BC_INT_OFFSET_FMT}}")
