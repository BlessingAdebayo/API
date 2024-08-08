from abc import ABC, abstractmethod
from typing import Dict, Iterator, Optional

from pymongo import MongoClient

from trading_api.algorithm.models.algorithm import AlgorithmInDB
from trading_api.core.repositories.mongo import BaseRepository


class AlgorithmRepository(ABC):
    @abstractmethod
    def is_healthy(self) -> bool:
        pass

    @abstractmethod
    def get_algorithm(self, trading_contract_address: str) -> Optional[AlgorithmInDB]:
        pass

    @abstractmethod
    def upsert_algorithm(self, algorithm: AlgorithmInDB) -> bool:
        pass

    @abstractmethod
    def all_algorithms(self) -> Iterator[AlgorithmInDB]:
        pass


class InMemoryAlgorithmRepository(AlgorithmRepository):
    memory: Dict[str, AlgorithmInDB]

    def __init__(self):
        self.memory = {}

    def is_healthy(self) -> bool:
        return True

    def upsert_algorithm(self, algorithm: AlgorithmInDB) -> bool:
        self.memory[algorithm.trading_contract_address] = algorithm
        return True

    def get_algorithm(self, trading_contract_address) -> Optional[AlgorithmInDB]:
        return self.memory.get(trading_contract_address)

    def all_algorithms(self) -> Iterator[AlgorithmInDB]:
        yield from self.memory.values()


class MongoAlgorithmRepository(BaseRepository, AlgorithmRepository):
    def __init__(self, client: MongoClient, db_name: str):
        super().__init__(client=client, db=client[db_name], collection_name="algorithms", dto_class=AlgorithmInDB)

    def upsert_algorithm(self, algorithm: AlgorithmInDB) -> bool:
        result = self._update_one(algorithm.filter_query(), self._op_set(algorithm.dict()))

        return result.acknowledged

    def get_algorithm(self, trading_contract_address: str) -> Optional[AlgorithmInDB]:
        return self._model_by_key_value(key="trading_contract_address", value=trading_contract_address)  # type: ignore

    def all_algorithms(self) -> Iterator[AlgorithmInDB]:
        yield from self._all_models()  # type: ignore
