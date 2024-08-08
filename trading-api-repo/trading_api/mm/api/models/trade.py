from pydantic import BaseModel, validator

from mm.domain.models import (
    Amounts,
    BeneficiaryAddresses,
    ContractAddress,
    Exchange,
    Slippage,
    Trade,
    TradeType,
    TransactionHash,
)


class CreateTradeRequest(BaseModel):
    contract: ContractAddress
    type: TradeType
    amounts: Amounts
    addresses: BeneficiaryAddresses
    slippage: Slippage
    exchange: Exchange

    @validator("slippage")
    def slippage_must_be_in_closed_interval_0_to_1(cls, slippage):
        if slippage < 0 or slippage > 1:
            raise ValueError("must be greater than or equal to 0 and less than or equal to 1")
        return slippage

    def to_trade(self):
        return Trade(
            type=self.type,
            amounts=self.amounts,
            addresses=self.addresses,
            slippage=self.slippage,
            exchange=self.exchange,
        )


class CreateTradeResponse(BaseModel):
    transaction_hash: TransactionHash


class RetrieveTradesResponse(BaseModel):
    trades: list
    page: int
    page_size: int
    total_pages: int
    total: int
