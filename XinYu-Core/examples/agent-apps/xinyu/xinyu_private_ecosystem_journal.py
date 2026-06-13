"""XinYu Private Ecosystem autonomy journal.

Append-only, sanitized journal of what XinYu observed, chose, ran, held, or
shared inside her own private ecosystem. This is evidence, not a control plane:
it never writes stable memory and never carries raw owner text, secrets, or
local paths.

The dossier (section "Phase 1") names this `xinyu_autonomy_journal.py`, but that
filename is already an unrelated owner-visible thought-note renderer. To avoid
clobbering existing functionality this journal store keeps the
`private_ecosystem` namespace. See
docs/plans/CLAUDE-XINYU-PRIVATE-ECOSYSTEM-DOSSIER-2026-06-02.md section 6.1.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_private_ecosystem_journal_store import append_private_ecosystem_journal_event
from xinyu_private_ecosystem_journal_store import read_private_ecosystem_journal_text

JOURNAL_VERSION = 1

JOURNAL_REL = Path("runtime/private_ecosystem/autonomy_journal.jsonl")

EVENT_KINDS = frozenset(
    {
        "tick_started",
        "goal_selected",
        "action_executed",
        "action_blocked",
        "memory_candidate_created",
        "share_prepared",
        "share_sent",
        "share_held",
    }
)

RISK_TIERS = frozenset(
    {"low_local", "approval_required", "owner_private_send", "high_blocked"}
)

PRIVACY_LEVELS = frozenset({"self_private", "owner_private_redacted", "public_status"})

STATUS_VALUES = frozenset({"completed", "queued", "blocked", "failed"})


@dataclass(frozen=True, slots=True)
class AutonomyJournalEvent:
    event_id: str
    event_kind: str
    observed_at: str
    source_module: str
    goal_id: str
    action_kind: str
    risk_tier: str
    status: str
    summary: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    privacy: str
    stable_memory_write: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_kind": self.event_kind,
            "observed_at": self.observed_at,
            "source_module": self.source_module,
            "goal_id": self.goal_id,
            "action_kind": self.action_kind,
            "risk_tier": self.risk_tier,
            "status": self.status,
            "summary": list(self.summary),
            "evidence_refs": list(self.evidence_refs),
            "privacy": self.privacy,
            "stable_memory_write": bool(self.stable_memory_write),
        }


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp_or_now_iso(value: Any = None) -> str:
    text = _safe_str(value).strip()
    if not text or text.lower() in {"none", "unknown", "null", "n/a", "na"}:
        return _now_iso()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return _now_iso()
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone().isoformat(timespec="seconds")


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _hash_json(value: Any, *, length: int = 16) -> str:
    blob = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8", errors="replace")).hexdigest()[:length]


_SECRET_RE = re.compile(
    r"(?i)\b(?:authorization|api[_-]?key|token|password|secret|cookie)\s*[:=]\s*[^\s<>'\"]+"
)
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}")
_SK_RE = re.compile(r"(?i)\bsk-[a-z0-9_-]{12,}")
_PATH_RE = re.compile(r"(?i)(?:[a-z]:\\|/users/|/home/|\\\\)[^\s<>'\"]+")


def sanitize_line(value: Any, *, limit: int = 200, default: str = "") -> str:
    """Collapse to one redacted line: strip secrets and local paths."""
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    text = _SECRET_RE.sub("<secret>", text)
    text = _BEARER_RE.sub("<secret>", text)
    text = _SK_RE.sub("<secret>", text)
    text = _PATH_RE.sub("<local_path>", text)
    if not text:
        return default
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _sanitize_refs(refs: Any) -> tuple[str, ...]:
    if not refs:
        return ()
    if isinstance(refs, str):
        refs = [refs]
    out: list[str] = []
    for ref in list(refs)[:12]:
        cleaned = sanitize_line(ref, limit=160)
        if cleaned:
            out.append(cleaned)
    return tuple(out)


def journal_path(root: Path) -> Path:
    return Path(root) / JOURNAL_REL


def append_journal_event(
    root: Path,
    *,
    event_kind: str,
    observed_at: str | None = None,
    source_module: str = "xinyu_private_ecosystem",
    goal_id: str = "",
    action_kind: str = "",
    risk_tier: str = "low_local",
    status: str = "completed",
    summary: Any = (),
    evidence_refs: Any = (),
    privacy: str = "self_private",
    stable_memory_write: bool = False,
) -> dict[str, Any]:
    """Append one sanitized journal event and return its dict form.

    stable_memory_write is hard-forced to False: this journal is never a stable
    memory write path.
    """
    observed_at = _timestamp_or_now_iso(observed_at)
    kind = event_kind if event_kind in EVENT_KINDS else "action_blocked"
    tier = risk_tier if risk_tier in RISK_TIERS else "high_blocked"
    state = status if status in STATUS_VALUES else "blocked"
    privacy_level = privacy if privacy in PRIVACY_LEVELS else "self_private"

    if isinstance(summary, str):
        summary_items = [summary]
    else:
        summary_items = list(summary or [])
    clean_summary = tuple(s for s in (sanitize_line(item) for item in summary_items[:8]) if s)

    event = AutonomyJournalEvent(
        event_id="pevt-"
        + _hash_json(
            {
                "event_kind": kind,
                "observed_at": observed_at,
                "goal_id": goal_id,
                "action_kind": action_kind,
                "summary": list(clean_summary),
            }
        ),
        event_kind=kind,
        observed_at=observed_at,
        source_module=_safe_str(source_module) or "xinyu_private_ecosystem",
        goal_id=sanitize_line(goal_id, limit=80),
        action_kind=sanitize_line(action_kind, limit=80),
        risk_tier=tier,
        status=state,
        summary=clean_summary,
        evidence_refs=_sanitize_refs(evidence_refs),
        privacy=privacy_level,
        stable_memory_write=False,
    )
    payload = event.to_dict()
    append_private_ecosystem_journal_event(journal_path(root), payload)
    return payload


def read_journal_events(root: Path, *, limit: int | None = None) -> list[dict[str, Any]]:
    lines = read_private_ecosystem_journal_text(journal_path(root)).splitlines()
    events: list[dict[str, Any]] = []
    for line in lines:
        clean = line.strip()
        if not clean:
            continue
        try:
            data = json.loads(clean)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            events.append(data)
    if limit is None:
        return events
    if limit <= 0:
        return []
    return events[-limit:]


def journal_summary(root: Path, *, limit: int = 50) -> dict[str, Any]:
    events = read_journal_events(root, limit=limit)
    kinds: dict[str, int] = {}
    stable_writes = 0
    for event in events:
        key = str(event.get("event_kind", "unknown"))
        kinds[key] = kinds.get(key, 0) + 1
        if bool(event.get("stable_memory_write")):
            stable_writes += 1
    latest = events[-1] if events else {}
    return {
        "total_recent": len(events),
        "event_kind_counts": kinds,
        "stable_memory_write_count": stable_writes,
        "latest_event_kind": str(latest.get("event_kind", "none")),
        "latest_observed_at": str(latest.get("observed_at", "")),
        "latest_goal_id": str(latest.get("goal_id", "")),
        "latest_status": str(latest.get("status", "")),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read XinYu private-ecosystem autonomy journal.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    summary = journal_summary(root, limit=max(1, args.limit))
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"recent_events={summary['total_recent']} latest={summary['latest_event_kind']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
