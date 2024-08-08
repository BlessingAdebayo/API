from datetime import datetime

from pydantic import BaseModel, SecretStr


class Token(BaseModel):
    access_token: str
    token_type: str


class CreateTokenRequest(BaseModel):
    username: str
    password: SecretStr


class CreateTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_at: datetime
