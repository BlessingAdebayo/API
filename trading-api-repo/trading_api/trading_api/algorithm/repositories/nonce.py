import logging
import time
import uuid
from abc import ABC, abstractmethod
from typing import Optional

from redis import Redis

from trading_api.algorithm.models.trade import Trade

logger = logging.getLogger(__name__)

Nonce = int
OptNonce = Optional[int]


class NonceRepository(ABC):
    @abstractmethod
    def get_nonce(self, trade: Trade, web3_nonce: Nonce) -> Nonce:
        pass

    @abstractmethod
    def reset_nonce(self, trade: Trade):
        pass


class RedisNonceRepository(NonceRepository):
    def __init__(self, connection_url: str):
        self.redis = Redis.from_url(connection_url)

    def reset_nonce(self, trade: Trade):
        logger.info(f"Resetting nonce for {get_nonce_key(trade)=}")
        self.redis.delete(get_nonce_key(trade))

    def get_nonce(self, trade: Trade, web3_nonce: Nonce) -> Nonce:
        # Get a lock for the nonce counter resource
        lock_key = get_lock_key(trade)
        self.obtain_lock(lock_key)

        nonce = self.get_nonce_counter(get_nonce_key(trade), web3_nonce)

        # Release lock for the nonce counter resource
        self.release_lock(lock_key)

        # return nonce
        logger.info(f"Retrieved nonce for {get_nonce_key(trade)=} {nonce=}")

        return nonce

    def obtain_lock(self, key: str):
        while True:
            result = self.redis.set(key, "LOCKED", nx=True, px=500)
            if result is not None:
                return

            time.sleep(0.1)

    def get_nonce_counter(self, key: str, current_nonce: Nonce) -> Nonce:
        """Get our nonce counter
        Increment the nonce counter as we don't want the next client to use the same counter
        """
        value = self.redis.get(key)
        nonce = current_nonce
        if value is not None:
            nonce = int(value)

        self.redis.set(key, nonce + 1)

        return nonce

    def release_lock(self, key: str):
        return self.redis.delete(key)


class InMemoryNonceRepository(NonceRepository):
    def __init__(self):
        self.memory = {}

    def reset_nonce(self, trade: Trade):
        key = get_nonce_key(trade)
        if key in self.memory:
            del self.memory[key]

    def get_nonce(self, trade: Trade, web3_nonce: Nonce) -> Nonce:
        key = get_nonce_key(trade)
        if key not in self.memory:
            self.memory[key] = web3_nonce + 1
            return web3_nonce

        nonce = self.memory[key]
        self.memory[key] = nonce + 1
        return self.memory[web3_nonce]


def get_lock_key(trade: Trade) -> str:
    return f"NONCE-LOCK-{trade.algorithm_id.public_address}"


def get_nonce_key(trade: Trade) -> str:
    return f"NONCE-COUNTER-{trade.algorithm_id.public_address}"
