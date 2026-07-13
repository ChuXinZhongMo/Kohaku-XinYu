from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urlparse

from xinyu_bridge_stores import (
    read_learning_ingest_scope_env,
    resolve_learning_ingest_scope_root,
)
from xinyu_bridge_values import as_bool as _as_bool
from xinyu_bridge_values import safe_str as _safe_str
from xinyu_local_scope import (
    LocalScopeError,
    default_local_scope_root,
    designated_read_roots,
    resolve_read_only_scope_path,
)


ATTACHMENT_DIRS_ENV = "XINYU_QQ_ATTACHMENT_DIRS"
LEGACY_ATTACHMENT_DIRS_ENV = "XINYU_ASTRBOT_ATTACHMENT_DIRS"


@dataclass(frozen=True)
class LearningIngestRequest:
    file_path: str
    file_url: str
    file_name: str
    origin: str
    reason: str
    question_id: str
    title: str
    label: str
    stage: bool
    curated: bool
    max_bytes: int


def parse_learning_ingest_request(
    payload: dict[str, Any],
    *,
    max_bytes: int,
    safe_str: Callable[[Any, str], str] = _safe_str,
    as_bool: Callable[[Any, bool], bool] = _as_bool,
) -> LearningIngestRequest:
    file_path = safe_str(payload.get("file_path") or payload.get("path"), "").strip()
    file_url = safe_str(payload.get("file_url") or payload.get("url"), "").strip()
    file_name = safe_str(payload.get("file_name") or payload.get("name"), "").strip()
    origin = safe_str(payload.get("origin"), "owner_supplied").strip() or "owner_supplied"
    reason = safe_str(payload.get("reason"), "owner supplied QQ file").strip() or "owner supplied QQ file"
    question_id = safe_str(payload.get("question_id"), "qq-file-learning").strip() or "qq-file-learning"
    title = safe_str(payload.get("title") or file_name, "").strip()
    label = safe_str(payload.get("label") or file_name, "").strip()
    stage = as_bool(payload.get("stage"), True)
    curated = as_bool(payload.get("curated"), origin == "owner_supplied")
    return LearningIngestRequest(
        file_path=file_path,
        file_url=file_url,
        file_name=file_name,
        origin=origin,
        reason=reason,
        question_id=question_id,
        title=title,
        label=label,
        stage=stage,
        curated=curated,
        max_bytes=max_bytes,
    )


def payload_path(value: str) -> Path:
    text = value.strip()
    if text.lower().startswith("file://"):
        parsed = urlparse(text)
        path_text = parsed.path
        if os.name == "nt" and len(path_text) > 2 and path_text[0] == "/" and path_text[2] == ":":
            path_text = path_text[1:]
        return Path(unquote(path_text))
    return Path(text)


def _env_roots(name: str) -> tuple[Path, ...]:
    configured = read_learning_ingest_scope_env(name).strip()
    if not configured:
        return ()
    roots: list[Path] = []
    for part in configured.split(os.pathsep):
        text = part.strip()
        if text:
            roots.append(resolve_learning_ingest_scope_root(text))
    return tuple(roots)


def _has_traversal(raw: str) -> bool:
    return any(part == ".." for part in Path(raw).parts)


def resolve_learning_ingest_path(xinyu_dir: Path, raw_path: str) -> Path:
    if _has_traversal(raw_path):
        raise LocalScopeError("path traversal is not allowed for learning ingest")
    parsed = payload_path(raw_path)
    read_roots = (
        designated_read_roots()
        + (default_local_scope_root(xinyu_dir),)
        + _env_roots(ATTACHMENT_DIRS_ENV)
        + _env_roots(LEGACY_ATTACHMENT_DIRS_ENV)
    )
    return resolve_read_only_scope_path(read_roots, parsed)
