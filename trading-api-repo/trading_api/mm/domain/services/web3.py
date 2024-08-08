import abc

from web3 import Web3
from web3.contract import Contract

from mm.domain.models import ChainId, ContractAddress, ContractVersion


class Web3Provider(abc.ABC):
    @abc.abstractmethod
    def get_web3(self, chain: ChainId) -> Web3:
        ...

    @abc.abstractmethod
    def get_ecr_contract(self, chain: ChainId) -> Contract:
        ...

    @abc.abstractmethod
    def get_contract(
        self, contract: ContractAddress, chain: ChainId, version: ContractVersion = ContractVersion.V1_0
    ) -> Contract:
        ...
