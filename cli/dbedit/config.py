from typing import Optional
from .. import cache

_USERNAME_KEY = "username"


def set_username(value: str) -> None:
    cache.store(_USERNAME_KEY, value)


def get_username() -> Optional[str]:
    return cache.get(_USERNAME_KEY)
