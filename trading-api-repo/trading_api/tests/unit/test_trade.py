from decimal import Decimal
from typing import Iterable
from unittest import mock
from unittest.mock import MagicMock

from hexbytes import HexBytes

from tests.utils import get_access_header, load_stub, make_algorithm_db
from trading_api.algorithm.lock import create_algorithm_transaction
from trading_api.algorithm.models.algorithm import (
    AlgorithmId,
    AlgorithmTransaction,
    NewAlgorithmLock,
    TradingContract,
    TradingContractVersion,
)
from trading_api.algorithm.models.crypto import ChainId, TransactionHash
from trading_api.algorithm.models.trade import TradeStatus
from trading_api.algorithm.repositories.algorithm import AlgorithmRepository
from trading_api.algorithm.repositories.lock import SYMBOL_V1, AlgorithmLockRepository
from trading_api.algorithm.repositories.nonce import NonceRepository
from trading_api.algorithm.repositories.transaction import TransactionRepository
from trading_api.algorithm.services.web3 import Web3Provider


def test_user_not_authorized(app_inst):
    response = app_inst.client.get("/api/v1")
    assert response.status_code == 401


@mock.patch("trading_api.algorithm.trade.send_trade_to_blockchain")
@mock.patch("trading_api.algorithm.status.retrieve_trade_status")
@mock.patch("trading_api.algorithm.trade.get_web3_nonce")
def test_buy_request(nonce: MagicMock, retrieve: MagicMock, send: MagicMock, app_inst, access_header_v1):
    pub_address = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
    send.return_value = (
        create_algorithm_transaction(AlgorithmId(public_address=pub_address), HexBytes("0x7b")),
        42,
    )
    retrieve.return_value = TradeStatus.TRADE_SUCCESSFUL
    nonce.return_value = 1
    lock_repository = app_inst.container[AlgorithmLockRepository]
    algo_repository: AlgorithmRepository = app_inst.container[AlgorithmRepository]

    algorithm_before = algo_repository.get_algorithm(pub_address)
    assert algorithm_before is not None
    assert algorithm_before.nonce_counter is None

    trade_request = load_stub("body-for-algorithm-trade.json")

    response = app_inst.client.post("/api/v1/buy", json=trade_request, headers=access_header_v1)
    assert response.status_code == 200
    assert response.json() == {
        "lock": {"algorithm_id": {"public_address": pub_address}, "symbol": SYMBOL_V1},
        "transaction_hash": {"value": "0x7b"},
        "lock_type": "SUCCESS:ALGORITHM-IS-NOW-LOCKED",
    }
    assert len(lock_repository.algorithm_locks) == 1
    assert lock_repository.algorithm_locks == {
        f"0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf-{SYMBOL_V1}": NewAlgorithmLock(
            algorithm_id=AlgorithmId(public_address=pub_address), symbol=SYMBOL_V1
        )
    }
    assert len(lock_repository.algorithm_transactions) == 1
    assert lock_repository.algorithm_transactions == {
        f"0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf-{SYMBOL_V1}": AlgorithmTransaction(
            algorithm_id=AlgorithmId(public_address=pub_address),
            transaction_hash=TransactionHash(value="0x7b"),
        )
    }
    algorithm = algo_repository.get_algorithm(pub_address)
    assert algorithm is not None
    assert algorithm.nonce_counter is None


def test_buy_request_with_disabled_algorithm_not_allowed(contract_account, app_inst, in_memory_w3):
    app_inst.container[Web3Provider] = in_memory_w3
    algorithm_user = make_algorithm_db(
        trading_contract_address=contract_account[0], controller_wallet_address=contract_account[0]
    )
    access_header = get_access_header(app_inst, algorithm_user=algorithm_user)
    trade_request = load_stub("body-for-algorithm-trade.json")

    algorithm_user.disabled = True

    response = app_inst.client.post("/api/v1/buy", json=trade_request, headers=access_header)

    assert response.status_code == 403


def test_buy_request_from_other_address_not_authorized(contract_account, app_inst, in_memory_w3):
    app_inst.container[Web3Provider] = in_memory_w3
    algorithm_user = make_algorithm_db(
        trading_contract_address=contract_account[0], controller_wallet_address=contract_account[0]
    )

    access_header = get_access_header(app_inst, algorithm_user=algorithm_user)

    other_address = str(contract_account[1])
    trade_request = load_stub("body-for-algorithm-trade.json")
    trade_request["trade"]["algorithm_id"]["public_address"] = other_address

    response = app_inst.client.post("/api/v1/buy", json=trade_request, headers=access_header)

    assert response.status_code == 401


def test_buy_request_from_other_trading_contract_raises_conflict(contract_account, app_inst):
    algorithm_user = make_algorithm_db(
        trading_contract_address=contract_account[0],
        controller_wallet_address=contract_account[0],
        trading_contract=TradingContract(version=TradingContractVersion.V2_0),
    )
    trade_request = load_stub("body-for-algorithm-trade.json")
    access_header = get_access_header(app_inst, algorithm_user=algorithm_user)

    response = app_inst.client.post("/api/v1/buy", json=trade_request, headers=access_header)

    assert response.status_code == 409


