from mm.data.repositories import InMemoryTradeRepository, InMemoryWalletKeyRepository
from mm.domain.repositories import TradeRepository, WalletKeyRepository
from tests.unit.mm.utils import assert_status_code, make_pair, make_trade


def test_retrieve_transaction_status(mm_app_unit):
    trades: InMemoryTradeRepository = mm_app_unit.container[TradeRepository]
    keys: InMemoryWalletKeyRepository = mm_app_unit.container[WalletKeyRepository]
    tx_hash = "0x1111111111111111111111111111111111111111111111111111111111111111"
    wallet = "0x2222222222222222222222222222222222222222222222222222222222222222"
    contract = "0x3333333333333333333333333333333333333333333333333333333333333333"
    keys.upsert(make_pair(wallet=wallet, contract=contract))
    trade1 = make_trade(
        hash=tx_hash,
        contract=contract,
    )
    trades.upsert(trade1)

    response = mm_app_unit.client.get(
        f"/api/avatea/status/{trade1.hash}",
    )

    assert_status_code(200, response)
    assert response.json()["message"] == "TRANSACTION_SUCCESSFUL"
