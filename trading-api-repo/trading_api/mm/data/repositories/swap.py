from typing import Iterator, Optional

from pymongo import DESCENDING, MongoClient
from pymongo.collection import Collection

from mm.domain.models import Amount, SwapFilter, SwapRecord, TransactionHash, TransactionStatus
from mm.domain.repositories import SwapRepository


class InMemorySwapRepository(SwapRepository):
    def __init__(self):
        self.memory: dict[TransactionHash, SwapRecord] = {}

    def __len__(self) -> int:
        return len(self.memory)

    def upsert(self, record: SwapRecord) -> None:
        self.memory[record.hash] = record

    def get(self, hash: TransactionHash) -> Optional[SwapRecord]:
        return self.memory.get(hash)

    def get_all_paginated(self, swap_filter: SwapFilter) -> Iterator[SwapRecord]:
        # Pagination not implemented.
        yield from filter(
            lambda x: swap_filter.contract is None or x.contract == swap_filter.contract, self.memory.values()
        )


def to_db(record: SwapRecord) -> dict:
    return dict(
        hash=record.hash,
        contract=record.contract,
        status=record.status.value,
        amounts=[str(amount) for amount in record.amounts],
        addresses=record.addresses,
        seller=record.seller,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def from_db(item: dict) -> SwapRecord:
    return SwapRecord(
        hash=item["hash"],
        contract=item["contract"],
        status=TransactionStatus(item["status"]),
        amounts=[Amount(amount) for amount in item["amounts"]],
        addresses=item["addresses"],
        seller=item["seller"],
        created_at=item["created_at"],
        updated_at=item["updated_at"],
    )


def filter_query(record: SwapRecord) -> dict:
    return {"hash": record.hash}


def swap_filter_query(swap_filter: SwapFilter) -> dict:
    if swap_filter.contract is None:
        return {}
    return {"contract": swap_filter.contract}


class MongoSwapRepository(SwapRepository):
    collection: Collection

    def __init__(self, client: MongoClient, db_name: str):
        self.collection = client[db_name]["swaps"]

    def __len__(self) -> int:
        return self.collection.count_documents({})

    def upsert(self, record: SwapRecord) -> None:
        return self.collection.update_one(filter_query(record), {"$set": to_db(record)}, upsert=True)

    def get(self, hash: TransactionHash) -> Optional[SwapRecord]:
        item = self.collection.find_one(filter={"hash": hash})
        if item is None:
            return None

        return from_db(item)

    def get_all_paginated(self, swap_filter: SwapFilter) -> Iterator[SwapRecord]:
        keys = [("created_at", DESCENDING)]
        for item in self.collection.find(
            swap_filter_query(swap_filter), batch_size=100, skip=swap_filter.skip, limit=swap_filter.limit
        ).sort(keys):
            yield from_db(item)
