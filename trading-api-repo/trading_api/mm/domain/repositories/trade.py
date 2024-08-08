import abc
from typing import Iterator, Optional

from mm.domain.models import TradeFilter, TradeRecord, TransactionHash


class TradeRepository(abc.ABC):
    @abc.abstractmethod
    def __len__(self) -> int:
        ...

    @abc.abstractmethod
    def upsert(self, record: TradeRecord) -> None:
        ...

    @abc.abstractmethod
    def get(self, hash: TransactionHash) -> Optional[TradeRecord]:
        ...

    @abc.abstractmethod
    def get_all_paginated(self, trade_filter: TradeFilter) -> Iterator[TradeRecord]:
        ...
