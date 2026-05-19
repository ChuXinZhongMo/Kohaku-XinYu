from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SAFE_STRING_KEYS = (
    "content_type",
    "created_at",
    "id",
    "kind",
    "origin",
    "question_id",
    "source_type",
    "stage_status",
)
UNSAFE_KEYS = (
    "claim",
    "reason",
    "source_url",
    "raw",
    "prompt",
    "reply",
    "owner",
)
FORBIDDEN_OUTPUT_MARKERS = (
    "http://",
    "https://",
    "openid=",
    "rkey=",
    "qqdownload",
)


@dataclass(frozen=True)
class SanitizedMetadata:
    path: str
    parse_ok: bool
    parse_error: str
    safe_fields: dict[str, str]
    unsafe_fields_present: tuple[str, ...]
    title_hash: str
    title_suffix: str
    stored_path_count: int
    stored_path_suffix_counts: dict[str, int]


def build_sanitized_metadata_manifest(root: Path) -> dict[str, Any]:
    root = root.resolve()
    items = [sanitize_metadata_file(path, root=root) for path in sorted(root.rglob("metadata.json"))]
    return {
        "root": root.as_posix(),
        "item_count": len(items),
        "parse_ok": sum(1 for item in items if item.parse_ok),
        "parse_failed": sum(1 for item in items if not item.parse_ok),
        "items": [
            {
                "path": item.path,
                "parse_ok": item.parse_ok,
                "parse_error": item.parse_error,
                "safe_fields": item.safe_fields,
                "unsafe_fields_present": list(item.unsafe_fields_present),
                "title_hash": item.title_hash,
                "title_suffix": item.title_suffix,
                "stored_path_count": item.stored_path_count,
                "stored_path_suffix_counts": item.stored_path_suffix_counts,
            }
            for item in items
        ],
        "privacy_note": "Sanitized metadata manifest; suppresses URL/token/raw claim/reason/prompt/reply/body values.",
    }


def sanitize_metadata_file(path: Path, *, root: Path | None = None) -> SanitizedMetadata:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    parsed: dict[str, Any] | None = None
    parse_error = ""
    try:
        loaded = json.loads(text)
        if isinstance(loaded, dict):
            parsed = loaded
    except Exception as exc:  # noqa: BLE001 - preserve only exception type, not raw parser text.
        parse_error = type(exc).__name__

    safe_fields: dict[str, str] = {}
    for key in SAFE_STRING_KEYS:
        value = _get_string_value(parsed, text, key)
        if value:
            safe_fields[key] = _safe_scalar(value)

    title = _get_string_value(parsed, text, "title")
    stored_paths = _get_stored_paths(parsed, text)
    unsafe_fields = tuple(key for key in UNSAFE_KEYS if _has_key(parsed, text, key))
    rel = path.as_posix()
    if root is not None:
        try:
            rel = path.resolve().relative_to(root).as_posix()
        except ValueError:
            rel = path.as_posix()
    suffix_counts = Counter(Path(stored_path).suffix.lower() or "<none>" for stored_path in stored_paths)
    return SanitizedMetadata(
        path=rel,
        parse_ok=parsed is not None,
        parse_error=parse_error,
        safe_fields=safe_fields,
        unsafe_fields_present=unsafe_fields,
        title_hash=_hash_text(title),
        title_suffix=Path(title).suffix.lower() if title else "",
        stored_path_count=len(stored_paths),
        stored_path_suffix_counts=dict(sorted(suffix_counts.items())),
    )


def render_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# XinYu Sanitized Learning Metadata Manifest",
        "",
        "This manifest is safe to inspect. It suppresses URL/token/raw claim/reason/prompt/reply/body values.",
        "",
        f"- root: `{manifest['root']}`",
        f"- item_count: {manifest['item_count']}",
        f"- parse_ok: {manifest['parse_ok']}",
        f"- parse_failed: {manifest['parse_failed']}",
        "",
        "## Items",
        "",
        "| Metadata | Parse | Safe fields | Unsafe keys present | Title hash | Stored paths | Suffix counts |",
        "| --- | --- | --- | --- | --- | ---: | --- |",
    ]
    for item in manifest.get("items") or []:
        safe_fields = ", ".join(f"{key}={value}" for key, value in sorted(item["safe_fields"].items()))
        unsafe = ", ".join(item["unsafe_fields_present"]) or "none"
        suffix_counts = ", ".join(
            f"{key}:{value}" for key, value in sorted((item.get("stored_path_suffix_counts") or {}).items())
        )
        parse = "ok" if item["parse_ok"] else f"failed:{item['parse_error']}"
        lines.append(
            f"| `{item['path']}` | {parse} | {safe_fields or 'none'} | {unsafe} | "
            f"`{item['title_hash']}` | {item['stored_path_count']} | {suffix_counts or 'none'} |"
        )
    rendered = "\n".join(lines).rstrip() + "\n"
    _assert_safe_output(rendered)
    return rendered


def _get_string_value(parsed: dict[str, Any] | None, text: str, key: str) -> str:
    if parsed is not None:
        value = parsed.get(key)
        if isinstance(value, str):
            return value
    match = re.search(rf'"{re.escape(key)}"\s*:\s*"((?:\\.|[^"\\])*)"', text, flags=re.DOTALL)
    if not match:
        return ""
    raw = match.group(1)
    try:
        decoded = json.loads(f'"{raw}"')
    except Exception:  # noqa: BLE001
        decoded = raw
    return decoded if isinstance(decoded, str) else ""


def _get_stored_paths(parsed: dict[str, Any] | None, text: str) -> list[str]:
    if parsed is not None:
        value = parsed.get("stored_paths")
        if isinstance(value, list):
            return [item for item in value if isinstance(item, str)]
    match = re.search(r'"stored_paths"\s*:\s*\[(.*?)\]', text, flags=re.DOTALL)
    if not match:
        return []
    return re.findall(r'"((?:\\.|[^"\\])*)"', match.group(1))


def _has_key(parsed: dict[str, Any] | None, text: str, key: str) -> bool:
    if parsed is not None and key in parsed:
        return True
    return re.search(rf'"{re.escape(key)}"\s*:', text) is not None


def _safe_scalar(value: str) -> str:
    clean = value.replace("\r", " ").replace("\n", " ").strip()
    for marker in FORBIDDEN_OUTPUT_MARKERS:
        clean = clean.replace(marker, "[redacted]")
    return clean[:120]


def _hash_text(value: str) -> str:
    if not value:
        return ""
    return "sha256:" + hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:16]


def _assert_safe_output(text: str) -> None:
    lowered = text.lower()
    for marker in FORBIDDEN_OUTPUT_MARKERS:
        if marker.lower() in lowered:
            raise RuntimeError(f"Unsafe marker in sanitized metadata output: {marker}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a sanitized learning metadata manifest.")
    parser.add_argument("--root", default="learning/owner_supplied")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", default="")
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    manifest = build_sanitized_metadata_manifest(Path(args.root))
    rendered = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n" if args.json else render_markdown(manifest)
    _assert_safe_output(rendered)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
