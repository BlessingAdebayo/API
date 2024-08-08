import logging
from decimal import Decimal

from eth_typing import ChecksumAddress
from eth_utils import from_wei
from web3.contract import Contract

from trading_api.algorithm.models.algorithm import Algorithm, AlgorithmId
from trading_api.algorithm.models.quote import PriceQuote, PriceQuoteResponse
from trading_api.algorithm.models.trade import BlockChainError
from trading_api.algorithm.services.web3 import Web3Provider

logger = logging.getLogger(__name__)


def handle_price_quote_request(symbol: str, algorithm: Algorithm, w3: Web3Provider) -> PriceQuoteResponse:
    contract = w3.get_trading_contract_tools(algorithm=algorithm)

    try:
        price = _get_token_price(symbol, algorithm, contract)
    except Exception as e:
        return handle_blockchain_error(e, algorithm.trading_contract_address)

    return PriceQuote(symbol=symbol.upper(), price=price)


def handle_blockchain_error(error: Exception, trading_contract_address: ChecksumAddress) -> BlockChainError:
    logger.error(f"Error requesting price quote. {trading_contract_address=}  {error=}")

    return BlockChainError(algorithm_id=AlgorithmId(public_address=trading_contract_address))


def _get_token_price(symbol: str, algorithm: Algorithm, contract: Contract) -> Decimal:
    price = contract.functions.getTokenPrice(algorithm.trading_contract_address, symbol.upper()).call()
    return Decimal(from_wei(price, "ether"))
