from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

enabled = not get_settings().TESTING

limiter = Limiter(
    key_func=get_remote_address,
    enabled=enabled,
)
