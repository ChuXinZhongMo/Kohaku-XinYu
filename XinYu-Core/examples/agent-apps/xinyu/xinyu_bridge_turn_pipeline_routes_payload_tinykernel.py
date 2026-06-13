from __future__ import annotations

from typing import Any


def build_tinykernel_payload(
    *,
    text: str,
    turn_id: str,
    observed_at: str,
) -> dict[str, Any]:
    return {
        "text": text,
        "turn_id": turn_id,
        "observed_at": observed_at,
    }


__all__ = ["build_tinykernel_payload"]
