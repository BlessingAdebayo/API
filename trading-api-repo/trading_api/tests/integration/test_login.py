from pprint import pprint

from tests.utils import load_stub
from trading_api.algorithm.repositories.algorithm import AlgorithmRepository
from trading_api.core.container import default_user_v1


def test_login_unauthorized(app_inst):
    request = load_stub("body-for-algorithm-login.json")

    response = app_inst.client.post("/api/v1/login", data=request)

    assert response.status_code == 401


def test_login_authorized(app_inst):
    user = default_user_v1()
    app_inst.container[AlgorithmRepository].upsert_algorithm(user)
    request = load_stub("body-for-algorithm-login.json")

    response = app_inst.client.post("/api/v1/login", data=request)

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_system_login_unauthorized(app_inst):
    request = load_stub("body-for-algorithm-login.json")

    response = app_inst.client.post("/api/v1/login", data=request)

    assert response.status_code == 401


def test_system_login_authorized(app_inst):
    request = load_stub("body-for-system-login.json")

    response = app_inst.client.post("/api/v1/login", data=request)

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_system_login_token(app_inst, system_access_header):
    request = load_stub("body-for-algorithm-register.json")
    trading_contract_address = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"

    response = app_inst.client.post(f"/api/v1/algorithms/{trading_contract_address}/register", json=request)

    assert response.status_code == 401

    response = app_inst.client.post(
        f"/api/v1/algorithms/{trading_contract_address}/register", json=request, headers=system_access_header
    )

    pprint(response.json())
    assert response.status_code == 200
    assert response.json() == {"status": "OK"}
