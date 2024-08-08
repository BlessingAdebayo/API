from decimal import Decimal
from typing import Iterable
from unittest import mock
from unittest.mock import MagicMock

from tests.utils import (
    ADDR1,
    ADDR2,
    load_stub,
    make_algorithm,
    make_algorithm_transaction,
    make_buy_trade,
    make_buy_trade_v2,
    make_sell_trade,
    make_sell_trade_v2,
)
from trading_api.algorithm.models.algorithm import (
    AlgorithmId,
    TradeResponseLockType,
    TradingContract,
    TradingContractVersion,
)
from trading_api.algorithm.models.trade import TradeStatus, TradeType
from trading_api.algorithm.repositories.lock import SYMBOL_V1, AlgorithmLockRepository, NewAlgorithmLock
from trading_api.algorithm.repositories.transaction import TransactionRepository
from trading_api.algorithm.trade import (
    get_trade_type,
    get_trading_check_function,
    get_trading_function,
    is_multi_token_trade,
    is_trade_possible,
)


@mock.patch("trading_api.algorithm.trade.is_trade_possible")
@mock.patch("trading_api.algorithm.trade.send_trade_to_blockchain")
@mock.patch("trading_api.algorithm.status.retrieve_trade_status")
@mock.patch("trading_api.algorithm.trade.get_web3_nonce")
def test_buy_v2_request(
    nonce: MagicMock, retrieve: MagicMock, send: MagicMock, possible: MagicMock, app_inst, access_header_v2
):
    send.return_value = make_algorithm_transaction(hash_value=ADDR1), 42
    retrieve.return_value = TradeStatus.TRADE_SUCCESSFUL
    nonce.return_value = 1
    lock_repository = app_inst.container[AlgorithmLockRepository]
    trade_request = load_stub("body-for-algorithm-trade-buy-v2.json")

    response = app_inst.client.post(f"/api/v2/algorithms/{ADDR2}/trade", json=trade_request, headers=access_header_v2)

    assert response.status_code == 200
    data = response.json()
    assert "lock" in data
    assert "algorithm_id" in data["lock"]
    assert "public_address" in data["lock"]["algorithm_id"]
    assert data["lock"]["algorithm_id"]["public_address"] == ADDR2
    assert "transaction_hash" in data
    assert "value" in data["transaction_hash"]
    assert data["transaction_hash"]["value"] == ADDR1
    assert "lock_type" in data
    assert data["lock_type"] == TradeResponseLockType.NOW_LOCKED
    assert len(lock_repository.algorithm_locks) == 1
    assert lock_repository.algorithm_locks == {
        f"{ADDR2}-BTC": NewAlgorithmLock(algorithm_id=AlgorithmId(public_address=ADDR2), symbol="BTC")
    }
    assert len(lock_repository.algorithm_transactions) == 1


@mock.patch("trading_api.algorithm.trade.is_trade_possible")
@mock.patch("trading_api.algorithm.trade.send_trade_to_blockchain")
@mock.patch("trading_api.algorithm.status.retrieve_trade_status")
@mock.patch("trading_api.algorithm.trade.get_web3_nonce")
def test_buy_v2_request_lowercase_tade_type(
    nonce: MagicMock, retrieve: MagicMock, send: MagicMock, possible: MagicMock, app_inst, access_header_v2
):
    send.return_value = make_algorithm_transaction(hash_value=ADDR1), 42
    retrieve.return_value = TradeStatus.TRADE_SUCCESSFUL
    nonce.return_value = 1
    algorithm_id = AlgorithmId(public_address=ADDR2)
    trade_request = load_stub("body-for-algorithm-trade-buy-v2-lowercase-trade-type.json")

    response = app_inst.client.post(f"/api/v2/algorithms/{ADDR2}/trade", json=trade_request, headers=access_header_v2)

    assert response.status_code == 200

    transactions = app_inst.container[TransactionRepository]
    event = list(transactions.get_trading_transactions(algorithm_id))[0]

    assert event.trade_type == TradeType.BUY


def test_buy_request_mixed_case_tade_type(app_inst, access_header_v2):
    trade_request = load_stub("body-for-algorithm-trade-buy-v2-mixed-case-trade-type.json")

    response = app_inst.client.post(f"/api/v2/algorithms/{ADDR2}/trade", json=trade_request, headers=access_header_v2)

    assert response.status_code == 422


