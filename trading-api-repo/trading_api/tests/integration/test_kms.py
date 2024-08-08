import logging
from typing import Iterator

import pytest
from web3 import Web3

from tests.blockchain import deploy_trading_contract, transfer_funds
from tests.utils import load_stub, make_algorithm
from trading_api.algorithm.models.crypto import ChainId
from trading_api.algorithm.models.trade import BuyTrade, TradeRequest
from trading_api.algorithm.repositories.key import MongoKeyRepository
from trading_api.algorithm.services.kms import AWSKeyManagementService
from trading_api.algorithm.services.web3 import HttpWeb3Provider
from trading_api.algorithm.trade import send_trade_to_blockchain

logger = logging.getLogger(__name__)

CANT_TEST_KMS_YET = "We currently don't test with KMS integrated due to cost and security"


@pytest.mark.skip(CANT_TEST_KMS_YET)
def test_create_key(km_service: AWSKeyManagementService):
    keyinfo = km_service.create_new_key()
    assert keyinfo.internal is not None, "internal id unfilled"
    assert keyinfo.external is not None, "external id unfilled"
    assert keyinfo.address is not None, "address unfilled"
    assert Web3.isAddress(address := keyinfo.address), f"{keyinfo.address=} is not a valid address"
    assert km_service.key_repository.get_key_alias_by_address(address) == keyinfo.internal, "key ids dont match"


@pytest.mark.skip(CANT_TEST_KMS_YET)
def test_list_keys(km_service: AWSKeyManagementService):
    km_service.create_new_key()
    response = km_service.list_key_aliases()
    assert isinstance(response, Iterator), f"wrong return type {response=} {type(response)}"
    response_list = list(response)
    assert len(response_list) > 0, "no keys returned"
    assert isinstance(response_list[0], str), f"wrong return type {response_list[0]=} {type(response_list[0])}"
    assert "alias" not in response_list[-1], f"alias should have been removed {response_list[-1]=}"


@pytest.mark.skip(CANT_TEST_KMS_YET)
def test_all_keyed_addresses(km_service: AWSKeyManagementService):
    km_service.create_new_key()
    keyed_addresses = km_service.all_keyed_addresses()

    assert isinstance(keyed_addresses, Iterator)
    keyed_addresses_list = list(keyed_addresses)
    assert len(keyed_addresses_list) > 0
    assert all(Web3.isChecksumAddress(address.controller_wallet_address) for address in keyed_addresses)


@pytest.mark.skip(CANT_TEST_KMS_YET)
def test_get_key(km_service: AWSKeyManagementService):
    key_id = km_service.create_new_key()
    keyinfo = km_service.key_alias_to_key_info(key_id.internal)

    assert keyinfo.key is not None, "public key unfilled"
    assert keyinfo.address is not None, "address unfilled"
    assert keyinfo.der is not None, "der unfilled"
    assert str(keyinfo.address).startswith("0x"), f"adress {keyinfo.address=} should start with '0x"
    assert len(keyinfo.address) == 42, f"adress should be len 42 not {len(keyinfo.address)}"
    assert Web3.isAddress(keyinfo.address), f"{keyinfo.address=} is not a valid address"


@pytest.mark.skip(CANT_TEST_KMS_YET)
def test_signing_and_verifying(km_service: AWSKeyManagementService):
    keyinfo = km_service.create_new_key()
    key_id = keyinfo.internal
    message = b'{"banana" : "apple"}'
    public_key = km_service.key_alias_to_key_info(key_id)
    signature, message_hash, rsv = km_service.sign_message(
        ChainId.RTN, message, key_id, Web3.toChecksumAddress(public_key.address), needs_hashing=True
    )
    assert message_hash is not None, "message hash is empty"
    assert int(rsv.v) in [27, 28], f"{rsv.v=} should be either 27 or 28"
    assert km_service.verify_message(message, key_id, signature, needs_hashing=True), "verification of signature failed"


