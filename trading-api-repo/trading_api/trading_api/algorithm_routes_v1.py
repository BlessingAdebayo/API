import logging

from eth_typing import ChecksumAddress
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from starlette import status
from starlette.responses import JSONResponse

from trading_api import core_routes, system_routes_v1
from trading_api.algorithm.balance import handle_balance_request
from trading_api.algorithm.models.algorithm import (
    Algorithm,
    AlgorithmIsLocked,
    AlgorithmWasLocked,
    TradingContractVersion,
)
from trading_api.algorithm.models.balance import AlgorithmBalance, AlgorithmBalanceResponse
from trading_api.algorithm.models.trade import (
    BlockChainError,
    InsufficientFunds,
    StatusRequest,
    TradeFailedResponse,
    TradeInProgressOrNotFoundResponse,
    TradeRequestResponse,
    TradeStatusResponse,
    TradeSuccessfulResponse,
)
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
from trading_api.algorithm.trade import handle_trade_request
from trading_api.algorithm_acl import BuyRequest, SellRequest
from trading_api.core.container import Container, di_container
from trading_api.core.login import get_current_active_algorithm

logger = logging.getLogger(__name__)

description = """Mercor is the first marketplace for decentralized algorithmic trading and this API lets you communicate
with our platform and deployed smart contracts. It allows you and your algorithm to place buy and sell orders, request
the status of trades, get general algorithm information, and access real-time token prices.

To start trading, please connect your wallet to the platform.

For questions, join us on our [Telegram channel](https://t.me/mercordevelopers)."""

app = FastAPI(
    title="Mercor Trading API",
    description=description,
    version="1.1.3",
    terms_of_service="https://mercor.finance/terms-and-conditions/",
    contact={
        "name": "Get help with this API",
        "url": "https://docs.mercor.finance/",
    },
)
app.include_router(system_routes_v1.router)
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
    path="/buy",
    response_model=TradeRequestResponse,  # type: ignore
    summary="Place buy order",
    responses={
        status.HTTP_200_OK: {"model": AlgorithmIsLocked},
        status.HTTP_423_LOCKED: {"model": AlgorithmWasLocked},
        status.HTTP_406_NOT_ACCEPTABLE: {"model": InsufficientFunds},
        status.HTTP_400_BAD_REQUEST: {"model": BlockChainError},
    },
)
async def buy(
    request: BuyRequest,
    background_tasks: BackgroundTasks,
    container: Container = Depends(di_container),
    current_algorithm: Algorithm = Depends(get_current_active_algorithm),
):
    """Place a buy order, where **input**:

    - **public_address** is the public address of the algorithm;
    - **slippage** is the maximum allowed difference in price percentage-wise (as a number between 0 and 1)
                   between the expected and actual price;
    - **relative_amount** is the percentage (as a number between 0 and 1) to buy relative to the paired token.

    Note: The `relative_amount`, given as 0.05 means 5% of the base token will be converted into the paired token.

    Note: `relative_amount` and `slippage` are both Decimal types and can be passed in as a string to avoid losing any
          precision.

    Note: The returned `transaction_hash` can be used to request its trade status.
    """
    _verify_trading_contract_address(current_algorithm, request.trade.algorithm_id.public_address)
    _verify_trading_contract_version(current_algorithm)

    buy = request.to_buy()

    response: TradeRequestResponse = handle_trade_request(
        trade_request=buy,
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
    background_tasks.add_task(
        background_task_check_tx_status,
        trade=buy,
        algorithm_id=request.trade.algorithm_id,
        transaction_hash=response.transaction_hash,
        container=container,
    )

    return response


@app.post(
    path="/sell",
    response_model=TradeRequestResponse,  # type: ignore
    summary="Place sell order",
    responses={
        status.HTTP_423_LOCKED: {"model": AlgorithmWasLocked},
        status.HTTP_406_NOT_ACCEPTABLE: {"model": InsufficientFunds},
        status.HTTP_400_BAD_REQUEST: {"model": BlockChainError},
    },
)
async def sell(
    request: SellRequest,
    background_tasks: BackgroundTasks,
    container: Container = Depends(di_container),
    current_algorithm: Algorithm = Depends(get_current_active_algorithm),
):
    """Place a sell order, where **input**:

    - **public_address** is the public address of the algorithm;
    - **slippage** is the maximum allowed difference in price percentage-wise (as a number between 0 and 1)
                   between the expected and actual price;
    - **relative_amount** is the percentage (as a number between 0 and 1) to sell relative to the base token.

    Note: The `relative_amount`, given as 0.05 means 5% of the paired token will be converted into the base token.

    Note: `relative_amount` and `slippage` are both Decimal types and can be passed in as a string to avoid losing any
          precision.

    Note: The returned `transaction_hash` can be used to request its trade status.
    """
    _verify_trading_contract_address(current_algorithm, request.trade.algorithm_id.public_address)
    _verify_trading_contract_version(current_algorithm)

    sell = request.to_sell()

    response: TradeRequestResponse = handle_trade_request(
        trade_request=sell,
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
    background_tasks.add_task(
        background_task_check_tx_status,
        trade=sell,
        algorithm_id=request.trade.algorithm_id,
        transaction_hash=response.transaction_hash,
        container=container,
    )

    return response


@app.post(
    path="/status",
    response_model=TradeStatusResponse,  # type: ignore
    summary="Show trade status",
    responses={
        status.HTTP_200_OK: {"model": TradeSuccessfulResponse},
        status.HTTP_202_ACCEPTED: {"model": TradeInProgressOrNotFoundResponse},
        status.HTTP_409_CONFLICT: {"model": TradeFailedResponse},
    },
)
async def trade_status(
    request: StatusRequest,
    container: Container = Depends(di_container),
    current_algorithm: Algorithm = Depends(get_current_active_algorithm),
):
    """Request the status of a buy or sell order, where **input**:

    - **transaction_hash** is the transaction hash returned after placing a buy or sell order;
    - **timeout_in_seconds** is the time to wait for a response. Min: 0, Max: 120 seconds.
    """
    _verify_trading_contract_version(current_algorithm)

    response: TradeStatusResponse = await handle_status_request(
        request, container[Web3Provider], container[TransactionRepository], container[AlgorithmRepository]
    )
    if isinstance(response, TradeInProgressOrNotFoundResponse):
        return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=response.dict())
    if isinstance(response, TradeFailedResponse):
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=response.dict())

    return response


