from typing import Optional

from pydantic import BaseModel

from .contract import ContractSpec

WalletAddress = str


class KeyAddressPair(BaseModel):
    internal_id: str
    external_id: str  # AWS alias.
    wallet: WalletAddress
    spec: Optional[ContractSpec]  # Set on contract linkage.

    @property
    def contract(self):
        if self.spec is None:
            return None
        return self.spec.address

    @property
    def chain(self):
        if self.spec is None:
            return None
        return self.spec.chain

    def filter_query(self) -> dict:
        return {"wallet": self.wallet}


KeyAddressPairs = list[KeyAddressPair]
