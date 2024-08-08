from decimal import Decimal
from typing import Iterable
from unittest import mock
from unittest.mock import MagicMock

import pytest
from hexbytes import HexBytes

from tests.utils import get_access_header, load_stub, make_algorithm_db
from trading_api.algorithm.lock import create_algorithm_transaction
from trading_api.algorithm.models.algorithm import AlgorithmId, AlgorithmWasLocked
from trading_api.algorithm.models.trade import (
    BuyTrade,
    Slippage,
    TradeStatus,
    TradeSuccessfulResponse,
    TradingTransaction,
)
from trading_api.algorithm.repositories.lock import AlgorithmLockRepository
from trading_api.algorithm.repositories.nonce import NonceRepository
from trading_api.algorithm.repositories.transaction import TransactionRepository
from trading_api.algorithm.services.web3 import Web3Provider


@pytest.mark.skip("flaky")
def test_buy_request_no_funds(
    app_inst, contract_account, http_w3, local_kms, transaction_repository: TransactionRepository
):
    app_inst.container[Web3Provider] = http_w3
    algorithm_user = make_algorithm_db(
        trading_contract_address=contract_account[0], controller_wallet_address=contract_account[0]
    )
    access_header = get_access_header(app_inst, algorithm_user=algorithm_user)
    lock_repository = app_inst.container[AlgorithmLockRepository]
    trade_request = load_stub("body-for-algorithm-trade.json")
    address = contract_account[0]
    trade_request["trade"]["algorithm_id"]["public_address"] = address
    algorithm_id = AlgorithmId(public_address=address)

    response = app_inst.client.post("/api/v1/buy", json=trade_request, headers=access_header)

    assert response.status_code == 200
    response_json = response.json()
    assert "lock" in response_json and "transaction_hash" in response_json

    lock = lock_repository.get_algorithm_lock(algorithm_id)
    assert isinstance(lock, AlgorithmWasLocked)
    assert lock.lock.algorithm_id == algorithm_id

    event_repo: TransactionRepository = app_inst.container[TransactionRepository]
    events = event_repo.get_trading_transactions(algorithm_id)

    assert isinstance(events, Iterable)
    events = list(events)
    assert len(events) == 1


@pytest.mark.skip("flaky")
@mock.patch("trading_api.algorithm.trade.send_trade_to_blockchain")
def test_buy_request_create_transaction(
    send: MagicMock, app_inst, contract_account, http_w3, local_kms, transaction_repository: TransactionRepository
):
    app_inst.container[Web3Provider] = http_w3
    algorithm_user = make_algorithm_db(
        trading_contract_address=contract_account[0], controller_wallet_address=contract_account[0]
    )
    access_header = get_access_header(app_inst, algorithm_user=algorithm_user)
    lock_repository = app_inst.container[AlgorithmLockRepository]
    trade_request = load_stub("body-for-algorithm-trade.json")
    address = contract_account[0]
    trade_request["trade"]["algorithm_id"]["public_address"] = address
    algorithm_id = AlgorithmId(public_address=address)
    send.return_value = create_algorithm_transaction(algorithm_id=algorithm_id, transaction_hash=HexBytes("0x7b")), 42
    nonce_repo: NonceRepository = app_inst.container[NonceRepository]

    trade = BuyTrade(
        algorithm_id=AlgorithmId(public_address=address),
        slippage=Slippage(amount=Decimal("0.05")),
        relative_amount=Decimal("0.5"),
    )
    assert nonce_repo.get_nonce(trade, web3_nonce=1) == 1

    response = app_inst.client.post("/api/v1/buy", json=trade_request, headers=access_header)

    assert response.status_code == 200
    response_json = response.json()
    assert "lock" in response_json and "transaction_hash" in response_json

    lock = lock_repository.get_algorithm_lock(algorithm_id)
    assert isinstance(lock, AlgorithmWasLocked)
    assert lock.lock.algorithm_id == algorithm_id

    event_repo: TransactionRepository = app_inst.container[TransactionRepository]
    events = event_repo.get_trading_transactions(algorithm_id)

    assert isinstance(events, Iterable)
    events = list(events)
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, TradingTransaction)
    assert event.status == TradeStatus.TRADE_IN_PROGRESS_OR_NOT_FOUND
    assert event.transaction_hash == "0x7b"
    assert event.trading_contract_address == "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
    assert event.relative_amount == Decimal("0.5")
    assert event.slippage_amount == Decimal("0.05")
    assert nonce_repo.get_nonce(trade, web3_nonce=1) == 1


@pytest.mark.skip("flaky")
@mock.patch("trading_api.algorithm.trade.send_trade_to_blockchain")
@mock.patch("trading_api.algorithm.status.check_trade_status")
def test_buy_request_nonce(
    retrieve: MagicMock,
    send: MagicMock,
    app_inst,
    contract_account,
    http_w3,
    local_kms,
    transaction_repository: TransactionRepository,
):
    retrieve.return_value = TradeStatus.TRADE_SUCCESSFUL
    app_inst.container[Web3Provider] = http_w3
    algorithm_user = make_algorithm_db(
        trading_contract_address=contract_account[0], controller_wallet_address=contract_account[0]
    )
    access_header = get_access_header(app_inst, algorithm_user=algorithm_user)
    lock_repository = app_inst.container[AlgorithmLockRepository]
    trade_request = load_stub("body-for-algorithm-trade.json")
    address = contract_account[0]
    trade_request["trade"]["algorithm_id"]["public_address"] = address
    algorithm_id = AlgorithmId(public_address=address)
    send.return_value = create_algorithm_transaction(algorithm_id=algorithm_id, transaction_hash=HexBytes("0x7b")), 42
    nonce_repo: NonceRepository = app_inst.container[NonceRepository]

    trade = BuyTrade(
        algorithm_id=AlgorithmId(public_address=address),
        slippage=Slippage(amount=Decimal("0.05")),
        relative_amount=Decimal("0.5"),
    )
    assert nonce_repo.get_nonce(trade, web3_nonce=1) == 1

    response = app_inst.client.post("/api/v1/buy", json=trade_request, headers=access_header)

    assert response.status_code == 200
    response_json = response.json()
    assert "lock" in response_json and "transaction_hash" in response_json

    lock = lock_repository.get_algorithm_lock(algorithm_id)
    assert isinstance(lock, AlgorithmWasLocked)
    assert lock.lock.algorithm_id == algorithm_id

    event_repo: TransactionRepository = app_inst.container[TransactionRepository]
    events = event_repo.get_trading_transactions(algorithm_id)

    assert isinstance(events, Iterable)
    events = list(events)
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, TradingTransaction)
    assert event.status == TradeStatus.TRADE_SUCCESSFUL
    assert nonce_repo.get_nonce(trade, web3_nonce=1) == 3
