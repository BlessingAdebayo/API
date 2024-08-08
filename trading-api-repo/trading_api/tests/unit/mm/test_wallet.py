from mm.domain.repositories import WalletKeyRepository
from mm.domain.services import KeyManagementService
from tests.unit.mm.utils import assert_status_code, make_pair

BASE_URI = "/api/avatea"
POST_WALLETS = f"{BASE_URI}/wallets"
LINK_CONTRACT = f"{BASE_URI}/contracts"


def test_create_wallet(mm_app_unit):
    request = {"count": 2}

    kms = mm_app_unit.container[KeyManagementService]
    kms.add_stub_key(
        make_pair(internal_id="test_internal_id_1", external_id="test_external_id_1", wallet="test_wallet_address_1")
    )
    kms.add_stub_key(
        make_pair(
            internal_id="test_internal_id_2",
            external_id="test_external_id_2",
            wallet="test_wallet_address_2",
        )
    )

    response = mm_app_unit.client.post(POST_WALLETS, json=request)

    assert response.status_code == 200
    data = response.json()
    assert len(data["pairs"]) == 2

    pair_1 = data["pairs"][1]
    assert pair_1["internal_id"] == "test_internal_id_1"
    assert pair_1["external_id"] == "test_external_id_1"
    assert pair_1["wallet"] == "test_wallet_address_1"
    assert pair_1["contract"] is None

    pair_2 = data["pairs"][0]
    assert pair_2["internal_id"] == "test_internal_id_2"
    assert pair_2["external_id"] == "test_external_id_2"
    assert pair_2["wallet"] == "test_wallet_address_2"


def test_link_contract(mm_app_unit):
    keys: WalletKeyRepository = mm_app_unit.container[WalletKeyRepository]
    wallet_address = "test_wallet_address_2"
    contract_address = "test_contract_address_2"
    chain_id = "RTN"
    request = {"wallet": wallet_address, "contract": contract_address, "chain": chain_id}
    keys.upsert(pair=make_pair(wallet=wallet_address))
    before = keys.get_by_wallet(wallet=wallet_address)
    assert before is not None and before.spec is None

    response = mm_app_unit.client.post(LINK_CONTRACT, json=request)

    assert_status_code(200, response)

    after = keys.get_by_wallet(wallet=wallet_address)
    assert after is not None
    assert after.spec.address == contract_address
    assert after.spec.chain == chain_id


def test_link_to_non_existing_wallet(mm_app_unit):
    keys: WalletKeyRepository = mm_app_unit.container[WalletKeyRepository]
    wallet_address = "test_wallet_address_2"
    contract_address = "test_contract_address_2"
    request = {
        "wallet": "test_wallet_address_3",
        "contract": contract_address,
        "chain": "RTN",
    }
    keys.upsert(pair=make_pair(wallet_address))

    response = mm_app_unit.client.post(LINK_CONTRACT, json=request)

    assert_status_code(404, response)
