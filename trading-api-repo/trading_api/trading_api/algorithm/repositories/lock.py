import abc
import logging
from typing import Dict, Optional, Union

from eth_typing import ChecksumAddress
from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from trading_api.algorithm.models.algorithm import (
    AlgorithmId,
    AlgorithmIsLocked,
    AlgorithmTransaction,
    AlgorithmWasLocked,
    NewAlgorithmLock,
)
from trading_api.algorithm.models.crypto import TransactionHash

logger = logging.getLogger(__name__)

SYMBOL_V1 = "DEFAULT"  # If we are dealing with a V1 trade we set the symbol to this const.


class AlgorithmLockRepository(abc.ABC):
    @abc.abstractmethod
    def is_healthy(self) -> bool:
        pass

    @abc.abstractmethod
    def remove_algorithm_lock(self, algorithm_id: AlgorithmId, symbol=SYMBOL_V1) -> None:
        pass

    @abc.abstractmethod
    def get_algorithm_lock(
        self, algorithm_id: AlgorithmId, symbol=SYMBOL_V1
    ) -> Union[NewAlgorithmLock, AlgorithmWasLocked]:
        pass

    @abc.abstractmethod
    def persist_algorithm_transaction(
        self, algorithm_transaction: AlgorithmTransaction, symbol=SYMBOL_V1
    ) -> AlgorithmIsLocked:
        pass


class RedisLockRepository(AlgorithmLockRepository):
    """Basic *Not guaranteed to be safe* Redis locking repository
    Reference: https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html
    """

    __lock_timeout_ms: int
    __base_key: str

    def __init__(self, connection_url: str, lock_timeout_ms: int = 100000):
        self.redis = Redis.from_url(connection_url)
        self.__lock_timeout_ms = lock_timeout_ms
        self.__base_key = "algorithm-locks:"
        self.__transaction_base_key = "algorithm-transactions:"

    def is_healthy(self) -> bool:
        try:
            return self.redis.ping()
        except RedisConnectionError:
            return False

    def remove_algorithm_lock(self, algorithm_id: AlgorithmId, symbol=SYMBOL_V1) -> None:
        self.redis.delete(self.__algorithm_key(algorithm_id, symbol))

    def get_algorithm_lock(
        self, algorithm_id: AlgorithmId, symbol=SYMBOL_V1
    ) -> Union[NewAlgorithmLock, AlgorithmWasLocked]:
        obtained_lock = self.__obtain_lock(self.__algorithm_key(algorithm_id, symbol))
        logger.debug(f"Tried to obtain lock: {algorithm_id=} {symbol=}\t{obtained_lock=}")

        if not obtained_lock:
            logger.debug(f"Could not obtain lock: {algorithm_id=} {symbol=}")
            transaction_hash = self.get_algorithm_transaction_hash(algorithm_id=algorithm_id, symbol=symbol)
            return AlgorithmWasLocked(
                lock=NewAlgorithmLock(algorithm_id=algorithm_id, symbol=symbol), transaction_hash=transaction_hash
            )

        return NewAlgorithmLock(algorithm_id=algorithm_id, symbol=symbol)

    def get_algorithm_transaction_hash(self, algorithm_id: AlgorithmId, symbol=SYMBOL_V1) -> Optional[TransactionHash]:
        key = self.__algorithm_transaction_key(algorithm_id, symbol)
        value = self.redis.get(key)
        if value is None:
            return None

        return TransactionHash(value=value)

    def persist_algorithm_transaction(
        self, algorithm_transaction: AlgorithmTransaction, symbol=SYMBOL_V1
    ) -> AlgorithmIsLocked:
        self.redis.set(
            self.__algorithm_transaction_key(algorithm_transaction.algorithm_id, symbol),
            algorithm_transaction.transaction_hash.value,
            px=self.__lock_timeout_ms,
        )

        return AlgorithmIsLocked(
            lock=NewAlgorithmLock(algorithm_id=algorithm_transaction.algorithm_id, symbol=symbol),
            transaction_hash=algorithm_transaction.transaction_hash,
        )

    def __obtain_lock(self, key):
        if not self.redis.exists(key):
            return bool(self.redis.set(key, "LOCKED", px=self.__lock_timeout_ms))

        return False

    def __algorithm_key(self, algorithm_id: AlgorithmId, symbol: str) -> str:
        return f"{self.__base_key}{algorithm_id.public_address}{symbol}"

    def __algorithm_transaction_key(self, algorithm_id: AlgorithmId, symbol: str) -> str:
        return f"{self.__transaction_base_key}{algorithm_id.public_address}{symbol}"


class InMemoryAlgorithmLockRepository(AlgorithmLockRepository):
    algorithm_locks: Dict[str, NewAlgorithmLock]
    algorithm_transactions: Dict[str, AlgorithmTransaction]

    def __init__(self):
        self.algorithm_locks = {}
        self.algorithm_transactions = {}

    def is_healthy(self) -> bool:
        return True

    def remove_algorithm_lock(self, algorithm_id: AlgorithmId, symbol="DEFAULT") -> None:
        del self.algorithm_locks[self.lock_key(algorithm_id.public_address, symbol)]

    def get_algorithm_lock(
        self, algorithm_id: AlgorithmId, symbol=SYMBOL_V1
    ) -> Union[NewAlgorithmLock, AlgorithmWasLocked]:
        key = self.lock_key(algorithm_id.public_address, symbol)
        lock = self.algorithm_locks.get(key)
        if lock is None:
            new_lock = NewAlgorithmLock(algorithm_id=algorithm_id, symbol=symbol)
            self.algorithm_locks[key] = new_lock
            return new_lock

        return AlgorithmWasLocked(lock=lock, transaction_hash=self.algorithm_transactions[key].transaction_hash)

    def persist_algorithm_transaction(
        self, algorithm_transaction: AlgorithmTransaction, symbol=SYMBOL_V1
    ) -> AlgorithmIsLocked:
        key = self.lock_key(algorithm_transaction.algorithm_id.public_address, symbol)
        self.algorithm_transactions[key] = algorithm_transaction

        return AlgorithmIsLocked(
            lock=self.algorithm_locks[key],
            transaction_hash=algorithm_transaction.transaction_hash,
        )

    @staticmethod
    def lock_key(public_address: ChecksumAddress, symbol) -> str:
        return f"{public_address}-{symbol}"
