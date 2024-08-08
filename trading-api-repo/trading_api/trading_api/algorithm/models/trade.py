import enum
from datetime import datetime
from decimal import Context, Decimal
from typing import List, Optional, Union

from eth_typing import ChecksumAddress
from pydantic import BaseModel, validator
from pymongo import ASCENDING, DESCENDING

from trading_api.algorithm.models.algorithm import AlgorithmId, AlgorithmIsLocked, AlgorithmWasLocked
from trading_api.algorithm.models.crypto import TransactionHash

BC_INT_PRECISION = 18  # Needs to be an integer for the `prec` parameter in `Context`.
BC_INT_OFFSET = Decimal("10") ** BC_INT_PRECISION


class Timestamp(BaseModel):
    value: int


class Slippage(BaseModel):
    amount: Decimal

    @property
    def raw_amount(self):
        """Property that returns the raw slippage for smart contract usage."""
        return Context(prec=BC_INT_PRECISION).create_decimal(BC_INT_OFFSET - (BC_INT_OFFSET * self.amount))


class BuyTrade(BaseModel):
    algorithm_id: AlgorithmId
    slippage: Slippage
    relative_amount: Decimal


class BuyTradeV2(BaseModel):
    algorithm_id: AlgorithmId
    slippage: Slippage
    relative_amount: Decimal
    symbol: str


class SellTrade(BaseModel):
    algorithm_id: AlgorithmId
    slippage: Slippage
    relative_amount: Decimal


class SellTradeV2(BaseModel):
    algorithm_id: AlgorithmId
    slippage: Slippage
    relative_amount: Decimal
    symbol: str


MultiTokenTrade = Union[BuyTradeV2, SellTradeV2]

Trade = Union[MultiTokenTrade, BuyTrade, SellTrade]


class TradeRequest(BaseModel):
    trade: Trade


class StatusRequest(BaseModel):
    algorithm_id: AlgorithmId
    transaction_hash: TransactionHash
    timeout_in_seconds: int

    @validator("timeout_in_seconds")
    def timeout_range(cls, timeout_value):
        assert 120 >= timeout_value >= 0
        return timeout_value


class InsufficientFunds(BaseModel):
    algorithm_id: AlgorithmId
    reason: str = "Not enough funds in algorithm contract to trade."


class BlockChainError(BaseModel):
    algorithm_id: AlgorithmId
    reason: str = "Blockchain error occurred."
    error: str = ""


class TradeStatus(str, enum.Enum):
    TRADE_IN_PROGRESS_OR_NOT_FOUND = "TRADE_IN_PROGRESS_OR_NOT_FOUND"
    TRADE_FAILED = "TRADE_FAILED"
    TRADE_SUCCESSFUL = "TRADE_SUCCESSFUL"


class TradeInProgressOrNotFoundResponse(BaseModel):
    code: TradeStatus = TradeStatus.TRADE_IN_PROGRESS_OR_NOT_FOUND
    message: str = "Trade is in progress or cannot be found."


class TradeFailedResponse(BaseModel):
    code: TradeStatus = TradeStatus.TRADE_FAILED
    message: str = "Trade failed."


class TradeSuccessfulResponse(BaseModel):
    code: TradeStatus = TradeStatus.TRADE_SUCCESSFUL
    message: str = "Trade successful."


class TradeType(str, enum.Enum):
    SELL = "SELL"
    BUY = "BUY"


class TradeTypeLower(str, enum.Enum):
    SELL = "sell"
    BUY = "buy"


class TradingTransaction(BaseModel):
    transaction_hash: str
    trading_contract_address: ChecksumAddress
    slippage_amount: Decimal
    relative_amount: Decimal
    symbol: Optional[str]
    status: TradeStatus
    trade_type: TradeType
    created_at: datetime
    updated_at: datetime

    def filter_query(self) -> dict:
        return {"transaction_hash": self.transaction_hash}

    @staticmethod
    def indexes() -> List:
        return [[("trading_contract_address", ASCENDING), ("created_at", DESCENDING)]]

    class Config:
        arbitrary_types_allowed = True


class TransactionPage(BaseModel):
    transactions: List[TradingTransaction]
    page: int
    page_size: int
    total_pages: int
    total: int


TradeRequestResponse = Union[AlgorithmIsLocked, AlgorithmWasLocked, InsufficientFunds, BlockChainError]
TradeStatusResponse = Union[TradeSuccessfulResponse, TradeInProgressOrNotFoundResponse, TradeFailedResponse]
