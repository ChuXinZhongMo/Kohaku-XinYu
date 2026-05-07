"""Append-only JSONL memory fallback store."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from ..types import MemoryLayer, PrivacyScope, SourceChannel, coerce_enum, safe_json_mapping
from .models import MemoryChunk, MemoryEvent


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            text = line.strip()
            if not text:
                continue
            value = json.loads(text)
            if isinstance(value, dict):
                rows.append(value)
    except (OSError, json.JSONDecodeError):
        return rows
    return rows


def dump_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
                handle.write("\n")
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def chunk_from_mapping(data: dict[str, Any]) -> MemoryChunk | None:
    chunk_id = str(data.get("chunk_id") or "").strip()
    text = str(data.get("text") or "").strip()
    if not chunk_id or not text:
        return None
    tags_raw = data.get("tags")
    tags = tuple(str(item).strip() for item in tags_raw if str(item).strip()) if isinstance(tags_raw, list) else ()
    metadata = safe_json_mapping(data.get("metadata"))
    return MemoryChunk(
        chunk_id=chunk_id,
        text=text,
        layer=coerce_enum(MemoryLayer, data.get("layer"), MemoryLayer.EVENTS),
        source_event_id=str(data.get("source_event_id") or ""),
        source_path=str(data.get("source_path") or ""),
        timestamp=str(data.get("timestamp") or ""),
        salience=int(data.get("salience") or 0),
        tags=tags,
        metadata=metadata,
    )


def event_from_mapping(data: dict[str, Any]) -> MemoryEvent | None:
    event_id = str(data.get("event_id") or "").strip()
    text = str(data.get("text") or "").strip()
    if not event_id or not text:
        return None
    layers_raw = data.get("layers")
    layers = (
        tuple(coerce_enum(MemoryLayer, item, MemoryLayer.EVENTS) for item in layers_raw)
        if isinstance(layers_raw, list)
        else ()
    )
    return MemoryEvent(
        event_id=event_id,
        timestamp=str(data.get("timestamp") or ""),
        source_channel=coerce_enum(SourceChannel, data.get("source_channel"), SourceChannel.UNKNOWN),
        privacy_scope=coerce_enum(PrivacyScope, data.get("privacy_scope"), PrivacyScope.UNKNOWN),
        actor_hash=str(data.get("actor_hash") or ""),
        text=text,
        salience=int(data.get("salience") or 0),
        layers=layers,
        metadata=safe_json_mapping(data.get("metadata")),
    )


class JsonlMemoryStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.events_path = root / "events.jsonl"
        self.chunks_path = root / "chunks.jsonl"

    def append_event(self, event: MemoryEvent) -> bool:
        rows = load_jsonl(self.events_path)
        if any(str(row.get("event_id")) == event.event_id for row in rows):
            return False
        rows.append(event.to_json())
        dump_jsonl(self.events_path, rows)
        return True

    def append_chunk(self, chunk: MemoryChunk) -> bool:
        rows = load_jsonl(self.chunks_path)
        if any(str(row.get("chunk_id")) == chunk.chunk_id for row in rows):
            return False
        rows.append(chunk.to_json())
        dump_jsonl(self.chunks_path, rows)
        return True

    def load_events(self) -> tuple[MemoryEvent, ...]:
        events = [event_from_mapping(row) for row in load_jsonl(self.events_path)]
        return tuple(event for event in events if event is not None)

    def load_chunks(self) -> tuple[MemoryChunk, ...]:
        chunks = [chunk_from_mapping(row) for row in load_jsonl(self.chunks_path)]
        return tuple(chunk for chunk in chunks if chunk is not None)

