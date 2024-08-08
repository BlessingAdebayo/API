import abc

from mm.domain.models import ContractAddress, KeyAddressPair, WalletAddress


class WalletKeyRepository(abc.ABC):
    @abc.abstractmethod
    def upsert(self, pair: KeyAddressPair) -> None:
        ...

    @abc.abstractmethod
    def get_by_wallet(self, wallet: WalletAddress) -> KeyAddressPair:
        ...

    @abc.abstractmethod
    def get_by_contract(self, contract: ContractAddress) -> KeyAddressPair:
        ...

    @abc.abstractmethod
    def delete_all(self):
        ...
