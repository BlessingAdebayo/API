import logging
from abc import ABC, abstractmethod
from typing import Optional

from pymongo import MongoClient

from trading_api.algorithm.models.address import AddressKeyPair
from trading_api.core.repositories.mongo import BaseRepository

logger = logging.getLogger(__name__)


class KeyRepository(ABC):
    """This repository stores the controller wallet addresses."""

    @abstractmethod
    def is_healthy(self) -> bool:
        pass

    @abstractmethod
    def add_address_key(self, pair: AddressKeyPair):
        pass

    @abstractmethod
    def get_key_alias_by_address(self, address: str) -> Optional[str]:
        pass

    @abstractmethod
    def get_address_by_key_alias(self, key_alias: str) -> Optional[str]:
        pass


class InMemoryKeyRepository(KeyRepository):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.storage = {}
        if any([len(args) > 0, len(kwargs) > 0]):
            logger.warning(f"ignored arguments in {self=} {args=} & {kwargs=}")

    def is_healthy(self) -> bool:
        return True

    def add_address_key(self, pair: AddressKeyPair):
        self.storage[pair.controller_wallet_address] = pair.key_alias

    def get_key_alias_by_address(self, address: str) -> Optional[str]:
        return self.storage.get(address, None)

    def get_address_by_key_alias(self, key_alias: str) -> Optional[str]:
        for address, addr_key_id in self.storage.items():
            if key_alias == key_alias:
                return address

        return None


class MongoKeyRepository(BaseRepository, KeyRepository):
    def __init__(self, client: MongoClient, db_name: str):
        super().__init__(
            client=client,
            db=client[db_name],
            collection_name="controller_wallet_address_keys",
            dto_class=AddressKeyPair,
        )

    def add_address_key(self, pair: AddressKeyPair):
        self._update_one(pair.filter_query(), self._op_set(pair.dict()))

    def get_key_alias_by_address(self, address: str) -> Optional[str]:
        pair: Optional[AddressKeyPair] = self._model_by_key_value(
            key="controller_wallet_address", value=address
        )  # type: ignore
        if pair is None:
            return None

        return pair.key_alias

    def get_address_by_key_alias(self, key_alias: str) -> Optional[str]:
        pair: Optional[AddressKeyPair] = self._model_by_key_value(key="key_alias", value=key_alias)  # type: ignore
        if pair is None:
            return None

        return pair.controller_wallet_address
