from __future__ import annotations

import argparse
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_proactive_presence import acknowledge_proactive_qq_message, claim_proactive_qq_message
from xinyu_proactive_request_loop import run_proactive_request_loop
from xinyu_qq_outbox import enqueue_owner_qq_outbox_message
from xinyu_proactive_context_adapter import read_recent_owner_private_context
from xinyu_visible_persona_voice import compose_proactive_visible_message

DEFAULT_MIN_INTERVAL_SECONDS = 21600
MAX_DIRECT_MESSAGE_CHARS = 360
SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bauthorization\s*:\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bapi[_-]?key\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\btoken\s*[:=]\s*[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bpassword\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bsk-[a-z0-9_-]{12,}"),
)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _one_line(value: Any, *, limit: int = MAX_DIRECT_MESSAGE_CHARS) -> str:
    text = re.sub(r"\s+", " ", "" if value is None else str(value)).strip()
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("<secret>", text)
    if limit > 0 and len(text) > limit:
        return text[: max(0, limit - 3)].rstrip() + "..."
    return text


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def _extract_list_field(text: str, field: str) -> str:
    match = re.search(rf"(?m)^-\s+{re.escape(field)}:\s*(.*)$", text)
    return _one_line(match.group(1), limit=180) if match else ""


def _proactive_recent_context(root: Path) -> str:
    state = _read_text(root / "memory/context/self_thought_state.md")
    parts = [
        _extract_list_field(state, "focus_label"),
        _extract_list_field(state, "evidence_label"),
        _extract_list_field(state, "why_now"),
        _extract_list_field(state, "after_owner_replies"),
        read_recent_owner_private_context(root),
    ]
    return "\n".join(part for part in parts if part)




def _replace_list_field(text: str, field: str, value: str) -> str:
    replacement = f"- {field}: {_one_line(value) or 'none'}"
    updated, count = re.subn(rf"(?m)^-\s+{re.escape(field)}:\s*.*$", replacement, text, count=1)
    if count:
        return updated
    return text.rstrip() + "\n" + replacement + "\n"


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _update_request_queued_state(
    root: Path,
    *,
    outbox_message_id: str,
    claim_id: str,
    updated_at: str,
) -> bool:
    path = root / "memory/context/proactive_request_state.md"
    state = _read_text(path)
    if not state:
        return False
    updated = _replace_list_field(state, "status", "queued_qq")
    updated = _replace_list_field(updated, "request_answer_state", "sent_waiting_owner_reply")
    updated = _replace_list_field(updated, "qq_outbox_message_id", outbox_message_id)
    updated = _replace_list_field(updated, "last_claim_id", claim_id)
    updated = _replace_list_field(updated, "last_ack_status", "queued")
    updated = _replace_list_field(updated, "adapter_message_id", outbox_message_id)
    updated = re.sub(r"(?m)^updated_at:\s*.*$", f"updated_at: {updated_at}", updated, count=1)
    _write_text(path, updated)
    return True


