from mm.data.repositories import InMemoryWalletKeyRepository
from mm.data.services import StubTransactionService
from mm.domain.repositories import WalletKeyRepository
from mm.domain.services import TransactionService
from tests.unit.mm.utils import assert_status_code, make_pair


def test_create_stake_in_liquidity_maker(mm_app_unit):
    tx_hash, wallet, contract = (
        "0x0000000000000000000000000000000000000000000000000000000000000000",
        "0x1111111111111111111111111111111111111111111111111111111111111111",
        "0x2222222222222222222222222222222222222222222222222222222222222222",
    )
    tx_service: StubTransactionService = mm_app_unit.container[TransactionService]
    tx_service.hashes.append(tx_hash)
    keys: InMemoryWalletKeyRepository = mm_app_unit.container[WalletKeyRepository]
    keys.upsert(pair=make_pair(wallet=wallet, contract=contract))

    response = mm_app_unit.client.post(
        "/api/avatea/stakes",
        json={
            "contract": contract,
            "amounts_base": [],
            "amounts_paired": [],
            "addresses_base": [],
            "addresses_paired": [],
            "slippage": 0.5,
            "exchange": "PANCAKESWAP",
        },
    )

    assert_status_code(200, response)
    assert response.json()["transaction_hash"] == tx_hash
