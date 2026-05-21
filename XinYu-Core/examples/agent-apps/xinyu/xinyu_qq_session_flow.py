from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any

from xinyu_qq_gateway_utils import hash_id, safe_str
from xinyu_qq_config import as_int


def event_session_queue_key(*, message_kind: str, group_id: Any = "", user_id: Any = "") -> str:
    if message_kind == "group":
        group = safe_str(group_id).strip()
        return f"group:{group or 'unknown'}"
    sender = safe_str(user_id).strip()
    return f"private:{sender or 'unknown'}"


def mark_latest_session_arrival(
    latest_by_session_hash: MutableMapping[str, int],
    session_queue_key: str,
    arrival_seq: int,
) -> None:
    if not session_queue_key or arrival_seq <= 0:
        return
    session_hash = hash_id(session_queue_key)
    previous = latest_by_session_hash.get(session_hash, 0)
    if arrival_seq > previous:
        latest_by_session_hash[session_hash] = arrival_seq


def prepared_arrival_waterline(payload: Mapping[str, Any] | None) -> int:
    payload = payload if isinstance(payload, Mapping) else {}
    metadata = payload.get("metadata")
    metadata = metadata if isinstance(metadata, Mapping) else {}
    arrivals: list[int] = []
    raw_arrivals = metadata.get("qq_arrival_seqs")
    if isinstance(raw_arrivals, list):
        arrivals.extend(as_int(value, 0) for value in raw_arrivals)
    arrivals.append(as_int(metadata.get("qq_arrival_seq"), 0))
    arrivals = [value for value in arrivals if value > 0]
    return max(arrivals) if arrivals else 0


def visible_reply_stale_waterline(
    *,
    route: str,
    target_message_kind: str,
    target_user_id: str,
    owner_user_ids: set[str] | frozenset[str],
    payload: Mapping[str, Any] | None,
    latest_by_session_hash: Mapping[str, int],
) -> tuple[bool, int, int]:
    if route != "chat":
        return False, 0, 0
    if target_message_kind != "private" or target_user_id not in owner_user_ids:
        return False, 0, 0
    payload = payload if isinstance(payload, Mapping) else {}
    metadata = payload.get("metadata")
    metadata = metadata if isinstance(metadata, Mapping) else {}
    session_hash = safe_str(metadata.get("qq_session_queue_hash")).strip()
    generation_waterline = prepared_arrival_waterline(payload)
    if not session_hash or generation_waterline <= 0:
        return False, generation_waterline, 0
    latest_arrival = latest_by_session_hash.get(session_hash, 0)
    return latest_arrival > generation_waterline, generation_waterline, latest_arrival
