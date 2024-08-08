import math
from datetime import timedelta

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from mm.api.dependencies import Container, di_container, verify_token
from mm.api.models import (
    CreateReleaseForRequest,
    CreateReleaseForResponse,
    CreateStakeInLiquidityMakerRequest,
    CreateStakeInLiquidityMakerResponse,
    CreateSwapRequest,
    CreateSwapResponse,
    CreateTradeRequest,
    CreateTradeResponse,
    CreateWalletsRequest,
    CreateWalletsResponse,
    LinkContractRequest,
    LinkContractResponse,
    RetrieveSwapsResponse,
    RetrieveTradesResponse,
    RetrieveTransactionStatusResponse,
    Token,
)
from mm.api.security import ACCESS_TOKEN_EXPIRE_MINUTES, authenticate_user, create_access_token
from mm.domain import (
    create_wallet_key_pairs,
    get_transaction_status,
    link_contract_to_wallet,
    release_for,
    stake_in_liquidity_maker,
    swap,
    trade,
)
from mm.domain.exceptions import BlockchainError, ContractNotFound, InvalidCredentials, WalletNotFound
from mm.domain.models import ContractAddress, ContractSpec, SwapFilter, TradeFilter, TransactionHash
from mm.domain.repositories import AuthenticationRepository, SwapRepository, TradeRepository, WalletKeyRepository
from mm.domain.services import KeyManagementService, TransactionService

avatea = FastAPI(
    title="Avatea API",
    version="0.0.1",
)


@avatea.exception_handler(InvalidCredentials)
async def invalid_credentials_handler(request: Request, exc: InvalidCredentials):
    return JSONResponse(
        status_code=401,
        content={"message": str(exc)},
        headers={"WWW-Authenticate": "Bearer"},
    )


@avatea.exception_handler(WalletNotFound)
async def wallet_not_found_handler(request: Request, exc: WalletNotFound):
    return JSONResponse(
        status_code=404,
        content={"message": str(exc)},
    )


@avatea.exception_handler(ContractNotFound)
async def contract_not_found_handler(request: Request, exc: ContractNotFound):
    return JSONResponse(
        status_code=404,
        content={"message": str(exc)},
    )


@avatea.exception_handler(BlockchainError)
async def blockchain_error_handler(request: Request, exc: BlockchainError):
    return JSONResponse(
        status_code=400,
        content={"message": str(exc)},
    )


@avatea.post(
    path="/token",
    response_model=Token,
    summary="Create a new token",
)
async def create_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    container: Container = Depends(di_container),
):
    """Create a new access token to authenticate with the service, where:

    - **username** is the username;
    - **password** is the secret.
    """
    user = authenticate_user(container[AuthenticationRepository], form_data.username, form_data.password)
    if not user:
        raise InvalidCredentials
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return Token(access_token=access_token, token_type="bearer")


@avatea.post(
    path="/wallets",
    response_model=CreateWalletsResponse,
    dependencies=[Depends(verify_token)],
    summary="Create new controller wallet(s)",
)
async def add_wallets(
    request: CreateWalletsRequest,
    container: Container = Depends(di_container),
):
    """Create new controller wallet(s), where:

    - **count** is the number of wallets to create.
    """
    pairs = list(
        create_wallet_key_pairs(request.count, container[WalletKeyRepository], container[KeyManagementService])
    )

    return CreateWalletsResponse.from_pairs(pairs=pairs)


@avatea.post(
    path="/contracts",
    response_model=LinkContractResponse,
    dependencies=[Depends(verify_token)],
    summary="Link a new contract",
)
async def link_contract(
    request: LinkContractRequest,
    container: Container = Depends(di_container),
):
    """Link a new market making contract to a controller wallet, where:

    - **contract** is the market maker contract address;
    - **chain** is the ID of the blockchain used.
    """
    link_contract_to_wallet(
        ContractSpec(request.contract, request.chain), request.wallet, keys=container[WalletKeyRepository]
    )

    return LinkContractResponse()


@avatea.get(
    path="/trades",
    response_model=RetrieveTradesResponse,
    dependencies=[Depends(verify_token)],
    summary="Retrieve all trades",
)
async def retrieve_trades(
    skip: int = 0,
    limit: int = 10,
    container: Container = Depends(di_container),
):
    trades = list(container[TradeRepository].get_all_paginated(TradeFilter(skip=skip, limit=limit)))
    total = len(container[TradeRepository])

    return RetrieveTradesResponse(
        trades=trades,
        page=math.floor(skip / limit),
        page_size=limit,
        total_pages=math.ceil(total / limit),
        total=total,
    )


@avatea.post(
    path="/trades",
    response_model=CreateTradeResponse,
    dependencies=[Depends(verify_token)],
    summary="Create a new trade",
)
async def create_trade(
    request: CreateTradeRequest,
    container: Container = Depends(di_container),
):
    """Create a new transaction to buy or sell a batch of tokens, where:

    - **contract** is the market maker contract address;
    - **type** is the type of trade to make. Can be either _BUY_ or _SELL_;
    - **amounts** is a list of tokens to be sold for each beneficiary;
    - **addresses** is a list of addresses of beneficiaries for which the tokens are sold;
    - **slippage**  is the amount of allowed slippage for the transaction;
    - **exchange**  is the name of the exchange on which the trade will be performed.
    """
    tx_hash = trade(
        request.contract,
        request.to_trade(),
        container[TransactionService],
        container[KeyManagementService],
        container[WalletKeyRepository],
        container[TradeRepository],
    )

    return CreateTradeResponse(transaction_hash=tx_hash)


