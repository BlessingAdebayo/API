from dataclasses import dataclass

from mm.domain.models import Amounts, BeneficiaryAddresses, Exchange, Slippage


@dataclass(frozen=True)
class Stake:
    amounts_base: Amounts
    amounts_paired: Amounts
    addresses_base: BeneficiaryAddresses
    addresses_paired: BeneficiaryAddresses
    slippage: Slippage
    exchange: Exchange
