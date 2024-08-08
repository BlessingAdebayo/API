from decimal import Decimal
from typing import Union

from pydantic import BaseModel

from trading_api.algorithm.models.trade import BlockChainError


class PriceQuote(BaseModel):
    symbol: str
    price: Decimal


PriceQuoteResponse = Union[PriceQuote, BlockChainError]
