from typing import Iterator, List

from eth_typing import ChecksumAddress

from trading_api.algorithm.models.address import (
    AddressKeyPair,
    AddressListResponse,
    AddressPair,
    CreateAddressesRequest,
    KeyedAddressPair,
)
from trading_api.algorithm.models.algorithm import AlgorithmInDB
from trading_api.algorithm.repositories.algorithm import AlgorithmRepository
from trading_api.algorithm.services.kms import KEYId, KeyManagementService


def handle_address_create_request(
    request: CreateAddressesRequest, key_management_service: KeyManagementService
) -> AddressListResponse:
    new_addresses = [new_address(key_management_service=key_management_service) for i in range(request.count)]

    return AddressListResponse(address_pairs=new_addresses)


def new_address(key_management_service) -> KeyedAddressPair:
    key_id: KEYId = key_management_service.create_new_key()
    keyed_pair = KeyedAddressPair(key_alias=key_id.internal, pair=AddressPair(controller_wallet_address=key_id.address))
    return keyed_pair


def handle_address_list_request(
    key_management_service: KeyManagementService, algorithm_repository: AlgorithmRepository
) -> AddressListResponse:
    all_keyed_addresses = key_management_service.all_keyed_addresses()
    all_algorithms = algorithm_repository.all_algorithms()

    address_pairs = create_keyed_address_pairs(all_keyed_addresses, all_algorithms)

    return AddressListResponse(address_pairs=address_pairs)


def create_keyed_address_pairs(
    all_keyed_addresses: Iterator[AddressKeyPair], all_algorithms: Iterator[AlgorithmInDB]
) -> List[KeyedAddressPair]:
    keyed_algorithms = {algo.controller_wallet_address: algo for algo in all_algorithms}
    keyed_address_pairs = [
        to_keyed_address_pair(keyed_address, keyed_algorithms) for keyed_address in all_keyed_addresses
    ]

    return keyed_address_pairs


def to_keyed_address_pair(
    address_key_pair: AddressKeyPair,
    algorithms_keyed_by_controller_wallet_addr: dict[ChecksumAddress, AlgorithmInDB],
) -> KeyedAddressPair:
    algorithm = algorithms_keyed_by_controller_wallet_addr.get(address_key_pair.controller_wallet_address)
    trading_contract_address = None
    if algorithm is not None:
        trading_contract_address = algorithm.trading_contract_address

    return KeyedAddressPair(
        key_alias=address_key_pair.key_alias,
        pair=AddressPair(
            controller_wallet_address=address_key_pair.controller_wallet_address,
            trading_contract_address=trading_contract_address,
        ),
    )
