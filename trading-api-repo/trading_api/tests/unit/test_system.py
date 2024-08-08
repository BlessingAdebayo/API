from tests.utils import load_stub, make_algorithm
from trading_api.algorithm.repositories.algorithm import AlgorithmRepository


def test_register_algorithm(app_inst, system_access_header):
    payload = load_stub("body-for-algorithm-register.json")
    endpoint = f"/api/v1/algorithms/{payload['trading_contract_address']}/register"

    response = app_inst.client.post(endpoint, json=payload, headers=system_access_header)

    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "OK"


def test_disable_algorithm(app_inst, system_access_header):
    payload = load_stub("body-for-algorithm-disable.json")
    address = payload["trading_contract_address"]
    algorithm_repository = app_inst.container[AlgorithmRepository]
    algorithm_repository.upsert_algorithm(make_algorithm(address))
    endpoint = f"/api/v1/algorithms/{address}/disable"

    response = app_inst.client.post(endpoint, json=payload, headers=system_access_header)

    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "OK"
    assert address in algorithm_repository.memory
    assert algorithm_repository.memory[address].disabled is True
