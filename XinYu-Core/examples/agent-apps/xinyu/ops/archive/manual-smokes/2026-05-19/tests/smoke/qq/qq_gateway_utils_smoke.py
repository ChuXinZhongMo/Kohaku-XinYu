from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

import logging

from xinyu_qq_gateway import _hash_id, _maybe_int, _quiet_websockets_handshake_noise, _safe_str
from xinyu_qq_gateway_utils import (
    hash_id,
    maybe_int,
    now_iso,
    quiet_websockets_handshake_noise,
    safe_str,
)


def main() -> int:
    failures: list[str] = []

    if safe_str(None, "fallback") != "fallback" or safe_str(123) != "123":
        failures.append("QQ gateway safe string helper changed")
    if hash_id(" XinYu ", length=8) != _hash_id(" XinYu ", length=8):
        failures.append("QQ gateway hash helper changed")
    if hash_id("", length=8) != "":
        failures.append("QQ gateway empty hash fallback changed")
    if maybe_int("123") != 123 or maybe_int("abc123") != "abc123":
        failures.append("QQ gateway maybe-int helper changed")
    if "T" not in now_iso():
        failures.append("QQ gateway now-iso helper changed")

    old_levels = {
        name: logging.getLogger(name).level
        for name in ("websockets.server", "websockets.protocol")
    }
    try:
        quiet_websockets_handshake_noise()
        for name in old_levels:
            if logging.getLogger(name).level != logging.CRITICAL:
                failures.append(f"QQ gateway websocket logger was not quieted: {name}")
    finally:
        for name, level in old_levels.items():
            logging.getLogger(name).setLevel(level)

    if (
        _safe_str is not safe_str
        or _hash_id is not hash_id
        or _maybe_int is not maybe_int
        or _quiet_websockets_handshake_noise is not quiet_websockets_handshake_noise
    ):
        failures.append("QQ gateway utility aliases no longer delegate")

    if failures:
        print("XinYu QQ gateway utils smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu QQ gateway utils smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
