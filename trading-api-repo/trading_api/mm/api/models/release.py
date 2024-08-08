from pydantic import BaseModel

from mm.domain.models import BeneficiaryAddresses, ContractAddress, Release, TransactionHash


class CreateReleaseForRequest(BaseModel):
    contract: ContractAddress
    addresses: BeneficiaryAddresses

    def to_release_for(self):
        return Release(addresses=self.addresses)


class CreateReleaseForResponse(BaseModel):
    transaction_hash: TransactionHash
