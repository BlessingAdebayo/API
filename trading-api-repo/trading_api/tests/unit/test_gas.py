import os

from trading_api.algorithm.models.crypto import ChainId
from trading_api.algorithm.trade import estimated_gas_factor_for_chain


def test_get_estimated_gas_RNB():
    os.environ["ESTIMATED_GAS_FACTOR_RTN"] = "11"
    os.environ["ESTIMATED_GAS_FACTOR_BSC"] = "12"
    os.environ["ESTIMATED_GAS_FACTOR"] = "13"

    assert estimated_gas_factor_for_chain(ChainId.RTN) == 11
    assert estimated_gas_factor_for_chain(ChainId.BSC) == 12
    assert estimated_gas_factor_for_chain("unknownchain") == 13

    del os.environ["ESTIMATED_GAS_FACTOR_RTN"]
    del os.environ["ESTIMATED_GAS_FACTOR"]
    assert estimated_gas_factor_for_chain(ChainId.RTN) == 20
    assert estimated_gas_factor_for_chain("unknownchain") == 15
