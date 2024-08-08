from datetime import datetime
from uuid import uuid4

import requests

from mm.domain.models import (
    Address,
    Amount,
    BeneficiaryAddresses,
    ChainId,
    KeyAddressPair,
    Seller,
    Slippage,
    SwapRecord,
    TradeRecord,
    TradeType,
    TransactionStatus,
)
from mm.domain.models.contract import ContractSpec


def make_pair(
    internal_id: str = None, external_id: str = None, wallet: str = None, contract: str = None
) -> KeyAddressPair:
    spec = None
    if contract:
        spec = ContractSpec(
            address=contract,
            chain=ChainId("RTN"),
        )
    return KeyAddressPair(
        internal_id=internal_id or str(uuid4()),
        external_id=external_id or str(uuid4()),
        wallet=wallet or str(uuid4()),
        spec=spec,
    )


def make_trade(hash: str = None, contract: str = None, addresses: BeneficiaryAddresses = None) -> TradeRecord:
    return TradeRecord(
        hash=hash or str(uuid4()),
        contract=contract or str(uuid4()),
        slippage=Slippage("0.5"),
        status=TransactionStatus.TRANSACTION_IN_PROGRESS,
        type=TradeType.BUY,
        addresses=addresses or [Address(str(uuid4()))],
        amounts=[Amount("1")],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def make_swap(
    hash: str = None,
    contract: str = None,
    addresses: BeneficiaryAddresses = None,
    seller: Seller = None,
) -> SwapRecord:
    return SwapRecord(
        hash=hash or str(uuid4()),
        contract=contract or str(uuid4()),
        status=TransactionStatus.TRANSACTION_IN_PROGRESS,
        amounts=[Amount("1")],
        addresses=addresses or [Address(str(uuid4()))],
        seller=seller or str(uuid4()),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def assert_status_code(expected: int, response: requests.Response):
    assert (
        response.status_code == expected
    ), f"response.status_code != {expected}, instead: {response.status_code}, json:{response.json()}`"
