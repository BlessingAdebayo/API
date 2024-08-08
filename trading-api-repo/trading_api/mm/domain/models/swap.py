from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .address import BeneficiaryAddresses
from .amount import Amounts
from .contract import ContractAddress
from .exchange import Exchange
from .transaction import TransactionHash, TransactionStatus

Seller = str


@dataclass(frozen=True)
class Swap:
    amounts: Amounts
    addresses: BeneficiaryAddresses
    seller: Seller
    exchange: Exchange


@dataclass(frozen=True)
class SwapRecord:
    hash: TransactionHash
    contract: ContractAddress
    status: TransactionStatus
    amounts: Amounts
    addresses: BeneficiaryAddresses
    seller: Seller
    created_at: datetime
    updated_at: datetime


SwapRecords = list[SwapRecord]


@dataclass(frozen=True)
class SwapFilter:
    skip: int
    limit: int
    contract: Optional[ContractAddress] = None
