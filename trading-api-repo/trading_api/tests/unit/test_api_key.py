from http import HTTPStatus
from unittest import mock
from unittest.mock import MagicMock

from tests.utils import ADDR2, load_stub, make_algorithm_transaction
from trading_api.algorithm.models.trade import TradeStatus
from trading_api.algorithm.repositories.algorithm import AlgorithmRepository
from trading_api.core.container import default_user_v2


def test_trade_status_v2_request_with_no_api_key_in_url_is_unauthorized(app_inst):
    app_inst.container[AlgorithmRepository].upsert_algorithm(default_user_v2())

    response = app_inst.client.post(
        url=f"/api/v2/algorithms/{ADDR2}/status",
        json=load_stub("body-for-algorithm-status-v2.json"),
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_trade_status_v2_request_with_incorrect_api_key_in_url_is_unauthorized(app_inst):
    app_inst.container[AlgorithmRepository].upsert_algorithm(default_user_v2())

    response = app_inst.client.post(
        url=f"/api/v2/algorithms/{ADDR2}/status",
        params=load_stub("query-for-api-key-unauthorized.params"),
        json=load_stub("body-for-algorithm-status-v2.json"),
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


@mock.patch("trading_api.algorithm.status.retrieve_trade_status")
def test_trade_status_v2_request_with_correct_api_key_in_url_is_authorized(retrieve: MagicMock, app_inst):
    retrieve.return_value = TradeStatus.TRADE_SUCCESSFUL
    app_inst.container[AlgorithmRepository].upsert_algorithm(default_user_v2())

    response = app_inst.client.post(
        url=f"/api/v2/algorithms/{ADDR2}/status",
        params=load_stub("query-for-api-key.params"),
        json=load_stub("body-for-algorithm-status-v2.json"),
    )

    assert response.status_code == HTTPStatus.OK


def test_buy_v2_request_with_incorrect_api_key_in_url_is_unauthorized(app_inst):
    app_inst.container[AlgorithmRepository].upsert_algorithm(default_user_v2())

    response = app_inst.client.post(
        url=f"/api/v2/algorithms/{ADDR2}/trade",
        params=load_stub("query-for-api-key-unauthorized.params"),
        json=load_stub("body-for-algorithm-trade-buy-v2.json"),
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


@mock.patch("trading_api.algorithm.trade.is_trade_possible")
@mock.patch("trading_api.algorithm.trade.send_trade_to_blockchain")
@mock.patch("trading_api.algorithm.status.retrieve_trade_status")
@mock.patch("trading_api.algorithm.trade.get_web3_nonce")
def test_buy_v2_request_with_correct_api_key_in_url_is_authorized(
    nonce: MagicMock, retrieve: MagicMock, send: MagicMock, possible: MagicMock, app_inst
):
    nonce.return_value = 1
    send.return_value = make_algorithm_transaction(), 1
    retrieve.return_value = TradeStatus.TRADE_SUCCESSFUL
    app_inst.container[AlgorithmRepository].upsert_algorithm(default_user_v2())

    response = app_inst.client.post(
        url=f"/api/v2/algorithms/{ADDR2}/trade",
        params=load_stub("query-for-api-key.params"),
        json=load_stub("body-for-algorithm-trade-buy-v2.json"),
    )

    assert response.status_code == HTTPStatus.OK


def test_sell_v2_request_with_incorrect_api_key_in_url_is_unauthorized(app_inst):
    app_inst.container[AlgorithmRepository].upsert_algorithm(default_user_v2())

    response = app_inst.client.post(
        url=f"/api/v2/algorithms/{ADDR2}/trade",
        params=load_stub("query-for-api-key-unauthorized.params"),
        json=load_stub("body-for-algorithm-trade-sell-v2.json"),
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


@mock.patch("trading_api.algorithm.trade.is_trade_possible")
@mock.patch("trading_api.algorithm.trade.send_trade_to_blockchain")
@mock.patch("trading_api.algorithm.status.retrieve_trade_status")
@mock.patch("trading_api.algorithm.trade.get_web3_nonce")
def test_sell_v2_request_with_correct_api_key_in_url_is_authorized(
    nonce: MagicMock, retrieve: MagicMock, send: MagicMock, possible: MagicMock, app_inst
):
    nonce.return_value = 1
    send.return_value = make_algorithm_transaction(), 42
    retrieve.return_value = TradeStatus.TRADE_SUCCESSFUL
    app_inst.container[AlgorithmRepository].upsert_algorithm(default_user_v2())

    response = app_inst.client.post(
        url=f"/api/v2/algorithms/{ADDR2}/trade",
        params=load_stub("query-for-api-key.params"),
        json=load_stub("body-for-algorithm-trade-sell-v2.json"),
    )

    assert response.status_code == HTTPStatus.OK
