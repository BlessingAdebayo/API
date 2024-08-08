import json
import logging
import logging.config
import os
from enum import Enum
from pathlib import Path
from typing import Optional

from boto3 import Session
from botocore.exceptions import ClientError
from dotenv import load_dotenv

API_ROOT_PATH = Path(__file__).parent.parent

logging.config.fileConfig(API_ROOT_PATH / "logging.conf", disable_existing_loggers=False)

logger = logging.getLogger(__name__)

LATEST_CONTRACT_VERSION = "v2.0"

if os.getenv("DEBUG") == "1":
    level = logging.DEBUG
    logger.setLevel(level)
    for handler in logging.getLogger().handlers:
        handler.setLevel(level)


class Stage(Enum):
    Test = "test"
    Local = "local"
    Development = "development"
    Staging = "staging"
    Production = "production"


class EnvNotSetException(Exception):
    def __init__(self, key: str):
        self.message = f"Tried to retrieve env-var[{key}] but it was not set."


class EnvVar(Enum):
    TASK_CHECK_TX_STATUS_SLEEP_TIME = "TASK_CHECK_TX_STATUS_SLEEP_TIME"
    ECR_CONTRACT_INFO_JSON_PATH = "ECR_CONTRACT_INFO_JSON_PATH"
    ECR_CONTRACT_ADDRESS_RTN = "ECR_CONTRACT_ADDRESS_RTN"
    ECR_CONTRACT_ADDRESS_BSC = "ECR_CONTRACT_ADDRESS_BSC"
    REGION_NAME = "REGION_NAME"
    PRIVATE_KEY = "PRIVATE_KEY"
    ACCESS_TOKEN_EXPIRE_MINUTES = "ACCESS_TOKEN_EXPIRE_MINUTES"
    SECRET_KEY = "SECRET_KEY"
    STAGE = "STAGE"
    UNIT = "UNIT"
    ESTIMATED_GAS_FACTOR = "ESTIMATED_GAS_FACTOR"
    ESTIMATED_GAS_FACTOR_BSC = "ESTIMATED_GAS_FACTOR_BSC"
    ESTIMATED_GAS_FACTOR_RTN = "ESTIMATED_GAS_FACTOR_RTN"
    ESTIMATED_GAS_PRICE_FACTOR = "ESTIMATED_GAS_PRICE_FACTOR"
    ESTIMATED_GAS_PRICE_FACTOR_BSC = "ESTIMATED_GAS_PRICE_FACTOR_BSC"
    ESTIMATED_GAS_PRICE_FACTOR_RTN = "ESTIMATED_GAS_PRICE_FACTOR_RTN"
    WEB3_PROVIDER_ENDPOINT_BSC = "WEB3_PROVIDER_ENDPOINT_BSC"
    WEB3_PROVIDER_ENDPOINT_RTN = "WEB3_PROVIDER_ENDPOINT_RTN"
    USE_WEB3_ENDPOINT = "USE_WEB3_ENDPOINT"
    JWT_SYSTEM_PASSWORD = "JWT_SYSTEM_PASSWORD"
    JWT_SYSTEM_USERNAME = "JWT_SYSTEM_USERNAME"
    FUND_WITHDRAWAL_ADDRESS = "FUND_WITHDRAWAL_ADDRESS"
    MONGO_DB_NAME = "MONGO_DB_NAME"
    MONGO_USERNAME = "MONGO_USERNAME"
    MONGO_PASSWORD = "MONGO_PASSWORD"
    MONGO_CONNECTION = "MONGO_CONNECTION"
    REDIS_URL = "REDIS_URL"
    REDIS_LOCK_TIMEOUT_MS = "REDIS_LOCK_TIMEOUT_MS"
    TRADING_CONTRACT_TOOLS_JSON_PATH = "TRADING_CONTRACT_TOOLS_JSON_PATH"
    TRADING_CONTRACT_TOOLS_ADDRESS_BSC = "TRADING_CONTRACT_TOOLS_ADDRESS_BSC"
    TRADING_CONTRACT_TOOLS_ADDRESS_RTN = "TRADING_CONTRACT_TOOLS_ADDRESS_RTN"


