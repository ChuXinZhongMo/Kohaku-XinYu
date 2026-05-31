from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from behavior_shadow_log import append_behavior_shadow_event


OUT_LOG = ROOT / "state" / "behavior_gate_shadow_smoke_v001.jsonl"
OUT_REPORT = ROOT / "eval" / "reports" / "xinyu_maia_behavior_shadow_log_smoke_v001.json"


SAMPLES = [
    {"turn_id": "shadow-smoke-001", "user_text": "\u4f60\u5148\u522b\u54ed", "source": "local_smoke"},
    {"turn_id": "shadow-smoke-002", "user_text": "\u8c01\u554a", "source": "local_smoke", "act": "question"},
    {"turn_id": "shadow-smoke-003", "user_text": "\u5982\u679c\u4ed6\u4e0d\u5728\u8fd9\u91cc", "source": "local_smoke"},
    {
        "turn_id": "shadow-smoke-004",
        "user_text": "check this file",
        "source": "local_smoke",
        "signal": "code_or_file_review_request",
    },
]


def main() -> int:
    if OUT_LOG.exists():
        OUT_LOG.unlink()
    events = []
    for payload in SAMPLES:
        stored = append_behavior_shadow_event(
            payload,
            path=OUT_LOG,
            source_endpoint="smoke",
            include_text=True,
        )
        events.append(stored["event"])

    report = {
        "generated_at": "2026-05-29",
        "status": "behavior_shadow_log_smoke_passed",
        "log_path": str(OUT_LOG.relative_to(ROOT)).replace("\\", "/"),
        "sample_count": len(SAMPLES),
        "event_count": len(events),
        "mode_counts": dict(sorted(Counter(event["behavior"]["mode"] for event in events).items())),
        "shadow_only_all": all(event.get("shadow_only") is True for event in events),
        "visible_reply_sent_any": any(event.get("visible_reply_sent") for event in events),
        "stable_memory_written_any": any(event.get("stable_memory_written") for event in events),
        "tool_executed_any": any(event.get("tool_executed") for event in events),
        "adapter_activated_any": any(event.get("adapter_activated") for event in events),
        "training_target_any": any(event.get("training_target") for event in events),
        "notes": [
            "Smoke log includes sample text only because include_text=True is explicit in this offline script.",
            "Runtime endpoint defaults to no text unless shadow_behavior_include_text is true.",
        ],
    }
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("event_count=" + str(report["event_count"]))
    print("mode_counts=" + json.dumps(report["mode_counts"], ensure_ascii=False, sort_keys=True))
    print("log_path=" + report["log_path"])
    print("report=" + str(OUT_REPORT.relative_to(ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
