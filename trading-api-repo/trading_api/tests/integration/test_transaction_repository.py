from datetime import datetime, timezone
from decimal import Decimal

import pytest

from tests.utils import ADDR2, ADDR3, ADDR4, ADDR5, make_transaction
from trading_api.algorithm.models.algorithm import AlgorithmId
from trading_api.algorithm.models.crypto import TransactionHash
from trading_api.algorithm.models.trade import TradeStatus
from trading_api.algorithm.repositories.transaction import MongoTransactionRepository


@pytest.fixture
def persist_transaction_for_other_contract(transaction_repository: MongoTransactionRepository):
    """This makes sure to check that the other tests are not impacted by having other transactions in the DB."""
    trading_contract_address = ADDR4
    transaction = make_transaction(trading_contract_address=trading_contract_address, transaction_hash=ADDR5)
    transaction_repository.persist_transaction(trading_transaction=transaction)
    algorithm_id = AlgorithmId(public_address=trading_contract_address)  # type: ignore

    assert len(list(transaction_repository.get_trading_transactions(algorithm=algorithm_id))) == 1


def test_persist_transaction(
    transaction_repository: MongoTransactionRepository, persist_transaction_for_other_contract
):
    expected_dt = datetime.fromtimestamp(0, timezone.utc)
    transaction = make_transaction(created_at=expected_dt, updated_at=expected_dt)

    transaction_repository.persist_transaction(trading_transaction=transaction)
    transactions = list(
        transaction_repository.get_trading_transactions(algorithm=AlgorithmId(public_address=ADDR2))
    )  # type: ignore

    assert len(transactions) == 1
    transaction = transactions[0]

    assert transaction.relative_amount == Decimal("0.5")
    assert transaction.transaction_hash == ADDR3
    assert transaction.trading_contract_address == ADDR2
    assert transaction.slippage_amount == Decimal("0.05")
    assert transaction.created_at == expected_dt
    assert transaction.updated_at == expected_dt
    assert transaction.status == TradeStatus.TRADE_IN_PROGRESS_OR_NOT_FOUND


def test_update_transaction_status(
    transaction_repository: MongoTransactionRepository, persist_transaction_for_other_contract
):
    expected_dt = datetime.fromtimestamp(0, timezone.utc)
    expected_update_dt = datetime.fromtimestamp(100, timezone.utc)
    updated_status = TradeStatus.TRADE_FAILED
    transaction = make_transaction(created_at=expected_dt, updated_at=expected_dt)
    tx_hash = TransactionHash(value=transaction.transaction_hash)
    algorithm_id = AlgorithmId(public_address=transaction.trading_contract_address)

    transaction_repository.persist_transaction(trading_transaction=transaction)
    transactions = list(transaction_repository.get_trading_transactions(algorithm=algorithm_id))

    assert len(transactions) == 1
    retrieved_tx = transactions[0]
    assert retrieved_tx.status == TradeStatus.TRADE_IN_PROGRESS_OR_NOT_FOUND
    assert retrieved_tx.created_at == expected_dt

    transaction_repository.update_transaction_status(tx_hash, updated_status, timestamp=expected_update_dt)

    transactions = list(transaction_repository.get_trading_transactions(algorithm=algorithm_id))
    retrieved_tx_updated = transactions[0]
    assert len(transactions) == 1
    assert retrieved_tx_updated.transaction_hash == tx_hash.value
    assert retrieved_tx_updated.status == updated_status
    assert retrieved_tx_updated.created_at == expected_dt
    assert retrieved_tx_updated.updated_at == expected_update_dt


def test_update_transaction(transaction_repository: MongoTransactionRepository, persist_transaction_for_other_contract):
    expected_dt = datetime.fromtimestamp(0, timezone.utc)
    expected_update_dt = datetime.fromtimestamp(100, timezone.utc)
    expected_updated_slippage = Decimal("0.10")

    transaction = make_transaction(created_at=expected_dt, updated_at=expected_dt)
    transaction_update = make_transaction(
        created_at=expected_dt, updated_at=expected_update_dt, slippage_amount=expected_updated_slippage
    )

    tx_hash = TransactionHash(value=transaction.transaction_hash)
    algorithm_id = AlgorithmId(public_address=transaction.trading_contract_address)

    transaction_repository.persist_transaction(trading_transaction=transaction)
    transactions = list(transaction_repository.get_trading_transactions(algorithm=algorithm_id))

    assert len(transactions) == 1
    retrieved_tx = transactions[0]
    assert retrieved_tx.transaction_hash == tx_hash.value
    assert retrieved_tx.slippage_amount == Decimal("0.05")
    assert retrieved_tx.created_at == expected_dt
    assert retrieved_tx.updated_at == expected_dt

    transaction_repository.update_transaction(transaction_update)

    transactions = list(transaction_repository.get_trading_transactions(algorithm=algorithm_id))
    retrieved_tx_updated = transactions[0]
    assert len(transactions) == 1
    assert retrieved_tx_updated.transaction_hash == tx_hash.value
    assert retrieved_tx_updated.slippage_amount == expected_updated_slippage
    assert retrieved_tx_updated.created_at == expected_dt
    assert retrieved_tx_updated.updated_at == expected_update_dt
