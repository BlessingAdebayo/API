from typing import Iterable

from web3 import Web3

from tests.utils import load_stub
from trading_api.algorithm.models.algorithm import AlgorithmInDB
from trading_api.algorithm.repositories.algorithm import AlgorithmRepository


def test_register_algorithm(app_inst, system_access_header):
    request = load_stub("body-for-algorithm-register.json")
    trading_contract_adress = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"

    response = app_inst.client.post(
        f"/api/v1/algorithms/{trading_contract_adress}/register", json=request, headers=system_access_header
    )

    assert response.status_code == 200
    assert response.json() == {"status": "OK"}

    repo: AlgorithmRepository = app_inst.container[AlgorithmRepository]
    algorithm = repo.get_algorithm(trading_contract_adress)
    assert algorithm.trading_contract_address == trading_contract_adress
    assert algorithm.hashed_password != request["unhashed_password"]
    assert algorithm.disabled is False


def test_register_algorithm_again(app_inst, system_access_header):
    request = load_stub("body-for-algorithm-register.json")
    trading_contract_address = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
    controller_wallet_address = "0xf05ef1c844e39757b6f94f89427b1ac302fcae1b"

    response = app_inst.client.post(
        f"/api/v1/algorithms/{trading_contract_address}/register", json=request, headers=system_access_header
    )

    assert response.status_code == 200
    assert response.json() == {"status": "OK"}

    repo: AlgorithmRepository = app_inst.container[AlgorithmRepository]
    algorithm = repo.get_algorithm(trading_contract_address)
    hashed_pw_first_request = algorithm.hashed_password
    assert algorithm.trading_contract_address == trading_contract_address
    assert algorithm.controller_wallet_address == controller_wallet_address
    assert algorithm.hashed_password != request["unhashed_password"]
    assert algorithm.disabled is False

    request["unhashed_password"] = "super-secret"
    response = app_inst.client.post(
        f"/api/v1/algorithms/{trading_contract_address}/register", json=request, headers=system_access_header
    )

    assert response.status_code == 200
    assert response.json() == {"status": "OK"}

    repo: AlgorithmRepository = app_inst.container[AlgorithmRepository]
    algorithm = repo.get_algorithm(trading_contract_address)
    assert algorithm.trading_contract_address == trading_contract_address
    assert algorithm.hashed_password != hashed_pw_first_request
    assert algorithm.disabled is False

    algorithms = repo.all_algorithms()
    assert isinstance(algorithms, Iterable)
    algorithms = list(algorithms)
    assert all(isinstance(algo, AlgorithmInDB) for algo in algorithms)
    assert len(algorithms) == 1
    assert algorithms[0].trading_contract_address == trading_contract_address
