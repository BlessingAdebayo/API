import logging
from typing import Union

from eth_typing import ChecksumAddress
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse

from trading_api import core_routes, system_routes_v2
from trading_api.algorithm.balance import handle_balance_request_v2
from trading_api.algorithm.models.algorithm import Algorithm, AlgorithmId, AlgorithmWasLocked
from trading_api.algorithm.models.balance import AlgorithmBalanceResponse
from trading_api.algorithm.models.crypto import TransactionHash
from trading_api.algorithm.models.quote import PriceQuoteResponse
from trading_api.algorithm.models.trade import (
    BlockChainError,
    InsufficientFunds,
    Trade,
    TradeFailedResponse,
    TradeInProgressOrNotFoundResponse,
    TradeRequestResponse,
    TradeStatusResponse,
    TradeType,
    TradeTypeLower,
)
from trading_api.algorithm.quote import handle_price_quote_request
from trading_api.algorithm.repositories.algorithm import AlgorithmRepository
from trading_api.algorithm.repositories.lock import AlgorithmLockRepository
from trading_api.algorithm.repositories.nonce import NonceRepository
from trading_api.algorithm.repositories.transaction import TransactionRepository
from trading_api.algorithm.services.kms import KeyManagementService
from trading_api.algorithm.services.web3 import Web3Provider
from trading_api.algorithm.status import background_task_check_tx_status, handle_status_request
from trading_api.algorithm.ticker import (
    CryptoToken,
    PancakeSwapService,
    TickerListResponse,
    TickerResponse,
    handle_ticker_list_request,
    handle_ticker_request,
)
from trading_api.algorithm.trade import TradingContractVersion, handle_trade_request
from trading_api.algorithm_acl import StatusRequestV2, TradeRequestV2
from trading_api.core.container import Container, di_container
from trading_api.core.login import get_current_active_algorithm

logger = logging.getLogger(__name__)

description = """Mercor is the first marketplace for decentralized algorithmic trading and this API lets you communicate
with our platform and deployed smart contracts. It allows you and your algorithm to place buy and sell orders, request
the status of trades, get general algorithm information, and access real-time token prices.

To start trading, please connect your wallet to the platform.

For questions, join us on our [Telegram channel](https://t.me/mercordevelopers).
"""

app = FastAPI(
    title="Mercor Trading API",
    description=description,
    version="2.1.0",
    terms_of_service="https://mercor.finance/terms-and-conditions/",
    contact={
        "name": "Get help with this API",
        "url": "https://docs.mercor.finance/",
    },
)
app.include_router(system_routes_v2.router)
app.include_router(core_routes.router)


@app.get(
    path="/",
    include_in_schema=False,
)
async def root(
    current_algorithm: Algorithm = Depends(get_current_active_algorithm),
):
    return {"message": "To the moon! 🚀", "status": "OK", "version": app.version}


@app.post(
    path="/algorithms/{address}/trade",
    response_model=TradeRequestResponse,  # type: ignore
    summary="Place buy or sell order",
    responses={
        status.HTTP_423_LOCKED: {"model": AlgorithmWasLocked},
        status.HTTP_406_NOT_ACCEPTABLE: {"model": InsufficientFunds},
        status.HTTP_400_BAD_REQUEST: {"model": BlockChainError},
    },
)
async def trade(
    request: TradeRequestV2,
    raw_request: Request,
    address: ChecksumAddress,
    background_tasks: BackgroundTasks,
    container: Container = Depends(di_container),
    current_algorithm: Algorithm = Depends(get_current_active_algorithm),
):
    """Make a trade, where:

    - **address** is the address of the algorithm, equal to the address of the trading contract;
    - **trade_type** is the type of trade to make. Can be either _BUY_ or _SELL_;
    - **slippage_amount** is the maximum difference between the expected and actual price. Can be a number between _0_
      and _1_. For example, _0.01_ means a maximum difference of 1 percent. Default: _0.005_;
    - **relative_amount** is the amount to buy or sell, relative to **symbol**. Can be a number between _0_ and _1_. For
      example, _0.75_ means 75 percent of the base token will be converted into **symbol**. Default: _1_;
    - **symbol** is the token symbol to buy or sell. Can be any token linked to the trading contract. For example:
      _BTC_;
    - **transaction_hash** is the returned hash that can be used to check the trade status.
    """
    _verify_trading_contract_address(current_algorithm, address)
    _verify_trading_contract_version(current_algorithm)

    raw_request_json = await raw_request.json()
    logger.info(f"Received trade request, {address=} {current_algorithm.json()=} {raw_request_json=}")

    if is_buy_trade_type(request.trade_type):
        trade_request = request.to_buy(address)
    else:
        trade_request = request.to_sell(address)  # type: ignore

    response: TradeRequestResponse = handle_trade_request(
        trade_request=trade_request,
        algorithm=current_algorithm,
        lock_repository=container[AlgorithmLockRepository],
        web3_provider=container[Web3Provider],
        km_service=container[KeyManagementService],
        trading_transaction_repository=container[TransactionRepository],
        algorithm_repository=container[AlgorithmRepository],
        nonce_repository=container[NonceRepository],
    )
    if isinstance(response, AlgorithmWasLocked):
        return JSONResponse(status_code=status.HTTP_423_LOCKED, content=response.dict())
    if isinstance(response, InsufficientFunds):
        return JSONResponse(status_code=status.HTTP_406_NOT_ACCEPTABLE, content=response.dict())
    if isinstance(response, BlockChainError):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=response.dict())

    dispatch_check_tx_status(
        trade=trade_request,
        background_tasks=background_tasks,
        algorithm_id=AlgorithmId(public_address=address),
        transaction_hash=response.transaction_hash,
        container=container,
    )

    return response


