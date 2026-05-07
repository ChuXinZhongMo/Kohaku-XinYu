from __future__ import annotations

from typing import Any


def _maybe_int(value: Any) -> int | str:
    text = str(value)
    return int(text) if text.isdigit() else text


def _target_params(target: Any) -> dict[str, Any]:
    if target.message_kind == "group":
        return {"group_id": _maybe_int(target.group_id)}
    return {"user_id": _maybe_int(target.user_id)}


def text_message_action(target: Any, text: str) -> tuple[str, dict[str, Any]]:
    action = "send_group_msg" if target.message_kind == "group" else "send_private_msg"
    params: dict[str, Any] = {
        "message": [{"type": "text", "data": {"text": text}}],
        "auto_escape": False,
        **_target_params(target),
    }
    return action, params


def image_message_action(target: Any, image_file: str) -> tuple[str, dict[str, Any]]:
    action = "send_group_msg" if target.message_kind == "group" else "send_private_msg"
    params: dict[str, Any] = {
        "message": [{"type": "image", "data": {"file": image_file}}],
        "auto_escape": False,
        **_target_params(target),
    }
    return action, params


def file_upload_action(target: Any, file_path: str, *, name: str) -> tuple[str, dict[str, Any]]:
    action = "upload_group_file" if target.message_kind == "group" else "upload_private_file"
    params: dict[str, Any] = {
        "file": file_path,
        "name": name,
        **_target_params(target),
    }
    return action, params
