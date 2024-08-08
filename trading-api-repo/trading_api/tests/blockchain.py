import logging
import typing
from pathlib import Path

import solcx
from eth_account import Account
from eth_typing import ChecksumAddress

from tests import TEST_CONTRACT_VERSION
from trading_api import EnvVar, get_env
from trading_api.algorithm.models.crypto import ChainId
from trading_api.algorithm.services.kms import AWSKeyManagementService
from trading_api.algorithm.services.web3 import Web3Provider

logger = logging.getLogger(__name__)


def compile_source_file(file_path):
    return solcx.compile_files(file_path)


def deploy_contract(w3, contract_interface, contract_args, deploy_tx):
    contract = w3.eth.contract(abi=contract_interface["abi"], bytecode=contract_interface["bin"])
    transaction = contract.constructor(*contract_args)
    tx_hash = transaction.transact(transaction=deploy_tx)

    receipt = w3.eth.get_transaction_receipt(tx_hash)
    assert receipt["status"] == 1

    return receipt["contractAddress"]


def deploy_trading_contract(
    deploy_tx,
    contract_public_address: ChecksumAddress,
    developer_public_address: ChecksumAddress,
    web3_provider: Web3Provider,
    km_service: AWSKeyManagementService,
):
    w3 = web3_provider.get_web3(chain=ChainId.RTN)
    if deploy_tx is None:
        deploy_tx = {
            "from": contract_public_address,
            "value": 0,
            "nonce": w3.eth.get_transaction_count(contract_public_address),
        }

    sol_version = "0.6.6"
    solcx.install_solc(sol_version)
    solcx.set_solc_version(sol_version)

    base_path = Path(__file__).parent.parent.parent.absolute()
    contract_source_path = (
        base_path / "mercor_smart_contracts" / TEST_CONTRACT_VERSION / "contracts" / "TradingContract.sol"
    )
    compiled_sol = compile_source_file(contract_source_path)

    contract_id = f"{contract_source_path}:TradingContract"
    contract_interface = compiled_sol[contract_id]

    contract_args = (
        "0x55d398326f99059fF775485246999027B3197955",  # _pairedToken
        "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",  # _baseToken
        10000,  # _maxTotalCap
        developer_public_address,  # _developerAddress
    )

    contract = w3.eth.contract(abi=contract_interface["abi"], bytecode=contract_interface["bin"])
    transaction = contract.constructor(*contract_args)
    # tx_hash = transaction.transact(transaction=deploy_tx)

    if km_service:
        deploy_tx["data"] = transaction.data_in_transaction
        signed_tx = km_service.sign_transaction(deploy_tx, contract_public_address, ChainId.RTN)
        deploy_tx = signed_tx.rawTransaction
        tx_hash = w3.eth.send_raw_transaction(deploy_tx)
        receipt = w3.eth.get_transaction_receipt(tx_hash)

        assert receipt["status"] == 1
        contract_address = receipt["contractAddress"]
    else:
        contract_address = deploy_contract(w3, contract_interface, contract_args, deploy_tx)

    trading_contract_var = w3.eth.contract(address=contract_address, abi=contract_interface["abi"])

    return trading_contract_var


@typing.no_type_check
def transfer_funds(from_account, to_address, w3_provider: Web3Provider):
    w3 = w3_provider.get_web3(chain=ChainId.RTN)
    logger.info(f"Account balance: {w3.eth.get_balance(from_account[0])}")
    logger.info(f"Account balance: {w3.eth.get_balance(w3.toChecksumAddress(to_address))}")
    assert w3.eth.get_balance(w3.toChecksumAddress(to_address)) == 0

    unit = get_env(EnvVar.UNIT, "ether")
    account = Account.from_key(from_account[1])
    txn = {
        "gas": w3.toWei(w3_provider.get_gas_amount(), unit=unit),
        "gasPrice": w3.toWei(w3_provider.get_gas_price(), unit=unit),
        "nonce": w3.eth.get_transaction_count(account.address),
        "to": w3.toChecksumAddress(to_address),
        "from": from_account[0],
        "value": w3.toWei(1_000_000, unit),
    }
    signed_txn = account.sign_transaction(txn)
    tx_hash: ChecksumAddress = w3.eth.send_raw_transaction(signed_txn.rawTransaction).hex()  # type: ignore

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    logger.info(receipt)
    assert receipt["status"] == 1

    logger.info(f"Account balance: {w3.eth.get_balance(from_account[0])}")
    logger.info(f"Account balance: {w3.eth.get_balance(w3.toChecksumAddress(to_address))}")
    assert w3.eth.get_balance(w3.toChecksumAddress(to_address)) > 0
