from hexbytes import HexBytes

from trading_api.algorithm.models.algorithm import AlgorithmId, AlgorithmTransaction
from trading_api.algorithm.models.crypto import TransactionHash
from trading_api.algorithm.models.trade import BuyTrade, BuyTradeV2, MultiTokenTrade, SellTrade, SellTradeV2, Trade
from trading_api.algorithm.repositories.lock import SYMBOL_V1


def create_algorithm_transaction(algorithm_id: AlgorithmId, transaction_hash: HexBytes) -> AlgorithmTransaction:
    return AlgorithmTransaction(
        algorithm_id=algorithm_id, transaction_hash=(TransactionHash(value=transaction_hash.hex()))
    )


def get_lock_symbol(trade: Trade) -> str:
    if isinstance(trade, SellTrade) or isinstance(trade, BuyTrade):
        return SYMBOL_V1

    if isinstance(trade, BuyTradeV2) or isinstance(trade, SellTradeV2):
        return trade.symbol

    raise ValueError("Cannot handle this type of trade.")
