import json
import logging
from abc import ABC, abstractmethod
from decimal import Decimal
from pathlib import Path
from typing import Optional

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress
from web3 import Web3
from web3.contract import Contract

from trading_api import EnvVar, get_env_force
from trading_api.algorithm.models.algorithm import Algorithm
from trading_api.algorithm.models.crypto import ChainId, ContractDetails

GAS_AMOUNT = Decimal(100_000 / 1e18)
GAS_PRICE = Decimal(5e9 / 1e18)

logger = logging.getLogger(__name__)


class Web3Provider(ABC):
    @abstractmethod
    def get_web3(self, chain: ChainId) -> Web3:
        pass

    @abstractmethod
    def get_trading_contract(self, algorithm: Algorithm) -> Contract:
        pass

    @abstractmethod
    def get_trading_contract_tools(self, algorithm: Algorithm) -> Contract:
        pass

    @abstractmethod
    def get_ecr_contract(self, chain: ChainId) -> Contract:
        pass

    @abstractmethod
    def get_account(self, algorithm_public_address: ChecksumAddress) -> LocalAccount:
        pass

    @staticmethod
    def get_gas_amount() -> Decimal:
        return GAS_AMOUNT

    @staticmethod
    def get_gas_price() -> Decimal:
        return GAS_PRICE


class HttpWeb3Provider(Web3Provider):
    def __init__(
        self,
        web3_bsc_uri: str,
        web3_rtn_uri: str,
        ecr_contract_bsc: ContractDetails,
        ecr_contract_rtn: ContractDetails,
        private_key: str = None,
    ):
        """

        :param ecr_contract_bsc:
        :param private_key: Only used for testing purposes, in prod we don't use this and use the KMS instead.
        """
        self._http_rtn_web3: Optional[Web3] = None
        self._http_bsc_web3: Optional[Web3] = None
        self._web3_rtn_uri = web3_rtn_uri
        self._web3_bsc_uri = web3_bsc_uri
        self._ecr_contract_bsc = ecr_contract_bsc
        self._ecr_contract_rtn = ecr_contract_rtn
        self._private_key = private_key

    def get_account(self, algorithm_public_address: ChecksumAddress) -> LocalAccount:
        return Account.from_key(self._private_key)

    def get_trading_contract(self, algorithm: Algorithm) -> Contract:
        abi = self.load_abi(Path(algorithm.trading_contract.location))

        return self.get_web3(chain=algorithm.chain_id).eth.contract(
            address=algorithm.trading_contract_address, abi=abi
        )  # type: ignore

    def get_trading_contract_tools(self, algorithm: Algorithm) -> Contract:
        abi = self.load_abi(Path(get_env_force(EnvVar.TRADING_CONTRACT_TOOLS_JSON_PATH)))

        if algorithm.chain_id == ChainId.BSC:
            address = get_env_force(EnvVar.TRADING_CONTRACT_TOOLS_ADDRESS_BSC)
        if algorithm.chain_id == ChainId.RTN:
            address = get_env_force(EnvVar.TRADING_CONTRACT_TOOLS_ADDRESS_RTN)

        return self.get_web3(chain=algorithm.chain_id).eth.contract(address=address, abi=abi)  # type: ignore

    def get_ecr_contract(self, chain: ChainId) -> Contract:
        contract = self._load_ecr_contract_details(chain)

        return self.get_web3(chain=chain).eth.contract(address=contract.address, abi=contract.abi)  # type: ignore

    def get_web3(self, chain: ChainId) -> Web3:
        if chain == chain.BSC:
            return self.bsc_web3()
        if chain == chain.RTN:
            return self.rtn_web3()

        raise ValueError(f"ChainId {chain} is not implemented.")

    @staticmethod
    def load_abi(path: Path) -> dict:
        with open(path) as f:
            info_json = json.load(f)
            abi = info_json["abi"]

        return abi

    def rtn_web3(self) -> Web3:
        if self._http_rtn_web3 is None:
            self._http_rtn_web3 = Web3(Web3.HTTPProvider(self._web3_rtn_uri))
            return self._http_rtn_web3

        return self._http_rtn_web3

    def bsc_web3(self) -> Web3:
        if self._http_bsc_web3 is None:
            self._http_bsc_web3 = Web3(Web3.HTTPProvider(self._web3_bsc_uri))
            return self._http_bsc_web3

        return self._http_bsc_web3

    def _load_ecr_contract_details(self, chain) -> ContractDetails:
        if chain == chain.BSC:
            return self._ecr_contract_bsc
        if chain == chain.RTN:
            return self._ecr_contract_rtn

        raise ValueError(f"ChainId {chain} is not implemented.")


class InMemoryWeb3Provider(Web3Provider):
    def __init__(self, w3: Web3, trading_contract: Contract, trading_contract_tools: Contract, private_key: str):
        self._private_key = private_key
        self._w3 = w3
        self._trading_contract = trading_contract
        self._trading_contract_tools = trading_contract_tools

    def get_ecr_contract(self, chain: ChainId) -> Contract:
        pass

    def get_account(self, algorithm_public_address: ChecksumAddress) -> LocalAccount:
        return Account.from_key(self._private_key)

    def get_trading_contract(self, algorithm: Algorithm) -> Contract:
        return self._trading_contract

    def get_trading_contract_tools(self, algorithm: Algorithm) -> Contract:
        return self._trading_contract_tools

    def get_web3(self, chain: ChainId) -> Web3:
        return self._w3
