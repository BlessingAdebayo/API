from mm.data.repositories import MongoWalletKeyRepository
from mm.domain.repositories import WalletKeyRepository
from tests.unit.mm.utils import make_pair


def test_add_to_key_repository(mm_app_int):
    keys: MongoWalletKeyRepository = mm_app_int.container[WalletKeyRepository]

    keys.upsert(pair=make_pair(wallet="test_wallet_address_2"))

    pair = make_pair(contract="test_contract_address_1")
    keys.upsert(pair=pair)

    r = keys.get_by_wallet(wallet=pair.wallet)

    assert "test_wallet_address_2" != r.wallet
    assert pair.wallet == r.wallet
    assert pair.contract == "test_contract_address_1"
    assert pair.external_id == r.external_id
    assert pair.internal_id == r.internal_id

    old_id = pair.external_id
    pair.external_id = "test_external_id_123"
    keys.upsert(pair=pair)

    r = keys.get_by_wallet(wallet=pair.wallet)

    assert pair.external_id == r.external_id
    assert old_id != r.external_id
