import enum
from dataclasses import dataclass

from .chain import ChainId

ContractAddress = str

ABI = dict


@dataclass(frozen=True)
class ContractDetails:
    address: ContractAddress
    abi: ABI


@dataclass(frozen=True)
class ContractSpec:
    address: ContractAddress
    chain: ChainId


class ContractVersion(str, enum.Enum):
    V1_0 = "v1.0"
