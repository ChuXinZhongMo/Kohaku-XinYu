from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from xinyu_qq_models import ReplyTarget


GATEWAY_NAME = "xinyu_native_qq_gateway"
GATEWAY_VERSION_FALLBACK = "0.1.24"


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_int(value: Any, default: int) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def outbox_target(gateway: Any, claim: dict[str, Any], reply_target_type: type[Any]) -> Any | None:
    target = claim.get("target")
    if not isinstance(target, dict):
        return None
    message_kind = _safe_str(target.get("message_kind"), "private").strip().lower()
    user_id = _safe_str(target.get("user_id")).strip()
    group_id = _safe_str(target.get("group_id")).strip()
    if message_kind != "private" or not user_id:
        return None
    return reply_target_type(message_kind="private", user_id=user_id, group_id=group_id)


def gateway_outbox_target(gateway: Any, claim: dict[str, Any]) -> ReplyTarget | None:
    return outbox_target(gateway, claim, ReplyTarget)


def onebot_action_result(gateway: Any, response: dict[str, Any] | None) -> tuple[bool, str, str]:
    if not response:
        return False, "", "onebot_action_timeout"
    status = _safe_str(response.get("status")).lower()
    retcode = response.get("retcode")
    ok = status in {"ok", "async"} or retcode == 0 or str(retcode) == "0"
    data = response.get("data")
    adapter_message_id = ""
    if isinstance(data, dict):
        adapter_message_id = _safe_str(data.get("message_id")).strip()
    if ok:
        return True, adapter_message_id, ""
    return False, adapter_message_id, _safe_str(response.get("message") or response.get("wording") or response)[:300]


async def ack_qq_outbox(
    gateway: Any,
    claim: dict[str, Any],
    *,
    status: str,
    adapter_message_id: str = "",
    error: str = "",
) -> None:
    try:
        await gateway.client.qq_outbox_ack(
            {
                "message_id": _safe_str(claim.get("message_id")),
                "claim_id": _safe_str(claim.get("claim_id")),
                "ack_status": status,
                "adapter_message_id": adapter_message_id,
                "adapter_error": error,
            }
        )
    except Exception as exc:
        print(f"[xinyu_qq_gateway] QQ outbox ack error: {type(exc).__name__}: {exc}", flush=True)


async def ack_sent_outbox_delivery(
    gateway: Any,
    claim: dict[str, Any],
    *,
    target: Any,
    visible_text: str,
    adapter_message_id: str,
    delivery_kind: str,
    adapter_error: str = "",
) -> None:
    payload = outbox_message_ack_payload(
        gateway,
        claim,
        target=target,
        visible_text=visible_text,
        adapter_message_id=adapter_message_id,
        delivery_kind=delivery_kind,
        adapter_error=adapter_error,
    )
    if payload:
        await record_sent_message_ack_payload(gateway, payload)


def outbox_message_ack_payload(
    gateway: Any,
    claim: dict[str, Any],
    *,
    target: Any,
    visible_text: str,
    adapter_message_id: str,
    delivery_kind: str,
    adapter_error: str = "",
) -> dict[str, Any]:
    adapter_message_id = _safe_str(adapter_message_id).strip()
    if not adapter_message_id:
        return {}
    metadata = claim.get("metadata")
    metadata = dict(metadata) if isinstance(metadata, dict) else {}
    outbox_message_id = _safe_str(claim.get("message_id")).strip()
    route = sent_outbox_delivery_route(outbox_message_id, delivery_kind)
    archive_message_ids = metadata.get("archive_message_ids")
    if not isinstance(archive_message_ids, list):
        archive_message_ids = metadata.get("source_message_ids")
    if not isinstance(archive_message_ids, list):
        archive_message_ids = []
    metadata.update(
        {
            "gateway_version": getattr(gateway, "gateway_version", GATEWAY_VERSION_FALLBACK),
            "source_route": route,
            "outbox_source": _safe_str(claim.get("source")).strip(),
            "outbox_message_type": _safe_str(claim.get("message_type")).strip(),
            "delivery_kind": _safe_str(delivery_kind).strip() or "text",
        }
    )
    return {
        "adapter": GATEWAY_NAME,
        "gateway": GATEWAY_NAME,
        "adapter_message_id": adapter_message_id,
        "route": route,
        "source_route": route,
        "session_id": _safe_str(metadata.get("session_id")).strip() or gateway._session_id(target),
        "turn_id": _safe_str(
            metadata.get("turn_id") or metadata.get("source_turn_id") or metadata.get("runtime_turn_id")
        ).strip(),
        "archive_message_ids": archive_message_ids,
        "archive_assistant_message_id": _safe_str(metadata.get("archive_assistant_message_id")).strip(),
        "source_message_id": _safe_str(metadata.get("source_message_id")).strip(),
        "outbox_message_id": outbox_message_id,
        "message_type": target.message_kind,
        "target": {
            "message_kind": target.message_kind,
            "user_id": target.user_id,
            "group_id": target.group_id or "",
        },
        "visible_text": visible_text,
        "visible_text_hash": _safe_str(metadata.get("visible_text_hash") or metadata.get("reply_hash")).strip(),
        "sent_at": _now_iso(),
        "adapter_error": adapter_error,
        "metadata": metadata,
    }


