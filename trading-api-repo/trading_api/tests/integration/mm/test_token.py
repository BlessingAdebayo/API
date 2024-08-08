from tests.utils import load_stub


def test_token_authorized(mm_app_int):
    request = load_stub("body-for-system-login.json")

    response = mm_app_int.client.post("/api/avatea/token", data=request)

    assert response.status_code == 200
    assert "access_token" in response.json()


def test_token_not_authorized(mm_app_int):
    request = load_stub("body-for-algorithm-login.json")

    response = mm_app_int.client.post("/api/avatea/token", data=request)

    assert response.status_code == 401
