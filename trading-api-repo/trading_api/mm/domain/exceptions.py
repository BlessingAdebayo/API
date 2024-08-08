from mm.domain.models import ContractAddress, Release, Stake, Swap, Trade, TransactionHash, WalletAddress


class InvalidCredentials(Exception):
    def __init__(self):
        super().__init__("ERROR: Incorrect username or password")


class WalletNotFound(Exception):
    def __init__(self, address: WalletAddress):
        super().__init__(f"ERROR: Cannot find wallet-key-pair for {address=}")


class ContractNotFound(Exception):
    def __init__(self, address: ContractAddress):
        super().__init__(f"ERROR: No smart contract linked for {address=}")


class BlockchainError(Exception):
    @classmethod
    def from_exception(cls, exception: Exception) -> "BlockchainError":
        return cls(f"ERROR: Could not send transaction to blockchain {exception}")

    @classmethod
    def from_trade(cls, trade: Trade) -> "BlockchainError":
        return cls(f"ERROR: Could not build transaction for blockchain with {trade=}")

    @classmethod
    def from_swap(cls, swap: Swap) -> "BlockchainError":
        return cls(f"ERROR: Could not build transaction for blockchain with {swap=}")

    @classmethod
    def from_stake(cls, stake: Stake) -> "BlockchainError":
        return cls(f"ERROR: Could not build transaction for blockchain with {stake=}")

    @classmethod
    def from_release(cls, release: Release) -> "BlockchainError":
        return cls(f"ERROR: Could not build transaction for blockchain with {release=}")

    @classmethod
    def from_transaction_receipt(cls, hash: TransactionHash) -> "BlockchainError":
        return cls(f"ERROR: Could not retrieve transaction receipt for {hash=}")
