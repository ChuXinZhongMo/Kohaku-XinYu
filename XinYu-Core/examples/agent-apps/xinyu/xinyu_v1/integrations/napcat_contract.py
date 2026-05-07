"""NapCat/OneBot assumptions used by XinYu."""

from __future__ import annotations


ONEBOT_PRIVATE_MESSAGE = "private"
ONEBOT_GROUP_MESSAGE = "group"
NAPCAT_LOCAL_HOSTS = ("127.0.0.1", "localhost")


def is_local_napcat_url(url: str) -> bool:
    lowered = url.lower()
    return any(host in lowered for host in NAPCAT_LOCAL_HOSTS)

