import functools
import logging
import os
from pathlib import Path
from typing import Callable

from pymongo import MongoClient

from mm import Stage
from mm.api.security import encode_password
from mm.data.repositories import (
    InMemorySwapRepository,
    InMemorySystemAuthRepository,
    InMemoryTradeRepository,
    InMemoryWalletKeyRepository,
    MongoSwapRepository,
    MongoTradeRepository,
    MongoWalletKeyRepository,
)
from mm.data.services import (
    AWSKeyManagementService,
    BlockchainTransactionService,
    HTTPWeb3Provider,
    StubKeyManagementService,
    StubTransactionService,
)
from mm.domain.repositories import AuthenticationRepository, SwapRepository, TradeRepository, WalletKeyRepository
from mm.domain.services import KeyManagementService, TransactionService, Web3Provider

DB_NAME = "market_maker"

logger = logging.getLogger(__name__)


class Container(dict):
    def __init__(self):
        super().__init__()
        logger.info("Building DI container")

        self.update(
            {
                AuthenticationRepository: build_authentication_repository,
                WalletKeyRepository: build_wallet_key_repository,
                TradeRepository: build_trade_repository,
                SwapRepository: build_swap_repository,
                TransactionService: build_transaction_service,
                KeyManagementService: build_key_management_service,
            },
        )

    def __getitem__(self, key):
        dependency = super().__getitem__(key)
        # If we are dealing with a callable, lazy load the dependency.
        if isinstance(dependency, Callable):
            logger.info(f"Building dependency for {key.__name__}")
            super().__setitem__(key, dependency())
            dependency = super().__getitem__(key)
        logger.debug(f"Returned dependency {key.__name__} -> {dependency.__class__.__name__}")

        return dependency

    def __setitem__(self, key, value):
        logger.info(f"Binding {key.__name__} set to {value.__class__.__name__}")
        super().__setitem__(key, value)


class FakeContainer(dict):
    def __init__(self):
        super().__init__()
        logger.info("Building Fake DI container")

        self.update(
            {
                AuthenticationRepository: build_authentication_repository,
                WalletKeyRepository: InMemoryWalletKeyRepository(),
                TradeRepository: InMemoryTradeRepository(),
                SwapRepository: InMemorySwapRepository(),
                TransactionService: StubTransactionService(),
                KeyManagementService: StubKeyManagementService(),
            },
        )


@functools.cache
def di_container() -> Container:
    return Container()  # Always returns the same instance.


@functools.cache
def build_mongo_client() -> MongoClient:
    return MongoClient(os.getenv("MONGO_CONNECTION_URI_MM", "mongodb://root:root@mongo:27017"), maxPoolSize=300)


@functools.cache
def build_web3_provider() -> Web3Provider:
    return HTTPWeb3Provider(
        web3_bsc_uri=os.getenv("WEB3_PROVIDER_ENDPOINT_BSC", ""),
        web3_rtn_uri=os.getenv("WEB3_PROVIDER_ENDPOINT_RTN", ""),
        ecr_contract_bsc=os.getenv("ECR_CONTRACT_ADDRESS_BSC", ""),
        ecr_contract_rtn=os.getenv("ECR_CONTRACT_ADDRESS_RTN", ""),
        ecr_contract_info_json_path=Path(os.getenv("ECR_CONTRACT_INFO_JSON_PATH", "")),
    )


@functools.cache
def build_authentication_repository() -> AuthenticationRepository:
    return InMemorySystemAuthRepository(
        os.environ["JWT_SYSTEM_USERNAME_MM"], encode_password(os.environ["JWT_SYSTEM_PASSWORD_MM"])
    )


@functools.cache
def build_wallet_key_repository():
    return MongoWalletKeyRepository(client=build_mongo_client(), db_name=DB_NAME)


@functools.cache
def build_trade_repository():
    return MongoTradeRepository(client=build_mongo_client(), db_name=DB_NAME)


@functools.cache
def build_swap_repository():
    return MongoSwapRepository(client=build_mongo_client(), db_name=DB_NAME)


@functools.cache
def build_transaction_service():
    return BlockchainTransactionService(web3=build_web3_provider())


@functools.cache
def build_key_management_service():
    return AWSKeyManagementService(
        web3_provider=build_web3_provider(),
        key_repository=build_wallet_key_repository(),
        region_name="eu-west-1",
        stage=Stage(os.getenv("STAGE", "")),
    )
