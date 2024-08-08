import abc

from mm.domain.models import (
    ChainId,
    KeyAddressPair,
    Release,
    SignedTransaction,
    Stake,
    Swap,
    Trade,
    Transaction,
    TransactionHash,
    TransactionStatus,
)


class TransactionService(abc.ABC):
    @abc.abstractmethod
    def create_trade_transaction(self, pair: KeyAddressPair, trade: Trade) -> Transaction:
        ...

    @abc.abstractmethod
    def create_swap_transaction(self, pair: KeyAddressPair, swap: Swap) -> Transaction:
        ...

    @abc.abstractmethod
    def create_stake_in_liquidity_maker_transaction(self, pair: KeyAddressPair, stake: Stake) -> Transaction:
        ...

    @abc.abstractmethod
    def create_release_for_transaction(self, pair: KeyAddressPair, release: Release) -> Transaction:
        ...

    @abc.abstractmethod
    def send(self, transaction: SignedTransaction) -> TransactionHash:
        ...

    @abc.abstractmethod
    def get_status(self, hash: TransactionHash, chain: ChainId) -> TransactionStatus:
        ...
