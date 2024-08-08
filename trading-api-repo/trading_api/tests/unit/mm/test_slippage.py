from mm.data.services.trade import _to_raw_amount
from mm.domain.models import Slippage


def test_raw_slippage_amount():
    slippage_min = Slippage("0")
    slippage_max = Slippage("1")
    slippage_hi = Slippage("0.99")
    slippage_lo = Slippage("0.01")

    assert _to_raw_amount(slippage_min) == 0
    assert _to_raw_amount(slippage_max) == 1000000000000000000
    assert _to_raw_amount(slippage_hi) == 990000000000000000
    assert _to_raw_amount(slippage_lo) == 10000000000000000
