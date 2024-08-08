import pytest

from mm.data.repositories import MongoSwapRepository
from mm.domain.repositories import SwapRepository
from tests.unit.mm.utils import assert_status_code, make_swap

DISABLED_TEMPORARILY = "Disabled temporarily because of legal reasons."


@pytest.mark.skip(DISABLED_TEMPORARILY)
def test_retrieve_swaps(mm_app_int):
    swaps: MongoSwapRepository = mm_app_int.container[SwapRepository]
    expected_swap1 = make_swap(hash="0x1111111111111111111111111111111111111111111111111111111111111111")
    expected_swap2 = make_swap(hash="0x2222222222222222222222222222222222222222222222222222222222222222")
    expected_swap3 = make_swap(hash="0x3333333333333333333333333333333333333333333333333333333333333333")
    swaps.upsert(record=expected_swap1)
    swaps.upsert(record=expected_swap2)
    swaps.upsert(record=expected_swap3)

    response = mm_app_int.client.get("/api/avatea/swaps", params={"skip": 1, "limit": 1})

    assert_status_code(200, response)
    data = response.json()
    assert len(data["swaps"]) == 1
    assert data["page"] == 1
    assert data["page_size"] == 1
    assert data["total_pages"] == 3
    assert data["total"] == 3
    actual_swap2 = data["swaps"].pop()
    assert expected_swap2.hash == actual_swap2["hash"]
    assert expected_swap2.contract == actual_swap2["contract"]
    assert expected_swap2.status == actual_swap2["status"]
    assert expected_swap2.amounts == actual_swap2["amounts"]
    assert expected_swap2.addresses == actual_swap2["addresses"]
    assert expected_swap2.seller == actual_swap2["seller"]


@pytest.mark.skip(DISABLED_TEMPORARILY)
def test_retrieve_swaps_for_contract(mm_app_int):
    swaps: MongoSwapRepository = mm_app_int.container[SwapRepository]
    contract_address, hash_1, hash_2 = (
        "0x0000000000000000000000000000000000000000000000000000000000000000",
        "0x1111111111111111111111111111111111111111111111111111111111111111",
        "0x2222222222222222222222222222222222222222222222222222222222222222",
    )
    expected_swap1 = make_swap(hash=hash_1, contract=contract_address)
    expected_swap2 = make_swap(hash=hash_2, contract=contract_address)
    expected_swap3 = make_swap()
    swaps.upsert(record=expected_swap1)
    swaps.upsert(record=expected_swap2)
    swaps.upsert(record=expected_swap3)

    response = mm_app_int.client.get(f"/api/avatea/swaps/{contract_address}")

    assert_status_code(200, response)
    data = response.json()
    assert len(data["swaps"]) == 2
    addresses = [swap["hash"] for swap in data["swaps"]]
    assert addresses == [hash_1, hash_2]
