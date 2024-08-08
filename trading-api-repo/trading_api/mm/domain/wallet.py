from typing import Iterable

from mm.domain.models import ContractAddress, KeyAddressPair, WalletAddress
from mm.domain.models.contract import ContractSpec
from mm.domain.repositories import WalletKeyRepository
from mm.domain.services import KeyManagementService


def create_wallet_key_pairs(
    count: int, keys: WalletKeyRepository, kms: KeyManagementService
) -> Iterable[KeyAddressPair]:
    for _ in range(count):
        address = kms.create_key_address()
        keys.upsert(address)

        yield address


def link_contract_to_wallet(spec: ContractSpec, wallet: WalletAddress, keys: WalletKeyRepository):
    pair = keys.get_by_wallet(wallet=wallet)
    pair.spec = spec
    keys.upsert(pair)

    return
