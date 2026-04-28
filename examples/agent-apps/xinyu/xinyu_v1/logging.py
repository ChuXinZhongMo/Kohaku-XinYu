"""Structured logging helpers with light privacy redaction."""

from __future__ import annotations

import hashlib
import json
import logging as std_logging
import re
from collections.abc import Mapping
from typing import Any

from .types import JSONValue, TraceContext


_DIGIT_RUN_RE = re.compile(r"\b\d{5,}\b")
_TOKEN_RE = re.compile(r"(?i)(api[_-]?key|token|authorization|secret)\s*[:=]\s*([^\s,;]+)")


def stable_hash(value: str, length: int = 12) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:length]


def redact_text(text: str) -> str:
    redacted = _TOKEN_RE.sub(lambda m: f"{m.group(1)}=<redacted>", text)
    return _DIGIT_RUN_RE.sub(lambda m: f"id:{stable_hash(m.group(0), 8)}", redacted)


def redact_mapping(mapping: Mapping[str, Any]) -> dict[str, JSONValue]:
    result: dict[str, JSONValue] = {}
    for raw_key, value in mapping.items():
        key = str(raw_key)
        lowered = key.lower()
        if any(marker in lowered for marker in ("token", "secret", "api_key", "authorization")):
            result[key] = "<redacted>"
        elif isinstance(value, str):
            result[key] = redact_text(value)
        elif isinstance(value, (int, float, bool)) or value is None:
            result[key] = value
        else:
            result[key] = redact_text(str(value))
    return result


def configure_logging(level: str = "INFO") -> None:
    std_logging.basicConfig(
        level=getattr(std_logging, level.upper(), std_logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


class StructuredLogger:
    def __init__(self, name: str) -> None:
        self._logger = std_logging.getLogger(name)

    def info(self, event: str, **fields: Any) -> None:
        self._log(std_logging.INFO, event, fields)

    def warning(self, event: str, **fields: Any) -> None:
        self._log(std_logging.WARNING, event, fields)

    def error(self, event: str, **fields: Any) -> None:
        self._log(std_logging.ERROR, event, fields)

    def debug(self, event: str, **fields: Any) -> None:
        self._log(std_logging.DEBUG, event, fields)

    def exception(self, event: str, **fields: Any) -> None:
        payload = self._payload(event, fields)
        self._logger.exception(json.dumps(payload, ensure_ascii=False))

    def _log(self, level: int, event: str, fields: Mapping[str, Any]) -> None:
        if not self._logger.isEnabledFor(level):
            return
        payload = self._payload(event, fields)
        self._logger.log(level, json.dumps(payload, ensure_ascii=False))

    def _payload(self, event: str, fields: Mapping[str, Any]) -> dict[str, JSONValue]:
        payload = redact_mapping(fields)
        payload["event"] = redact_text(event)
        trace = fields.get("trace")
        if isinstance(trace, TraceContext):
            payload["trace"] = trace.to_json()
        return payload


def get_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)

