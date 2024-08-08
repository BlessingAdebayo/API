import abc
import enum
from typing import Dict

import requests
from pydantic import BaseModel

API = "https://api.pancakeswap.info/api/v2"


@enum.unique
class CryptoToken(str, enum.Enum):
    Cake = "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82"
    WBNB = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
    BUSD = "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56"
    USDT = "0x55d398326f99059fF775485246999027B3197955"
    ETH = "0x2170Ed0880ac9A755fd29B2688956BD959F933F8"
    USDC = "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"
    BTCB = "0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c"
    TUSD = "0x14016E85a25aeb13065688cAFB43044C2ef86784"
    MBOX = "0x3203c9E46cA618C8C1cE5dC67e7e9D75f5da2377"
    DOT = "0x7083609fCE4d1d8Dc0C979AAb8c869Ea2C873402"
    SAFEMOON = "0x8076C74C5e3F5852037F31Ff0093Eeb8c8ADd8D3"
    BELT = "0xE0e514c71282b6f4e823703a39374Cf58dc3eA4f"
    DAI = "0x1AF3F329e8BE154074D8769D1FFa4eE058B1DBc3"
    ALPACA = "0x8F0528cE5eF7B51152A59745bEfDD91D97091d2F"
    LINK = "0xF8A0BF9cF54Bb92F17374d9e9A321E6a111a51bD"
    HERO = "0xD40bEDb44C081D2935eebA6eF5a3c8A31A1bBE13"
    ADA = "0x3EE2200Efb3400fAbB9AacF31297cBdD1d435D47"
    XRP = "0x1D2F0da169ceB9fC7B3144628dB156f3F6c60dBE"
    BabyDoge = "0xc748673057861a797275CD8A068AbB95A902e8de"
    AXS = "0x715D400F88C167884bbCc41C5FeA407ed4D2f8A0"
    UST = "0x23396cF899Ca06c4472205fC903bDB4de249D6fC"
    UNI = "0xBf5140A22578168FD562DCcF235E5D43A02ce9B1"
    BTT = "0x8595F9dA7b868b1822194fAEd312235E43007b49"
    XVS = "0xcF6BB5389c92Bdda8a3747Ddb454cB7a64626C63"
    rUSD = "0x07663837218A003e66310a01596af4bf4e44623D"
    TRX = "0x85EAC5Ac2F758618dFa09bDbe0cf174e7d574D5B"
    QBT = "0x17B7163cf1Dbd286E262ddc68b553D899B93f526"
    C98 = "0xaEC945e04baF28b135Fa7c640f624f8D90F1C3a6"
    DOGE = "0xbA2aE424d960c26247Dd6c32edC70B295c744C43"
    VAI = "0x4BD17003473389A42DAF6a0a729f6Fdb328BbBd7"
    SFP = "0xD41FDb03Ba84762dD66a0af1a6C8540FF1ba5dfb"
    ALPHA = "0xa1faa113cbE53436Df28FF0aEe54275c13B40975"
    PVU = "0x31471E0791fCdbE82fbF4C44943255e923F1b794"
    HUNNY = "0x565b72163f17849832A692A3c5928cc502f46D69"
    CBET = "0xc212D39E35F22F259457bE79Fc2D822FA7122e6e"
    TKO = "0x9f589e3eabe42ebC94A44727b3f3531C0c877809"
    BEL = "0x8443f091997f06a61670B735ED92734F5628692F"
    TSC = "0xA2a26349448ddAfAe34949a6Cc2cEcF78c0497aC"
    SUSHI = "0x947950BcC74888a40Ffa2593C5798F11Fc9124C4"
    ALICE = "0xAC51066d7bEC65Dc4589368da368b212745d63E8"
    WIN = "0xaeF0d72a118ce24feE3cD1d43d383897D05B4e99"
    CHR = "0xf9CeC8d50f6c8ad3Fb6dcCEC577e05aA32B224FE"
    TLM = "0x2222227E22102Fe3322098e4CBfE18cFebD57c95"
    DODO = "0x67ee3Cb086F8a16f34beE3ca72FAD36F7Db929e2"
    PORNROCKET = "0xCF9f991b14620f5ad144Eec11f9bc7Bf08987622"
    BP = "0xACB8f52DC63BB752a51186D1c55868ADbFfEe9C1"
    SFUND = "0x477bC8d23c634C154061869478bce96BE6045D12"
    NRV = "0x42F6f551ae042cBe50C739158b4f0CAC0Edb9096"
    SGO = "0xe5D46cC0Fd592804B36F9dc6D2ed7D4D149EBd6F"
    CLU = "0x1162E2EfCE13f99Ed259fFc24d99108aAA0ce935"


class PancakeSwapTicker(BaseModel):
    name: str
    symbol: str
    price: str
    price_BNB: str


class PancakeSwapTickerResponse(BaseModel):
    updated_at: int
    data: PancakeSwapTicker


class PancakeSwapTickerListResponse(BaseModel):
    updated_at: int
    data: Dict[str, PancakeSwapTicker]


TickerResponse = PancakeSwapTickerResponse


TickerListResponse = PancakeSwapTickerListResponse


class PancakeSwapService(abc.ABC):
    @abc.abstractmethod
    def get_ticker(self, crypto_token: CryptoToken) -> PancakeSwapTickerResponse:
        pass

    @abc.abstractmethod
    def get_ticker_list(self) -> PancakeSwapTickerListResponse:
        pass


class PancakeSwapAPIService(PancakeSwapService):
    def get_ticker(self, crypto_token: CryptoToken) -> PancakeSwapTickerResponse:
        response = requests.get(API + "/tokens/" + crypto_token)
        response.raise_for_status()

        return PancakeSwapTickerResponse.parse_obj(response.json())

    def get_ticker_list(self) -> PancakeSwapTickerListResponse:
        response = requests.get(API + "/tokens")
        response.raise_for_status()

        return PancakeSwapTickerListResponse.parse_obj(response.json())


class InMemoryPancakeSwapService(PancakeSwapService):
    def get_ticker(self, crypto_token: CryptoToken) -> PancakeSwapTickerResponse:
        return PancakeSwapTickerResponse.parse_obj(
            {"updated_at": 0, "data": {"name": "PancakeSwap Token", "symbol": "Cake", "price": "1", "price_BNB": "1"}}
        )

    def get_ticker_list(self) -> PancakeSwapTickerListResponse:
        return PancakeSwapTickerListResponse.parse_obj(
            {
                "updated_at": 0,
                "data": {
                    "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82": {
                        "name": "PancakeSwap Token",
                        "symbol": "Cake",
                        "price": "1",
                        "price_BNB": "1",
                    },
                    "0x2170Ed0880ac9A755fd29B2688956BD959F933F8": {
                        "name": "Ethereum Token",
                        "symbol": "ETH",
                        "price": "1",
                        "price_BNB": "1",
                    },
                },
            }
        )


def handle_ticker_request(crypto_token: CryptoToken, service: PancakeSwapService) -> PancakeSwapTickerResponse:
    return service.get_ticker(crypto_token)


def handle_ticker_list_request(service: PancakeSwapService) -> PancakeSwapTickerListResponse:
    return service.get_ticker_list()
