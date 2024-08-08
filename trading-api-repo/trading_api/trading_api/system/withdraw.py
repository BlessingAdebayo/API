from decimal import ROUND_HALF_UP, Decimal

from eth_typing import ChecksumAddress
from fastapi import HTTPException

from trading_api import EnvVar, get_env, get_env_force
from trading_api.algorithm.models.algorithm import Algorithm, AlgorithmId, AlgorithmInDB
from trading_api.algorithm.repositories.algorithm import AlgorithmRepository
from trading_api.algorithm.services.kms import KeyManagementService
from trading_api.algorithm.services.web3 import Web3Provider
from trading_api.system.models.withdraw import WithdrawFundsRequest, WithdrawFundsResponse


def handle_withdraw_funds(
    algorithm_id: AlgorithmId,
    request: WithdrawFundsRequest,
    web3_provider: Web3Provider,
    key_management_service: KeyManagementService,
    algorithm_repository: AlgorithmRepository,
) -> WithdrawFundsResponse:
    algorithm = algorithm_repository.get_algorithm(trading_contract_address=algorithm_id.public_address)
    if algorithm is None:
        raise HTTPException(status_code=404, detail="Algorithm not found.")
    if algorithm.disabled:
        raise HTTPException(status_code=401, detail="Algorithm disabled.")
    try:
        transaction_hash = _withdraw_funds(key_management_service, web3_provider, algorithm, request.relative_amount)
    except ValueError as message:
        raise HTTPException(status_code=500, detail=str(message))

    return WithdrawFundsResponse(
        algorithm=algorithm, recipient=get_env_force(EnvVar.FUND_WITHDRAWAL_ADDRESS), transaction_hash=transaction_hash
    )


def _withdraw_funds(
    key_management_service: KeyManagementService,
    web3_provider: Web3Provider,
    algorithm: AlgorithmInDB,
    relative_amount: Decimal,
) -> ChecksumAddress:
    web3 = web3_provider.get_web3(chain=algorithm.chain_id)
    address = web3.toChecksumAddress(algorithm.controller_wallet_address)
    balance = web3.eth.get_balance(address)
    if not balance > 0:
        raise ValueError("Algorithm has no funds.")

    amount = relative_amount.quantize(Decimal(".01"), rounding=ROUND_HALF_UP)

    unit = get_env(EnvVar.UNIT, "ether")
    txn = {
        "gas": web3.toWei(web3_provider.get_gas_amount(), unit=unit),
        "gasPrice": web3.toWei(web3_provider.get_gas_price(), unit=unit),
        "nonce": web3.eth.get_transaction_count(address),
        "to": web3.toChecksumAddress(get_env_force(EnvVar.FUND_WITHDRAWAL_ADDRESS)),
        "from": address,
        "value": web3.toWei(amount, unit),
    }
    signed_txn = key_management_service.sign_transaction(transaction=txn, address=address, chain=algorithm.chain_id)

    txn_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction).hex()
    receipt = web3.eth.wait_for_transaction_receipt(txn_hash)
    if not receipt["status"] == 1:
        raise ValueError("Transaction reverted")

    return txn_hash
