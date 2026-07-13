"""Owner-private autonomous share gate for the XinYu Private Ecosystem.

This is the ONLY path by which the private ecosystem may proactively reach the
owner. It enforces dossier section 7.2:

  * explicit grant (enabled) and not paused (kill switch)
  * owner-private QQ channel only (never group / non-owner / public / third party)
  * daily rate limit, cooldown, quiet hours
  * max message length
  * dedupe by dedupe_key
  * privacy filter (no raw paths, tokens, cookies, secrets, raw owner text,
    unreviewed sensitive memory)

It never bypasses the QQ outbox claim/ack semantics — it enqueues through the
existing owner-private outbox helper.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping

from stores.state_service import append_jsonl, atomic_write_text, read_json

from xinyu_private_ecosystem_grants import load_grants, share_grant
from xinyu_qq_outbox import enqueue_owner_qq_outbox_message

SHARE_VERSION = 1

LEDGER_REL = Path("runtime/private_ecosystem/owner_private_share_ledger.jsonl")
STATE_MD_REL = Path("memory/context/private_ecosystem_owner_share_state.md")
QQ_CONFIG_REL = Path("xinyu_qq_gateway.config.json")

ALLOWED_KINDS = frozenset(
    {
        "discovery",
        "joy_share",
        "experiment_result",
        "self_reflection",
        "needs_owner_attention",
        "blocked_need",
    }
)

DISALLOWED_CHANNELS = frozenset(
    {"group", "public", "email", "third_party", "non_owner", "broadcast"}
)

_SECRET_RE = re.compile(
    r"(?i)\b(?:authorization|api[_-]?key|token|password|secret|cookie)\s*[:=]\s*[^\s<>'\"]+"
)
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}")
_SK_RE = re.compile(r"(?i)\bsk-[a-z0-9_-]{12,}")
_PATH_RE = re.compile(r"(?i)(?:[a-z]:\\|/users/|/home/|\\\\)[^\s<>'\"]+")
_LONGDIGIT_RE = re.compile(r"\b\d{12,}\b")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _safe_str(value: Any) -> str:
    return "" if value is None else str(value)


def _parse_dt(value: Any) -> datetime | None:
    text = _safe_str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def _as_int(value: Any, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def privacy_filter(value: Any, *, limit: int = 800) -> tuple[str, list[str], bool]:
    """Return (clean_text, flags, hard_blocked).

    Secrets / local paths / long-digit identifiers are redacted (soft). The
    presence of any of those is flagged. ``hard_blocked`` is reserved for
    content the filter must refuse outright rather than redact.
    """
    raw = re.sub(r"\s+", " ", _safe_str(value)).strip()
    flags: list[str] = []
    text = raw
    if _SECRET_RE.search(text) or _BEARER_RE.search(text) or _SK_RE.search(text):
        flags.append("secret_redacted")
    text = _SECRET_RE.sub("<secret>", text)
    text = _BEARER_RE.sub("<secret>", text)
    text = _SK_RE.sub("<secret>", text)
    if _PATH_RE.search(text):
        flags.append("local_path_redacted")
    text = _PATH_RE.sub("<local_path>", text)
    if _LONGDIGIT_RE.search(text):
        flags.append("identifier_redacted")
    text = _LONGDIGIT_RE.sub("<id>", text)
    if len(text) > limit:
        text = text[: max(0, limit - 3)].rstrip() + "..."
    return text, flags, False


def _owner_user_id(root: Path) -> str:
    raw = read_json(root / QQ_CONFIG_REL, default=None)
    if not isinstance(raw, dict):
        return ""
    for key in ("owner_user_ids", "whitelist_user_ids"):
        value = raw.get(key)
        candidates = value if isinstance(value, list) else [value]
        for item in candidates:
            user_id = _safe_str(item).strip()
            if user_id and user_id.lower() != "none":
                return user_id
    return ""


def _in_quiet_hours(now: datetime, quiet_hours: str) -> bool:
    text = _safe_str(quiet_hours).strip()
    if not text or "-" not in text:
        return False
    try:
        start_s, end_s = text.split("-", 1)
        sh, sm = (int(p) for p in start_s.strip().split(":", 1))
        eh, em = (int(p) for p in end_s.strip().split(":", 1))
    except (ValueError, TypeError):
        return False
    minute = now.hour * 60 + now.minute
    start = sh * 60 + sm
    end = eh * 60 + em
    if start == end:
        return False
    if start < end:
        return start <= minute < end
    # wraps past midnight
    return minute >= start or minute < end


def _read_ledger(root: Path) -> list[dict[str, Any]]:
    path = root / LEDGER_REL
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for line in lines:
        clean = line.strip()
        if not clean:
            continue
        try:
            data = json.loads(clean)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            out.append(data)
    return out


def _ledger_window(rows: list[dict[str, Any]], now: datetime, *, hours: int = 24) -> list[dict[str, Any]]:
    cutoff = now - timedelta(hours=hours)
    recent: list[dict[str, Any]] = []
    for row in rows:
        ts = _parse_dt(row.get("evaluated_at"))
        if ts is None or ts >= cutoff:
            recent.append(row)
    return recent


def _build_message(candidate: Mapping[str, Any], *, max_chars: int) -> tuple[str, list[str]]:
    summary = _safe_str(candidate.get("summary") or candidate.get("reason"))
    question = _safe_str(candidate.get("concrete_question"))
    combined = summary
    if question:
        combined = f"{summary}\n{question}".strip()
    return privacy_filter(combined, limit=max_chars)[:2]


def evaluate_and_maybe_queue(
    root: Path,
    *,
    candidate: Mapping[str, Any],
    grants: Mapping[str, Any] | None = None,
    evaluated_at: str | None = None,
    allow_send: bool = True,
) -> dict[str, Any]:
    """Evaluate one owner-private share candidate against all gates.

    Returns a sanitized dict. ``queued`` is True only when an owner-private QQ
    message was actually enqueued.
    """
    root = Path(root)
    evaluated_at = evaluated_at or _now_iso()
    now = _parse_dt(evaluated_at) or datetime.now().astimezone()
    if grants is None:
        grants = load_grants(root)
    section = share_grant(grants)

    daily_limit = max(0, min(8, _as_int(section.get("daily_limit"), 8)))
    cooldown_minutes = max(0, _as_int(section.get("cooldown_minutes"), 30))
    max_chars = max(1, min(800, _as_int(section.get("max_message_chars"), 800)))
    quiet_hours = _safe_str(section.get("quiet_hours")) or "00:00-06:00"

    rows = _read_ledger(root)
    window = _ledger_window(rows, now, hours=24)
    queued_today = sum(1 for row in window if bool(row.get("queued")))
    last_queued = max(
        (ts for ts in (_parse_dt(row.get("evaluated_at")) for row in rows if bool(row.get("queued"))) if ts),
        default=None,
    )
    cooldown_remaining = 0
    if last_queued is not None and cooldown_minutes > 0:
        elapsed = (now - last_queued).total_seconds() / 60.0
        cooldown_remaining = max(0, int(round(cooldown_minutes - elapsed)))
    daily_remaining = max(0, daily_limit - queued_today)

    kind = _safe_str(candidate.get("kind")) or "self_reflection"
    channel = _safe_str(candidate.get("channel")).lower()
    dedupe_key = _safe_str(candidate.get("dedupe_key")) or hashlib.sha256(
        json.dumps(candidate.get("reason", ""), default=str).encode("utf-8")
    ).hexdigest()[:16]

    blocks: list[str] = []
    if not bool(section.get("enabled")):
        blocks.append("share_grant_disabled")
    if bool(section.get("paused")):
        blocks.append("share_paused")
    if kind not in ALLOWED_KINDS:
        blocks.append("share_kind_not_allowed")
    if channel in DISALLOWED_CHANNELS:
        blocks.append("non_owner_channel_blocked")
    if channel and channel != "owner_private":
        blocks.append("non_owner_channel_blocked")

    owner_id = _owner_user_id(root)
    if not owner_id:
        blocks.append("owner_target_missing")

    message, privacy_flags = _build_message(candidate, max_chars=max_chars)
    if not message.strip():
        blocks.append("message_empty")
    if bool(candidate.get("contains_unreviewed_sensitive_memory")) or bool(candidate.get("owner_raw_text")):
        blocks.append("sensitive_content_blocked")

    # Dedupe against already-queued findings (rolling 24h).
    if any(_safe_str(row.get("dedupe_key")) == dedupe_key and bool(row.get("queued")) for row in window):
        blocks.append("duplicate_finding")

    if _in_quiet_hours(now, quiet_hours) and not bool(section.get("quiet_hours_override")):
        blocks.append("quiet_hours")
    if daily_remaining <= 0:
        blocks.append("daily_budget_exhausted")
    if cooldown_remaining > 0:
        blocks.append("cooldown_active")

    allowed = not blocks
    queued = False
    delivery_level = "hold"
    outbox_notes: list[str] = []
    message_hash = "sha256:" + hashlib.sha256(message.encode("utf-8", errors="replace")).hexdigest()[:16] if message else "none"

    if allowed and allow_send:
        result = enqueue_owner_qq_outbox_message(
            root,
            message=message,
            source="xinyu_private_ecosystem_share",
            dedupe_key=f"pe-share-{dedupe_key}",
            metadata={
                "private_ecosystem_share": True,
                "share_kind": kind,
                "is_owner_user": True,
                "message_type": "private",
            },
        )
        queued = bool(result.get("queued"))
        outbox_notes = [str(n) for n in (result.get("notes") or [])][:6]
        delivery_level = "send_owner_private" if queued else "hold"
        if not queued and "duplicate" in " ".join(outbox_notes).lower():
            blocks.append("outbox_duplicate")
    elif allowed and not allow_send:
        delivery_level = "queue_owner_private"  # would queue, but caller asked to hold sends

    request_id = "share-" + hashlib.sha256(
        json.dumps({"dedupe_key": dedupe_key, "evaluated_at": evaluated_at}, default=str).encode("utf-8")
    ).hexdigest()[:16]

    ledger_row = {
        "version": SHARE_VERSION,
        "request_id": request_id,
        "evaluated_at": evaluated_at,
        "kind": kind,
        "channel": "owner_private",
        "dedupe_key": dedupe_key,
        "allowed": allowed,
        "queued": queued,
        "delivery_level": delivery_level,
        "blocks": blocks,
        "privacy_flags": privacy_flags,
        "message_hash": message_hash,
        "daily_remaining": daily_remaining - (1 if queued else 0),
        "cooldown_minutes": cooldown_minutes,
    }
    append_jsonl(root / LEDGER_REL, ledger_row)
    _write_state_markdown(root, ledger_row, section, evaluated_at=evaluated_at)

    return {
        "prepared": True,
        "ok": True,
        "request_id": request_id,
        "kind": kind,
        "channel": "owner_private",
        "allowed": allowed,
        "queued": queued,
        "delivery_level": delivery_level,
        "reason": blocks[0] if blocks else ("queued_owner_private" if queued else "ready_held"),
        "blocks": blocks,
        "privacy_flags": privacy_flags,
        "message_hash": message_hash,
        "owner_target_resolved": bool(owner_id),
        "daily_remaining": max(0, daily_remaining - (1 if queued else 0)),
        "daily_limit": daily_limit,
        "cooldown_remaining_minutes": cooldown_remaining,
        "cooldown_minutes": cooldown_minutes,
        "quiet_hours": quiet_hours,
        "paused": bool(section.get("paused")),
        "enabled": bool(section.get("enabled")),
        "outbox_notes": outbox_notes,
    }


def _write_state_markdown(
    root: Path, ledger_row: Mapping[str, Any], section: Mapping[str, Any], *, evaluated_at: str
) -> None:
    lines = [
        "---",
        "memory_type: private_ecosystem_owner_share_state",
        "protected: true",
        "source: xinyu_owner_private_share",
        f"updated_at: {evaluated_at}",
        "status: active",
        "tags: [private_ecosystem, owner_private_share, sanitized]",
        "---",
        "",
        "# XinYu Owner-Private Autonomous Share State",
        "",
        f"- enabled: {str(bool(section.get('enabled'))).lower()}",
        f"- paused: {str(bool(section.get('paused'))).lower()}",
        f"- last_delivery_level: {ledger_row.get('delivery_level', 'none')}",
        f"- last_allowed: {str(bool(ledger_row.get('allowed'))).lower()}",
        f"- last_queued: {str(bool(ledger_row.get('queued'))).lower()}",
        f"- last_block_reasons: {','.join(ledger_row.get('blocks', [])) or 'none'}",
        f"- daily_remaining: {ledger_row.get('daily_remaining', 0)}",
        f"- cooldown_minutes: {ledger_row.get('cooldown_minutes', 0)}",
        f"- message_hash: {ledger_row.get('message_hash', 'none')}",
        "- raw_owner_text_in_state: false",
        "- visible_message_text_in_state: false",
        "- channel: owner_private_only",
        "",
        "## Boundaries",
        "",
        "- owner-private QQ message to Atimea only; never group / public / third party.",
        "- secrets, local paths, and long identifiers are redacted before send.",
        "- a paused grant is an immediate kill switch.",
    ]
    atomic_write_text(root / STATE_MD_REL, "\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate one owner-private share candidate.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--evaluated-at", default="")
    parser.add_argument("--kind", default="self_reflection")
    parser.add_argument("--summary", default="")
    parser.add_argument("--dedupe-key", default="")
    parser.add_argument("--no-send", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    candidate = {
        "kind": args.kind,
        "summary": args.summary or "private ecosystem reflection",
        "dedupe_key": args.dedupe_key or "",
    }
    result = evaluate_and_maybe_queue(
        root,
        candidate=candidate,
        evaluated_at=args.evaluated_at or None,
        allow_send=not args.no_send,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"delivery={result['delivery_level']} queued={result['queued']} reason={result['reason']}")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
