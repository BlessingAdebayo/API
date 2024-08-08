from tests.utils import load_stub, make_algorithm_db
from trading_api.algorithm.repositories.algorithm import AlgorithmRepository


def test_disable_algorithm(app_inst, system_access_header):
    algorithm_repository = app_inst.container[AlgorithmRepository]
    payload = load_stub("body-for-algorithm-disable.json")
    address = payload["trading_contract_address"]
    algorithm_repository.upsert_algorithm(make_algorithm_db(address))

    response = app_inst.client.post(f"/api/v1/algorithms/{address}/disable", json=payload, headers=system_access_header)

    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "OK"
    algorithm = algorithm_repository.get_algorithm(address)
    assert algorithm is not None
    assert algorithm.disabled is True
