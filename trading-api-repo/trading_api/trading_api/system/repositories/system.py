from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel


class SystemUser(BaseModel):
    username: str
    hashed_password: str


class SystemAuthRepository(ABC):
    @abstractmethod
    def get_system_user(self, username: str) -> Optional[SystemUser]:
        pass


class InMemorySystemAuthRepository(SystemAuthRepository):
    def __init__(self, system_user: SystemUser):
        self.username = system_user.username
        self.hashed_password = system_user.hashed_password

    def get_system_user(self, username: str) -> Optional[SystemUser]:
        if self.username != username:
            return None

        return SystemUser(username=self.username, hashed_password=self.hashed_password)
