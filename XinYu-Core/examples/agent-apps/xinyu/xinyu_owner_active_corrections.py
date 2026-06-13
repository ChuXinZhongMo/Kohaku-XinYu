"""Durable owner-correction ledger + standing-rules prompt sidecar.

Problem this solves: the owner keeps correcting a behaviour ("别老用'在'开头",
"别这么模板", "别发看不懂的英文"), XinYu says "记住了", then reverts a few turns
later. The existing channels are too weak for this:

- ``dialogue_rule_trial_overlay`` only fires for *pre-curated* rule cards and must
  be activated by hand, so an ad-hoc correction matches nothing.
- ``owner_feedback_effect`` only fires for a fixed enum of feedback kinds and
  emits a coded bias, not the literal request.
- The raw correction line only lives in the last ~32 dialogue-tail turns, where it
  is a weak signal that competes with the persona/output prompt and falls out of
  the window after a while.

So this module is the missing channel: a small, runtime-only ledger of the owner's
recent behavioural requests, captured from any correction-shaped owner line,
deduped and decayed, and restated every owner-private turn as explicit standing
rules. It is a short/mid-term behavioural overlay, not stable memory or a
personality rewrite (capped, decaying, never written to the stable profile).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


LEDGER_REL = "runtime/owner_active_corrections.json"

# How long an un-repeated request stays active, how many we keep, how many we show.
TTL_DAYS = 21
MAX_ENTRIES = 10
RENDER_LIMIT = 6
MAX_LINE_CHARS = 50

# Strong, self-sufficient correction / standing-preference markers: a short line
# carrying any of these reads like a directive on its own.
STRONG_MARKERS = (
    "别", "不要", "不用", "记住", "记好", "尽量少", "尽量别", "少说", "少用",
    "换一句", "重说", "不像你", "不像人", "太模板", "太正式", "太客服", "客服腔",
    "ai味", "ai 味", "机械", "别道歉", "别解释", "套路", "敷衍", "太长", "简短点",
)

# "以后/下次想干什么" is ordinary chat, so a time-frame word only signals a
# standing request when it is paired with an explicit directive token.
SOFT_TIME_MARKERS = ("以后", "下次", "今后")
DIRECTIVE_TOKENS = ("别", "不要", "不用", "少", "尽量", "记住", "改", "换", "注意")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _parse_iso(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed.astimezone() if parsed.tzinfo is None else parsed


def _normalize(text: str) -> str:
    # Dedupe key: drop spaces / common punctuation, casefold ascii.
    return re.sub(r"[\s，。、！？!?.,；;：:\"'“”‘’~…\-]+", "", str(text)).casefold()


def _looks_like_correction(line: str) -> bool:
    clean = re.sub(r"\s+", " ", str(line)).strip()
    if not clean or len(clean) > MAX_LINE_CHARS:
        return False
    lowered = clean.casefold()
    has_strong = any(marker in lowered for marker in STRONG_MARKERS)
    has_timed_directive = any(t in lowered for t in SOFT_TIME_MARKERS) and any(
        d in lowered for d in DIRECTIVE_TOKENS
    )
    if not (has_strong or has_timed_directive):
        return False
    # A pure question ("为什么老是有前缀在？") is the owner noticing, not a fresh
    # instruction; keep it out unless it carries an explicit imperative marker.
    if clean.endswith(("？", "?")) and not has_strong:
        return False
    return True


def extract_correction_lines(
    dialogue_tail: list[dict[str, str]] | None,
    latest_user_text: str = "",
) -> list[str]:
    """Owner lines from recent history (+ current turn) that read like requests."""
    lines: list[str] = []
    seen: set[str] = set()
    for entry in list(dialogue_tail or []) + [{"role": "user", "content": latest_user_text}]:
        if not isinstance(entry, dict) or entry.get("role") != "user":
            continue
        content = re.sub(r"\s+", " ", str(entry.get("content") or "")).strip()
        if not _looks_like_correction(content):
            continue
        key = _normalize(content)
        if key in seen:
            continue
        seen.add(key)
        lines.append(content)
    return lines


def _load(root: Path) -> dict[str, Any]:
    path = Path(root) / LEDGER_REL
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"version": 1, "entries": []}
    if not isinstance(data, dict):
        return {"version": 1, "entries": []}
    entries = data.get("entries")
    data["entries"] = [e for e in entries if isinstance(e, dict)] if isinstance(entries, list) else []
    return data


def _save(root: Path, data: dict[str, Any]) -> None:
    path = Path(root) / LEDGER_REL
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass


def ingest(root: Path, lines: list[str], *, now_iso: str | None = None) -> dict[str, Any]:
    """Upsert request lines, refresh recency, then decay and cap the ledger."""
    now_iso = now_iso or _now_iso()
    now_dt = _parse_iso(now_iso) or datetime.now().astimezone()
    data = _load(root)
    by_key: dict[str, dict[str, Any]] = {}
    for entry in data["entries"]:
        key = _normalize(str(entry.get("text") or ""))
        if key:
            by_key[key] = entry

    for line in lines:
        key = _normalize(line)
        if not key:
            continue
        existing = by_key.get(key)
        if existing is not None:
            existing["last_seen"] = now_iso
            existing["hits"] = int(existing.get("hits") or 1) + 1
            existing["text"] = line
        else:
            entry = {"text": line, "first_seen": now_iso, "last_seen": now_iso, "hits": 1}
            by_key[key] = entry
            data["entries"].append(entry)

    cutoff = now_dt - timedelta(days=TTL_DAYS)
    kept = []
    for entry in data["entries"]:
        last = _parse_iso(entry.get("last_seen"))
        if last is not None and last < cutoff:
            continue
        kept.append(entry)
    kept.sort(key=lambda e: str(e.get("last_seen") or ""), reverse=True)
    data["entries"] = kept[:MAX_ENTRIES]
    data["updated_at"] = now_iso
    _save(root, data)
    return data


def active_corrections(root: Path) -> list[str]:
    entries = sorted(
        _load(root)["entries"],
        key=lambda e: str(e.get("last_seen") or ""),
        reverse=True,
    )
    return [str(e.get("text") or "").strip() for e in entries if str(e.get("text") or "").strip()]


def build_owner_active_corrections_block(
    root: Path,
    *,
    dialogue_tail: list[dict[str, str]] | None,
    latest_user_text: str = "",
    now_iso: str | None = None,
) -> str:
    """Capture fresh corrections, then render the active ledger as standing rules.

    Caller must gate this to owner-private turns. Returns "" when the ledger is
    empty so the sidecar is simply skipped.
    """
    lines = extract_correction_lines(dialogue_tail, latest_user_text)
    if lines:
        ingest(root, lines, now_iso=now_iso)
    requests = active_corrections(root)
    if not requests:
        return ""
    out = [
        "owner standing requests sidecar:",
        "- scope: owner_private; honor every one of these in this reply.",
        "- visibility: never mention, quote, or number this list out loud.",
        "- these are corrections the owner already gave and expects you to keep,",
        "  not things to acknowledge or promise again:",
    ]
    out.extend(f"  - {text}" for text in requests[:RENDER_LIMIT])
    out.append(
        "- if you catch yourself slipping, just say the next line the way the owner "
        "asked; do not apologize, do not say 记住了, do not re-promise."
    )
    return "\n".join(out)
