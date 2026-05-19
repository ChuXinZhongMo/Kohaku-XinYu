from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from ._diagnostic_paths import ensure_app_root_on_path
except ImportError:  # pragma: no cover - direct script execution
    from _diagnostic_paths import ensure_app_root_on_path


TRACE_REL = Path("runtime/self_presence_trace.jsonl")
APP_ROOT = ensure_app_root_on_path()

MODULES: tuple[dict[str, Any], ...] = (
    {
        "name": "bridge_turn_pipeline",
        "path": "xinyu_bridge_turn_pipeline.py",
        "scope": "Core chat pre-model route order",
        "markers": ("event_sourcing", "action_layer_intercepted", "recent_action_followup", "action_digest", "v1_shadow", "v1_canary"),
    },
    {
        "name": "bridge_action_routes",
        "path": "xinyu_bridge_action_routes.py",
        "scope": "Action layer and action follow-up routes",
        "markers": ("action_layer_intercepted", "action_experience", "recent_action_followup", "action_digest_followup"),
    },
    {
        "name": "bridge_v1_routes",
        "path": "xinyu_bridge_v1_routes.py",
        "scope": "v1 shadow and owner simple canary routes",
        "markers": ("v1_shadow", "v1_canary"),
    },
    {
        "name": "qq_normalizer",
        "path": "xinyu_qq_normalizer.py",
        "scope": "OneBot text, segment, CQ, sender and message-kind normalization",
        "source_markers": ("qq_gateway",),
    },
    {
        "name": "qq_command_router",
        "path": "xinyu_qq_command_router.py",
        "scope": "QQ command prefixes, group trigger, blocked/passthrough routing",
        "source_markers": ("qq_gateway",),
    },
    {
        "name": "qq_attachment_resolver",
        "path": "xinyu_qq_attachment_resolver.py",
        "scope": "QQ file/image/sticker resolution before Core routes",
        "markers": ("file_resolution", "attachment_followup", "sticker_import"),
        "source_markers": ("qq_gateway",),
    },
    {
        "name": "qq_outbox_client",
        "path": "xinyu_qq_outbox_client.py",
        "scope": "QQ outbox target, send ack, and pending ack spool",
        "markers": ("qq_outbox", "outbox", "message_ack"),
    },
)


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default


def _load_last_turn_event(root: Path) -> dict[str, Any]:
    trace_path = root / TRACE_REL
    if not trace_path.exists():
        return {}
    last: dict[str, Any] = {}
    try:
        lines = trace_path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return {}
    for line in lines[-400:]:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("event_kind") in {"turn_finished", "turn_failed"}:
            last = event
    return last


def build_diagnostics(root: Path) -> dict[str, Any]:
    root = root.resolve()
    event = _load_last_turn_event(root)
    notes = event.get("notes") if isinstance(event.get("notes"), list) else []
    note_text = "\n".join(_safe_str(note) for note in notes)
    source_channel = _safe_str(event.get("source_channel"))

    modules: list[dict[str, Any]] = []
    for item in MODULES:
        markers = tuple(_safe_str(marker) for marker in item.get("markers", ()))
        source_markers = tuple(_safe_str(marker) for marker in item.get("source_markers", ()))
        influenced = any(marker and marker in note_text for marker in markers)
        if not influenced and source_channel:
            influenced = any(marker and marker in source_channel for marker in source_markers)
        path = _safe_str(item.get("path"))
        modules.append(
            {
                "name": item["name"],
                "path": path,
                "present": bool(path and (root / path).exists()),
                "scope": item["scope"],
                "influenced_last_turn": influenced,
            }
        )

    return {
        "root": str(root),
        "trace": str(root / TRACE_REL),
        "last_turn": {
            "turn_id": _safe_str(event.get("turn_id")),
            "observed_at": _safe_str(event.get("observed_at")),
            "status": _safe_str(event.get("status")),
            "source_channel": source_channel,
            "notes": [_safe_str(note) for note in notes[:16]],
        },
        "modules": modules,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Show which refactored live modules influenced the latest XinYu turn.")
    parser.add_argument("--root", type=Path, default=APP_ROOT)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    data = build_diagnostics(args.root)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    last_turn = data["last_turn"]
    print("XinYu live module diagnostics")
    print(f"last_turn: {last_turn.get('turn_id') or 'missing'} {last_turn.get('status') or 'unknown'}")
    print(f"source: {last_turn.get('source_channel') or 'unknown'}")
    for module in data["modules"]:
        used = "used" if module["influenced_last_turn"] else "ready"
        present = "present" if module["present"] else "missing"
        print(f"- {module['name']}: {present}, {used} - {module['scope']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
