import pytest

from trading_api.algorithm.services.web3 import Web3Provider


@pytest.mark.skip(reason="Fails on calling trading contract functions.")
def test_algorithm_balance_request(app_inst, access_header_v1, in_memory_w3):
    app_inst.container.set_dependency(Web3Provider, in_memory_w3)

    expected = {"supply": {"amount": 0}, "ratio": {"amount": 0}}

    response = app_inst.client.get("/api/v1/balance", headers=access_header_v1)

    assert response.status_code == 200
    assert response.json() == expected
