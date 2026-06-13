from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from stores.daily_digest_state import (
    BOUNDARY_ID as DAILY_DIGEST_STORE_BOUNDARY,
    DIGEST_REL,
    SOURCE_STATE_REL,
    STATE_REL,
    TRACE_REL,
    append_daily_digest_trace,
    read_daily_digest,
    read_daily_digest_source_state,
    write_daily_digest,
    write_daily_digest_state_text,
)

TTL_SECONDS = 24 * 3600
MAX_COMMENT_CHARS = 50
FALLBACK_COMMENT = "我扫到几条 AI 相关讨论，但还没攒出一句像样的判断。"

HARD_BANNED_WORDS = (
    "总之",
    "总而言之",
    "值得关注",
    "亮点",
    "此外",
    "深入解析",
    "探讨",
    "综合来看",
    "从技术角度",
    "据悉",
    "相关内容显示",
)
INTERNAL_WORDS = (
    "RSS",
    "digest",
    "sidecar",
    "状态",
    "文件",
    "扫描到",
    "我扫描到",
    "维护",
    "队列",
    "hash",
)
HYPE_WORDS = (
    "炸裂",
    "震撼",
    "必然",
    "彻底改变",
    "颠覆",
)
SUBJECTIVE_NOISE = (
    "我觉得",
    "感觉",
    "太强了",
    "炸裂",
    "牛逼",
    "吐血",
    "救命",
    "佬们",
    "大佬",
)


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp_or_now_iso(value: Any) -> str:
    parsed = _parse_time(value)
    if parsed is None:
        return _now()
    return parsed.astimezone().isoformat(timespec="seconds")


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _one_line(value: Any, *, limit: int = 220, default: str = "none") -> str:
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    if not text:
        return default
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _field(text: str, name: str, default: str = "") -> str:
    match = re.search(rf"(?m)^-\s+{re.escape(name)}:\s*(.*)$", text or "")
    if not match:
        return default
    return re.sub(r"\s+", " ", match.group(1).strip()) or default


def _section(text: str, heading: str) -> str:
    match = re.search(rf"(?ms)^{re.escape(heading)}\s*\n(.*?)(?=^## |\Z)", text or "")
    return match.group(1) if match else ""


