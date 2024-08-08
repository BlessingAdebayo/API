import logging
from datetime import datetime

from mm.domain.models import SwapRecord, TradeRecord, TransactionHash, TransactionStatus
from mm.domain.repositories import SwapRepository, TradeRepository, WalletKeyRepository
from mm.domain.services import TransactionService

logger = logging.getLogger(__name__)


def get_transaction_status(
    tx_hash: TransactionHash,
    tx_service: TransactionService,
    trades: TradeRepository,
    swaps: SwapRepository,
    keys: WalletKeyRepository,
) -> TransactionStatus:
    tx = trades.get(tx_hash) or swaps.get(tx_hash)
    if tx is None:
        return TransactionStatus.TRANSACTION_NOT_FOUND

    chain = keys.get_by_contract(tx.contract).chain
    tx_status = tx_service.get_status(tx_hash, chain)

    if isinstance(tx, TradeRecord):
        trades.upsert(
            TradeRecord(
                hash=tx.hash,
                contract=tx.contract,
                slippage=tx.slippage,
                status=tx_status,
                type=tx.type,
                addresses=tx.addresses,
                amounts=tx.amounts,
                created_at=tx.created_at,
                updated_at=datetime.utcnow(),
            )
        )
    elif isinstance(tx, SwapRecord):
        swaps.upsert(
            SwapRecord(
                hash=tx.hash,
                contract=tx.contract,
                status=tx_status,
                amounts=tx.amounts,
                addresses=tx.addresses,
                seller=tx.seller,
                created_at=tx.created_at,
                updated_at=datetime.utcnow(),
            )
        )

    return tx_status