@mock.patch("trading_api.algorithm.trade.is_trade_possible")
@mock.patch("trading_api.algorithm.trade.send_trade_to_blockchain")
@mock.patch("trading_api.algorithm.status.retrieve_trade_status")
@mock.patch("trading_api.algorithm.trade.get_web3_nonce")
def test_sell_v2_request(
    nonce: MagicMock, retrieve: MagicMock, send: MagicMock, possible: MagicMock, app_inst, access_header_v2
):
    send.return_value = make_algorithm_transaction(hash_value=ADDR1), 42
    retrieve.return_value = TradeStatus.TRADE_SUCCESSFUL
    algorithm_id = AlgorithmId(public_address=ADDR2)
    nonce.return_value = 1
    trade_request = load_stub("body-for-algorithm-trade-sell-v2.json")

    response = app_inst.client.post(f"/api/v2/algorithms/{ADDR2}/trade", json=trade_request, headers=access_header_v2)

    assert response.status_code == 200
    data = response.json()
    assert "lock" in data
    assert "algorithm_id" in data["lock"]
    assert "public_address" in data["lock"]["algorithm_id"]
    assert data["lock"]["algorithm_id"]["public_address"] == ADDR2
    assert "transaction_hash" in data
    assert "value" in data["transaction_hash"]
    assert data["transaction_hash"]["value"] == ADDR1
    assert "lock_type" in data
    assert data["lock_type"] == TradeResponseLockType.NOW_LOCKED

    transactions = app_inst.container[TransactionRepository]
    events = transactions.get_trading_transactions(algorithm_id)

    assert isinstance(events, Iterable)
    events = list(events)
    assert len(events) == 1
    event = events[0]
    assert event.status == TradeStatus.TRADE_IN_PROGRESS_OR_NOT_FOUND
    assert event.transaction_hash == ADDR1
    assert event.trading_contract_address == ADDR2
    assert event.relative_amount == Decimal("1")
    assert event.slippage_amount == Decimal("0.005")
    assert event.symbol == "BTC"


@mock.patch("trading_api.algorithm.trade.is_trade_possible")
@mock.patch("trading_api.algorithm.trade.send_trade_to_blockchain")
@mock.patch("trading_api.algorithm.status.retrieve_trade_status")
@mock.patch("trading_api.algorithm.trade.get_web3_nonce")
def test_sell_v2_request_lowercase_tade_type(
    nonce: MagicMock, retrieve: MagicMock, send: MagicMock, possible: MagicMock, app_inst, access_header_v2
):
    send.return_value = make_algorithm_transaction(hash_value=ADDR1), 42
    retrieve.return_value = TradeStatus.TRADE_SUCCESSFUL
    algorithm_id = AlgorithmId(public_address=ADDR2)
    nonce.return_value = 1
    trade_request = load_stub("body-for-algorithm-trade-sell-v2-lowercase-trade-type.json")

    response = app_inst.client.post(f"/api/v2/algorithms/{ADDR2}/trade", json=trade_request, headers=access_header_v2)

    assert response.status_code == 200

    transactions = app_inst.container[TransactionRepository]
    event = list(transactions.get_trading_transactions(algorithm_id))[0]

    assert event.trade_type == TradeType.SELL


def test_is_possible_trade(in_memory_w3):
    buy = make_buy_trade()
    sell = make_sell_trade()
    algorithm = make_algorithm(trading_contract=TradingContract(version=TradingContractVersion.V2_0))

    assert is_trade_possible(buy, algorithm, in_memory_w3) is True
    assert is_trade_possible(sell, algorithm, in_memory_w3) is True


@mock.patch("trading_api.algorithm.trade.is_trade_possible")
def test_trade_is_not_possible(possible: MagicMock, app_inst, access_header_v2):
    possible.return_value = False
    trade_request = load_stub("body-for-algorithm-trade-buy-v2.json")

    response = app_inst.client.post(f"/api/v2/algorithms/{ADDR2}/trade", json=trade_request, headers=access_header_v2)

    assert response.status_code == 400


def test_is_multi_token_trade():
    trades = make_buy_trade_v2(), make_sell_trade_v2()

    assert is_multi_token_trade(trades[0]) is True
    assert is_multi_token_trade(trades[1]) is True

    trades = make_buy_trade(), make_sell_trade()

    assert is_multi_token_trade(trades[0]) is False
    assert is_multi_token_trade(trades[1]) is False


def test_get_trading_check_function_buy(trading_contract_tools):
    trade = make_buy_trade_v2()

    trading_check_function = get_trading_check_function(trade=trade, trading_contract_tools=trading_contract_tools)

    assert trading_check_function.fn_name == "buyCheck"


def test_get_trading_check_function_sell(trading_contract_tools):
    trade = make_sell_trade_v2()

    trading_check_function = get_trading_check_function(trade=trade, trading_contract_tools=trading_contract_tools)

    assert trading_check_function.fn_name == "sellCheck"


def test_get_trading_function_buy(in_memory_w3):
    algorithm = make_algorithm(trading_contract=TradingContract(version=TradingContractVersion.V2_0))
    trade = make_buy_trade_v2()
    trading_contract = in_memory_w3.get_trading_contract(algorithm=algorithm)

    trading_function = get_trading_function(trade=trade, trading_contract=trading_contract)

    assert trading_function.fn_name == "buy"


def test_get_trading_function_sell(in_memory_w3):
    algorithm = make_algorithm(trading_contract=TradingContract(version=TradingContractVersion.V2_0))
    trade = make_sell_trade_v2()
    trading_contract = in_memory_w3.get_trading_contract(algorithm=algorithm)

    trading_function = get_trading_function(trade=trade, trading_contract=trading_contract)

    assert trading_function.fn_name == "sell"


def test_get_trade_type_buy():
    trade = make_buy_trade_v2()

    trade_type = get_trade_type(trade=trade)

    assert trade_type == TradeType.BUY


def test_get_trade_type_sell():
    trade = make_sell_trade_v2()

    trade_type = get_trade_type(trade=trade)

    assert trade_type == TradeType.SELL
