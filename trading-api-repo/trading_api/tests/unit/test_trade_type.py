from trading_api.algorithm.models.trade import TradeType, TradeTypeLower
from trading_api.algorithm_routes_v2 import is_buy_trade_type


def test_is_buy_trade_type():
    assert is_buy_trade_type(TradeType.BUY) is True
    assert is_buy_trade_type(TradeType.SELL) is False
    assert is_buy_trade_type(TradeTypeLower.BUY) is True
    assert is_buy_trade_type(TradeTypeLower.SELL) is False
