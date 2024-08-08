from pydantic import BaseModel

from mm.domain.models import Amounts, BeneficiaryAddresses, ContractAddress, Exchange, Seller, Swap, TransactionHash


class CreateSwapRequest(BaseModel):
    contract: ContractAddress
    amounts: Amounts
    addresses: BeneficiaryAddresses
    seller: Seller
    exchange: Exchange

    def to_swap(self):
        return Swap(
            amounts=self.amounts,
            addresses=self.addresses,
            seller=self.seller,
            exchange=self.exchange,
        )


class CreateSwapResponse(BaseModel):
    transaction_hash: TransactionHash


class RetrieveSwapsResponse(BaseModel):
    swaps: list
    page: int
    page_size: int
    total_pages: int
    total: int
