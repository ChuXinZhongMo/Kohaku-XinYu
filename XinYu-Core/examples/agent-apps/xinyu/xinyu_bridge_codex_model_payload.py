from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from xinyu_bridge_trusted_search import trusted_public_search_task_allowed as _trusted_public_search_task_allowed
from xinyu_bridge_values import as_bool, as_int, safe_str


CODEX_DEFAULT_TIMEOUT_SECONDS = 3600
CODEX_VISIBLE_WINDOW_TITLE = "Xinyu codex"


def can_model_delegate_codex(
    payload: dict[str, Any],
    *,
    task_text: str = "",
    trusted_public_search_allowed: Callable[[str], bool] = _trusted_public_search_task_allowed,
) -> bool:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    message_type = safe_str(payload.get("message_type")).lower()
    if message_type and not (message_type.startswith("private") or message_type.startswith("desktop_private")):
        return False
    group_id = safe_str(payload.get("group_id")).strip()
    if group_id not in {"", "0", "none", "None"}:
        return False
    if as_bool(metadata.get("is_owner_user"), default=False):
        return True
    if not as_bool(metadata.get("is_trusted_user"), default=False):
        return False
    return trusted_public_search_allowed(task_text)


def build_model_codex_payload(
    payload: dict[str, Any],
    *,
    session_key: str,
    task_text: str,
    timeout_seconds: int = CODEX_DEFAULT_TIMEOUT_SECONDS,
    window_title: str = CODEX_VISIBLE_WINDOW_TITLE,
    trusted_public_search_allowed: Callable[[str], bool] = _trusted_public_search_task_allowed,
) -> dict[str, Any]:
    source_metadata = payload.get("metadata")
    if not isinstance(source_metadata, dict):
        source_metadata = {}
    is_owner = as_bool(source_metadata.get("is_owner_user"), default=False)
    is_trusted = as_bool(source_metadata.get("is_trusted_user"), default=False)
    trusted_public_search = is_trusted and not is_owner and trusted_public_search_allowed(task_text)
    owner_local_write_approved = is_owner and as_bool(
        source_metadata.get("owner_local_write_approved"),
        default=False,
    )
    metadata = {
        "gateway": safe_str(payload.get("adapter"), "xinyu_core_bridge"),
        "source": "qq_gateway_codex_execute_message",
        "is_owner_user": is_owner,
        "is_trusted_user": is_trusted,
        "trusted_public_search_task": trusted_public_search,
        "owner_local_write_approved": owner_local_write_approved,
        "codex_auxiliary_brain": True,
        "direct_cli_execution": False,
        "delegated_by_model": True,
    }
    return {
        "platform": safe_str(payload.get("platform"), "qq"),
        "adapter": safe_str(payload.get("adapter"), "xinyu_core_bridge"),
        "message_type": "private_codex_model_delegate",
        "session_id": session_key,
        "user_id": safe_str(payload.get("user_id")),
        "sender_name": safe_str(payload.get("sender_name")),
        "group_id": None,
        "bot_id": safe_str(payload.get("bot_id")),
        "message_id": safe_str(payload.get("message_id")),
        "text": (
            "Use Codex auxiliary brain for this trusted public-source search task:\n"
            if trusted_public_search
            else "Use Codex auxiliary brain for this owner-approved task:\n"
        )
        + task_text,
        "raw_owner_task": task_text,
        "source": "qq_gateway_codex_execute_message",
        "background": True,
        "auto_study": True,
        "timeout_seconds": timeout_seconds,
        "visible_window": True,
        "window_title": window_title,
        "network_access": True,
        "include_dialogue_context": True,
        "timestamp": as_int(payload.get("timestamp"), int(time.time())),
        "metadata": metadata,
    }


def build_self_code_iteration_codex_payload(
    runtime: Any,
    payload: dict[str, Any],
    *,
    session_key: str,
    task_text: str,
) -> dict[str, Any]:
    codex_payload = runtime._build_model_codex_payload(
        payload,
        session_key=session_key,
        task_text=task_text,
    )
    metadata = codex_payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
        codex_payload["metadata"] = metadata
    approval_id = runtime._extract_self_code_approval_id(task_text)
    codex_payload["auto_study"] = False
    metadata["delegated_by_model"] = False
    metadata["delegated_by_owner_self_code_iteration"] = True
    metadata["self_code_iteration"] = True
    metadata["approval_id"] = approval_id
    metadata["owner_intervention"] = (
        "owner private direct self-code request"
        if approval_id.startswith("selfcode-direct-")
        else "owner approved one-time self-code ticket through QQ"
    )
    return {"payload": codex_payload, "approval_id": approval_id}