@app.get(
    path="/balance",
    response_model=AlgorithmBalanceResponse,  # type: ignore
    summary="Show algorithm balance",
    responses={
        status.HTTP_200_OK: {"model": AlgorithmBalance},
        status.HTTP_400_BAD_REQUEST: {"model": BlockChainError},
    },
)
async def balance(
    container: Container = Depends(di_container),
    current_algorithm: Algorithm = Depends(get_current_active_algorithm),
):
    """Request the balance, where the **output**:

    - **supply** is the total supply of the algorithm in BNB;
    - **ratio** is the ratio between 0 and 1 that reflects the amount of the base token relative to the paired token.

    Note: A ratio of 1, means 100% of the total supply is in the paired token;
          a ratio of 0, means 100% of the total supply is in the base token.
    """
    _verify_trading_contract_version(current_algorithm)

    response: AlgorithmBalanceResponse = handle_balance_request(current_algorithm, container[Web3Provider])
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
    """List ticker data for all tokens, where **output**:

    - **updated_at** is the time in _seconds since the Epoch_ (UNIX time), the price was last updated;
    - **name** is the token name;
    - **symbol** is the token ticker symbol;
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
    """List ticker data for a specific token, where **output**:

    - **updated_at** is the time in _seconds since the Epoch_ (UNIX time), the price was last updated;
    - **name** is the token name;
    - **symbol** is the token ticker symbol;
    - **price** is the token price;
    - **price_BNB** is the token price in BNB.
    """
    return handle_ticker_request(token, container[PancakeSwapService])


def _verify_trading_contract_address(algorithm: Algorithm, trading_contract_address: ChecksumAddress):
    if trading_contract_address != algorithm.trading_contract_address:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                f"Address {trading_contract_address} is not authorized for this action with this authorization header."
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )


def _verify_trading_contract_version(algorithm: Algorithm):
    if algorithm.trading_contract.version >= TradingContractVersion.V2_0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"This API version does not accept {algorithm.trading_contract_address=} with "
                f"{algorithm.trading_contract.version=}. Only V1 algorithms are valid."
            ),
        )