def send_proactive_direct(
    root: Path,
    *,
    evaluated_at: str | None = None,
    min_interval_seconds: int = DEFAULT_MIN_INTERVAL_SECONDS,
    claim_id: str = "",
    dry_run: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    evaluated_at = evaluated_at or _now_iso()
    claim_id = _one_line(claim_id, limit=96) or f"direct-proactive-{int(time.time())}"

    request = run_proactive_request_loop(
        root,
        evaluated_at=evaluated_at,
        delivery_level="queue_owner_private",
        cooldown_seconds=max(0, int(min_interval_seconds)),
    )
    if not request.get("accepted"):
        return {
            "accepted": False,
            "queued": False,
            "claim_id": claim_id,
            "status": "request_loop_failed",
            "notes": ["direct_request_loop_failed"] + [str(note) for note in request.get("notes", [])],
            "request": request,
        }

    claim = claim_proactive_qq_message(
        root,
        evaluated_at=evaluated_at,
        mode="runtime_proactive_direct_send",
        claim=True,
        claim_id=claim_id,
        min_interval_seconds=max(0, int(min_interval_seconds)),
    )
    if not claim.get("candidate_claimed"):
        return {
            "accepted": True,
            "queued": False,
            "claim_id": claim_id,
            "status": "not_ready",
            "notes": ["direct_send_not_claimed"] + [str(note) for note in claim.get("notes", [])],
            "claim": claim,
        }

    raw_message = _one_line(claim.get("reply"), limit=MAX_DIRECT_MESSAGE_CHARS)
    recent_context = _proactive_recent_context(root)
    message = compose_proactive_visible_message(
        raw_message,
        source="proactive_direct_send",
        recent_context=recent_context,
    ).strip()
    message = _one_line(message, limit=MAX_DIRECT_MESSAGE_CHARS)
    if not message:
        acknowledge_proactive_qq_message(
            root,
            acked_at=evaluated_at,
            claim_id=claim_id,
            ack_status="failed",
            adapter_error="empty_direct_message",
        )
        return {
            "accepted": False,
            "queued": False,
            "claim_id": claim_id,
            "status": "failed",
            "notes": ["empty_direct_message"],
        }

    if dry_run:
        acknowledge_proactive_qq_message(
            root,
            acked_at=evaluated_at,
            claim_id=claim_id,
            ack_status="dry_run",
        )
        return {
            "accepted": True,
            "queued": False,
            "claim_id": claim_id,
            "status": "dry_run_claimed_not_enqueued",
            "message_preview": message,
            "notes": ["dry_run_no_qq_outbox_enqueue"],
        }

    queued = enqueue_owner_qq_outbox_message(
        root,
        message=message,
        source="xinyu_proactive_direct_sender",
        dedupe_key=f"proactive-direct:{claim.get('proactive_request_id') or claim_id}",
        metadata={
            "source": "xinyu_proactive_direct_sender",
            "proactive_request_id": claim.get("proactive_request_id", "none"),
            "claim_id": claim_id,
            "direct_proactive": True,
            "owner_private_only": True,
        },
    )
    if not queued.get("accepted"):
        acknowledge_proactive_qq_message(
            root,
            acked_at=evaluated_at,
            claim_id=claim_id,
            ack_status="failed",
            adapter_error=",".join(str(note) for note in queued.get("notes", [])),
        )
        return {
            "accepted": False,
            "queued": False,
            "claim_id": claim_id,
            "status": "failed",
            "notes": ["qq_outbox_enqueue_failed"] + [str(note) for note in queued.get("notes", [])],
        }

    outbox_message_id = str(queued.get("message_id") or "")
    _update_request_queued_state(
        root,
        outbox_message_id=outbox_message_id,
        claim_id=claim_id,
        updated_at=evaluated_at,
    )
    acknowledge_proactive_qq_message(
        root,
        acked_at=evaluated_at,
        claim_id=claim_id,
        ack_status="sent",
        adapter_message_id=outbox_message_id,
    )
    return {
        "accepted": True,
        "queued": bool(queued.get("queued")),
        "claim_id": claim_id,
        "status": "queued_qq",
        "outbox_message_id": outbox_message_id,
        "message_preview": message,
        "notes": ["direct_proactive_queued"] + [str(note) for note in queued.get("notes", [])],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Directly enqueue one gated owner-private proactive QQ message.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--evaluated-at", default=None)
    parser.add_argument("--min-interval-seconds", type=int, default=DEFAULT_MIN_INTERVAL_SECONDS)
    parser.add_argument("--claim-id", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = send_proactive_direct(
        args.root,
        evaluated_at=args.evaluated_at,
        min_interval_seconds=args.min_interval_seconds,
        claim_id=args.claim_id,
        dry_run=args.dry_run,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"status: {result.get('status')}")
        print(f"queued: {result.get('queued')}")
        if result.get("message_preview"):
            print(f"message_preview: {result.get('message_preview')}")
        for note in result.get("notes", []):
            print(f"note: {note}")
    return 0 if result.get("accepted") else 1


if __name__ == "__main__":
    raise SystemExit(main())
