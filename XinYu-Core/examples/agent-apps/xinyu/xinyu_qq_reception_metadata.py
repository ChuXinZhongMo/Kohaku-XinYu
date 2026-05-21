from __future__ import annotations

from typing import Any

from xinyu_qq_gateway_utils import hash_id, safe_str


def ensure_payload_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    payload["metadata"] = metadata
    return metadata


def annotate_prepared_reception_metadata(
    payload: dict[str, Any],
    *,
    event_message_id: Any,
    arrival_seq: int,
    prepared_seq: int,
    session_queue_key: str,
) -> dict[str, Any]:
    metadata = ensure_payload_metadata(payload)
    metadata.update(
        {
            "qq_arrival_seq": arrival_seq,
            "qq_prepared_seq": prepared_seq,
            "qq_session_queue_hash": hash_id(session_queue_key),
            "qq_gateway_received_message_id": safe_str(event_message_id).strip(),
        }
    )
    return metadata


def annotate_dispatch_reception_metadata(payload: dict[str, Any], *, dispatch_seq: int) -> dict[str, Any]:
    metadata = ensure_payload_metadata(payload)
    metadata["qq_dispatch_seq"] = dispatch_seq
    return metadata
