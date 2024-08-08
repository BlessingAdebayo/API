import pytest

from tests.utils import load_stub
from trading_api.algorithm.services.web3 import Web3Provider


@pytest.mark.skip("flaky")
def test_trade_status_api(app_inst, http_w3, access_header_v1):
    app_inst.container[Web3Provider] = http_w3
    request = load_stub("body-for-algorithm-status.json")

    response = app_inst.client.post("/api/v1/status", json=request, headers=access_header_v1)

    assert response.status_code == 202
    assert response.json() == {
        "code": "TRADE_IN_PROGRESS_OR_NOT_FOUND",
        "message": "Trade is in progress or cannot be found.",
    }
