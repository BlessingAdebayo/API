from mm.domain.models import ContractAddress, Stake, TransactionHash
from mm.domain.repositories import WalletKeyRepository
from mm.domain.services import KeyManagementService, TransactionService


def stake_in_liquidity_maker(
    contract: ContractAddress,
    stake: Stake,
    tx_service: TransactionService,
    key_service: KeyManagementService,
    keys: WalletKeyRepository,
) -> TransactionHash:
    pair = keys.get_by_contract(contract)

    tx = tx_service.create_stake_in_liquidity_maker_transaction(pair=pair, stake=stake)
    signed_tx = key_service.sign_transaction(transaction=tx, pair=pair, chain=pair.chain)

    tx_hash = tx_service.send(signed_tx)

    return tx_hash