def set_defaults():
    # Defaults
    logger.debug("Setting default environment variables..")
    os.environ[EnvVar.SECRET_KEY.value] = "46bf2efca41f935ff1ce71448080d8c4193421ffe75fe991e1ca210981b78dc7"
    os.environ[EnvVar.ESTIMATED_GAS_FACTOR.value] = "2"
    os.environ[EnvVar.ECR_CONTRACT_INFO_JSON_PATH.value] = str(
        API_ROOT_PATH
        / ".contracts"
        / LATEST_CONTRACT_VERSION
        / "artifacts"
        / "contracts"
        / "utils"
        / "Ecr.sol"
        / "Ecr.json"
    )
    os.environ[EnvVar.TRADING_CONTRACT_TOOLS_JSON_PATH.value] = str(
        API_ROOT_PATH
        / ".contracts"
        / LATEST_CONTRACT_VERSION
        / "artifacts"
        / "contracts"
        / "TradingContractTools.sol"
        / "TradingContractTools.json"
    )
    logger.debug(f"Current environment: {os.environ}")
    logger.debug("Setting environment variables from the .env file..")
    load_dotenv(API_ROOT_PATH / ".env")
    logger.debug(f"Current environment: {os.environ}")


def get_env(key: EnvVar, default: Optional[str] = None) -> Optional[str]:
    assert key in EnvVar

    return os.getenv(key.value, default)


def get_env_force(key: EnvVar, default: Optional[str] = None) -> str:
    assert key in EnvVar

    value = os.getenv(key.value, default)
    if value is None:
        raise EnvNotSetException(key.value)

    return value


def set_secret(session: Session, tries=0):
    stage_name = get_env(EnvVar.STAGE, Stage.Development.value)
    secret_name = f"{stage_name}/trading_api/environment"
    client = session.client("secretsmanager")
    secrets = {}

    try:
        response: dict = client.get_secret_value(SecretId=secret_name)
        secret_string = response.get("SecretString", {})
        secrets = dict(json.loads(secret_string))
    except ClientError as e:
        logger.error(e)
        if tries < 3:
            set_secret(session=session, tries=tries + 1)
        else:
            raise e

    for key, value in secrets.items():
        os.environ[str(key)] = str(value)


def set_endpoints(session: Session, tries=0):
    stage_name = get_env(EnvVar.STAGE, Stage.Development.value)
    client = session.client("elasticache")

    try:
        redis_found = False
        clusters = client.describe_cache_clusters(ShowCacheNodeInfo=True)

        for cluster in clusters["CacheClusters"]:
            if stage_name not in cluster["CacheClusterId"]:
                continue

            redis_endpoint = cluster["CacheNodes"][0]["Endpoint"]["Address"]
            os.environ[EnvVar.REDIS_URL.value] = f"redis://{redis_endpoint}"
            redis_found = True
        assert (
            redis_found
        ), f"couldn't find redis cluster among clusters: {[cluster['CacheClusterId'] for cluster in clusters]}"
    except ClientError as e:
        logger.error(e)
        if tries < 3:
            set_endpoints(session=session, tries=tries + 1)

        else:
            raise e

    client = session.client("docdb")

    try:
        clusters = client.describe_db_clusters()

        mongo_found = False
        for cluster in clusters["DBClusters"]:
            if stage_name not in cluster["DBClusterIdentifier"]:
                continue
            if "mongo" not in cluster["DBClusterIdentifier"]:
                continue
            mongo_endpoint = cluster["ReaderEndpoint"]
            mongo_port = cluster["Port"]
            mongo_username = get_env(EnvVar.MONGO_USERNAME)
            mongo_password = get_env(EnvVar.MONGO_PASSWORD)
            config_query = "?ssl=true&ssl_ca_certs=rds-combined-ca-bundle.pem&replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false"
            os.environ[
                EnvVar.MONGO_CONNECTION.value
            ] = f"mongodb://{mongo_username}:{mongo_password}@{mongo_endpoint}:{mongo_port}/{config_query}"
            mongo_found = True
        assert (
            mongo_found
        ), f"couldn't find redis cluster among clusters: {[cluster['DBClusterIdentifier'] for cluster in clusters]}"
    except ClientError as e:
        logger.error(e)
        if tries < 3:
            set_endpoints(session=session, tries=tries + 1)

        else:
            raise e


def load_aws_env():
    session = Session(region_name=get_env(EnvVar.REGION_NAME))

    logger.debug("Setting environment variables from aws secretsmanager..")
    set_secret(session)
    logger.debug(f"Current environment: {os.environ}")
    logger.debug("Setting environment variables using the aws cluster endpoints for Redis and Mongodb..")
    set_endpoints(session)
    logger.debug(f"Current environment: {os.environ}")


def configure_environment():
    logger.debug("Configuring environment.")
    set_defaults()
    if get_env(EnvVar.STAGE, Stage.Local.value) != Stage.Local.value:
        load_aws_env()
    if (
        get_env(EnvVar.SECRET_KEY) == "46bf2efca41f935ff1ce71448080d8c4193421ffe75fe991e1ca210981b78dc7"
        and get_env(EnvVar.STAGE) == Stage.Production.value
    ):
        logger.error("CHANGE THE SECRET_KEY IN PRODUCTION !!!")


configure_environment()
