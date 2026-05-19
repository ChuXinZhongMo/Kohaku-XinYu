from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import json
import tempfile
from pathlib import Path
from typing import Any

from xinyu_tinykernel_shadow import TRACE_REL, record_tinykernel_shadow


def fake_post(endpoint: str, payload: dict[str, Any], timeout_seconds: float) -> dict[str, Any]:
    return {
        "event_kind": "tinykernel_compose_shadow",
        "ok": True,
        "shadow_only": True,
        "turn_id": payload.get("turn_id", ""),
        "request_hash": "hash-smoke",
        "request_chars": len(str(payload.get("user_text", ""))),
        "mode": "reply",
        "reply_candidate": "可以，先 shadow。",
        "emotion_biases": [{"lens": "curiosity", "activation": 0.66}],
        "selected_bias": {"lens": "curiosity", "activation": 0.66},
        "confidence": 0.7,
        "elapsed_ms": 1.2,
        "notes": ["compose_shadow", "shadow_only"],
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="xinyu-tinykernel-shadow-") as tmp:
        root = Path(tmp)
        disabled = record_tinykernel_shadow(
            root,
            turn_id="turn-disabled",
            source="local_test",
            user_text="不要记录原文",
            enabled=False,
        )
        if disabled.get("recorded") is not False:
            print("FAIL disabled call should not record")
            return 1
        enabled = record_tinykernel_shadow(
            root,
            turn_id="turn-enabled",
            source="local_test",
            user_text="这个 idea 可行吗",
            enabled=True,
            post_fn=fake_post,
            observed_at="2026-05-13T14:00:00+08:00",
        )
        if not enabled.get("recorded") or not enabled.get("ok"):
            print(f"FAIL enabled call did not record ok: {enabled}")
            return 1
        trace = root / TRACE_REL
        if not trace.exists():
            print("FAIL trace missing")
            return 1
        row = json.loads(trace.read_text(encoding="utf-8").strip())
        if row.get("event_kind") != "tinykernel_compose_shadow_observation":
            print(f"FAIL wrong event_kind: {row}")
            return 1
        if "这个 idea 可行吗" in trace.read_text(encoding="utf-8"):
            print("FAIL trace leaked raw user text")
            return 1
        if row.get("selected_lens") != "curiosity" or row.get("reply_candidate_chars", 0) <= 0:
            print(f"FAIL trace summary wrong: {row}")
            return 1
    print("OK tinykernel_shadow_smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
