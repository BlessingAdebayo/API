import enum
from dataclasses import dataclass

from eth_account import datastructures

from .chain import ChainId

Transaction = dict
TransactionHash = str
TransactionHashes = list[TransactionHash]


class TransactionStatus(str, enum.Enum):
    TRANSACTION_NOT_FOUND = "TRANSACTION_NOT_FOUND"
    TRANSACTION_IN_PROGRESS = "TRANSACTION_IN_PROGRESS"
    TRANSACTION_FAILED = "TRANSACTION_FAILED"
    TRANSACTION_SUCCESSFUL = "TRANSACTION_SUCCESSFUL"


@dataclass(frozen=True)
class SignedTransaction:
    chain: ChainId
    eth: datastructures.SignedTransaction
