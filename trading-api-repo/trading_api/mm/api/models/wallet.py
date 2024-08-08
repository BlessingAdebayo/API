from typing import Optional

from pydantic import BaseModel

from mm.domain.models import ContractAddress, KeyAddressPair, KeyAddressPairs, WalletAddress


class CreateWalletsRequest(BaseModel):
    count: int


class WalletAddressPair(BaseModel):
    internal_id: str
    external_id: str  # AWS alias.
    wallet: WalletAddress
    contract: Optional[ContractAddress]

    @classmethod
    def from_pair(cls, pair: KeyAddressPair):
        return WalletAddressPair(
            internal_id=pair.internal_id,
            external_id=pair.external_id,
            wallet=pair.wallet,
            contract=pair.contract,
        )


WalletAddressPairs = list[WalletAddressPair]


class CreateWalletsResponse(BaseModel):
    pairs: WalletAddressPairs

    @classmethod
    def from_pairs(cls, pairs: KeyAddressPairs):
        return CreateWalletsResponse(pairs=list(map(WalletAddressPair.from_pair, pairs)))
