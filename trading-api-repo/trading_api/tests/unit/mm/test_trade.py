from mm.data.repositories import InMemoryTradeRepository, InMemoryWalletKeyRepository
from mm.data.services import StubTransactionService
from mm.domain.repositories import TradeRepository, WalletKeyRepository
from mm.domain.services import TransactionService
from tests.unit.mm.utils import assert_status_code, make_pair, make_trade


def test_create_trade(mm_app_unit):
    tx_hash, wallet, contract = (
        "0x0000000000000000000000000000000000000000000000000000000000000000",
        "0x1111111111111111111111111111111111111111111111111111111111111111",
        "0x2222222222222222222222222222222222222222222222222222222222222222",
    )
    tx_service: StubTransactionService = mm_app_unit.container[TransactionService]
    tx_service.hashes.append(tx_hash)
    trades: InMemoryTradeRepository = mm_app_unit.container[TradeRepository]
    keys: InMemoryWalletKeyRepository = mm_app_unit.container[WalletKeyRepository]
    keys.upsert(pair=make_pair(wallet=wallet, contract=contract))

    response = mm_app_unit.client.post(
        "/api/avatea/trades",
        json={
            "contract": contract,
            "chain": "RTN",
            "type": "BUY",
            "amounts": [],
            "addresses": [],
            "slippage": "0.5",
            "exchange": "PANCAKESWAP",
        },
    )

    assert_status_code(200, response)
    assert response.json()["transaction_hash"] == tx_hash
    trade = trades.get(tx_hash)
    assert trade.hash == tx_hash
    assert trade.contract == contract


def test_retrieve_trade(mm_app_unit):
    trades: InMemoryTradeRepository = mm_app_unit.container[TradeRepository]
    expected_trade1 = make_trade(
        hash="0x1000000000000000000000000000000000000000000000000000000000000000",
        contract="0x0000000000000000000000000000000000000000000000000000000000000001",
    )
    expected_trade2 = make_trade(
        hash="0x2000000000000000000000000000000000000000000000000000000000000000",
        contract="0x0000000000000000000000000000000000000000000000000000000000000002",
    )
    trades.memory[expected_trade1.hash] = expected_trade1
    trades.memory[expected_trade2.hash] = expected_trade2

    response = mm_app_unit.client.get("/api/avatea/trades")

    assert_status_code(200, response)
    data = response.json()
    assert len(data["trades"]) == 2
    actual_trade1 = data["trades"][0]
    actual_trade2 = data["trades"][1]
    assert expected_trade1.hash == actual_trade1["hash"]
    assert expected_trade1.contract == actual_trade1["contract"]
    assert expected_trade1.slippage == actual_trade1["slippage"]
    assert expected_trade1.status == actual_trade1["status"]
    assert expected_trade1.type == actual_trade1["type"]
    assert expected_trade1.addresses == actual_trade1["addresses"]
    assert expected_trade1.amounts == actual_trade1["amounts"]
    assert expected_trade2.hash == actual_trade2["hash"]
    assert expected_trade2.contract == actual_trade2["contract"]
    assert expected_trade2.slippage == actual_trade2["slippage"]
    assert expected_trade2.status == actual_trade2["status"]
    assert expected_trade2.type == actual_trade2["type"]
    assert expected_trade2.addresses == actual_trade2["addresses"]
    assert expected_trade2.amounts == actual_trade2["amounts"]


def test_retrieve_trades_for_contract(mm_app_unit):
    trades: InMemoryTradeRepository = mm_app_unit.container[TradeRepository]
    expected_trade1 = make_trade(
        hash="0x1000000000000000000000000000000000000000000000000000000000000000",
        contract="0x0000000000000000000000000000000000000000000000000000000000000001",
    )
    expected_trade2 = make_trade(
        hash="0x2000000000000000000000000000000000000000000000000000000000000000",
        contract="0x0000000000000000000000000000000000000000000000000000000000000002",
    )
    trades.memory[expected_trade1.hash] = expected_trade1
    trades.memory[expected_trade2.hash] = expected_trade2

    response = mm_app_unit.client.get(f"/api/avatea/trades/{expected_trade1.contract}")

    assert_status_code(200, response)
    data = response.json()
    assert len(data["trades"]) == 1
    actual_trade1 = data["trades"][0]
    assert expected_trade1.hash == actual_trade1["hash"]
    assert expected_trade1.contract == actual_trade1["contract"]
    assert expected_trade1.slippage == actual_trade1["slippage"]
    assert expected_trade1.status == actual_trade1["status"]
    assert expected_trade1.type == actual_trade1["type"]
    assert expected_trade1.addresses == actual_trade1["addresses"]
    assert expected_trade1.amounts == actual_trade1["amounts"]
