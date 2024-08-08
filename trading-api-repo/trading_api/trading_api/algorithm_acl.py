from decimal import Decimal
from typing import Union

from eth_typing import ChecksumAddress
from pydantic import BaseModel

from trading_api.algorithm.models.algorithm import AlgorithmId
from trading_api.algorithm.models.trade import (
    BuyTrade,
    BuyTradeV2,
    SellTrade,
    SellTradeV2,
    Slippage,
    StatusRequest,
    TradeRequest,
    TradeType,
    TradeTypeLower,
    TransactionHash,
)


class StatusRequestV2(BaseModel):
    transaction_hash: ChecksumAddress
    timeout_in_seconds: int = 0

    def to_status(self, algorithm_id: ChecksumAddress) -> StatusRequest:
        return StatusRequest(
            algorithm_id=AlgorithmId(public_address=algorithm_id),
            transaction_hash=TransactionHash(value=self.transaction_hash),
            timeout_in_seconds=self.timeout_in_seconds,
        )


class TradeRequestV2(BaseModel):
    trade_type: Union[TradeType, TradeTypeLower]
    slippage_amount: Decimal = Decimal("0.005")
    relative_amount: Decimal = Decimal("1")
    symbol: str

    def to_buy(self, algorithm_id: ChecksumAddress) -> BuyTradeV2:
        return BuyTradeV2(
            algorithm_id=AlgorithmId(public_address=algorithm_id),
            slippage=Slippage(amount=self.slippage_amount),
            relative_amount=self.relative_amount,
            symbol=self.symbol,
        )

    def to_sell(self, algorithm_id: ChecksumAddress) -> SellTradeV2:
        return SellTradeV2(
            algorithm_id=AlgorithmId(public_address=algorithm_id),
            slippage=Slippage(amount=self.slippage_amount),
            relative_amount=self.relative_amount,
            symbol=self.symbol,
        )


class BuyRequestV2(BaseModel):
    slippage_amount: Decimal = Decimal("0.005")
    relative_amount: Decimal = Decimal("1")
    symbol: str

    def to_buy(self, algorithm_id: ChecksumAddress) -> BuyTradeV2:
        return BuyTradeV2(
            algorithm_id=AlgorithmId(public_address=algorithm_id),
            slippage=Slippage(amount=self.slippage_amount),
            relative_amount=self.relative_amount,
            symbol=self.symbol,
        )


class SellRequestV2(BaseModel):
    slippage_amount: Decimal = Decimal("0.005")
    relative_amount: Decimal = Decimal("1")
    symbol: str

    def to_sell(self, algorithm_id: ChecksumAddress) -> SellTradeV2:
        return SellTradeV2(
            algorithm_id=AlgorithmId(public_address=algorithm_id),
            slippage=Slippage(amount=self.slippage_amount),
            relative_amount=self.relative_amount,
            symbol=self.symbol,
        )


class BuyRequest(TradeRequest):
    trade: BuyTrade

    def to_buy(self) -> BuyTrade:
        return self.trade


class SellRequest(TradeRequest):
    trade: SellTrade

    def to_sell(self) -> SellTrade:
        return self.trade
