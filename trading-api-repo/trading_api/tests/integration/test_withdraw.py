import pytest
from fastapi import status

from tests.utils import ADDR2 as RECIPIENT
from tests.utils import ADDR3 as EMPTY
from tests.utils import load_stub, make_algorithm
from trading_api.algorithm.models.algorithm import Algorithm
from trading_api.algorithm.repositories.algorithm import AlgorithmRepository

SKIP_REASON = "We don't test withdrawal due to not wanting to create algorithms and their private keys in AWS."


@pytest.mark.skip(SKIP_REASON)
def test_withdraw_funds(app_inst, system_access_header, km_service):
    json = load_stub("body-for-system-controller-wallet-funds-withdrawal.json")
    algorithm_repository = app_inst.container[AlgorithmRepository]
    algorithm = make_algorithm()
    algorithm_repository.upsert_algorithm(algorithm)
    endpoint = _make_withdraw_endpoint(algorithm)

    response = app_inst.client.post(endpoint, headers=system_access_header, json=json)

    assert response.status_code == status.HTTP_200_OK
    json = response.json()
    assert json["algorithm"] == algorithm
    assert json["recipient"] == RECIPIENT


@pytest.mark.skip(SKIP_REASON)
def test_withdraw_funds_nonexistent_algorithm(app_inst, system_access_header, km_service):
    json = load_stub("body-for-system-controller-wallet-funds-withdrawal.json")
    algorithm = make_algorithm()
    endpoint = _make_withdraw_endpoint(algorithm)

    response = app_inst.client.post(endpoint, headers=system_access_header, json=json)

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.skip(SKIP_REASON)
def test_withdraw_funds_disabled_algorithm(app_inst, system_access_header, km_service):
    json = load_stub("body-for-system-controller-wallet-funds-withdrawal.json")
    algorithm_repository = app_inst.container[AlgorithmRepository]
    algorithm = make_algorithm(disabled=True)
    algorithm_repository.upsert_algorithm(algorithm)
    endpoint = _make_withdraw_endpoint(algorithm)

    response = app_inst.client.post(endpoint, headers=system_access_header, json=json)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.skip(SKIP_REASON)
def test_withdraw_funds_empty_wallet(app_inst, system_access_header, km_service):
    json = load_stub("body-for-system-controller-wallet-funds-withdrawal.json")
    algorithm_repository = app_inst.container[AlgorithmRepository]
    algorithm = make_algorithm(controller_wallet_address=EMPTY)
    algorithm_repository.upsert_algorithm(algorithm)
    endpoint = _make_withdraw_endpoint(algorithm)

    response = app_inst.client.post(endpoint, headers=system_access_header, json=json)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def _make_withdraw_endpoint(algorithm: Algorithm):
    return f"/api/v1/algorithms/{algorithm.trading_contract_address}/withdraw"
