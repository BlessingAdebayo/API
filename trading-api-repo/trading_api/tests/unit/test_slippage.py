from decimal import Decimal

from trading_api.algorithm.models.trade import Slippage


def test_raw_slippage_amount():
    slippage_lo = Slippage(amount=Decimal("0.01"))
    slippage_hi = Slippage(amount=Decimal("0.99"))

    assert slippage_lo.raw_amount == 990000000000000000
    assert slippage_hi.raw_amount == 10000000000000000
