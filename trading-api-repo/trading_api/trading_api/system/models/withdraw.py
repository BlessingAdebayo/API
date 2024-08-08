from decimal import Decimal

from eth_typing import ChecksumAddress
from pydantic import BaseModel

from trading_api.algorithm.models.algorithm import Algorithm


class WithdrawFundsRequest(BaseModel):
    relative_amount: Decimal


class WithdrawFundsResponse(BaseModel):
    algorithm: Algorithm
    recipient: ChecksumAddress
    transaction_hash: ChecksumAddress
