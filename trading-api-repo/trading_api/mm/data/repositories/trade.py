from typing import Iterator, Optional

from pymongo import DESCENDING, MongoClient
from pymongo.collection import Collection

from mm.domain.models import Amount, Slippage, TradeFilter, TradeRecord, TradeType, TransactionHash, TransactionStatus
from mm.domain.repositories import TradeRepository


class InMemoryTradeRepository(TradeRepository):
    def __init__(self):
        self.memory: dict[TransactionHash, TradeRecord] = {}

    def __len__(self) -> int:
        return len(self.memory)

    def upsert(self, record: TradeRecord) -> None:
        self.memory[record.hash] = record

    def get(self, hash: TransactionHash) -> Optional[TradeRecord]:
        return self.memory.get(hash)

    def get_all_paginated(self, trade_filter: TradeFilter) -> Iterator[TradeRecord]:
        # Pagination not implemented.
        yield from filter(
            lambda x: trade_filter.contract is None or x.contract == trade_filter.contract, self.memory.values()
        )


def to_db(record: TradeRecord) -> dict:
    return dict(
        hash=record.hash,
        contract=record.contract,
        slippage=str(record.slippage),
        status=record.status.value,
        type=record.type.value,
        addresses=record.addresses,
        amounts=[str(amount) for amount in record.amounts],
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def from_db(item: dict) -> TradeRecord:
    return TradeRecord(
        hash=item["hash"],
        contract=item["contract"],
        slippage=Slippage(item["slippage"]),
        status=TransactionStatus(item["status"]),
        type=TradeType(item["type"]),
        addresses=item["addresses"],
        amounts=[Amount(amount) for amount in item["amounts"]],
        created_at=item["created_at"],
        updated_at=item["updated_at"],
    )


def filter_query(record: TradeRecord) -> dict:
    return {"hash": record.hash}


def trade_filter_query(trade_filter: TradeFilter) -> dict:
    if trade_filter.contract is None:
        return {}
    return {"contract": trade_filter.contract}


class MongoTradeRepository(TradeRepository):
    collection: Collection

    def __init__(self, client: MongoClient, db_name: str):
        self.collection = client[db_name]["trades"]

    def __len__(self) -> int:
        return self.collection.count_documents({})

    def upsert(self, record: TradeRecord) -> None:
        return self.collection.update_one(filter_query(record), {"$set": to_db(record)}, upsert=True)

    def get(self, hash: TransactionHash) -> Optional[TradeRecord]:
        item = self.collection.find_one(filter={"hash": hash})
        if item is None:
            return None

        return from_db(item)

    def get_all_paginated(self, trade_filter: TradeFilter) -> Iterator[TradeRecord]:
        keys = [("created_at", DESCENDING)]
        for item in self.collection.find(
            trade_filter_query(trade_filter), batch_size=100, skip=trade_filter.skip, limit=trade_filter.limit
        ).sort(keys):
            yield from_db(item)
