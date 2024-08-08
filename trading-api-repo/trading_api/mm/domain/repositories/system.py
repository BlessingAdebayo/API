import abc
from typing import Optional

from mm.domain.models import SystemUser


class AuthenticationRepository(abc.ABC):
    @abc.abstractmethod
    def get_system_user(self, username: str) -> Optional[SystemUser]:
        ...
