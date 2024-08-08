import enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .address import BeneficiaryAddresses
from .amount import Amounts
from .contract import ContractAddress
from .exchange import Exchange
from .slippage import Slippage
from .transaction import TransactionHash, TransactionStatus


class TradeType(str, enum.Enum):
    SELL = "SELL"
    BUY = "BUY"


@dataclass(frozen=True)
class Trade:
    type: TradeType
    amounts: Amounts
    addresses: BeneficiaryAddresses
    slippage: Slippage
    exchange: Exchange


@dataclass(frozen=True)
class TradeRecord:
    hash: TransactionHash
    contract: ContractAddress
    slippage: Slippage
    status: TransactionStatus
    type: TradeType
    amounts: Amounts
    addresses: BeneficiaryAddresses
    created_at: datetime
    updated_at: datetime


TradeRecords = list[TradeRecord]


@dataclass(frozen=True)
class TradeFilter:
    skip: int
    limit: int
    contract: Optional[ContractAddress] = None
