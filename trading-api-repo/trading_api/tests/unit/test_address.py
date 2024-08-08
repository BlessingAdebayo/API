from web3 import Web3

from tests.utils import ADDR1, ADDR2, ADDR3, KEY_ALIAS1, KEY_ALIAS2, make_algorithm_db
from trading_api.algorithm.models.address import AddressKeyPair, KeyedAddressPair
from trading_api.system.address import create_keyed_address_pairs, new_address


def test_new_address(km_service):
    new_address(km_service)
    all_keyed_addresses = list(km_service.all_keyed_addresses())

    assert len(all_keyed_addresses) == 1
    assert isinstance(all_keyed_addresses[0], AddressKeyPair)


def test_create_address_pairs():
    algorithms = iter([make_algorithm_db()])
    keyed_addresses = iter(
        [
            AddressKeyPair(controller_wallet_address=Web3.toChecksumAddress(ADDR2), key_alias=KEY_ALIAS1),
            AddressKeyPair(controller_wallet_address=Web3.toChecksumAddress(ADDR3), key_alias=KEY_ALIAS2),
        ]
    )

    keyed_address_pairs = create_keyed_address_pairs(all_keyed_addresses=keyed_addresses, all_algorithms=algorithms)

    assert isinstance(keyed_address_pairs, list)
    assert all(isinstance(address, KeyedAddressPair) for address in keyed_address_pairs)
    assert len(keyed_address_pairs) == 2
    assert keyed_address_pairs[0].key_alias == KEY_ALIAS1
    assert keyed_address_pairs[0].pair.trading_contract_address == ADDR1
    assert keyed_address_pairs[0].pair.controller_wallet_address == ADDR2
    assert keyed_address_pairs[1].key_alias == KEY_ALIAS2
    assert keyed_address_pairs[1].pair.trading_contract_address is None
    assert keyed_address_pairs[1].pair.controller_wallet_address == ADDR3
