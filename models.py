from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    id: int
    name: str
    email: str
    password_hash: str
    role: str
    organization: str = ""
