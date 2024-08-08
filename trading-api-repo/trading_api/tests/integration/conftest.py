import logging
import os
from pathlib import Path

import pytest
import solcx
from fastapi import FastAPI
from starlette.testclient import TestClient
from web3 import Web3

from main import app
from tests import TEST_CONTRACT_VERSION
from tests.blockchain import compile_source_file, deploy_contract
from tests.utils import load_stub
from trading_api import (
    EnvNotSetException,
    EnvVar,
    Stage,
    algorithm_routes_v1,
    algorithm_routes_v2,
    get_env,
    get_env_force,
)
from trading_api.algorithm.models.crypto import ContractDetails
from trading_api.algorithm.repositories.algorithm import AlgorithmRepository
from trading_api.algorithm.repositories.key import MongoKeyRepository
from trading_api.algorithm.repositories.lock import AlgorithmLockRepository
from trading_api.algorithm.repositories.transaction import TransactionRepository
from trading_api.algorithm.services.kms import AWSKeyManagementService, KeyManagementService, LocalKeyManagementService
from trading_api.algorithm.services.web3 import HttpWeb3Provider
from trading_api.core.container import Container, default_user_v1, default_user_v2, di_container
from trading_api.core.repositories.mongo import BaseRepository, connect_mongo

logger = logging.getLogger(__name__)

CANT_TEST_KMS_YET = "We don't (yet) have an AWS KMS running for our integration tests.."


class App:
    def __init__(self, app_api: FastAPI, client: TestClient, container: Container):
        self.app = app_api
        self.client = client
        self.container = container

    app: FastAPI
    client: TestClient
    container: Container


@pytest.fixture
def w3():
    blockchain_http_url = get_env(EnvVar.WEB3_PROVIDER_ENDPOINT_RTN)
    w3 = Web3(Web3.HTTPProvider(blockchain_http_url))

    return w3


@pytest.fixture
def contract_account():
    contract_address = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
    private_key = "0x0000000000000000000000000000000000000000000000000000000000000001"
    return contract_address, private_key


@pytest.fixture
def developer_account():
    return "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF", ""


@pytest.fixture
def trading_contract(developer_account, contract_account, w3):
    """Returns a variable referencing the deployed trading contract

    Example usage:
    > count = trading_contract_var.functions.getCount().call()
    > pprint(trading_contract_var.all_functions())
    """
    sol_version = "0.6.6"
    solcx.install_solc(sol_version)
    solcx.set_solc_version(sol_version)

    base_path = Path(__file__).parent.parent.parent.parent.absolute()
    contract_source_path = (
        base_path / "mercor_smart_contracts" / TEST_CONTRACT_VERSION / "contracts" / "TradingContract.sol"
    )
    compiled_sol = compile_source_file(contract_source_path)

    contract_id = f"{contract_source_path}:TradingContract"
    contract_interface = compiled_sol[contract_id]

    contract_args = (
        "0x55d398326f99059fF775485246999027B3197955",  # _pairedToken
        "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",  # _baseToken
        10000,  # _maxTotalCap
        developer_account[0],  # _developerAddress
    )
    deploy_tx = {"from": contract_account[0], "value": 0, "nonce": w3.eth.get_transaction_count(contract_account[0])}
    contract_address = deploy_contract(w3, contract_interface, contract_args, deploy_tx)
    trading_contract_var = w3.eth.contract(address=contract_address, abi=contract_interface["abi"])

    return trading_contract_var


@pytest.fixture
def ecr_contract(contract_account, w3):
    sol_version = "0.6.6"
    solcx.install_solc(sol_version)
    solcx.set_solc_version(sol_version)

    base_path = Path(__file__).parent.parent.parent.parent.absolute()
    contract_source_path = (
        base_path / "mercor_smart_contracts" / TEST_CONTRACT_VERSION / "contracts" / "utils" / "Ecr.sol"
    )
    compiled_sol = compile_source_file(contract_source_path)

    contract_id = f"{contract_source_path}:Ecr"
    contract_interface = compiled_sol[contract_id]
    contract_args = ()
    deploy_tx = {"from": contract_account[0], "value": 0, "nonce": w3.eth.get_transaction_count(contract_account[0])}
    contract_address = deploy_contract(w3, contract_interface, contract_args, deploy_tx)

    return w3.eth.contract(address=contract_address, abi=contract_interface["abi"])


