import logging
from typing import Union

from trading_api.algorithm.models.algorithm import (
    AlgorithmInDB,
    FailedToRegisterAlgorithmResponse,
    RegisterAlgorithm,
    RegisteredAlgorithmResponse,
    TradingContract,
)
from trading_api.algorithm.repositories.algorithm import AlgorithmRepository
from trading_api.core.security import encode_password

logger = logging.getLogger(__name__)


def to_db(algorithm: RegisterAlgorithm) -> AlgorithmInDB:
    return AlgorithmInDB(
        trading_contract_address=algorithm.trading_contract_address,
        controller_wallet_address=algorithm.controller_wallet_address,
        hashed_password=encode_password(algorithm.unhashed_password),
        trading_contract=TradingContract(version=algorithm.trading_contract_version),
        chain_id=algorithm.chain_id,
        disabled=algorithm.disabled,
    )


def handle_register_algorithm(
    algorithm: RegisterAlgorithm, algorithm_repository: AlgorithmRepository
) -> Union[RegisteredAlgorithmResponse, FailedToRegisterAlgorithmResponse]:
    # TODO: verify if the controller wallet matches the EnvVar.Stage?
    algorithm_in_db = to_db(algorithm)
    if algorithm_repository.upsert_algorithm(algorithm_in_db):
        logger.info(f"REGISTERED Algorithm {algorithm.trading_contract_address=} {algorithm.disabled=}")
        return RegisteredAlgorithmResponse()

    logger.error(f"FAILED to register Algorithm {algorithm.trading_contract_address=} {algorithm.disabled=}")
    return FailedToRegisterAlgorithmResponse()
