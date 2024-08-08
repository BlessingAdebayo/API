import json
import logging
from decimal import Decimal
from pathlib import Path
from typing import Optional

from web3 import Web3
from web3.contract import Contract

from mm import API_ROOT_PATH
from mm.domain.models import ChainId, ContractAddress, ContractVersion
from mm.domain.services import Web3Provider

GAS_AMOUNT = Decimal(100_000 / 1e18)
GAS_PRICE = Decimal(5e9 / 1e18)

logger = logging.getLogger(__name__)


class HTTPWeb3Provider(Web3Provider):
    def __init__(
        self,
        web3_bsc_uri: str,
        web3_rtn_uri: str,
        ecr_contract_bsc: ContractAddress,
        ecr_contract_rtn: ContractAddress,
        ecr_contract_info_json_path: Path,
    ):
        self.ecr_contract_info_json_path = ecr_contract_info_json_path
        self._http_rtn_web3: Optional[Web3] = None
        self._http_bsc_web3: Optional[Web3] = None

        self._web3_rtn_uri = web3_rtn_uri
        self._web3_bsc_uri = web3_bsc_uri
        self._ecr_contract_bsc = ecr_contract_bsc
        self._ecr_contract_rtn = ecr_contract_rtn

    def get_ecr_contract(self, chain: ChainId) -> Contract:
        address, abi = self._load_ecr_contract_details(chain)

        return self.get_web3(chain=chain).eth.contract(address=address, abi=abi)  # type: ignore

    def get_contract(
        self, contract: ContractAddress, chain: ChainId, version: ContractVersion = ContractVersion.V1_0
    ) -> Contract:
        abi = load_abi(
            Path(
                API_ROOT_PATH
                / ".contracts"
                / "mm"
                / version.value
                / "artifacts"
                / "contracts"
                / "MarketMaker.sol"
                / "MarketMaker.json"
            )
        )

        return self.get_web3(chain=chain).eth.contract(address=contract, abi=abi)  # type: ignore

    def get_web3(self, chain: ChainId) -> Web3:
        if chain == chain.BSC:
            return self.bsc_web3()
        if chain == chain.RTN:
            return self.rtn_web3()

        raise ValueError(f"ChainId {chain} is not implemented.")

    def rtn_web3(self) -> Web3:
        if self._http_rtn_web3 is None:
            self._http_rtn_web3 = Web3(Web3.HTTPProvider(self._web3_rtn_uri))
            return self._http_rtn_web3

        return self._http_rtn_web3

    def bsc_web3(self) -> Web3:
        if self._http_bsc_web3 is None:
            self._http_bsc_web3 = Web3(Web3.HTTPProvider(self._web3_bsc_uri))
            return self._http_bsc_web3

        return self._http_bsc_web3

    def _load_ecr_contract_details(self, chain) -> tuple[ContractAddress, dict]:
        abi = load_abi(self.ecr_contract_info_json_path)
        if chain == chain.BSC:
            return self._ecr_contract_bsc, abi
        if chain == chain.RTN:
            return self._ecr_contract_rtn, abi

        raise ValueError(f"ChainId {chain} is not implemented.")


def load_abi(path: Path) -> dict:
    with open(path) as f:
        info_json = json.load(f)
        abi = info_json["abi"]

    return abi
