from mm.domain.models import ContractAddress, Release, TransactionHash
from mm.domain.repositories import WalletKeyRepository
from mm.domain.services import KeyManagementService, TransactionService


def release_for(
    contract: ContractAddress,
    release: Release,
    tx_service: TransactionService,
    key_service: KeyManagementService,
    keys: WalletKeyRepository,
) -> TransactionHash:
    pair = keys.get_by_contract(contract)

    tx = tx_service.create_release_for_transaction(pair=pair, release=release)
    signed_tx = key_service.sign_transaction(transaction=tx, pair=pair, chain=pair.chain)
    tx_hash = tx_service.send(signed_tx)

    return tx_hash
