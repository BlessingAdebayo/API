from typing import Union

from eth_typing import ChecksumAddress
from fastapi import APIRouter, Depends, Security

from trading_api import EnvVar, get_env_force
from trading_api.algorithm.models.address import AddressListResponse, CreateAddressesRequest
from trading_api.algorithm.models.algorithm import (
    AlgorithmId,
    DisableAlgorithm,
    DisabledAlgorithmResponse,
    FailedToDisableAlgorithmResponse,
    FailedToRegisterAlgorithmResponse,
    RegisterAlgorithm,
    RegisteredAlgorithmResponse,
)
from trading_api.algorithm.models.trade import TransactionPage
from trading_api.algorithm.repositories.algorithm import AlgorithmRepository
from trading_api.algorithm.repositories.transaction import TransactionRepository
from trading_api.algorithm.services.kms import KeyManagementService
from trading_api.algorithm.services.web3 import Web3Provider
from trading_api.core.container import Container, di_container
from trading_api.core.login import get_current_system_user
from trading_api.system.address import handle_address_create_request, handle_address_list_request
from trading_api.system.disable import handle_disable_algorithm
from trading_api.system.models.withdraw import WithdrawFundsRequest, WithdrawFundsResponse
from trading_api.system.register import handle_register_algorithm
from trading_api.system.transactions import handle_transaction_list_request
from trading_api.system.withdraw import handle_withdraw_funds

router = APIRouter(
    include_in_schema=get_env_force(EnvVar.STAGE, "local") != "production",
    tags=["system"],
)


@router.get(
    path="/algorithms/",
    response_model=AddressListResponse,  # type: ignore
    summary="Show controller wallets",
)
async def get_controller_wallet_addresses(
    container: Container = Depends(Container),
    current_system_user=Security(get_current_system_user, scopes=["system"]),
):
    """List pairs of controller wallet address and trading contract address, where **output**:

    - **key_alias** is the alias of the private key linked to the controller wallet;
    - **controller_wallet_address** is the public address of the controller wallet;
    - **trading_contract_address** is the public address of the trading contract.

    Note: If the `trading_contract_address` is `None`, the controller wallet is not yet paired.
    """
    return handle_address_list_request(
        key_management_service=container[KeyManagementService], algorithm_repository=container[AlgorithmRepository]
    )


@router.post(
    path="/algorithms/create",
    response_model=AddressListResponse,  # type: ignore
    summary="Create controller wallets",
)
async def create_controller_wallet_addresses(
    createRequest: CreateAddressesRequest,
    container: Container = Depends(di_container),
    current_system_user=Security(get_current_system_user, scopes=["system"]),
):
    """Create controller wallets addresses, where **input**:

    - **count** is the number of controller wallet addresses to create.
    """
    return handle_address_create_request(request=createRequest, key_management_service=container[KeyManagementService])


@router.post(
    path="/algorithms/{address}/register",
    response_model=Union[RegisteredAlgorithmResponse, FailedToRegisterAlgorithmResponse],  # type: ignore
    summary="Register algorithm",
)
async def register_algorithm(
    address: str,
    algorithm: RegisterAlgorithm,
    container: Container = Depends(di_container),
    current_system_user=Security(get_current_system_user, scopes=["system"]),
):
    """Register an algorithm, where **input**:

    - **trading_contract_address** is the public address of the trading contract;
    - **controller_wallet_address** is the public address of the controller wallet;
    - **trading_contract_version** is the version of the trading contract;
    - **chain_id** is the ID of the blockchain that is used;
    - **disabled** is a toggle to enable the algorithm. Default: enabled;
    - **unhashed_password** is the system password.
    """
    assert address == algorithm.trading_contract_address

    return handle_register_algorithm(algorithm, container[AlgorithmRepository])


@router.post(
    path="/algorithms/{address}/disable",
    response_model=Union[DisabledAlgorithmResponse, FailedToDisableAlgorithmResponse],  # type: ignore
    summary="Disable algorithm",
)
async def disable_algorithm(
    address: str,
    algorithm: DisableAlgorithm,
    container: Container = Depends(di_container),
    current_system_user=Security(get_current_system_user, scopes=["system"]),
):
    """Disable an algorithm, where **input**:

    - **trading_contract_address** is the public address of the trading contract.
    """
    assert address == algorithm.trading_contract_address

    return handle_disable_algorithm(algorithm, container[AlgorithmRepository])


@router.get(
    path="/algorithms/{address}/transactions",
    response_model=TransactionPage,  # type: ignore
    summary="Paginate algorithm transactions",
)
async def get_transactions(
    address: ChecksumAddress,
    skip: int = 0,
    limit: int = 50,
    container: Container = Depends(di_container),
    current_system_user=Security(get_current_system_user, scopes=["system"]),
):
    """List paginated transactions of an algorithm, where **input**:

    - **trading_wallet_address** is the public address of the trading wallet.
    """
    return handle_transaction_list_request(address, skip, limit, container[TransactionRepository])


@router.post(
    path="/algorithms/{address}/withdraw",
    response_model=WithdrawFundsResponse,
    summary="Withdraw algorithm funds",
)
async def withdraw_algorithm_funds(
    address: str,
    request: WithdrawFundsRequest,
    container: Container = Depends(di_container),
    current_system_user=Security(get_current_system_user, scopes=["system"]),
):
    """Withdraw funds from an algorithm, where **input**:

    - **relative_amount** is the percentage (as a number between 0 and 1) to withdraw from the controller wallet of the
                          algorithm.

    Note: The `relative_amount`, given as 0.05 means 5% of the funds from the controller wallet will be withdrawn.
    """
    return handle_withdraw_funds(
        request=request,
        algorithm_id=AlgorithmId(public_address=address),
        web3_provider=container[Web3Provider],
        key_management_service=container[KeyManagementService],
        algorithm_repository=container[AlgorithmRepository],
    )
