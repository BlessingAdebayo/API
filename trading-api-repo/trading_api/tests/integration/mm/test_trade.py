from mm.data.repositories import MongoTradeRepository
from mm.domain.repositories import TradeRepository
from tests.unit.mm.utils import assert_status_code, make_trade


def test_retrieve_trades(mm_app_int):
    trades: MongoTradeRepository = mm_app_int.container[TradeRepository]
    expected_trade1 = make_trade(hash="0x1111111111111111111111111111111111111111111111111111111111111111")
    expected_trade2 = make_trade(hash="0x2222222222222222222222222222222222222222222222222222222222222222")
    expected_trade3 = make_trade(hash="0x3333333333333333333333333333333333333333333333333333333333333333")
    trades.upsert(record=expected_trade1)
    trades.upsert(record=expected_trade2)
    trades.upsert(record=expected_trade3)

    response = mm_app_int.client.get("/api/avatea/trades", params={"skip": 1, "limit": 1})

    assert_status_code(200, response)
    data = response.json()
    assert len(data["trades"]) == 1
    assert data["page"] == 1
    assert data["page_size"] == 1
    assert data["total_pages"] == 3
    assert data["total"] == 3
    actual_trade2 = data["trades"].pop()
    assert expected_trade2.hash == actual_trade2["hash"]
    assert expected_trade2.contract == actual_trade2["contract"]
    assert expected_trade2.slippage == actual_trade2["slippage"]
    assert expected_trade2.status == actual_trade2["status"]
    assert expected_trade2.type == actual_trade2["type"]


def test_retrieve_trades_for_contract(mm_app_int):
    trades: MongoTradeRepository = mm_app_int.container[TradeRepository]
    contract_address, hash_1, hash_2 = (
        "0x0000000000000000000000000000000000000000000000000000000000000000",
        "0x1111111111111111111111111111111111111111111111111111111111111111",
        "0x2222222222222222222222222222222222222222222222222222222222222222",
    )
    expected_trade1 = make_trade(hash=hash_1, contract=contract_address)
    expected_trade2 = make_trade(hash=hash_2, contract=contract_address)
    expected_trade3 = make_trade()
    trades.upsert(record=expected_trade1)
    trades.upsert(record=expected_trade2)
    trades.upsert(record=expected_trade3)

    response = mm_app_int.client.get(f"/api/avatea/trades/{contract_address}")

    assert_status_code(200, response)
    data = response.json()
    assert len(data["trades"]) == 2
    addresses = [trade["hash"] for trade in data["trades"]]
    assert addresses == [hash_1, hash_2]
