from tests.utils import load_stub


def test_get_ticker(app_inst, access_header_v1):
    endpoint = "/api/v1/ticker/0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82"
    expected = load_stub("response-ticker-pancakeswap.json")

    response = app_inst.client.get(endpoint, headers=access_header_v1)

    assert response.status_code == 200
    assert response.json() == expected


def test_get_ticker_list(app_inst, access_header_v1):
    endpoint = "/api/v1/ticker/"
    expected = load_stub("response-ticker-pancakeswap-list.json")

    response = app_inst.client.get(endpoint, headers=access_header_v1)

    assert response.status_code == 200
    assert response.json() == expected
