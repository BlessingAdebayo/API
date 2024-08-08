from datetime import datetime, timedelta, timezone

from tests.utils import ADDR2, ADDR3, ADDR4, make_transaction
from trading_api.algorithm.repositories.transaction import MongoTransactionRepository


def test_transaction_api(app_inst, system_access_header, transaction_repository: MongoTransactionRepository):
    expected_dt = datetime.fromtimestamp(0, timezone.utc)
    transaction = make_transaction(transaction_hash=ADDR3, created_at=expected_dt, updated_at=expected_dt)
    transaction_repository.persist_transaction(trading_transaction=transaction)

    expected_dt += timedelta(hours=1)
    transaction = make_transaction(transaction_hash=ADDR4, created_at=expected_dt, updated_at=expected_dt)
    transaction_repository.persist_transaction(trading_transaction=transaction)

    response = app_inst.client.get(f"/api/v1/algorithms/{ADDR2}/transactions", headers=system_access_header)

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 0
    assert data["page_size"] == 50
    assert data["total"] == 2
    assert data["total_pages"] == 1
    assert data["transactions"][0] == {
        "created_at": "1970-01-01T01:00:00+00:00",
        "relative_amount": 0.5,
        "slippage_amount": 0.05,
        "symbol": None,
        "status": "TRADE_IN_PROGRESS_OR_NOT_FOUND",
        "trading_contract_address": ADDR2,
        "transaction_hash": ADDR4,
        "updated_at": "1970-01-01T01:00:00+00:00",
        "trade_type": "BUY",
    }
    assert data["transactions"][1] == {
        "created_at": "1970-01-01T00:00:00+00:00",
        "relative_amount": 0.5,
        "slippage_amount": 0.05,
        "symbol": None,
        "status": "TRADE_IN_PROGRESS_OR_NOT_FOUND",
        "trading_contract_address": ADDR2,
        "transaction_hash": ADDR3,
        "updated_at": "1970-01-01T00:00:00+00:00",
        "trade_type": "BUY",
    }
