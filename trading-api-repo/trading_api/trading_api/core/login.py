import functools
import logging
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional, Union

from fastapi import Depends, HTTPException, Request
from fastapi.security import SecurityScopes

from trading_api import EnvVar, get_env
from trading_api.algorithm.models.algorithm import AlgorithmInDB
from trading_api.algorithm.repositories.algorithm import AlgorithmRepository
from trading_api.core.container import Container, di_container
from trading_api.core.security import (
    AccessToken,
    InactiveAlgorithm,
    IncorrectCredentials,
    InsufficientPermissions,
    InvalidCredentials,
    InvalidScopedCredentials,
    authenticate_user,
    encode_access_token,
    optional_api_key_query,
    optional_oauth2_scheme,
    verify_access_token,
)
from trading_api.system.repositories.system import SystemAuthRepository, SystemUser

logger = logging.getLogger(__name__)


async def handle_login_request(
    request: Request, form_data, algorithm_repository: AlgorithmRepository, system_repository: SystemAuthRepository
) -> AccessToken:
    ip = request.client.host

    logger.info(f"### LOGIN REQUEST {form_data.username}, IP={ip}")

    user = authenticate_user(
        get_user_fn(algorithm_repository, system_repository, form_data.scopes), form_data.username, form_data.password
    )
    if user is None and not form_data.scopes:
        raise InvalidCredentials()
    if user is None:
        raise IncorrectCredentials()

    username = get_username(user)

    expires_delta = timedelta(minutes=int(get_env(EnvVar.ACCESS_TOKEN_EXPIRE_MINUTES, "1")))  # type: ignore
    expires = datetime.now(timezone.utc) + expires_delta
    try:
        access_token = encode_access_token({"sub": username, "scopes": form_data.scopes}, expires_delta)
    except HTTPException as e:
        logger.warning(
            f"LOGIN DENIED {form_data.username}, IP={ip} " f"due to {type(e)} - {e.status_code} - {e.detail}"
        )
        raise e
    except Exception as e:
        logger.warning(f"LOGIN FAILED {form_data.username}, IP={ip} " f"due to {type(e)}: {e}")
        raise e

    logger.info(f"LOGIN GRANTED {form_data.username}, IP={request.client.host}")
    return AccessToken(access_token=access_token, token_type="bearer", expires_at=expires.timestamp())


def get_user_fn(
    algorithm_repository: AlgorithmRepository, system_repository: SystemAuthRepository, scopes: list[str]
) -> Union[Callable[[str], Optional[SystemUser]], Callable[[str], Optional[AlgorithmInDB]]]:
    if "system" in scopes:
        return functools.partial(get_system_user, system_repository)
    else:
        return functools.partial(get_algorithm, algorithm_repository)


@functools.singledispatch
def get_username(user):
    raise NotImplementedError


@get_username.register
def get_system_username(user: SystemUser) -> str:
    return user.username


@get_username.register
def get_algorithm_username(user: AlgorithmInDB) -> str:
    return user.trading_contract_address


def get_algorithm(repository: AlgorithmRepository, username: str) -> Optional[AlgorithmInDB]:
    return repository.get_algorithm(username)


async def get_current_algorithm(
    request: Request,
    token: str = Depends(optional_oauth2_scheme),
    api_key: str = Depends(optional_api_key_query),
    container: Container = Depends(di_container),
) -> Union[SystemUser, AlgorithmInDB]:
    if not token and not api_key:
        raise InvalidCredentials()

    get_user_fn = functools.partial(get_algorithm, container[AlgorithmRepository])

    user = None
    if token:
        username = verify_access_token(token, on_error=InvalidCredentials).username
        user = get_user_fn(username)
    if api_key:
        username = request.path_params.get("address", "")
        user = authenticate_user(get_user_fn, username, password=api_key)  # type: ignore

    if user is None:
        raise InvalidCredentials()

    return user


async def get_current_active_algorithm(
    current_user: AlgorithmInDB = Depends(get_current_algorithm),
) -> AlgorithmInDB:
    if current_user.disabled:
        raise InactiveAlgorithm()

    return current_user


def get_system_user(repository: SystemAuthRepository, username: str) -> Optional[SystemUser]:
    return repository.get_system_user(username)


async def get_current_system_user(
    security_scopes: SecurityScopes,
    token: str = Depends(optional_oauth2_scheme),
    container: Container = Depends(di_container),
) -> SystemUser:
    if not token:
        raise InvalidCredentials()

    scopes = security_scopes.scope_str

    token_data = verify_access_token(token, on_error=lambda: InvalidScopedCredentials(scopes))
    if "system" not in token_data.scopes:
        raise InsufficientPermissions(scopes)

    user = get_system_user(container[SystemAuthRepository], username=token_data.username)
    if user is None:
        raise InvalidScopedCredentials(scopes)

    return user