@app.post(
    path="/algorithms/{address}/status",
    response_model=TradeStatusResponse,  # type: ignore
    summary="Show trade status",
    responses={
        status.HTTP_202_ACCEPTED: {"model": TradeInProgressOrNotFoundResponse},
        status.HTTP_409_CONFLICT: {"model": TradeFailedResponse},
    },
)
async def trade_status(
    request: StatusRequestV2,
    address: ChecksumAddress,
    container: Container = Depends(di_container),
    current_algorithm: Algorithm = Depends(get_current_active_algorithm),
):
    """Request the status of a trade, where:

    - **address** is the address of the algorithm, equal to the address of the trading contract;
    - **transaction_hash** is the hash returned after making a trade;
    - **timeout_in_seconds** is the time to wait for a response. Min: _0_ seconds. Max: _120_ seconds. Default: _0_.
    """
    _verify_trading_contract_version(current_algorithm)

    response: TradeStatusResponse = await handle_status_request(
        request=request.to_status(address),
        web3_provider=container[Web3Provider],
        trading_transaction_repository=container[TransactionRepository],
        algorithm_repository=container[AlgorithmRepository],
    )
    if isinstance(response, TradeInProgressOrNotFoundResponse):
        return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=response.dict())
    if isinstance(response, TradeFailedResponse):
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=response.dict())

    return response


@app.get(
    path="/algorithms/{address}/balance",
    response_model=AlgorithmBalanceResponse,  # type: ignore
    summary="Show algorithm balance",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": BlockChainError},
    },
)
async def balance(
    address: ChecksumAddress,
    container: Container = Depends(di_container),
    current_algorithm: Algorithm = Depends(get_current_active_algorithm),
):
    """Show the algorithm balance, where:

    - **address** is the address of the algorithm, equal to the address of the trading contract;
    - **amount** is the total supply of the algorithm in BNB.
    """
    _verify_trading_contract_address(current_algorithm, address)
    _verify_trading_contract_version(current_algorithm)

    response: AlgorithmBalanceResponse = handle_balance_request_v2(current_algorithm, container[Web3Provider])
    if isinstance(response, BlockChainError):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=response.dict())

    return response


@app.get(
    path="/algorithms/{address}/quote/{symbol}",
    response_model=PriceQuoteResponse,  # type: ignore
    summary="Show price quote",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": BlockChainError},
    },
)
async def get_price_quote(
    address: ChecksumAddress,
    symbol: str,
    container: Container = Depends(di_container),
    current_algorithm: Algorithm = Depends(get_current_active_algorithm),
):
    """Show a price quote for a paired token, where:

    - **address** is the address of the algorithm, equal to the address of the trading contract;
    - **symbol** is the symbol of a paired token. For example: _BTC_;
    - **price** is the token price.
    """
    _verify_trading_contract_version(current_algorithm)

    response: PriceQuoteResponse = handle_price_quote_request(symbol, current_algorithm, container[Web3Provider])
    if isinstance(response, BlockChainError):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=response.dict())

    return response


@app.get(
    path="/ticker/",
    response_model=TickerListResponse,
    summary="Show token data",
)
async def get_ticker_list(
    container: Container = Depends(di_container),
    current_algorithm: Algorithm = Depends(get_current_active_algorithm),
):
    """Show ticker data for all tokens, where:

    - **updated_at** is the time, in UNIX time, the price was last updated;
    - **name** is the token name;
    - **symbol** is the token symbol;
    - **price** is the token price;
    - **price_BNB** is the token price in BNB.
    """
    return handle_ticker_list_request(container[PancakeSwapService])


@app.get(
    path="/ticker/{token}",
    response_model=TickerResponse,
    summary="Show single token data",
)
async def get_ticker(
    token: CryptoToken,
    container: Container = Depends(di_container),
    current_algorithm: Algorithm = Depends(get_current_active_algorithm),
):
    """Show ticker data for a specific token, where:

    - **token** is the token address;
    - **updated_at** is the time, in UNIX time, the price was last updated;
    - **name** is the token name;
    - **symbol** is the token symbol;
    - **price** is the token price;
    - **price_BNB** is the token price in BNB.
    """
    return handle_ticker_request(token, container[PancakeSwapService])


def _verify_trading_contract_address(algorithm: Algorithm, trading_contract_address: str):
    if trading_contract_address != algorithm.trading_contract_address:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                f"Address {trading_contract_address} is not authorized for this action with this authorization header."
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )


def _verify_trading_contract_version(algorithm: Algorithm):
    if algorithm.trading_contract.version != TradingContractVersion.V2_0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"This API version does not accept {algorithm.trading_contract_address=} with "
                f"{algorithm.trading_contract.version=}. Only V2 algorithms are valid."
            ),
        )


def dispatch_check_tx_status(
    background_tasks: BackgroundTasks,
    trade: Trade,
    algorithm_id: AlgorithmId,
    transaction_hash: TransactionHash,
    container: Container,
):
    background_tasks.add_task(
        background_task_check_tx_status,
        trade=trade,
        algorithm_id=algorithm_id,
        transaction_hash=transaction_hash,
        container=container,
    )


def is_buy_trade_type(trade_type: Union[TradeType, TradeTypeLower]):
    return trade_type in (TradeType.BUY, TradeTypeLower.BUY)
