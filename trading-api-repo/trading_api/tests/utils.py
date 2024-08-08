import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Union

from eth_typing import ChecksumAddress, HexAddress, HexStr

from trading_api.algorithm.models.algorithm import (
    Algorithm,
    AlgorithmId,
    AlgorithmInDB,
    AlgorithmTransaction,
    TradingContract,
    TradingContractVersion,
)
from trading_api.algorithm.models.crypto import ChainId, TransactionHash
from trading_api.algorithm.models.trade import (
    BuyTrade,
    BuyTradeV2,
    SellTrade,
    SellTradeV2,
    Slippage,
    TradeRequest,
    TradeStatus,
    TradeType,
    TradingTransaction,
)
from trading_api.algorithm.repositories.algorithm import AlgorithmRepository
from trading_api.core.security import encode_password


def get_id() -> str:
    return str(uuid.uuid4())


def get_access_header(app_inst, algorithm_user):
    app_inst.container[AlgorithmRepository].upsert_algorithm(algorithm_user)

    request = load_stub("body-for-algorithm-login.json")
    response = app_inst.client.post("/api/v1/login", data=request)

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"
    received_token = response.json()["access_token"]
    return {"Authorization": f"bearer {received_token}"}


def to_checksum_address(address: str):
    return ChecksumAddress(HexAddress(HexStr(address)))


ADDR1 = to_checksum_address("0xF05EF1C844E39757B6F94f89427B1AC302fcAe1b")
ADDR2 = to_checksum_address("0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf")  # This is the default user in tests.
ADDR3 = to_checksum_address("0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82")
ADDR4 = to_checksum_address("0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56")
ADDR5 = to_checksum_address("0x55d398326f99059fF775485246999027B3197955")

KEY_ALIAS1 = "controller-wallet/development/00000000-0000-0000-0000-000000000001"
KEY_ALIAS2 = "controller-wallet/development/00000000-0000-0000-0000-000000000002"


def make_algorithm(
    trading_contract_address=ADDR1,
    controller_wallet_address=ADDR2,
    chain_id: ChainId = ChainId.RTN,
    trading_contract: TradingContract = TradingContract(version=TradingContractVersion.V1_0),
    disabled: bool = False,
) -> Algorithm:
    return Algorithm(
        trading_contract_address=trading_contract_address,
        controller_wallet_address=controller_wallet_address,
        trading_contract=trading_contract,
        chain_id=chain_id,
        disabled=disabled,
    )


def make_algorithm_db(
    trading_contract_address=ADDR1,
    controller_wallet_address=ADDR2,
    chain_id: ChainId = ChainId.RTN,
    trading_contract: TradingContract = TradingContract(version=TradingContractVersion.V1_0),
    password="secret",
) -> AlgorithmInDB:
    return AlgorithmInDB(
        trading_contract_address=trading_contract_address,
        controller_wallet_address=controller_wallet_address,
        trading_contract=trading_contract,
        chain_id=chain_id,
        hashed_password=encode_password(password),
    )


def make_buy_trade(trading_contract_address: ChecksumAddress = ADDR1) -> BuyTrade:
    return BuyTrade(
        algorithm_id=AlgorithmId(public_address=trading_contract_address),
        slippage=Slippage(amount=Decimal(100)),
        relative_amount=Decimal(0.1),
    )


def make_sell_trade(trading_contract_address: ChecksumAddress = ADDR1) -> SellTrade:
    return SellTrade(
        algorithm_id=AlgorithmId(public_address=trading_contract_address),
        slippage=Slippage(amount=Decimal(100)),
        relative_amount=Decimal(0.1),
    )


def make_buy_trade_v2(trading_contract_address: ChecksumAddress = ADDR1, symbol="BTC") -> BuyTradeV2:
    return BuyTradeV2(
        algorithm_id=AlgorithmId(public_address=trading_contract_address),
        slippage=Slippage(amount=Decimal(100)),
        relative_amount=Decimal(0.1),
        symbol=symbol,
    )


def make_sell_trade_v2(trading_contract_address: ChecksumAddress = ADDR1, symbol="BTC") -> SellTradeV2:
    return SellTradeV2(
        algorithm_id=AlgorithmId(public_address=trading_contract_address),
        slippage=Slippage(amount=Decimal(100)),
        relative_amount=Decimal(0.1),
        symbol=symbol,
    )


def make_trade_request(trade: Union[BuyTrade, SellTrade]) -> TradeRequest:
    return TradeRequest(trade=trade)


def make_algorithm_transaction(
    algorithm_id: AlgorithmId = AlgorithmId(public_address=ADDR2),
    hash_value: ChecksumAddress = ADDR3,
) -> AlgorithmTransaction:
    return AlgorithmTransaction(algorithm_id=algorithm_id, transaction_hash=TransactionHash(value=hash_value))


def make_transaction(
    created_at: datetime = None,
    relative_amount: Decimal = Decimal("0.5"),
    slippage_amount: Decimal = Decimal("0.05"),
    status: TradeStatus = TradeStatus.TRADE_IN_PROGRESS_OR_NOT_FOUND,
    trading_contract_address: ChecksumAddress = ADDR2,
    transaction_hash: ChecksumAddress = ADDR3,
    updated_at: datetime = None,
    trade_type: TradeType = TradeType.BUY,
):
    if created_at is None:
        created_at = datetime.now(timezone.utc)
    if updated_at is None:
        updated_at = datetime.now(timezone.utc)

    return TradingTransaction(
        transaction_hash=transaction_hash,
        trading_contract_address=trading_contract_address,
        slippage_amount=slippage_amount,
        relative_amount=relative_amount,
        status=status,
        created_at=created_at,
        updated_at=updated_at,
        trade_type=trade_type,
    )


def load_stub(relative_path) -> dict:
    full_path = Path(__file__).parent / "stubs" / relative_path
    return json.loads(full_path.read_text())