@pytest.mark.skip(CANT_TEST_KMS_YET)
def test_retrieve_right_address(km_service: AWSKeyManagementService, http_w3):
    w3 = http_w3.get_web3(chain=ChainId.RTN)
    key_id = "test3"
    public_key = km_service.key_alias_to_key_info(key_alias=key_id)
    assert public_key.address == w3.toChecksumAddress("0xf05ef1c844e39757b6f94f89427b1ac302fcae1b")


@pytest.mark.skip(CANT_TEST_KMS_YET)
def test_sign_transaction_and_send(contract_account, http_w3, km_service: AWSKeyManagementService):
    w3 = http_w3.get_web3(chain=ChainId.RTN)
    address = km_service.create_new_key().address
    UNIT = "ether"
    address = w3.toChecksumAddress(address)

    transfer_funds(from_account=contract_account, to_address=address, w3_provider=http_w3)

    logger.info(f"Account balance: {w3.eth.get_balance(contract_account[0])}")
    logger.info(f"Account balance: {w3.eth.get_balance(w3.toChecksumAddress(address))}")
    assert w3.eth.get_balance(w3.toChecksumAddress(address)) > 0

    transaction_dict = {
        "nonce": w3.eth.get_transaction_count(w3.toChecksumAddress(address)),
        "gasPrice": w3.toWei(http_w3.get_gas_price(), unit=UNIT),
        "gas": w3.toWei(http_w3.get_gas_amount(), unit=UNIT),
        "to": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf",
        "value": w3.toWei(1, UNIT),
        "data": b"",
    }

    signed_txn = km_service.sign_transaction(transaction=transaction_dict, address=address, chain=ChainId.RTN)

    tx_hash: str = w3.eth.send_raw_transaction(signed_txn.rawTransaction).hex()
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    logger.info(receipt)
    assert receipt["status"] == 1


@pytest.mark.skip(CANT_TEST_KMS_YET)
def test_create_controller_wallet_addresses(app_inst, key_repository, system_access_header):
    app_inst.container[MongoKeyRepository] = key_repository
    create_request = load_stub("body-for-system-controller-wallet-address-create.json")

    response = app_inst.client.post(f"/api/v1/algorithms/create", json=create_request, headers=system_access_header)

    assert response.status_code == 200
    data = response.json()
    assert "address_pairs" in data
    assert len(data["address_pairs"]) == 3

    for pair in data["address_pairs"]:
        address = pair["controller_wallet_address"]
        assert Web3.isChecksumAddress(address)
        assert pair["trading_contract_address"] is None

        key_id = key_repository.get_key_alias_by_address(address)
        assert isinstance(key_id, str) and len(key_id)


@pytest.mark.skip(CANT_TEST_KMS_YET)
def test_buy_request_kms(app_inst, contract_account, http_w3: HttpWeb3Provider, km_service: AWSKeyManagementService):
    w3 = http_w3.get_web3(chain=ChainId.RTN)
    algorithm_address = km_service.create_new_key().address
    algorithm_address = w3.toChecksumAddress(algorithm_address)
    algorithm = make_algorithm(trading_contract_address=algorithm_address, controller_wallet_address=algorithm_address)
    buy_data = {
        "algorithm_id": {"public_address": algorithm_address},
        "slippage": {"amount": 0.05},
        "relative_amount": 0.50,
    }
    trade_request: TradeRequest = TradeRequest(trade=BuyTrade(**buy_data))
    transfer_funds(contract_account, algorithm_address, http_w3)

    deploy_tx = {
        "gas": 6_721_975,
        "gasPrice": 1_000_000,
        "value": 0,
        "nonce": w3.eth.get_transaction_count(algorithm_address),
    }
    trading_contract = deploy_trading_contract(
        deploy_tx,
        contract_public_address=algorithm_address,
        developer_public_address=contract_account[0],
        web3_provider=http_w3,
        km_service=km_service,
    )
    # TODO: Fix this once we enable this test.
    # http_w3.set_contract_address(trading_contract_address=trading_contract.address)

    with pytest.raises(ValueError) as exc_info:
        transaction, nonce = send_trade_to_blockchain(
            trade_request, algorithm=algorithm, web3_provider=http_w3, km_service=km_service
        )

        assert "revert Not enough funds to trade" in str(exc_info.value)
