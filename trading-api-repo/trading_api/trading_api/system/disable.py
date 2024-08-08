import logging
from typing import Union

from trading_api.algorithm.models.algorithm import (
    DisableAlgorithm,
    DisabledAlgorithmResponse,
    FailedToDisableAlgorithmResponse,
)
from trading_api.algorithm.repositories.algorithm import AlgorithmRepository

logger = logging.getLogger(__name__)


def handle_disable_algorithm(
    algorithm: DisableAlgorithm, algorithm_repository: AlgorithmRepository
) -> Union[DisabledAlgorithmResponse, FailedToDisableAlgorithmResponse]:
    algorithm_in_db = algorithm_repository.get_algorithm(algorithm.trading_contract_address)
    if algorithm_in_db:
        algorithm_in_db.disabled = True
        algorithm_repository.upsert_algorithm(algorithm_in_db)
        logger.info(f"Disabled Algorithm {algorithm.trading_contract_address=}")
        return DisabledAlgorithmResponse()

    logger.error(f"FAILED to disable Algorithm (not in database): {algorithm.trading_contract_address=}")
    return FailedToDisableAlgorithmResponse()
