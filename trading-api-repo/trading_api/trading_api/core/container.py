import functools
import json
import logging
from functools import partial
from pathlib import Path
from typing import Callable, Optional

from tests.utils import ADDR1, ADDR2
from trading_api import EnvVar, Stage, get_env, get_env_force
from trading_api.algorithm.models.algorithm import AlgorithmInDB, TradingContract, TradingContractVersion
from trading_api.algorithm.models.crypto import ChainId, ContractDetails
from trading_api.algorithm.repositories.algorithm import (
    AlgorithmRepository,
    InMemoryAlgorithmRepository,
    MongoAlgorithmRepository,
)
from trading_api.algorithm.repositories.key import InMemoryKeyRepository, KeyRepository, MongoKeyRepository
from trading_api.algorithm.repositories.lock import (
    AlgorithmLockRepository,
    InMemoryAlgorithmLockRepository,
    RedisLockRepository,
)
from trading_api.algorithm.repositories.nonce import InMemoryNonceRepository, NonceRepository, RedisNonceRepository
from trading_api.algorithm.repositories.transaction import (
    InMemoryTransactionRepository,
    MongoTransactionRepository,
    TransactionRepository,
)
from trading_api.algorithm.services.kms import AWSKeyManagementService, KeyManagementService, LocalKeyManagementService
from trading_api.algorithm.services.web3 import HttpWeb3Provider, Web3Provider
from trading_api.algorithm.ticker import InMemoryPancakeSwapService, PancakeSwapAPIService, PancakeSwapService
from trading_api.core.repositories.mongo import connect_mongo
from trading_api.core.security import encode_password
from trading_api.system.repositories.system import InMemorySystemAuthRepository, SystemAuthRepository, SystemUser

logger = logging.getLogger(__name__)


def build_kms(
    web3_provider_fn: Callable[[], Web3Provider], key_repository_fn: Callable[[], KeyRepository]
) -> KeyManagementService:
    return AWSKeyManagementService(
        web3_provider=web3_provider_fn(),
        region_name=get_env(EnvVar.REGION_NAME, ""),  # type: ignore
        key_repository=key_repository_fn(),
        stage=Stage(get_env_force(EnvVar.STAGE, Stage.Local.value)),
    )


