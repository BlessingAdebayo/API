import abc

from mm.domain.models import ChainId, KeyAddressPair, SignedTransaction, Transaction


class KeyManagementService(abc.ABC):
    @abc.abstractmethod
    def create_key_address(self) -> KeyAddressPair:
        ...

    @abc.abstractmethod
    def sign_transaction(self, transaction: Transaction, pair: KeyAddressPair, chain: ChainId) -> SignedTransaction:
        ...
