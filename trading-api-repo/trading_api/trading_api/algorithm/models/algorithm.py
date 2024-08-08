import enum
from typing import Optional

from eth_typing import ChecksumAddress
from pydantic import BaseModel, validator
from web3 import Web3

from trading_api import API_ROOT_PATH
from trading_api.algorithm.models.crypto import ChainId, PublicKey, TransactionHash


class TradingContractVersion(str, enum.Enum):
    V1_0 = "1.0"
    V1_1 = "1.1"
    V2_0 = "2.0"


class TradingContract(BaseModel):
    version: TradingContractVersion

    @property
    def name(self):
        if self.version is TradingContractVersion.V2_0:
            return "MultiTokenTradingContract"
        return "TradingContract"

    @property
    def location(self):
        return (
            API_ROOT_PATH
            / ".contracts"
            / f"v{self.version.value}"
            / "artifacts"
            / "contracts"
            / f"{self.name}.sol"
            / f"{self.name}.json"
        )


class Algorithm(BaseModel):
    trading_contract_address: ChecksumAddress
    controller_wallet_address: ChecksumAddress
    trading_contract: TradingContract
    chain_id: ChainId
    disabled: bool = False

    @validator("trading_contract_address", "controller_wallet_address")
    def is_checksum_address(cls, value):
        address = Web3.toChecksumAddress(value)
        assert Web3.isChecksumAddress(address)
        return address


class AlgorithmInDB(BaseModel):
    trading_contract_address: ChecksumAddress
    controller_wallet_address: ChecksumAddress
    trading_contract: Optional[TradingContract] = None
    chain_id: ChainId
    disabled: bool = False
    hashed_password: str
    nonce_counter: Optional[int]

    @classmethod
    def parse_obj(cls, *args, **kwargs):
        data = args[0]
        if "trading_contract_version" in data and data["trading_contract_version"] < TradingContractVersion.V2_0:
            data["trading_contract"] = {"version": data["trading_contract_version"]}

        return super().parse_obj(*args, **kwargs)

    def filter_query(self) -> dict:
        return {"trading_contract_address": self.trading_contract_address}


class RegisterAlgorithm(BaseModel):
    trading_contract_address: ChecksumAddress
    controller_wallet_address: ChecksumAddress
    trading_contract_version: TradingContractVersion
    chain_id: ChainId
    disabled: bool = False
    unhashed_password: str


class RegisteredAlgorithmResponse(BaseModel):
    status: str = "OK"


class FailedToRegisterAlgorithmResponse(BaseModel):
    status: str = "FAILED"


class DisableAlgorithm(BaseModel):
    trading_contract_address: ChecksumAddress


class DisabledAlgorithmResponse(BaseModel):
    status: str = "OK"


class FailedToDisableAlgorithmResponse(BaseModel):
    status: str = "FAILED"


class AlgorithmId(BaseModel):
    public_address: ChecksumAddress


class AlgorithmTransaction(BaseModel):
    algorithm_id: AlgorithmId
    transaction_hash: TransactionHash


class NewAlgorithmLock(BaseModel):
    algorithm_id: AlgorithmId
    symbol: str


class TradeResponseLockType(str, enum.Enum):
    NOW_LOCKED = "SUCCESS:ALGORITHM-IS-NOW-LOCKED"
    WAS_LOCKED = "DENIED:ALGORITHM-ALREADY-LOCKED"


class AlgorithmIsLocked(BaseModel):
    lock: NewAlgorithmLock
    transaction_hash: TransactionHash
    lock_type: TradeResponseLockType = TradeResponseLockType.NOW_LOCKED


class AlgorithmWasLocked(BaseModel):
    lock: NewAlgorithmLock  # This lock is not actually new.
    transaction_hash: Optional[TransactionHash]
    lock_type: TradeResponseLockType = TradeResponseLockType.WAS_LOCKED


class AlgorithmPublicKey(BaseModel):
    algorithm_id: AlgorithmId
    public_key: PublicKey
