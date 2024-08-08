from datetime import datetime

from mm.domain.models import ContractAddress, Swap, SwapRecord, TransactionHash, TransactionStatus
from mm.domain.repositories import SwapRepository, WalletKeyRepository
from mm.domain.services import KeyManagementService, TransactionService


def swap(
    contract: ContractAddress,
    swap: Swap,
    tx_service: TransactionService,
    key_service: KeyManagementService,
    keys: WalletKeyRepository,
    swaps: SwapRepository,
) -> TransactionHash:

    pair = keys.get_by_contract(contract)

    tx = tx_service.create_swap_transaction(pair=pair, swap=swap)
    signed_tx = key_service.sign_transaction(transaction=tx, pair=pair, chain=pair.chain)

    tx_hash = tx_service.send(signed_tx)

    swap_record = SwapRecord(
        hash=tx_hash,
        contract=contract,
        status=TransactionStatus.TRANSACTION_IN_PROGRESS,
        amounts=swap.amounts,
        addresses=swap.addresses,
        seller=swap.seller,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    swaps.upsert(swap_record)

    return tx_hash
