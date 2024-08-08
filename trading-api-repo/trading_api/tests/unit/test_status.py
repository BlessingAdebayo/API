import pytest
from web3.types import TxReceipt

from tests.utils import ADDR2, load_stub
from trading_api.algorithm.services.web3 import Web3Provider


def test_status_not_found(in_memory_w3, app_inst, access_header_v1):
    app_inst.container[Web3Provider] = in_memory_w3

    request = load_stub("body-for-algorithm-status.json")

    response = app_inst.client.post("/api/v1/status", json=request, headers=access_header_v1)

    assert response.json()["code"] == "TRADE_IN_PROGRESS_OR_NOT_FOUND"
    assert response.json()["message"] == "Trade is in progress or cannot be found."
    assert response.status_code == 202


def test_status_successful(eth_tester, w3, in_memory_w3, app_inst, access_header_v1):
    app_inst.container[Web3Provider] = in_memory_w3

    tx_hash = w3.eth.send_transaction({"to": eth_tester.get_accounts()[0], "from": w3.eth.coinbase, "value": 12345})
    tx_receipt: TxReceipt = w3.eth.wait_for_transaction_receipt(tx_hash, 180)

    request = {
        "algorithm_id": {"public_address": ADDR2},
        "transaction_hash": {"value": tx_hash.hex()},
        "timeout_in_seconds": 0,
    }

    response = app_inst.client.post("/api/v1/status", json=request, headers=access_header_v1)

    assert response.status_code == 200
    assert response.json() == {"code": "TRADE_SUCCESSFUL", "message": "Trade successful."}


def test_timeout_value_range(in_memory_w3, app_inst, access_header_v1):
    client = app_inst.client
    app_inst.container[Web3Provider] = in_memory_w3
    request = {
        "algorithm_id": {"public_address": ADDR2},
        "transaction_hash": {"value": "0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060"},
    }

    request["timeout_in_seconds"] = -1
    response = client.post("/api/v1/status", json=request, headers=access_header_v1)
    assert response.status_code == 422
    assert response.json() == {
        "detail": [{"loc": ["body", "timeout_in_seconds"], "msg": "", "type": "assertion_error"}]
    }

    request["timeout_in_seconds"] = 121
    response = client.post("/api/v1/status", json=request, headers=access_header_v1)
    assert response.status_code == 422
    assert response.json() == {
        "detail": [{"loc": ["body", "timeout_in_seconds"], "msg": "", "type": "assertion_error"}]
    }

    request["timeout_in_seconds"] = 1
    response = client.post("/api/v1/status", json=request, headers=access_header_v1)
    assert response.status_code == 202

    request["timeout_in_seconds"] = 0
    response = client.post("/api/v1/status", json=request, headers=access_header_v1)
    assert response.status_code == 202


@pytest.mark.skip("Not sure how to implement this.")
def test_status_failed(eth_tester, w3, in_memory_w3, app_inst):
    app_inst.container[Web3Provider] = in_memory_w3
    w3.eth.send_transaction(
        {
            "to": eth_tester.get_accounts()[0],
            "from": w3.eth.coinbase,
            "value": 12345,
            "gas": 0,
            "gasPrice": w3.toWei(50, "gwei"),
            "nonce": 0,
        }
    )

    request = load_stub("body-for-algorithm-status.json")

    response = app_inst.client.post("/api/v1/status", json=request)

    assert response.status_code == 200
    assert response.json() == {"code": 2, "message": "Trade failed."}