@avatea.get(
    path="/trades/{contract_address}",
    response_model=RetrieveTradesResponse,
    dependencies=[Depends(verify_token)],
    summary="Retrieve trades for a contract",
)
async def retrieve_trades_for_contract(
    contract_address: ContractAddress,
    skip: int = 0,
    limit: int = 10,
    container: Container = Depends(di_container),
):
    trades = list(
        container[TradeRepository].get_all_paginated(TradeFilter(skip=skip, limit=limit, contract=contract_address))
    )
    total = len(container[TradeRepository])

    return RetrieveTradesResponse(
        trades=trades,
        page=math.floor(skip / limit),
        page_size=limit,
        total_pages=math.ceil(total / limit),
        total=total,
    )


# @avatea.get(
#     path="/swaps",
#     response_model=RetrieveSwapsResponse,
#     dependencies=[Depends(verify_token)],
#     summary="Retrieve all swaps",
# )
async def retrieve_swaps(
    skip: int = 0,
    limit: int = 10,
    container: Container = Depends(di_container),
):
    swaps = list(container[SwapRepository].get_all_paginated(SwapFilter(skip=skip, limit=limit)))
    total = len(container[SwapRepository])

    return RetrieveSwapsResponse(
        swaps=swaps,
        page=math.floor(skip / limit),
        page_size=limit,
        total_pages=math.ceil(total / limit),
        total=total,
    )


# @avatea.post(
#     path="/swaps",
#     response_model=CreateSwapResponse,
#     dependencies=[Depends(verify_token)],
#     summary="Create a new swap",
# )
async def create_swap(
    request: CreateSwapRequest,
    container: Container = Depends(di_container),
):
    """Create a new transaction to swap a batch of tokens, where:

    - **contract** is the market maker contract address;
    - **amounts** is a list of amounts of tokens to be swapped for each beneficiary;
    - **addresses** is a list of addresses of beneficiaries for which the tokens are swapped;
    - **seller** is the address from which the tokens are swapped;
    - **exchange** is the name of the exchange from which the price will be fetched.
    """
    tx_hash = swap(
        request.contract,
        request.to_swap(),
        container[TransactionService],
        container[KeyManagementService],
        container[WalletKeyRepository],
        container[SwapRepository],
    )

    return CreateSwapResponse(transaction_hash=tx_hash)


# @avatea.get(
#     path="/swaps/{contract_address}",
#     response_model=RetrieveSwapsResponse,
#     dependencies=[Depends(verify_token)],
#     summary="Retrieve swaps for a contract",
# )
async def retrieve_swaps_for_contract(
    contract_address: ContractAddress,
    skip: int = 0,
    limit: int = 10,
    container: Container = Depends(di_container),
):
    swaps = list(
        container[SwapRepository].get_all_paginated(SwapFilter(skip=skip, limit=limit, contract=contract_address))
    )
    total = len(container[SwapRepository])

    return RetrieveSwapsResponse(
        swaps=swaps,
        page=math.floor(skip / limit),
        page_size=limit,
        total_pages=math.ceil(total / limit),
        total=total,
    )


@avatea.post(
    path="/stakes",
    response_model=CreateStakeInLiquidityMakerResponse,
    dependencies=[Depends(verify_token)],
    summary="Create a new stake",
)
async def create_stake_in_liquidity_maker(
    request: CreateStakeInLiquidityMakerRequest,
    container: Container = Depends(di_container),
):
    """Create a new stake in liquidity for base and paired tokens, where:

    - **contract** is the market maker contract address;
    - **amounts_base** is a list of amounts of base tokens to be provided for liquidity for each beneficiary;
    - **amounts_paired** is a list of amounts of paired tokens to be provided for liquidity for each beneficiary;
    - **addresses_base** is a list of addresses of beneficiaries for which the base tokens are provided;
    - **addresses_paired** is a list of addresses of beneficiaries for which the paired tokens are provided;
    - **slippage**  is the amount of allowed slippage for the transaction;
    - **exchange** is the name of the exchange from which the price will be fetched.
    """
    tx_hash = stake_in_liquidity_maker(
        request.contract,
        request.to_stake(),
        container[TransactionService],
        container[KeyManagementService],
        container[WalletKeyRepository],
    )

    return CreateStakeInLiquidityMakerResponse(transaction_hash=tx_hash)


@avatea.post(
    path="/releases",
    response_model=CreateReleaseForResponse,
    dependencies=[Depends(verify_token)],
    summary="Create a new token release",
)
async def create_release_for(
    request: CreateReleaseForRequest,
    container: Container = Depends(di_container),
):
    """Release tokens from the vesting schedule for an array of beneficiaries, where:

    - **contract** is the market maker contract address;
    - **addresses** is a list of addresses of beneficiaries for which the tokens are released.
    """
    tx_hash = release_for(
        request.contract,
        request.to_release_for(),
        container[TransactionService],
        container[KeyManagementService],
        container[WalletKeyRepository],
    )

    return CreateReleaseForResponse(transaction_hash=tx_hash)


@avatea.get(
    path="/status/{transaction_hash}",
    response_model=RetrieveTransactionStatusResponse,
    dependencies=[Depends(verify_token)],
    summary="Retrieve a transaction its status",
)
async def retrieve_transaction_status(
    transaction_hash: TransactionHash,
    container: Container = Depends(di_container),
):
    """Retrieve the transaction status of a trade, where:

    - **transaction_hash** is the hash returned after making a transaction.
    """
    tx_status = get_transaction_status(
        transaction_hash,
        container[TransactionService],
        container[TradeRepository],
        container[SwapRepository],
        container[WalletKeyRepository],
    )

    return RetrieveTransactionStatusResponse(message=tx_status.value)
