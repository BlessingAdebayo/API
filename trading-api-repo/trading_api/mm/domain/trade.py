from datetime import datetime

from mm.domain.models import ContractAddress, Trade, TradeRecord, TransactionHash, TransactionStatus
from mm.domain.repositories import TradeRepository, WalletKeyRepository
from mm.domain.services import KeyManagementService, TransactionService


def trade(
    contract: ContractAddress,
    trade: Trade,
    tx_service: TransactionService,
    key_service: KeyManagementService,
    keys: WalletKeyRepository,
    trades: TradeRepository,
) -> TransactionHash:

    pair = keys.get_by_contract(contract)

    tx = tx_service.create_trade_transaction(pair, trade)
    signed_tx = key_service.sign_transaction(transaction=tx, pair=pair, chain=pair.chain)

    tx_hash = tx_service.send(signed_tx)

    tx_record = TradeRecord(
        hash=tx_hash,
        contract=contract,
        slippage=trade.slippage,
        status=TransactionStatus.TRANSACTION_IN_PROGRESS,
        type=trade.type,
        addresses=trade.addresses,
        amounts=trade.amounts,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    trades.upsert(tx_record)

    return tx_hash
