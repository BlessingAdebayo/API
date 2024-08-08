from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from trading_api.algorithm.repositories.algorithm import AlgorithmRepository
from trading_api.core.container import Container, di_container
from trading_api.core.login import handle_login_request
from trading_api.core.security import AccessToken
from trading_api.system.repositories.system import SystemAuthRepository

router = APIRouter()


@router.post(
    path="/login",
    response_model=AccessToken,
    tags=["login"],
    summary="Log in",
)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    container: Container = Depends(di_container),
):
    """Log in, where:

    - **username** is the username;
    - **password** is the secret.
    """
    return await handle_login_request(
        request=request,
        form_data=form_data,
        algorithm_repository=container[AlgorithmRepository],
        system_repository=container[SystemAuthRepository],
    )
