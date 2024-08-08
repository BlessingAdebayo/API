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
    path="/wallets/",
    response_model=AddressListResponse,  # type: ignore
    summary="Show controller wallets",
)
async def get_controller_wallet_addresses(
    container: Container = Depends(Container),
    current_system_user=Security(get_current_system_user, scopes=["system"]),
):
    """Show controller wallet and trading contract pairs, where:

    - **key_alias** is the alias of the private key linked to the controller wallet;
    - **controller_wallet_address** is the address of the controller wallet;
    - **trading_contract_address** is the address of the trading contract, equal to the address of an algorithm. If it
      is _None_, it is not yet paired with an algorithm.
    """
    return handle_address_list_request(
        key_management_service=container[KeyManagementService], algorithm_repository=container[AlgorithmRepository]
    )


@router.post(
    path="/wallets/",
    response_model=AddressListResponse,  # type: ignore
    summary="Create controller wallets",
)
async def create_controller_wallet_addresses(
    createRequest: CreateAddressesRequest,
    container: Container = Depends(di_container),
    current_system_user=Security(get_current_system_user, scopes=["system"]),
):
    """Create controller wallets, where:

    - **count** is the number of controller wallet addresses to create.
    """
    return handle_address_create_request(request=createRequest, key_management_service=container[KeyManagementService])


@router.post(
    path="/algorithms/{address}",
    response_model=Union[RegisteredAlgorithmResponse, FailedToRegisterAlgorithmResponse],  # type: ignore
    summary="Register algorithm",
)
async def register_algorithm(
    address: ChecksumAddress,
    algorithm: RegisterAlgorithm,
    container: Container = Depends(di_container),
    current_system_user=Security(get_current_system_user, scopes=["system"]),
):
    """Register an algorithm, where:

    - **address** is the address of the algorithm to register, equal to the address of the trading contract;
    - **trading_contract_address** is the address of the trading contract, equal to the address of the algorithm to
      register;
    - **controller_wallet_address** is the address of the controller wallet;
    - **trading_contract_version** is the version of the trading contract;
    - **chain_id** is the ID of the blockchain used;
    - **disabled** is a toggle to disable the algorithm. Default: _False_;
    - **unhashed_password** is the algorithm secret.
    """
    assert address == algorithm.trading_contract_address

    return handle_register_algorithm(algorithm, container[AlgorithmRepository])


@router.patch(
    path="/algorithms/{address}",
    response_model=Union[DisabledAlgorithmResponse, FailedToDisableAlgorithmResponse],  # type: ignore
    summary="Disable algorithm",
)
async def disable_algorithm(
    address: ChecksumAddress,
    container: Container = Depends(di_container),
    current_system_user=Security(get_current_system_user, scopes=["system"]),
):
    """Disable an algorithm, where:

    - **address** is the address of the algorithm to disable, equal to the address of the trading contract.
    """
    return handle_disable_algorithm(DisableAlgorithm(trading_contract_address=address), container[AlgorithmRepository])


@router.get(
    path="/algorithms/{address}",
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
    """Paginate transactions made by an algorithm, where:

    - **address** is the address of the algorithm to disable, equal to the address of the trading contract;
    - **skip** is the number of transactions to skip;
    - **limit** is the number of items to set per page.
    """
    return handle_transaction_list_request(address, skip, limit, container[TransactionRepository])


@router.post(
    path="/algorithms/{address}/balance",
    response_model=WithdrawFundsResponse,
    summary="Withdraw algorithm funds",
)
async def withdraw_algorithm_funds(
    address: ChecksumAddress,
    request: WithdrawFundsRequest,
    container: Container = Depends(di_container),
    current_system_user=Security(get_current_system_user, scopes=["system"]),
):
    """Withdraw funds from an algorithm, where:

    - **address** is the address of the algorithm to withdraw funds from, equal to the address of the trading contract;
    - **relative_amount** is the amount to withdraw from the controller wallet paired to the algorithm. Can be a number
      between _0_ and _1_. For example, _0.95_ means 95 percent of the funds from the controller wallet will be
      withdrawn.
    """
    return handle_withdraw_funds(
        request=request,
        algorithm_id=AlgorithmId(public_address=address),
        web3_provider=container[Web3Provider],
        key_management_service=container[KeyManagementService],
        algorithm_repository=container[AlgorithmRepository],
    )
