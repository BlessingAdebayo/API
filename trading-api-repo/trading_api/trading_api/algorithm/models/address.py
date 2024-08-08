from typing import List, Optional

from eth_typing import ChecksumAddress
from pydantic import BaseModel


class AddressKeyPair(BaseModel):
    controller_wallet_address: ChecksumAddress  # Address coupled to the public-key in AWS KMS
    key_alias: str  # Amazon aws KMS key-id belonging to this address.

    def filter_query(self) -> dict:
        return {"controller_wallet_address": self.controller_wallet_address}


class AddressPair(BaseModel):
    controller_wallet_address: ChecksumAddress
    trading_contract_address: Optional[
        ChecksumAddress
    ]  # If the trading_contract_address is None, the controller wallet is not yet paired.


class KeyedAddressPair(BaseModel):
    key_alias: str
    pair: AddressPair


class AddressListResponse(BaseModel):
    address_pairs: List[KeyedAddressPair]


class CreateAddressesRequest(BaseModel):
    count: int
