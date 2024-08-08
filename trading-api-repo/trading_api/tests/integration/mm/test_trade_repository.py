from datetime import datetime

from mm.data.repositories import MongoTradeRepository
from mm.domain.repositories import TradeRepository
from tests.unit.mm.utils import make_trade


def test_add_to_trade_repository(mm_app_int):
    trades: MongoTradeRepository = mm_app_int.container[TradeRepository]
    expected_trade1 = make_trade(hash="0x1111111111111111111111111111111111111111111111111111111111111111")
    expected_trade2 = make_trade(hash="0x2222222222222222222222222222222222222222222222222222222222222222")
    trades.upsert(record=expected_trade1)
    trades.upsert(record=expected_trade2)

    actual_trade1 = trades.get(hash=expected_trade1.hash)
    actual_trade2 = trades.get(hash=expected_trade2.hash)

    assert actual_trade1.hash != actual_trade2.hash
    assert actual_trade2.hash == expected_trade2.hash
    assert actual_trade2.contract == expected_trade2.contract
    assert actual_trade2.slippage == expected_trade2.slippage
    assert actual_trade2.status == expected_trade2.status
    assert actual_trade2.type == expected_trade2.type
    assert isinstance(actual_trade2.created_at, datetime)
    assert isinstance(actual_trade2.updated_at, datetime)
