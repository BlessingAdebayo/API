import datetime
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Iterable, Iterator

import pymongo
from pymongo import MongoClient

from trading_api.algorithm.models.algorithm import AlgorithmId
from trading_api.algorithm.models.crypto import TransactionHash
from trading_api.algorithm.models.trade import TradeStatus, TradingTransaction
from trading_api.core.repositories.mongo import BaseRepository, BaseRepositoryInterface


class TransactionRepository(BaseRepositoryInterface, ABC):
    @abstractmethod
    def is_healthy(self) -> bool:
        pass

    @abstractmethod
    def get_trading_transactions(self, algorithm: AlgorithmId) -> Iterable[TradingTransaction]:
        pass

    @abstractmethod
    def get_transactions_paginated(self, algorithm: AlgorithmId, skip: int, limit: int) -> Iterable[TradingTransaction]:
        pass

    @abstractmethod
    def persist_transaction(self, trading_transaction: TradingTransaction):
        pass

    @abstractmethod
    def update_transaction(self, trading_transaction: TradingTransaction):
        pass

    @abstractmethod
    def update_transaction_status(
        self, transaction_hash: TransactionHash, trade_status: TradeStatus, timestamp: datetime.datetime
    ):
        pass

    @abstractmethod
    def get_transaction_count(self, algorithm: AlgorithmId) -> int:
        pass


class MongoTransactionRepository(BaseRepository, TransactionRepository):
    def __init__(self, client: MongoClient, db_name: str):
        super().__init__(
            client=client, db=client[db_name], collection_name="trading_transactions", dto_class=TradingTransaction
        )

    def update_transaction_status(
        self, transaction_hash: TransactionHash, trade_status: TradeStatus, timestamp: datetime.datetime
    ):
        filter_query = {"transaction_hash": transaction_hash.value}
        update_dict = self._op_set({"status": trade_status.value, "updated_at": timestamp})

        self._update_one(filter_query, update_dict, upsert=False)

    def update_transaction(self, trading_transaction: TradingTransaction):
        transaction_dict = trading_transaction.dict()
        del transaction_dict["created_at"]
        self._update_one(trading_transaction.filter_query(), self._op_set(transaction_dict))

    def persist_transaction(self, trading_transaction: TradingTransaction):
        self._update_one(trading_transaction.filter_query(), self._op_set(trading_transaction.dict()))

    def get_transactions_paginated(self, algorithm: AlgorithmId, skip: int, limit: int) -> Iterator[TradingTransaction]:
        return self._models_by_key_value_paginated(
            key="trading_contract_address",
            value=algorithm.public_address,
            skip=skip,
            limit=limit,
            sort_query=[("created_at", pymongo.DESCENDING)],
        )

    def get_trading_transactions(self, algorithm: AlgorithmId) -> Iterator[TradingTransaction]:
        return self._models_by_key_value(key="trading_contract_address", value=algorithm.public_address)  # type: ignore

    def get_transaction_count(self, algorithm: AlgorithmId) -> int:
        return self._count_docs_by_key_value(key="trading_contract_address", value=algorithm.public_address)


class InMemoryTransactionRepository(TransactionRepository):
    def __init__(self):
        self.memory = defaultdict(list)

    def is_healthy(self) -> bool:
        return True

    def get_transaction_count(self, algorithm: AlgorithmId) -> int:
        return len(self.memory[algorithm.public_address])

    def update_transaction(self, trading_transaction: TradingTransaction):
        pass

    def update_transaction_status(
        self, transaction_hash: TransactionHash, trade_status: TradeStatus, timestamp: datetime.datetime
    ):
        pass

    def persist_transaction(self, trading_transaction: TradingTransaction):
        self.memory[trading_transaction.trading_contract_address].append(trading_transaction)

    def get_transactions_paginated(self, algorithm: AlgorithmId, skip: int, limit: int) -> Iterator[TradingTransaction]:
        # Note: No paginated/limiting implemented here.
        return self.get_trading_transactions(algorithm=algorithm)

    def get_trading_transactions(self, algorithm: AlgorithmId) -> Iterator[TradingTransaction]:
        yield from self.memory[algorithm.public_address]
