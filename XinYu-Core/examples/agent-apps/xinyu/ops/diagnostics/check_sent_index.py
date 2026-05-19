from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from _diagnostic_paths import APP_ROOT, ensure_app_root_on_path

ensure_app_root_on_path()

from xinyu_sent_reply_index import lookup_sent_reply_by_adapter_msg_id


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Look up a QQ adapter message id in XinYu's sent reply index.",
    )
    parser.add_argument("adapter_msg_id", help="QQ/NapCat message_id, with or without qq: prefix.")
    parser.add_argument("--root", default=str(APP_ROOT), help="XinYu app root directory.")
    parser.add_argument("--adapter", default="xinyu_native_qq_gateway", help="Adapter name stored in the index.")
    parser.add_argument("--route", default="", help="Optional route filter, such as chat or qq_outbox.")
    parser.add_argument("--json", action="store_true", help="Print raw JSON result.")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = lookup_sent_reply_by_adapter_msg_id(
        Path(args.root),
        args.adapter_msg_id,
        adapter=args.adapter,
        route=args.route,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("found") else 1

    if not result.get("found"):
        notes = ", ".join(_safe_str(note) for note in result.get("notes", []))
        print(f"not found: {args.adapter_msg_id} ({notes or 'sent_reply_index_miss'})")
        return 1

    entry = result.get("entry") if isinstance(result.get("entry"), dict) else {}
    print(f"adapter_message_id: {_safe_str(entry.get('adapter_message_id'))}")
    print(f"route: {_safe_str(entry.get('route'))}")
    print(f"turn_id: {_safe_str(entry.get('turn_id')) or 'none'}")
    print(f"session_id: {_safe_str(entry.get('session_id')) or 'none'}")
    print(f"outbox_message_id: {_safe_str(entry.get('outbox_message_id')) or 'none'}")
    print(f"archive_assistant_message_id: {_safe_str(entry.get('archive_assistant_message_id')) or 'none'}")
    print(f"visible_text_hash: {_safe_str(entry.get('visible_text_hash')) or 'none'}")
    print(f"sent_at: {_safe_str(entry.get('sent_at')) or 'none'}")
    preview = _safe_str(entry.get("visible_text_preview")).strip()
    if preview:
        print(f"visible_text_preview: {preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
