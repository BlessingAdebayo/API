from datetime import datetime

from mm.data.repositories import MongoSwapRepository
from mm.domain.repositories import SwapRepository
from tests.unit.mm.utils import make_swap


def test_add_to_swap_repository(mm_app_int):
    swaps: MongoSwapRepository = mm_app_int.container[SwapRepository]
    expected_swap1 = make_swap(hash="0x1111111111111111111111111111111111111111111111111111111111111111")
    expected_swap2 = make_swap(hash="0x2222222222222222222222222222222222222222222222222222222222222222")
    swaps.upsert(record=expected_swap1)
    swaps.upsert(record=expected_swap2)

    actual_swap1 = swaps.get(hash=expected_swap1.hash)
    actual_swap2 = swaps.get(hash=expected_swap2.hash)

    assert actual_swap1.hash != actual_swap2.hash
    assert actual_swap2.hash == expected_swap2.hash
    assert actual_swap2.contract == expected_swap2.contract
    assert actual_swap2.status == expected_swap2.status
    assert actual_swap2.amounts == expected_swap2.amounts
    assert actual_swap2.addresses == expected_swap2.addresses
    assert actual_swap2.seller == expected_swap2.seller
    assert isinstance(actual_swap2.created_at, datetime)
    assert isinstance(actual_swap2.updated_at, datetime)
