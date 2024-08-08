from dataclasses import dataclass


@dataclass(frozen=True)
class SystemUser:
    username: str
    hashed_password: str
