from typing import Optional

from mm.domain.models import SystemUser
from mm.domain.repositories import AuthenticationRepository


class InMemorySystemAuthRepository(AuthenticationRepository):
    def __init__(self, username: str, hashed_password: str):
        self.username = username
        self.hashed_password = hashed_password

    def get_system_user(self, username: str) -> Optional[SystemUser]:
        if self.username != username:
            return None

        return SystemUser(username=self.username, hashed_password=self.hashed_password)
