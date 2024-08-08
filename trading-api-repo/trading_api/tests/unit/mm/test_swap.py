import pytest

from mm.data.repositories import InMemorySwapRepository, InMemoryWalletKeyRepository
from mm.data.services import StubTransactionService
from mm.domain.repositories import SwapRepository, WalletKeyRepository
from mm.domain.services import TransactionService
from tests.unit.mm.utils import assert_status_code, make_pair, make_swap

DISABLED_TEMPORARILY = "Disabled temporarily because of legal reasons."


@pytest.mark.skip(DISABLED_TEMPORARILY)
def test_create_swap(mm_app_unit):
    tx_hash, wallet, contract, seller = (
        "0x0000000000000000000000000000000000000000000000000000000000000000",
        "0x1111111111111111111111111111111111111111111111111111111111111111",
        "0x3333333333333333333333333333333333333333333333333333333333333333",
        "0x4444444444444444444444444444444444444444444444444444444444444444",
    )
    tx_service: StubTransactionService = mm_app_unit.container[TransactionService]
    tx_service.hashes.append(tx_hash)
    swaps: InMemorySwapRepository = mm_app_unit.container[SwapRepository]
    keys: InMemoryWalletKeyRepository = mm_app_unit.container[WalletKeyRepository]
    keys.upsert(pair=make_pair(wallet=wallet, contract=contract))

    response = mm_app_unit.client.post(
        "/api/avatea/swaps",
        json={
            "contract": contract,
            "amounts": [],
            "addresses": [],
            "seller": seller,
            "exchange": "PANCAKESWAP",
        },
    )

    assert_status_code(200, response)
    assert response.json()["transaction_hash"] == tx_hash
    swap = swaps.get(tx_hash)
    assert swap.hash == tx_hash
    assert swap.contract == contract


@pytest.mark.skip(DISABLED_TEMPORARILY)
def test_retrieve_swap(mm_app_unit):
    swaps: InMemorySwapRepository = mm_app_unit.container[SwapRepository]
    expected_swap1 = make_swap(
        hash="0x1000000000000000000000000000000000000000000000000000000000000000",
        contract="0x0000000000000000000000000000000000000000000000000000000000000001",
    )
    expected_swap2 = make_swap(
        hash="0x2000000000000000000000000000000000000000000000000000000000000000",
        contract="0x0000000000000000000000000000000000000000000000000000000000000002",
    )
    swaps.memory[expected_swap1.hash] = expected_swap1
    swaps.memory[expected_swap2.hash] = expected_swap2

    response = mm_app_unit.client.get("/api/avatea/swaps")

    assert_status_code(200, response)
    data = response.json()
    assert len(data["swaps"]) == 2
    actual_swap1 = data["swaps"][0]
    actual_swap2 = data["swaps"][1]
    assert expected_swap1.hash == actual_swap1["hash"]
    assert expected_swap1.contract == actual_swap1["contract"]
    assert expected_swap1.status == actual_swap1["status"]
    assert expected_swap1.amounts == actual_swap1["amounts"]
    assert expected_swap1.addresses == actual_swap1["addresses"]
    assert expected_swap1.seller == actual_swap1["seller"]
    assert expected_swap2.hash == actual_swap2["hash"]
    assert expected_swap2.contract == actual_swap2["contract"]
    assert expected_swap2.status == actual_swap2["status"]
    assert expected_swap2.amounts == actual_swap2["amounts"]
    assert expected_swap2.addresses == actual_swap2["addresses"]
    assert expected_swap2.seller == actual_swap2["seller"]


@pytest.mark.skip(DISABLED_TEMPORARILY)
def test_retrieve_swaps_for_contract(mm_app_unit):
    swaps: InMemorySwapRepository = mm_app_unit.container[SwapRepository]
    expected_swap1 = make_swap(
        hash="0x1000000000000000000000000000000000000000000000000000000000000000",
        contract="0x0000000000000000000000000000000000000000000000000000000000000001",
    )
    expected_swap2 = make_swap(
        hash="0x2000000000000000000000000000000000000000000000000000000000000000",
        contract="0x0000000000000000000000000000000000000000000000000000000000000002",
    )
    swaps.memory[expected_swap1.hash] = expected_swap1
    swaps.memory[expected_swap2.hash] = expected_swap2

    response = mm_app_unit.client.get(f"/api/avatea/swaps/{expected_swap1.contract}")

    assert_status_code(200, response)
    data = response.json()
    assert len(data["swaps"]) == 1
    actual_swap1 = data["swaps"][0]
    assert expected_swap1.hash == actual_swap1["hash"]
    assert expected_swap1.contract == actual_swap1["contract"]
    assert expected_swap1.status == actual_swap1["status"]
    assert expected_swap1.amounts == actual_swap1["amounts"]
    assert expected_swap1.addresses == actual_swap1["addresses"]
    assert expected_swap1.seller == actual_swap1["seller"]
