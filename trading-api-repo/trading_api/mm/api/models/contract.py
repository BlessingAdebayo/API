from pydantic import BaseModel

from mm.domain.models import ChainId, ContractAddress, WalletAddress


class LinkContractRequest(BaseModel):
    wallet: WalletAddress
    contract: ContractAddress
    chain: ChainId


class LinkContractResponse(BaseModel):
    message: str = "OK."
