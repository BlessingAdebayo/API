from pydantic import BaseModel

from mm.domain.models import Amounts, BeneficiaryAddresses, ContractAddress, Exchange, Slippage, Stake, TransactionHash


class CreateStakeInLiquidityMakerRequest(BaseModel):
    contract: ContractAddress
    amounts_base: Amounts
    amounts_paired: Amounts
    addresses_base: BeneficiaryAddresses
    addresses_paired: BeneficiaryAddresses
    slippage: Slippage
    exchange: Exchange

    def to_stake(self):
        return Stake(
            amounts_base=self.amounts_base,
            amounts_paired=self.amounts_paired,
            addresses_base=self.addresses_base,
            addresses_paired=self.addresses_paired,
            slippage=self.slippage,
            exchange=self.exchange,
        )


class CreateStakeInLiquidityMakerResponse(BaseModel):
    transaction_hash: TransactionHash
