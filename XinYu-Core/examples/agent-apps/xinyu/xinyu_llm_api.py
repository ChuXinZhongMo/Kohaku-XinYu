from __future__ import annotations

from typing import Any, Sequence

ANTHROPIC_VERSION = "2023-06-01"


def is_anthropic_messages_provider(provider: str) -> bool:
    text = str(provider or "").strip().lower()
    return text in {"message", "messages"} or "anthropic" in text or "claude" in text


def anthropic_messages_endpoint(base_url: str) -> str:
    trimmed = str(base_url or "").rstrip("/")
    lowered = trimmed.lower()
    if lowered.endswith("/messages"):
        return trimmed
    if lowered.endswith("/v1"):
        return f"{trimmed}/messages"
    return f"{trimmed}/v1/messages"


def openai_headers(api_key: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json; charset=utf-8", "Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def anthropic_headers(api_key: str) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
        "anthropic-version": ANTHROPIC_VERSION,
    }
    if api_key:
        headers["x-api-key"] = api_key
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def anthropic_payload_from_messages(
    messages: Sequence[dict[str, str]],
    *,
    model: str,
    temperature: float,
    max_tokens: int,
) -> dict[str, Any]:
    system_parts: list[str] = []
    dialogue: list[dict[str, str]] = []
    for message in messages:
        role = str(message.get("role") or "").strip()
        content = str(message.get("content") or "").strip()
        if not content:
            continue
        if role == "system":
            system_parts.append(content)
        elif role in {"user", "assistant"}:
            dialogue.append({"role": role, "content": content})
    payload: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": dialogue,
    }
    if system_parts:
        payload["system"] = "\n\n".join(system_parts)
    return payload


def extract_openai_text(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                return str(message.get("content") or "").strip()
            return str(first.get("text") or "").strip()
    return str(data.get("text") or data.get("reply") or "").strip()


def extract_anthropic_text(data: dict[str, Any]) -> str:
    content = data.get("content")
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = str(item.get("text") or "").strip()
                if text:
                    parts.append(text)
        return "\n".join(parts).strip()
    return str(content or data.get("text") or data.get("completion") or data.get("reply") or "").strip()


def extract_api_error_message(data: dict[str, Any]) -> str:
    error = data.get("error")
    if isinstance(error, str):
        return error.strip()
    if isinstance(error, dict):
        message = str(error.get("message") or "").strip()
        if message:
            return message
    return str(data.get("message") or "").strip()