def sent_outbox_delivery_route(outbox_message_id: str, delivery_kind: str) -> str:
    base = "proactive" if _safe_str(outbox_message_id).startswith("proactive:") else "qq_outbox"
    kind = _safe_str(delivery_kind).strip().lower()
    if kind in {"image", "caption"}:
        return f"{base}_{kind}"
    return base


async def poll_pending_message_acks(gateway: Any, connection_id: str) -> None:
    await asyncio.sleep(2)
    while True:
        try:
            await flush_pending_message_acks(gateway)
            await asyncio.sleep(max(5, gateway.config.qq_outbox_poll_seconds))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"[xinyu_qq_gateway] sent-message ack spool error {connection_id}: {type(exc).__name__}: {exc}", flush=True)
            await asyncio.sleep(max(5, gateway.config.qq_outbox_poll_seconds))


async def ack_sent_visible_reply(
    gateway: Any,
    prepared: Any,
    *,
    reply: str,
    core_response: dict[str, Any],
    action_response: dict[str, Any] | None,
) -> None:
    message_ack_url = _safe_str(getattr(gateway.client, "message_ack_url", gateway.config.message_ack_url)).strip()
    if not gateway.config.bridge_token or not message_ack_url:
        return
    payload = sent_message_ack_payload(
        gateway,
        prepared,
        reply=reply,
        core_response=core_response,
        action_response=action_response,
    )
    if not payload:
        return
    await record_sent_message_ack_payload(gateway, payload)


async def record_sent_message_ack_payload(gateway: Any, payload: dict[str, Any]) -> bool:
    message_ack_url = _safe_str(getattr(gateway.client, "message_ack_url", gateway.config.message_ack_url)).strip()
    if not gateway.config.bridge_token or not message_ack_url:
        return False
    spooled = spool_pending_message_ack(gateway, payload)
    return await send_message_ack_payload(gateway, payload, mark_acked=True, spool_on_failure=not spooled)


def spool_pending_message_ack(gateway: Any, payload: dict[str, Any]) -> bool:
    try:
        result = gateway.ack_spool.append_pending(payload)
    except Exception as exc:
        print(f"[xinyu_qq_gateway] sent-message ack pending spool error: {type(exc).__name__}: {exc}", flush=True)
        return False
    if result.get("queued"):
        return True
    notes = result.get("notes") if isinstance(result.get("notes"), list) else []
    print(f"[xinyu_qq_gateway] sent-message ack pending spool rejected: {notes}", flush=True)
    return False


def spool_acked_message_ack(gateway: Any, payload: dict[str, Any]) -> bool:
    try:
        result = gateway.ack_spool.append_acked(payload)
    except Exception as exc:
        print(f"[xinyu_qq_gateway] sent-message acked spool error: {type(exc).__name__}: {exc}", flush=True)
        return False
    if result.get("acked"):
        return True
    notes = result.get("notes") if isinstance(result.get("notes"), list) else []
    print(f"[xinyu_qq_gateway] sent-message acked spool rejected: {notes}", flush=True)
    return False