@mock.patch("trading_api.algorithm.trade.send_trade_to_blockchain")
@mock.patch("trading_api.algorithm.status.retrieve_trade_status")
@mock.patch("trading_api.algorithm.trade.get_web3_nonce")
def test_sell_request(nonce: MagicMock, retrieve: MagicMock, send: MagicMock, app_inst, access_header_v1):
    algorithm_id = AlgorithmId(public_address="0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf")
    send.return_value = create_algorithm_transaction(algorithm_id=algorithm_id, transaction_hash=HexBytes("0x7b")), 1
    retrieve.return_value = TradeStatus.TRADE_SUCCESSFUL
    nonce.return_value = 1

    trade_request = load_stub("body-for-algorithm-trade.json")

    response = app_inst.client.post("/api/v1/sell", json=trade_request, headers=access_header_v1)
    assert response.status_code == 200
    assert response.json() == {
        "lock": {"algorithm_id": {"public_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"}, "symbol": SYMBOL_V1},
        "transaction_hash": {"value": "0x7b"},
        "lock_type": "SUCCESS:ALGORITHM-IS-NOW-LOCKED",
    }

    event_repo: TransactionRepository = app_inst.container[TransactionRepository]
    events = event_repo.get_trading_transactions(algorithm_id)

    assert isinstance(events, Iterable)
    events = list(events)
    assert len(events) == 1
    event = events[0]
    assert event.status == TradeStatus.TRADE_IN_PROGRESS_OR_NOT_FOUND
    assert event.transaction_hash == "0x7b"
    assert event.trading_contract_address == "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
    assert event.relative_amount == Decimal("0.50")
    assert event.slippage_amount == Decimal("0.05")


def test_sell_request_with_disabled_algorithm_not_allowed(contract_account, app_inst, in_memory_w3):
    app_inst.container[Web3Provider] = in_memory_w3
    algorithm_user = make_algorithm_db(
        trading_contract_address=contract_account[0], controller_wallet_address=contract_account[0]
    )
    access_header = get_access_header(app_inst, algorithm_user=algorithm_user)
    trade_request = load_stub("body-for-algorithm-trade.json")

    algorithm_user.disabled = True

    response = app_inst.client.post("/api/v1/sell", json=trade_request, headers=access_header)

    assert response.status_code == 403


def test_sell_request_from_other_address_not_authorized(contract_account, app_inst, in_memory_w3):
    app_inst.container[Web3Provider] = in_memory_w3
    algorithm_user = make_algorithm_db(
        trading_contract_address=contract_account[0], controller_wallet_address=contract_account[0]
    )
    access_header = get_access_header(app_inst, algorithm_user=algorithm_user)
    other_address = str(contract_account[1])
    trade_request = load_stub("body-for-algorithm-trade.json")
    trade_request["trade"]["algorithm_id"]["public_address"] = other_address

    response = app_inst.client.post("/api/v1/sell", json=trade_request, headers=access_header)

    assert response.status_code == 401


def test_trade_request_not_authorized(app_inst):
    trade_request = load_stub("body-for-algorithm-trade-unauthorized.json")

    response = app_inst.client.post("/api/v1/buy", json=trade_request)

    assert response.status_code == 401


def test_algorithm_is_locked(app_inst, access_header_v1, in_memory_w3):
    app_inst.container[Web3Provider] = in_memory_w3
    expected_was_locked_dict = {
        "lock": {"algorithm_id": {"public_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"}, "symbol": SYMBOL_V1},
        "transaction_hash": {"value": "0x6b7aaa"},
        "lock_type": "DENIED:ALGORITHM-ALREADY-LOCKED",
    }
    lock_dict = {
        "algorithm_id": {"public_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"},
        "transaction_hash": {"value": "0x6b7aaa"},
    }
    lock_repository = app_inst.container[AlgorithmLockRepository]
    lock_repository.get_algorithm_lock(
        algorithm_id=AlgorithmId(public_address="0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf")
    )
    lock_repository.persist_algorithm_transaction(AlgorithmTransaction(**lock_dict))
    trade_request = load_stub("body-for-algorithm-trade.json")

    response = app_inst.client.post("/api/v1/buy", json=trade_request, headers=access_header_v1)

    assert response.status_code == 423
    assert response.json() == expected_was_locked_dict


def test_contract_buy_request(contract_account, app_inst, in_memory_w3, km_service):
    app_inst.container[Web3Provider] = in_memory_w3
    algorithm_user = make_algorithm_db(
        trading_contract_address=contract_account[0], controller_wallet_address=contract_account[0]
    )
    access_header = get_access_header(app_inst, algorithm_user=algorithm_user)

    trade_request = load_stub("body-for-algorithm-trade.json")
    trade_request["trade"]["algorithm_id"]["public_address"] = contract_account[0]

    response = app_inst.client.post("/api/v1/buy", json=trade_request, headers=access_header)
    assert response.status_code == 200
    assert response.json()["lock_type"] == "SUCCESS:ALGORITHM-IS-NOW-LOCKED"

    lock_repository = app_inst.container[AlgorithmLockRepository]
    assert len(lock_repository.algorithm_locks) == 1
    assert lock_repository.algorithm_locks == {
        f"0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf-{SYMBOL_V1}": NewAlgorithmLock(
            algorithm_id=AlgorithmId(public_address="0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"),
            symbol=SYMBOL_V1,
        )
    }
    assert len(lock_repository.algorithm_transactions) == 1
    assert list(lock_repository.algorithm_transactions.values())[0].algorithm_id == AlgorithmId(
        public_address="0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
    )

    transaction_hash = list(lock_repository.algorithm_transactions.values())[0].transaction_hash.value
    w3 = in_memory_w3.get_web3(chain=ChainId.RTN)
    tx_receipt = w3.eth.wait_for_transaction_receipt(HexBytes(transaction_hash), timeout=20)

    assert tx_receipt["status"] == 0
