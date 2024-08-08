from dataclasses import dataclass

from mm.domain.models import BeneficiaryAddresses


@dataclass(frozen=True)
class Release:
    addresses: BeneficiaryAddresses
