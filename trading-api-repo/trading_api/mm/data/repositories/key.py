from pymongo import MongoClient
from pymongo.collection import Collection

from mm.domain.exceptions import ContractNotFound, WalletNotFound
from mm.domain.models import ContractAddress, KeyAddressPair, WalletAddress
from mm.domain.models.contract import ContractSpec
from mm.domain.repositories import WalletKeyRepository


class InMemoryWalletKeyRepository(WalletKeyRepository):
    def __init__(self):
        self.memory: dict[WalletAddress, KeyAddressPair] = {}

    def upsert(self, pair: KeyAddressPair) -> None:
        self.memory[pair.wallet] = pair

    def get_by_wallet(self, wallet: WalletAddress) -> KeyAddressPair:
        pair = self.memory.get(wallet)
        if pair is None:
            raise WalletNotFound(wallet)

        return pair

    def get_by_contract(self, contract: ContractAddress) -> KeyAddressPair:
        for _, pair in self.memory.items():
            if pair.contract == contract:
                return pair
        raise ContractNotFound(contract)

    def delete_all(self):
        self.memory = {}


def to_db(pair: KeyAddressPair) -> dict:
    spec = None
    if pair.spec is not None:
        spec = dict(address=pair.spec.address, chain=pair.spec.chain)

    return dict(
        internal_id=pair.internal_id,
        external_id=pair.external_id,
        wallet=pair.wallet,
        spec=spec,
    )


def from_db(item: dict) -> KeyAddressPair:
    spec = item.get("spec")
    if spec is not None:
        spec = ContractSpec(
            address=spec["address"],
            chain=spec["chain"],
        )
    return KeyAddressPair(
        internal_id=item["internal_id"],
        external_id=item["external_id"],
        wallet=item["wallet"],
        spec=spec,
    )


class MongoWalletKeyRepository(WalletKeyRepository):
    collection: Collection

    def __init__(self, client: MongoClient, db_name: str):
        self.collection = client[db_name]["controller_wallet_keys"]

    def upsert(self, pair: KeyAddressPair) -> None:
        return self.collection.update_one(pair.filter_query(), {"$set": to_db(pair)}, upsert=True)

    def get_by_wallet(self, wallet: WalletAddress) -> KeyAddressPair:
        item = self.collection.find_one(filter={"wallet": wallet})
        if item is None:
            raise WalletNotFound(wallet)

        return from_db(item)

    def get_by_contract(self, contract: ContractAddress) -> KeyAddressPair:
        item = self.collection.find_one(filter={"spec.address": contract})
        if item is None:
            raise ContractNotFound(contract)

        return from_db(item)

    def delete_all(self):
        self.collection.delete_many({})