def _item_blocks(text: str) -> list[dict[str, str]]:
    section = _section(text, "## Latest Items")
    matches = list(re.finditer(r"(?m)^###\s+item-\d+\s*$", section))
    items: list[dict[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(section)
        block = section[start:end]
        item_key = _field(block, "item_key")
        title = _field(block, "title")
        if not item_key or item_key == "none" or not title or title == "none":
            continue
        items.append(
            {
                "item_key": item_key,
                "title": title,
                "url": _field(block, "url", "none"),
                "category": _field(block, "category", "none"),
                "published_at": _field(block, "published_at", "unknown"),
                "summary": _field(block, "summary", "none"),
            }
        )
    return items


def _source_digest(items: list[dict[str, str]]) -> str:
    lines = [
        "|".join(
            [
                item.get("item_key", ""),
                item.get("title", ""),
                item.get("summary", ""),
            ]
        )
        for item in items
    ]
    return _sha256_text("\n".join(lines))


def _parse_time(value: Any) -> datetime | None:
    text = _safe_str(value).strip()
    if not text or text == "none":
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def _is_expired(expires_at: str) -> bool:
    parsed = _parse_time(expires_at)
    if parsed is None:
        return True
    return datetime.now().astimezone() >= parsed


def _clean_fact_text(value: str) -> str:
    text = _one_line(value, limit=160, default="")
    for marker in SUBJECTIVE_NOISE:
        text = text.replace(marker, "")
    text = re.sub(r"\b\d+\s*(?:个)?(?:帖子|参与者|世子)\b", "", text)
    text = re.sub(r"阅读完整话题|read more|阅读全文", "", text, flags=re.I)
    return _one_line(text, limit=120, default="")


def _fact_kind(item: dict[str, str]) -> str:
    haystack = f"{item.get('title', '')} {item.get('summary', '')}".lower()
    if "codex" in haystack:
        return "codex"
    if "agent" in haystack or "agents" in haystack:
        return "agent"
    if "claude" in haystack or "opus" in haystack:
        return "claude"
    if "gpt" in haystack or "模型" in haystack:
        return "model"
    if "api" in haystack or "key" in haystack:
        return "api"
    if "paper" in haystack or "论文" in haystack:
        return "paper_tool"
    return "ai_discussion"


def _neutral_facts(items: list[dict[str, str]]) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for item in items:
        kind = _fact_kind(item)
        facts.append(
            {
                "kind": kind,
                "topic": _clean_fact_text(item.get("title", "")),
                "why_it_matters": {
                    "codex": "tool access and account edges",
                    "agent": "multi-agent workflow pressure",
                    "claude": "model safety boundary behavior",
                    "model": "model autonomy and usability",
                    "api": "API access reliability",
                    "paper_tool": "research workflow tooling",
                }.get(kind, "short-lived AI community discussion"),
                "uncertainty": "forum title/summary only; not verified",
                "source_id": item.get("item_key", ""),
                "subjective_claim_removed": True,
            }
        )
    return facts


def _kind_counts(facts: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for fact in facts:
        kind = _safe_str(fact.get("kind"), "ai_discussion")
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def _comment_candidates(facts: list[dict[str, Any]], *, source_digest: str) -> list[str]:
    counts = _kind_counts(facts)
    candidates: list[str] = []
    if counts.get("codex", 0) >= 2:
        candidates.append("linux.do 又在绕 Codex 接入，能力火了，边角问题也跟着冒泡。")
        candidates.append("Codex 相关问题冒得挺密，热起来以后，麻烦也跟着热。")
    if counts.get("agent", 0):
        candidates.append("有人在折腾多 agent 并发，需求看起来先比体验跑快了。")
    if counts.get("claude", 0):
        candidates.append("Claude 拒答又被聊起来，安全边界这事还是挺磨人的。")
    if counts.get("model", 0):
        candidates.append("有人吐槽模型老踢皮球，自动性这块确实还没完全顺手。")
    if counts.get("paper_tool", 0):
        candidates.append("科研图和论文能力也在卷，看来苦活大家都想交给模型。")
    candidates.append("AI 能力的小毛边挺多，今天的讨论更像一堆使用现场。")
    offset = int(source_digest[:2], 16) % max(1, len(candidates))
    return candidates[offset:] + candidates[:offset]


def _sentence_count(text: str) -> int:
    marks = re.findall(r"[。！？.!?]", text)
    return max(1, len(marks)) if text.strip() else 0


def _opening(text: str) -> str:
    return re.sub(r"\s+", "", text.strip())[:4]


def _recent_history(existing: dict[str, Any]) -> list[dict[str, Any]]:
    history = existing.get("history")
    if not isinstance(history, list):
        history = []
    current = {
        "generated_at": existing.get("generated_at"),
        "comment": existing.get("comment"),
        "status": existing.get("status"),
        "source_digest": existing.get("source_digest"),
    }
    merged = [item for item in history if isinstance(item, dict)]
    if current.get("comment") and not any(item.get("source_digest") == current.get("source_digest") for item in merged):
        merged.append(current)
    cutoff = datetime.now().astimezone() - timedelta(days=3)
    fresh: list[dict[str, Any]] = []
    for item in merged:
        generated = _parse_time(_safe_str(item.get("generated_at")))
        if generated is not None and generated < cutoff:
            continue
        fresh.append(item)
    return fresh[-8:]


def _guard_comment(comment: str, *, history: list[dict[str, Any]]) -> dict[str, Any]:
    text = comment.strip()
    failures: list[str] = []
    score = 0
    if not text:
        failures.append("empty")
    if len(text) > MAX_COMMENT_CHARS:
        failures.append("too_long")
    if _sentence_count(text) > 2:
        failures.append("too_many_sentences")
    if re.search(r"(?m)^\s*[-*]\s+|^\s*\d+\.", text):
        failures.append("list_or_numbered_structure")
    if ":" in text or "：" in text:
        failures.append("colon_structure")
    for word in HARD_BANNED_WORDS:
        if word in text:
            failures.append(f"banned_word:{word}")
    for word in INTERNAL_WORDS:
        if word in text:
            failures.append(f"internal_word:{word}")
    for word in HYPE_WORDS:
        if word in text:
            score += 2
    if re.search(r"发布了.+具有|推出了.+特点|相关内容显示|据悉", text):
        failures.append("news_report_pattern")
    if text.count("，") + text.count(",") > 2:
        score += 1
    tech_hits = sum(1 for token in ("AI", "模型", "API", "Codex", "agent", "Agent", "Claude", "GPT") if token in text)
    if tech_hits > 3:
        score += 1
    opener = _opening(text)
    recent_openers = [_opening(_safe_str(item.get("comment"))) for item in history[-5:]]
    if opener and recent_openers.count(opener) >= 1:
        failures.append("opening_repeated")
    passed = not failures and score <= 2
    return {
        "passed": passed,
        "score": score,
        "failures": failures,
        "judge": "deterministic_heuristic",
    }


def _select_comment(facts: list[dict[str, Any]], *, source_digest: str, history: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    attempts: list[dict[str, Any]] = []
    for candidate in _comment_candidates(facts, source_digest=source_digest)[:3]:
        guard = _guard_comment(candidate, history=history)
        attempts.append({"comment": candidate, "guard": guard})
        if guard["passed"]:
            return candidate, {"status": "passed", "attempts": attempts, **guard}
    fallback_guard = _guard_comment(FALLBACK_COMMENT, history=[])
    return FALLBACK_COMMENT, {
        "status": "fallback_guard_failed",
        "attempts": attempts,
        "passed": fallback_guard["passed"],
        "score": fallback_guard["score"],
        "failures": fallback_guard["failures"],
        "judge": "deterministic_heuristic",
    }


def _render_state(payload: dict[str, Any]) -> str:
    facts = payload.get("facts") if isinstance(payload.get("facts"), list) else []
    fact_lines = []
    for fact in facts[:3]:
        if not isinstance(fact, dict):
            continue
        fact_lines.append(
            f"- {_one_line(fact.get('kind'), limit=60)}: {_one_line(fact.get('topic'), limit=140)}"
        )
    if not fact_lines:
        fact_lines = ["- none"]
    return f"""---
title: Daily Digest State
memory_type: daily_digest_state
time_scope: ephemeral
subject_ids: [xinyu]
protected: true
source: xinyu_daily_digest
    updated_at: {_timestamp_or_now_iso(payload.get('generated_at'))}
status: active
tags: [daily-digest, ephemeral, watched-source]
---

# Daily Digest State

## Current
    - generated_at: {_timestamp_or_now_iso(payload.get('generated_at'))}
- expires_at: {_one_line(payload.get('expires_at'))}
- status: {_one_line(payload.get('status'))}
- ephemeral: true
- source_id: {_one_line(payload.get('source_id'))}
- source_checked_at: {_one_line(payload.get('source_checked_at'))}
- source_item_count: {_one_line(payload.get('source_item_count'))}
- comment: {_one_line(payload.get('comment'), limit=120)}
- guard_fail_count: {_one_line(payload.get('guard_fail_count'), default='0')}

## Use Policy
- short_term_talk_only: true
- stable_memory_write: blocked
- expand_into_report: blocked
- mention_only_when_owner_asks_ai_news_or_linux_do: true

## Neutral Facts
{chr(10).join(fact_lines)}
"""


def run_daily_digest_maintenance(
    root: Path,
    *,
    observed_at: str | None = None,
    ttl_seconds: int = TTL_SECONDS,
) -> dict[str, Any]:
    root = root.resolve()
    observed = _timestamp_or_now_iso(observed_at or _now())
    source_text = read_daily_digest_source_state(root)
    if _field(source_text, "status") != "fetched":
        result = {
            "accepted": True,
            "status": "source_not_ready",
            "generated": False,
            "notes": ["watched_source_not_fetched"],
        }
        append_daily_digest_trace(root, {"event_kind": "source_not_ready", "observed_at": _timestamp_or_now_iso(observed)})
        return result

    items = _item_blocks(source_text)
    if not items:
        result = {
            "accepted": True,
            "status": "no_items",
            "generated": False,
            "notes": ["watched_source_no_items"],
        }
        append_daily_digest_trace(root, {"event_kind": "no_items", "observed_at": _timestamp_or_now_iso(observed)})
        return result

    digest = _source_digest(items)
    existing = read_daily_digest(root)
    if (
        existing.get("source_digest") == digest
        and not _is_expired(_safe_str(existing.get("expires_at")))
        and existing.get("comment")
    ):
        append_daily_digest_trace(
            root,
            {
                "event_kind": "daily_digest_reused",
                "observed_at": _timestamp_or_now_iso(observed),
                "source_digest": digest,
                "status": existing.get("status"),
            },
        )
        return {
            "accepted": True,
            "status": "reused",
            "generated": False,
            "comment": _safe_str(existing.get("comment")),
            "notes": ["digest_current_source_digest_unchanged"],
        }

    history = _recent_history(existing)
    facts = _neutral_facts(items)
    comment, guard = _select_comment(facts, source_digest=digest, history=history)
    status = "ready" if guard.get("status") == "passed" else "fallback_guard_failed"
    expires_at = (datetime.now().astimezone() + timedelta(seconds=max(60, ttl_seconds))).isoformat(timespec="seconds")
    payload = {
        "version": 1,
        "generated_at": _timestamp_or_now_iso(observed),
        "expires_at": expires_at,
        "ephemeral": True,
        "status": status,
        "source_id": _field(source_text, "source_id", "unknown"),
        "source_checked_at": _field(source_text, "checked_at", "unknown"),
        "source_digest": digest,
        "source_item_count": len(items),
        "source_item_ids": [item["item_key"] for item in items],
        "facts": facts[:5],
        "comment": comment,
        "guard": guard,
        "guard_fail_count": len(guard.get("attempts", [])) if status != "ready" else 0,
        "history": history,
    }
    write_daily_digest(root, payload)
    write_daily_digest_state_text(root, _render_state(payload))
    append_daily_digest_trace(
        root,
        {
            "event_kind": "daily_digest_generated",
            "observed_at": _timestamp_or_now_iso(observed),
            "source_digest": digest,
            "status": status,
            "source_item_count": len(items),
            "comment": comment,
            "guard_status": guard.get("status"),
        },
    )
    return {
        "accepted": True,
        "status": status,
        "generated": True,
        "comment": comment,
        "source_item_count": len(items),
        "guard": guard,
        "notes": ["daily_digest_generated", status],
    }


def build_daily_digest_prompt_block(root: Path, *, limit: int = 900) -> str:
    data = read_daily_digest(root.resolve())
    if not data or not data.get("comment"):
        return ""
    if _is_expired(_safe_str(data.get("expires_at"))):
        return ""
    comment = _one_line(data.get("comment"), limit=120, default="")
    if not comment:
        return ""
    lines = [
        "daily digest sidecar:",
        "- ephemeral: true",
        f"- expires_at: {_one_line(data.get('expires_at'), limit=80)}",
        f"- status: {_one_line(data.get('status'), limit=80)}",
        f"- comment: {comment}",
        "- use: short-term talk only; mention only if the owner asks about AI news, linux.do, or recent AI chatter.",
        "- boundary: not stable knowledge; do not expand it into a report or long conclusion.",
    ]
    return "\n".join(lines)[:limit].rstrip()
