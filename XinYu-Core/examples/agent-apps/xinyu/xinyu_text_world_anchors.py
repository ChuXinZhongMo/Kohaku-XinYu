"""Text-only world anchors + light pre-send fact guards.

Goal: stop the model from inventing 周几/日期 when the runtime already knows them.
This is intentionally post-generation and conservative — it rewrites only clear
mismatches, never invents new chat content.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from xinyu_bridge_state_text_time import chinese_weekday_name

_CN_WEEKDAYS = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
# Also catch 周天 / 星期天 as Sunday aliases in user-facing Chinese.
_WEEKDAY_ALIASES = {
    "周一": "周一",
    "星期一": "周一",
    "礼拜一": "周一",
    "周二": "周二",
    "星期二": "周二",
    "礼拜二": "周二",
    "周三": "周三",
    "星期三": "周三",
    "礼拜三": "周三",
    "周四": "周四",
    "星期四": "周四",
    "礼拜四": "周四",
    "周五": "周五",
    "星期五": "周五",
    "礼拜五": "周五",
    "周六": "周六",
    "星期六": "周六",
    "礼拜六": "周六",
    "周日": "周日",
    "周天": "周日",
    "星期日": "周日",
    "星期天": "周日",
    "礼拜日": "周日",
    "礼拜天": "周日",
}

# "今天是周日" / "今天周日" / "今日星期二" / "现在周一"
_TODAY_WEEKDAY_RE = re.compile(
    r"(今天|今日|现在)(?:是|为)?("
    + "|".join(sorted(_WEEKDAY_ALIASES.keys(), key=len, reverse=True))
    + r")"
)
_BARE_WEEKDAY_CLAIM_RE = re.compile(
    r"(?<![上这那每到])("  # avoid 上周日 / 这周一 / 每天周一-ish false hits as best-effort
    + "|".join(sorted((k for k in _WEEKDAY_ALIASES if k.startswith("周")), key=len, reverse=True))
    + r")(?![一二三四五六日天末])"
)


def world_anchor_prompt_lines(*, now: datetime | None = None) -> list[str]:
    """Short hard facts for prompt injection (Chinese companion style)."""
    current = (now or datetime.now().astimezone()).astimezone()
    weekday = chinese_weekday_name(current)
    return [
        "## World Anchors (hard facts — do not re-derive)",
        f"- today_local_date: {current.date().isoformat()}",
        f"- today_local_weekday: {weekday}",
        f"- today_local_hour: {current.hour:02d}",
        f"- timezone: {current.tzinfo}",
        (
            f"- speak_rule: 若提到今天/现在的星期，只能说「{weekday}」。"
            "不要根据记忆或感觉改写周几；owner 纠正时以 owner 为准。"
        ),
    ]


def world_anchor_prompt_block(*, now: datetime | None = None) -> str:
    return "\n".join(world_anchor_prompt_lines(now=now))


def _normalize_weekday_token(token: str) -> str:
    return _WEEKDAY_ALIASES.get(token, token)


def repair_visible_weekday_claims(
    reply: str,
    *,
    now: datetime | None = None,
    user_text: str = "",
) -> dict[str, Any]:
    """Rewrite wrong '今天是X' weekday claims to the runtime weekday.

    Conservative: only touches phrases that claim *today/now* is a weekday.
    Bare weekday mentions without 今天/今日/现在 are left alone (could be about
    plans or past days).
    """
    text = (reply or "").strip()
    if not text:
        return {"reply": text, "changed": False, "notes": ()}

    current = (now or datetime.now().astimezone()).astimezone()
    correct = chinese_weekday_name(current)
    notes: list[str] = []

    def _sub_today(match: re.Match[str]) -> str:
        head = match.group(1)
        claimed = _normalize_weekday_token(match.group(2))
        if claimed == correct:
            return match.group(0)
        notes.append(f"weekday_claim_repaired:{claimed}->{correct}")
        # Prefer short natural phrasing.
        if head in {"今天", "今日"}:
            return f"今天{correct}"
        return f"{head}是{correct}"

    repaired = _TODAY_WEEKDAY_RE.sub(_sub_today, text)

    # If owner is correcting weekday and she still asserts a wrong one with 今天,
    # the regex above already fixed it. Optionally drop apology templates later.

    changed = repaired != text
    return {
        "reply": repaired if changed else text,
        "changed": changed,
        "notes": tuple(notes),
        "correct_weekday": correct,
    }


def apply_text_realism_visible_pass(
    reply: str,
    *,
    now: datetime | None = None,
    user_text: str = "",
) -> dict[str, Any]:
    """Single entry for gateway visible path (post-sanitize)."""
    result = repair_visible_weekday_claims(reply, now=now, user_text=user_text)
    return result
