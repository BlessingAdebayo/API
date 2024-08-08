import logging
from datetime import datetime, timedelta
from typing import Callable, List, Optional, Union

from fastapi import HTTPException, status
from fastapi.security import APIKeyQuery, OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ValidationError

from trading_api import EnvVar, get_env
from trading_api.algorithm.models.algorithm import AlgorithmInDB
from trading_api.system.repositories.system import SystemUser

logger = logging.getLogger(__name__)


class AccessToken(BaseModel):
    access_token: str
    token_type: str
    expires_at: datetime


class AccessTokenData(BaseModel):
    username: str
    scopes: List[str] = []


ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

optional_api_key_query = APIKeyQuery(
    name="api_key",
    auto_error=False,
)
optional_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    scopes={"system": "Access system endpoints."},
    auto_error=False,
)


def IncorrectCredentials(
    detail: str = "Incorrect credentials",
) -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, detail=detail)


def InvalidCredentials(
    detail: str = "Invalid credentials",
) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail=detail, headers=create_bearer_authorization_header())


def InvalidScopedCredentials(
    scopes: str,
    detail: str = "Invalid credentials for scope",
) -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED, detail=detail, headers=create_bearer_authorization_header_with_scopes(scopes)
    )


def InsufficientPermissions(
    scopes: str,
    detail: str = "Not enough permissions",
) -> HTTPException:
    return HTTPException(
        status.HTTP_403_FORBIDDEN, detail=detail, headers=create_bearer_authorization_header_with_scopes(scopes)
    )


def InactiveAlgorithm(
    detail: str = "Inactive algorithm",
) -> HTTPException:
    return HTTPException(status.HTTP_403_FORBIDDEN, detail=detail)


def create_bearer_authorization_header() -> dict:
    return {"WWW-Authenticate": "Bearer"}


def create_bearer_authorization_header_with_scopes(scopes: str) -> dict:
    return {"WWW-Authenticate": f'Bearer scope="{scopes}"'}


def encode_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(
    get_user_fn: Union[
        Callable[[str], Optional[SystemUser]],
        Callable[[str], Optional[AlgorithmInDB]],
    ],
    username: str,
    password: str,
) -> Union[Optional[SystemUser], Optional[AlgorithmInDB]]:
    user = get_user_fn(username)
    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


def encode_access_token(data: dict, expires_delta: timedelta) -> str:
    expire = datetime.utcnow() + expires_delta

    to_encode = data.copy()
    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        get_env(EnvVar.SECRET_KEY, "46bf2efca41f935ff1ce71448080d8c4193421ffe75fe991e1ca210981b78dc7"),
        algorithm=ALGORITHM,
    )


def verify_access_token(token: str, on_error: Callable[[], Exception]) -> AccessTokenData:
    try:
        payload = jwt.decode(
            token,
            get_env(EnvVar.SECRET_KEY, "46bf2efca41f935ff1ce71448080d8c4193421ffe75fe991e1ca210981b78dc7"),
            algorithms=[ALGORITHM],
        )
    except (JWTError, ValidationError) as e:
        raise on_error() from e

    username: str = payload.get("sub")
    if username is None:
        raise on_error()

    token_scopes = payload.get("scopes", [])
    return AccessTokenData(username=username, scopes=token_scopes)
