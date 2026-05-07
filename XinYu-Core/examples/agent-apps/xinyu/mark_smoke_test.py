from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from xinyu_goldmark import mark_goldmark_request, read_goldmark_overlay
from xinyu_sent_reply_index import register_sent_reply_ack


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


def run_temp_smoke() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="xinyu-goldmark-smoke-") as tmp:
        root = Path(tmp)
        register_sent_reply_ack(
            root,
            {
                "adapter": "xinyu_native_qq_gateway",
                "adapter_message_id": "smoke-adapter-1",
                "route": "chat",
                "session_id": "qq:private:owner",
                "turn_id": "turn-20260503T193453-sha256:smoke",
                "visible_text": "smoke reply",
            },
        )
        result = mark_goldmark_request(
            root,
            {
                "adapter": "xinyu_native_qq_gateway",
                "adapter_message_id": "smoke-adapter-1",
                "route": "chat",
                "owner_note": "smoke note",
                "source_message_id": "smoke-command-1",
            },
        )
        overlay = read_goldmark_overlay(root)
        ok = bool(result.get("marked")) and len(overlay) == 1 and bool(overlay[0].get("turn_id"))
        return {"ok": ok, "mode": "temp", "result": result, "overlay_count": len(overlay)}


def run_live_mark(adapter_message_id: str, *, note: str) -> dict[str, object]:
    result = mark_goldmark_request(
        _repo_root(),
        {
            "adapter": "xinyu_native_qq_gateway",
            "adapter_message_id": adapter_message_id,
            "route": "chat",
            "owner_note": note,
            "source_message_id": "mark_smoke_test",
        },
    )
    overlay = read_goldmark_overlay(_repo_root())
    return {"ok": bool(result.get("marked")), "mode": "live", "result": result, "overlay_count": len(overlay)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test P4b Goldmark marking.")
    parser.add_argument("adapter_message_id", nargs="?", help="Optional live QQ adapter message id to mark.")
    parser.add_argument("--note", default="mark smoke test", help="Owner note for live marking.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args()

    if args.adapter_message_id:
        result = run_live_mark(args.adapter_message_id, note=args.note)
    else:
        result = run_temp_smoke()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok: {str(result['ok']).lower()}")
        print(f"mode: {result['mode']}")
        print(f"overlay_count: {result['overlay_count']}")
        print(f"result: {result['result']}")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