class Container(dict):
    def __init__(self):
        super().__init__()
        logger.info("Building DI container")

        self.web3_provider = None
        self.mongo_client = None
        self.mongo_db_name = get_env(EnvVar.MONGO_DB_NAME, "trading_api")
        self.redis_url = get_env(EnvVar.REDIS_URL)

        lock_repository = RedisLockRepository(
            connection_url=self.redis_url, lock_timeout_ms=int(get_env(EnvVar.REDIS_LOCK_TIMEOUT_MS))
        )

        system_auth_repository = InMemorySystemAuthRepository(
            SystemUser(
                username=get_env(EnvVar.JWT_SYSTEM_USERNAME),
                hashed_password=encode_password(get_env(EnvVar.JWT_SYSTEM_PASSWORD)),
            )
        )

        self.update(
            {
                SystemAuthRepository: system_auth_repository,
                AlgorithmLockRepository: lock_repository,
                Web3Provider: self.build_web3_provider,
                AlgorithmRepository: self.build_algorithm_repository,
                PancakeSwapService: PancakeSwapAPIService(),
                KeyRepository: self.build_key_repository,
                KeyManagementService: partial(
                    build_kms, web3_provider_fn=self.build_web3_provider, key_repository_fn=self.build_key_repository
                ),
                TransactionRepository: self.build_transaction_repository,
                NonceRepository: self.build_nonce_repository,
            }
        )

    def __getitem__(self, key):
        dependency = super().__getitem__(key)
        # If we are dealing with a callable, it means we lazy load the dependency only once.
        if isinstance(dependency, Callable):
            logger.info(f"Building dependency for {key.__name__}")
            super().__setitem__(key, dependency())
            dependency = super().__getitem__(key)
        logger.debug(f"Returned dependency {key.__name__} -> {dependency.__class__.__name__}")

        return dependency

    def __setitem__(self, key, value):
        logger.info(f"Binding {key.__name__} set to {value.__class__.__name__}")
        super().__setitem__(key, value)

    def create_mongo_client(self):
        if self.mongo_client is None:
            self.mongo_client = connect_mongo(get_env(EnvVar.MONGO_CONNECTION, "mongodb://root:root@mongo:27017"))

        return self.mongo_client

    def build_web3_provider(self) -> Optional[Web3Provider]:
        if self.web3_provider is not None:
            return self.web3_provider

        private_key = get_env(EnvVar.PRIVATE_KEY, "")
        if not get_env(EnvVar.USE_WEB3_ENDPOINT):
            return None

        web3_bsc = get_env_force(EnvVar.WEB3_PROVIDER_ENDPOINT_BSC)
        web3_rtn = get_env_force(EnvVar.WEB3_PROVIDER_ENDPOINT_RTN)
        ecr_address_bsc = get_env_force(EnvVar.ECR_CONTRACT_ADDRESS_BSC)
        ecr_address_rtn = get_env_force(EnvVar.ECR_CONTRACT_ADDRESS_RTN)
        ecr_contract_path = get_env_force(EnvVar.ECR_CONTRACT_INFO_JSON_PATH)
        ecr_abi = self.read_contract_abi(Path(ecr_contract_path))

        self.web3_provider = HttpWeb3Provider(
            web3_bsc_uri=web3_bsc,
            web3_rtn_uri=web3_rtn,
            ecr_contract_bsc=ContractDetails(address=ecr_address_bsc, abi=ecr_abi),
            ecr_contract_rtn=ContractDetails(address=ecr_address_rtn, abi=ecr_abi),
            private_key=private_key,
        )

        return self.web3_provider

    def build_transaction_repository(self) -> MongoTransactionRepository:
        return MongoTransactionRepository(client=self.create_mongo_client(), db_name=self.mongo_db_name)

    def build_algorithm_repository(self):
        return MongoAlgorithmRepository(client=self.create_mongo_client(), db_name=self.mongo_db_name)

    def build_key_repository(self) -> MongoKeyRepository:
        return MongoKeyRepository(client=self.create_mongo_client(), db_name=self.mongo_db_name)

    def build_nonce_repository(self):
        return RedisNonceRepository(connection_url=self.redis_url)

    @staticmethod
    def read_contract_abi(contract_path: Path) -> dict:
        with open(contract_path) as f:  # type: ignore
            info_json = json.load(f)
            abi = info_json["abi"]

        return abi


class FakeContainer(dict):
    def __init__(self):
        super().__init__()

        system_user = SystemUser(username="System John Doe", hashed_password=encode_password("secret"))
        self.update(
            {
                AlgorithmLockRepository: InMemoryAlgorithmLockRepository(),
                AlgorithmRepository: InMemoryAlgorithmRepository(),
                KeyManagementService: LocalKeyManagementService(web3_provider=None),  # type: ignore
                KeyRepository: InMemoryKeyRepository(),
                PancakeSwapService: InMemoryPancakeSwapService(),
                SystemAuthRepository: InMemorySystemAuthRepository(system_user),
                TransactionRepository: InMemoryTransactionRepository(),
                Web3Provider: None,
                NonceRepository: InMemoryNonceRepository(),
            }
        )

    def __getitem__(self, key):
        dependency = super().__getitem__(key)
        logger.debug(f"[FAKE] Returned dependency {key.__name__} -> {dependency.__class__.__name__}")

        return dependency

    def __setitem__(self, key, value):
        logger.info(f"[FAKE] Binding {key.__name__} set to {value.__class__.__name__}")
        super().__setitem__(key, value)


@functools.cache
def di_container() -> Container:
    # Cache this thing so its a singleton and we only build it once.
    return Container()


def default_user_v1() -> AlgorithmInDB:
    return AlgorithmInDB(
        trading_contract_address=ADDR2,
        controller_wallet_address=ADDR1,
        hashed_password=encode_password("secret"),
        chain_id=ChainId.RTN,
        trading_contract=TradingContract(version=TradingContractVersion.V1_0),
    )


def default_user_v2() -> AlgorithmInDB:
    return AlgorithmInDB(
        trading_contract_address=ADDR2,
        controller_wallet_address=ADDR1,
        hashed_password=encode_password("secret"),
        chain_id=ChainId.RTN,
        trading_contract=TradingContract(version=TradingContractVersion.V2_0),
    )