def sent_message_ack_payload(
    gateway: Any,
    prepared: Any,
    *,
    reply: str,
    core_response: dict[str, Any],
    action_response: dict[str, Any] | None,
) -> dict[str, Any]:
    ok, adapter_message_id, adapter_error = onebot_action_result(gateway, action_response)
    if not ok or not adapter_message_id:
        return {}
    source_payload = prepared.payload if isinstance(prepared.payload, dict) else {}
    archive_message_ids = core_response.get("archive_message_ids")
    if not isinstance(archive_message_ids, list):
        archive_message_ids = []
    delivery_kind = ""
    voice_fallback_reason = ""
    if isinstance(action_response, dict):
        delivery_kind = _safe_str(action_response.get("xinyu_delivery_kind")).strip()
        voice_fallback_reason = _safe_str(action_response.get("xinyu_voice_fallback_reason")).strip()
        data = action_response.get("data")
        if not delivery_kind and isinstance(data, dict):
            delivery_kind = _safe_str(data.get("delivery_kind")).strip()
    delivery_kind = delivery_kind or "text"
    metadata = {
        "gateway_version": getattr(gateway, "gateway_version", GATEWAY_VERSION_FALLBACK),
        "source_route": prepared.route or "chat",
        "delivery_kind": delivery_kind,
    }
    if voice_fallback_reason:
        metadata["voice_fallback_reason"] = voice_fallback_reason
    return {
        "adapter": GATEWAY_NAME,
        "gateway": GATEWAY_NAME,
        "adapter_message_id": adapter_message_id,
        "route": _safe_str(core_response.get("route") or prepared.route or "chat").strip() or "chat",
        "source_route": prepared.route or "chat",
        "session_id": _safe_str(core_response.get("session_id") or source_payload.get("session_id")).strip(),
        "turn_id": _safe_str(core_response.get("turn_id")).strip(),
        "archive_message_ids": archive_message_ids,
        "archive_assistant_message_id": _safe_str(core_response.get("archive_assistant_message_id")).strip(),
        "source_message_id": _safe_str(source_payload.get("message_id")).strip(),
        "message_type": prepared.target.message_kind,
        "target": {
            "message_kind": prepared.target.message_kind,
            "user_id": prepared.target.user_id,
            "group_id": prepared.target.group_id or "",
        },
        "visible_text": reply,
        "visible_text_hash": _safe_str(core_response.get("reply_hash")).strip(),
        "sent_at": _now_iso(),
        "adapter_error": adapter_error,
        "delivery_kind": delivery_kind,
        "metadata": metadata,
    }


async def send_message_ack_payload(
    gateway: Any,
    payload: dict[str, Any],
    *,
    mark_acked: bool,
    spool_on_failure: bool,
) -> bool:
    try:
        result = await gateway.client.message_ack(payload)
    except Exception as exc:
        if spool_on_failure:
            spool_pending_message_ack(gateway, payload)
        print(f"[xinyu_qq_gateway] sent-message ack error: {type(exc).__name__}: {exc}", flush=True)
        return False

    accepted = bool(result.get("accepted"))
    indexed = result.get("indexed", result.get("ack_recorded", True)) is not False
    if accepted and indexed:
        if mark_acked:
            spool_acked_message_ack(gateway, payload)
        return True

    if spool_on_failure:
        spool_pending_message_ack(gateway, payload)
    notes = result.get("notes") if isinstance(result.get("notes"), list) else []
    print(f"[xinyu_qq_gateway] sent-message ack rejected: {notes}", flush=True)
    return False


async def flush_pending_message_acks(gateway: Any, *, limit: int = 20) -> dict[str, Any]:
    pending = gateway.ack_spool.pending_payloads()
    flushed = 0
    for payload in pending[: max(0, limit)]:
        retry_payload = dict(payload)
        retry_payload["ack_attempts"] = _as_int(retry_payload.get("ack_attempts"), 0) + 1
        ok = await send_message_ack_payload(gateway, retry_payload, mark_acked=True, spool_on_failure=True)
        if ok:
            flushed += 1
    return {"pending_count": len(pending), "flushed_count": flushed}