@pytest.fixture
def http_w3(contract_account, trading_contract, ecr_contract):
    # BSC is empty since we don't want to run against the real BSC in tests...
    return HttpWeb3Provider(
        "",
        get_env_force(EnvVar.WEB3_PROVIDER_ENDPOINT_RTN),
        ecr_contract_bsc=ContractDetails(ecr_contract.address, ecr_contract.abi),
        ecr_contract_rtn=ContractDetails(ecr_contract.address, ecr_contract.abi),
        private_key=contract_account[1],
    )


@pytest.fixture
def app_inst():
    container = Container()

    def constructor():
        return container

    app.dependency_overrides[di_container] = constructor
    algorithm_routes_v1.app.dependency_overrides[di_container] = constructor
    algorithm_routes_v2.app.dependency_overrides[di_container] = constructor
    client = TestClient(app)

    redis = container[AlgorithmLockRepository].redis
    logger.debug("\nTEST START: All keys:")
    for key in redis.scan_iter("*"):
        redis.delete(key)
        logger.debug(f"TEST START: {key=}")

    yield App(app_api=app, client=client, container=container)

    # Teardown:
    for dep_key in container.keys():
        try:
            dep = container[dep_key]
        except EnvNotSetException as e:
            # If we hit an error by by constructing a dep in a test we didn't need (that loads an env we don't have), lets just pass.
            logger.debug(e)
            continue

        if isinstance(dep, BaseRepository):
            dep.delete_all()

    logger.debug("\nPurging keys..")
    for key in redis.scan_iter("*"):
        redis.delete(key)
        logger.debug(f"TEST END: Deleted {key=}")


@pytest.fixture
def local_kms(http_w3, app_inst):
    # By default we override the AWS KMS with a local one,
    # as we don't have an AWS KMS yet for integration tests.
    local_key_management_service = LocalKeyManagementService(http_w3)
    app_inst.container[KeyManagementService] = local_key_management_service
    return local_key_management_service


@pytest.fixture
def transaction_repository(app_inst):
    repository = app_inst.container[TransactionRepository]
    repository.db.trading_transactions.delete_many({})

    yield repository

    repository.db.trading_transactions.delete_many({})


@pytest.fixture
def algorithm_lock_repository(app_inst):
    return app_inst.container[AlgorithmLockRepository]


@pytest.fixture
def access_header_v1(app_inst):
    app_inst.container[AlgorithmRepository].upsert_algorithm(default_user_v1())
    request = load_stub("body-for-algorithm-login.json")

    response = app_inst.client.post("/api/v1/login", data=request)

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

    received_token = response.json()["access_token"]
    return {"Authorization": f"bearer {received_token}"}


@pytest.fixture
def access_header_v2(app_inst):
    app_inst.container[AlgorithmRepository].upsert_algorithm(default_user_v2())
    request = load_stub("body-for-algorithm-login.json")

    response = app_inst.client.post("/api/v2/login", data=request)

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

    received_token = response.json()["access_token"]
    return {"Authorization": f"bearer {received_token}"}


@pytest.fixture
def system_access_header(app_inst):
    request = load_stub("body-for-system-login.json")

    response = app_inst.client.post("/api/v1/login", data=request)

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

    received_token = response.json()["access_token"]

    return {"Authorization": f"bearer {received_token}"}


@pytest.fixture
def mongo_client():
    mongo_client = connect_mongo(os.getenv("MONGO_CONNECTION", "mongodb://root:root@mongo:27017"))

    return mongo_client, os.getenv("MONGO_DB_NAME", "trading_api")


@pytest.fixture
def key_repository(mongo_client):
    repo = MongoKeyRepository(client=mongo_client[0], db_name=mongo_client[1])

    yield repo

    repo.delete_all()


@pytest.fixture()
def km_service(http_w3, key_repository, app_inst):
    aws_key_management_service = AWSKeyManagementService(
        http_w3,
        key_manager_username=os.environ.get("KEY_MANAGER_USERNAME", ""),
        key_manager_password=os.environ.get("KEY_MANAGER_PASSWORD", ""),
        stage=Stage.Test,
        region_name="eu-central-1",
        key_repository=key_repository,
    )
    return aws_key_management_service
