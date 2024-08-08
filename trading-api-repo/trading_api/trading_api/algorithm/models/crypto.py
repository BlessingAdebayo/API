import enum
from collections import namedtuple

from pydantic import BaseModel

# This is a namedtuple because the types didn't work well with pydantic
ContractDetails = namedtuple("ContractDetails", ["address", "abi"])


class ChainId(str, enum.Enum):
    RTN = "RTN"  # rinkeby-test-network
    BSC = "BSC"  # binance-smart-chain


class TransactionHash(BaseModel):
    value: str


class PublicKey(BaseModel):
    value: str
