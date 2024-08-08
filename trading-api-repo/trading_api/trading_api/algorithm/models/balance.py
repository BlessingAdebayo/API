from decimal import Decimal
from typing import Union

from pydantic import BaseModel

from trading_api.algorithm.models.trade import BlockChainError


class TotalSupply(BaseModel):
    amount: Decimal


class RelativeAmount(BaseModel):
    amount: Decimal


class AlgorithmBalance(BaseModel):
    supply: TotalSupply
    ratio: RelativeAmount


class AlgorithmBalanceV2(BaseModel):
    supply: TotalSupply


AlgorithmBalanceResponse = Union[AlgorithmBalanceV2, AlgorithmBalance, BlockChainError]
