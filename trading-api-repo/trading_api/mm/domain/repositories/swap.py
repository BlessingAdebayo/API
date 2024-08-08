import abc
from typing import Iterator, Optional

from mm.domain.models import SwapFilter, SwapRecord, TransactionHash


class SwapRepository(abc.ABC):
    @abc.abstractmethod
    def __len__(self) -> int:
        ...

    @abc.abstractmethod
    def upsert(self, record: SwapRecord) -> None:
        ...

    @abc.abstractmethod
    def get(self, hash: TransactionHash) -> Optional[SwapRecord]:
        ...

    @abc.abstractmethod
    def get_all_paginated(self, swap_filter: SwapFilter) -> Iterator[SwapRecord]:
        ...
