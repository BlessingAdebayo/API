from pathlib import Path
from types import SimpleNamespace

import pytest
import solcx
from eth_tester import PyEVMBackend
from fastapi import FastAPI
from starlette.testclient import TestClient
from web3 import EthereumTesterProvider, Web3

from main import app
from tests import TEST_CONTRACT_VERSION
from tests.blockchain import deploy_contract
from tests.utils import get_access_header, load_stub
from trading_api import algorithm_routes_v1, algorithm_routes_v2
from trading_api.algorithm.repositories.algorithm import InMemoryAlgorithmRepository
from trading_api.algorithm.repositories.lock import InMemoryAlgorithmLockRepository
from trading_api.algorithm.repositories.transaction import InMemoryTransactionRepository
from trading_api.algorithm.services.kms import KeyManagementService, LocalKeyManagementService
from trading_api.algorithm.services.web3 import InMemoryWeb3Provider
from trading_api.core.container import FakeContainer, default_user_v1, default_user_v2, di_container


class AppTest:
    def __init__(self, app: FastAPI, client: TestClient, container: FakeContainer):
        self.app = app
        self.client = client
        self.container = container

    app: FastAPI
    client: TestClient
    container: FakeContainer


@pytest.fixture
def app_inst():
    fake_container = FakeContainer()

    def constructor():
        return fake_container

    app.dependency_overrides[di_container] = constructor
    algorithm_routes_v1.app.dependency_overrides[di_container] = constructor
    algorithm_routes_v2.app.dependency_overrides[di_container] = constructor
    client = TestClient(app)

    return AppTest(app=app, client=client, container=fake_container)


@pytest.fixture
def access_header_v1(app_inst: AppTest):
    user = default_user_v1()
    return get_access_header(app_inst, user)


@pytest.fixture
def access_header_v2(app_inst: AppTest):
    user = default_user_v2()
    return get_access_header(app_inst, user)


@pytest.fixture
def system_access_header(app_inst: AppTest):
    payload = load_stub("body-for-system-login.json")
    endpoint = "/api/v1/login"

    response = app_inst.client.post(endpoint, data=payload)

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"
    received_token = response.json()["access_token"]

    return {"Authorization": f"bearer {received_token}"}


@pytest.fixture
def lock_repository() -> InMemoryAlgorithmLockRepository:
    return InMemoryAlgorithmLockRepository()


def __compile_source_file(file_path):
    return solcx.compile_files(file_path)


def __deploy_contract(w3, contract_interface, contract_args, deploy_tx):
    contract = w3.eth.contract(abi=contract_interface["abi"], bytecode=contract_interface["bin"])
    _pairedToken, _maxIndividualCap, _maxTotalCap, _developerAddress = contract_args
    transaction = contract.constructor(_pairedToken, _maxIndividualCap, _maxTotalCap, _developerAddress)
    tx_hash = transaction.transact(transaction=deploy_tx)

    receipt = w3.eth.get_transaction_receipt(tx_hash)
    assert receipt["status"] == 1

    return receipt["contractAddress"]


@pytest.fixture
def tester_provider():
    custom_genesis = PyEVMBackend._generate_genesis_params(overrides={"gas_limit": 10_000_000})
    backend = PyEVMBackend(genesis_parameters=custom_genesis)

    return EthereumTesterProvider(backend)


@pytest.fixture
def eth_tester(tester_provider):
    return tester_provider.ethereum_tester


def zero_gas_price_strategy(web3, transaction_params=None):
    return 0  # zero gas price makes testing simpler.


@pytest.fixture
def w3(tester_provider):
    w3 = Web3(tester_provider)
    w3.eth.set_gas_price_strategy(zero_gas_price_strategy)

    return w3


@pytest.fixture
def contract_account(eth_tester):
    return (eth_tester.get_accounts()[0], eth_tester.backend.account_keys[0])


@pytest.fixture
def trading_contract(eth_tester, contract_account, w3):
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
    compiled_sol = __compile_source_file(contract_source_path)

    contract_id = f"{contract_source_path}:TradingContract"
    contract_interface = compiled_sol[contract_id]
    contract_args = (
        "0x55d398326f99059fF775485246999027B3197955",  # _pairedToken
        "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",  # _baseToken
        10000,  # _maxTotalCap
        eth_tester.get_accounts()[1],  # _developerAddress
    )

    # balance = w3.fromWei(w3.eth.get_balance(contract_account[0]), 'gwei')
    # print(f"Contract balance: {balance}")

    deploy_tx = {
        "from": contract_account[0],
        "value": 0,
        "gas": 10_000_000,
        "nonce": w3.eth.get_transaction_count(contract_account[0]),
    }

    contract_address = deploy_contract(w3, contract_interface, contract_args, deploy_tx)
    trading_contract_var = w3.eth.contract(address=contract_address, abi=contract_interface["abi"])

    return trading_contract_var


@pytest.fixture
def trading_contract_tools():
    return SimpleNamespace(
        functions=SimpleNamespace(
            buyCheck=SimpleNamespace(fn_name="buyCheck"), sellCheck=SimpleNamespace(fn_name="sellCheck")
        )
    )


@pytest.fixture
def transaction_repository():
    return InMemoryTransactionRepository()


@pytest.fixture
def algorithm_repository():
    return InMemoryAlgorithmRepository()


@pytest.fixture
def in_memory_w3(tester_provider, contract_account, trading_contract, trading_contract_tools):
    return InMemoryWeb3Provider(
        Web3(tester_provider), trading_contract, trading_contract_tools, private_key=contract_account[1]
    )


@pytest.fixture
def km_service(app_inst, in_memory_w3):
    service = LocalKeyManagementService(in_memory_w3)
    app_inst.container[KeyManagementService] = service

    return service
