import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from mm.domain.models import SystemUser
from mm.domain.repositories import AuthenticationRepository

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


def encode_password(password: str):
    return pwd_context.hash(password)


def authenticate_user(repository: AuthenticationRepository, username: str, password: str) -> Optional[SystemUser]:
    user = repository.get_system_user(username)
    if user is None or not verify_password(password, user.hashed_password):
        return None

    return user


def create_access_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + expires_delta})

    return jwt.encode(to_encode, os.environ["SECRET_KEY"], algorithm=ALGORITHM)


async def verify_token(token: str = Depends(oauth2_scheme)) -> None:
    try:
        jwt.decode(token, os.environ["SECRET_KEY"], algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
