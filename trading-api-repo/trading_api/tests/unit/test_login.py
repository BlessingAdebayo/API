from tests.utils import load_stub
from trading_api.algorithm.repositories.algorithm import AlgorithmRepository
from trading_api.core.container import default_user_v1


def test_login_user_get_token(app_inst):
    app_inst.container[AlgorithmRepository].upsert_algorithm(default_user_v1())
    request = load_stub("body-for-algorithm-login.json")

    response = app_inst.client.post("/api/v1/login", data=request)
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_login_user_denied(app_inst):
    request = load_stub("body-for-algorithm-login-unauthorized.json")

    response = app_inst.client.post("/api/v1/login", data=request)

    assert response.status_code == 401


def test_login_user_use_token(access_header_v1, app_inst):
    response = app_inst.client.get("/api/v1")
    assert response.status_code == 401

    response = app_inst.client.get("/api/v1", headers=access_header_v1)
    assert response.status_code == 200
