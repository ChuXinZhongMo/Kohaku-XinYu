from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from xinyu_attention_posture import update_attention_posture
from xinyu_proactive_direct_sender import DEFAULT_MIN_INTERVAL_SECONDS, send_proactive_direct


def process_life_event(
    root: Path,
    event_payload: dict[str, Any],
    *,
    evaluated_at: str | None = None,
    allow_direct_send: bool = False,
    min_interval_seconds: int = DEFAULT_MIN_INTERVAL_SECONDS,
    claim_id: str = "",
    dry_run: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    attention = update_attention_posture(root, event_payload, evaluated_at=evaluated_at)
    direct_send = {
        "attempted": False,
        "queued": False,
        "status": "not_attempted",
        "notes": ["direct_send_disabled" if not allow_direct_send else "route_not_direct_sendable"],
    }
    route = str(attention.get("route", {}).get("route", "unknown"))
    if allow_direct_send and route == "owner_private_question":
        event_id = str(attention.get("event", {}).get("event_id") or "life-event")
        direct_send = send_proactive_direct(
            root,
            evaluated_at=evaluated_at,
            min_interval_seconds=min_interval_seconds,
            claim_id=claim_id or f"life-event-{event_id}",
            dry_run=dry_run,
        )
        direct_send = {"attempted": True, **direct_send}
    return {
        "accepted": bool(attention.get("accepted")),
        "event_id": attention.get("event", {}).get("event_id", "unknown"),
        "route": route,
        "attention": attention.get("attention", {}),
        "self_thought_written": bool(attention.get("self_thought_written")),
        "direct_send": direct_send,
        "notes": list(attention.get("notes", [])) + list(direct_send.get("notes", [])),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Process one sanitized life event through attention and optional direct proactive send.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--event-json", required=True)
    parser.add_argument("--evaluated-at", default=None)
    parser.add_argument("--allow-direct-send", action="store_true")
    parser.add_argument("--min-interval-seconds", type=int, default=DEFAULT_MIN_INTERVAL_SECONDS)
    parser.add_argument("--claim-id", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    payload = json.loads(args.event_json)
    if not isinstance(payload, dict):
        raise SystemExit("event-json must be an object")
    result = process_life_event(
        args.root,
        payload,
        evaluated_at=args.evaluated_at,
        allow_direct_send=args.allow_direct_send,
        min_interval_seconds=args.min_interval_seconds,
        claim_id=args.claim_id,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("accepted") else 1


if __name__ == "__main__":
    raise SystemExit(main())
