from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from xinyu_text_variants import readable_markers


RECENT_CONTEXT_REL = Path("memory/context/recent_context.md")
RECENT_CONTEXT_ANCHOR_REL = Path("memory/context/recent_context_runtime_anchor.md")

NEAR_REFERENCE_MARKERS = readable_markers(
    "刚才",
    "刚刚",
    "上次",
    "继续",
    "接着",
    "断在哪",
    "没完",
    "进度",
    "这三件",
    "这三个",
    "哪三件",
    "哪三个",
    "三件事",
    "三个事",
    "这件事",
    "刚才那个",
    "刚才说的",
    "那个呢",
)

UNCERTAIN_REFERENCE_MISS_MARKERS = readable_markers(
    "哪三件",
    "没印象",
    "不记得",
    "你说的是哪段",
    "你指的是哪段",
    "我不知道你说的是哪",
)

PROTECTED_RECENT_ANCHOR_MARKERS = readable_markers(
    "three quick fixes",
    "approved three",
    "这三件",
    "这三个",
    "三件事",
    "三个事",
    "duller",
    "refactor",
    "重构",
    "变笨",
    "恢复最近聊天上下文",
    "recent_context",
    "recent context",
    "learning closed loop",
    "学习闭环",
    "repair loop",
    "修复回路",
    "修复循环",
    "QQ gateway",
    "NapCat",
    "没有QQ",
    "no QQ",
    "Drive E",
    "E盘",
    "current priority",
    "当前优先级",
)

INTERNAL_TO_HUMAN_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("restore recent_context", "恢复最近聊天上下文"),
    ("recent_context", "最近聊天上下文"),
    ("recent context", "最近聊天上下文"),
    ("lower learning closed loop prompt weight", "降低被纠错后的反复提醒"),
    ("learning closed loop prompt weight", "被纠错后的反复提醒"),
    ("learning_closed_loop", "反复修同一类问题的那段"),
    ("learning closed loop", "反复修同一类问题的那段"),
    ("学习闭环提示的权重", "被纠错后的反复提醒"),
    ("学习闭环提示", "反复修复提醒"),
    ("学习闭环", "反复修同一类问题的那段"),
    ("prompt pressure", "被指出说话问题后的压力"),
    ("prompt weight", "提醒分量"),
    ("cool down the repair loop", "别一直围着同一个错误打转"),
    ("repair loop", "反复修同一处"),
    ("修复回路", "反复修同一处"),
    ("修复循环", "反复修同一处"),
    ("runtime presence", "运行状态"),
    ("continuity handoff", "接续记录"),
    ("sidecar admission", "临时上下文取舍"),
    ("sidecar", "临时上下文"),
)

THREE_FIXES_FACTS = "恢复最近聊天上下文、降低被纠错后的反复提醒、别一直围着同一个错误打转"
THREE_FIXES_CHAT_REPLY = "这三件嘛：先把刚才聊到哪接住；你说我不对，我就别反复念叨；还有别一直围着同一个错打转。"
THREE_FIXES_DETAIL_REPLY = "这三个嘛：先把刚才聊到哪接住；你说我不对，我就别反复念叨；还有别一直围着同一个错打转。"


def looks_like_near_reference(text: str) -> bool:
    compact = _compact(text)
    if not compact:
        return False
    return any(_compact(marker) in compact for marker in NEAR_REFERENCE_MARKERS)


def build_owner_continuity_hint(
    root: Path,
    *,
    user_text: str,
    dialogue_tail: list[dict[str, Any]] | None = None,
    max_chars: int = 900,
) -> str:
    if not looks_like_near_reference(user_text):
        return ""

    raw_context = _read_context_sources(root)
    lines: list[str] = [
        "owner-visible continuity hint:",
        "If the owner uses 这/那个/刚才/继续/断在哪, resolve the reference from session tail and these human facts before saying you do not remember.",
    ]

    three_fixes = owner_reference_fallback(root, user_text=user_text)
    if three_fixes:
        lines.append(f"Likely referent for 这三件/这三个: {three_fixes}")

    tail_hint = _dialogue_tail_hint(dialogue_tail or [])
    if tail_hint:
        lines.append(tail_hint)

    for anchor in _humanized_anchor_lines(raw_context):
        if three_fixes and anchor in three_fixes:
            continue
        lines.append(f"Recent anchor: {anchor}")
        if len(lines) >= 6:
            break

    lines.append(
        "Visible wording rule: answer with these facts in ordinary Chinese; do not mention files, prompts, helper labels, gates, state names, or that you read context."
    )
    return _trim("\n".join(lines), max_chars)


def owner_reference_fallback(root: Path, *, user_text: str) -> str:
    compact = _compact(user_text)
    if not any(marker in compact for marker in ("这三件", "这三个", "哪三件", "哪三个", "三件事", "三个事")):
        return ""
    raw_context = _read_context_sources(root).lower()
    has_three = "three quick fixes" in raw_context or "三件" in raw_context or "三个" in raw_context
    has_context = (
        "recent_context" in raw_context
        or "recent context" in raw_context
        or "恢复最近聊天上下文" in raw_context
        or "恢复聊天上下文" in raw_context
    )
    has_pressure = (
        "learning" in raw_context
        or "学习闭环" in raw_context
        or "被纠错后的反复提醒" in raw_context
        or "反复提醒" in raw_context
    )
    has_loop = (
        "repair loop" in raw_context
        or "修复" in raw_context
        or "别一直围着同一个错误打转" in raw_context
        or "同一个错误打转" in raw_context
    )
    if not (has_three and has_context and has_pressure and has_loop):
        return ""
    return THREE_FIXES_FACTS


def repair_owner_reference_miss(root: Path, *, user_text: str, reply: str) -> str:
    if not reply.strip() or not owner_reference_fallback(root, user_text=user_text):
        return ""
    compact_reply = _compact(reply)
    if not any(_compact(marker) in compact_reply for marker in UNCERTAIN_REFERENCE_MISS_MARKERS):
        return ""
    return THREE_FIXES_CHAT_REPLY


def repair_incomplete_three_fix_reply(root: Path, *, user_text: str, reply: str) -> str:
    fallback = owner_reference_fallback(root, user_text=user_text)
    if not reply.strip() or not fallback:
        return ""
    compact_reply = _compact(reply)
    has_context = any(marker in compact_reply for marker in ("上下文", "接着", "连续", "断片"))
    has_pressure = any(marker in compact_reply for marker in ("纠错", "纠正", "反复提醒", "复盘", "道歉", "承诺"))
    has_loop = any(marker in compact_reply for marker in ("围着", "打转", "同一个错误", "同一个毛病", "绕回来"))
    if has_context and has_pressure and has_loop:
        return ""
    return THREE_FIXES_DETAIL_REPLY


def humanize_internal_context_terms(text: str) -> str:
    clean = text
    for before, after in INTERNAL_TO_HUMAN_REPLACEMENTS:
        clean = re.sub(re.escape(before), after, clean, flags=re.IGNORECASE)
    return clean


def extract_protected_recent_anchors(text: str, *, limit: int = 8) -> list[str]:
    anchors: list[str] = []
    seen: set[str] = set()
    for raw_line in _unwrap_content_envelope(text).splitlines():
        line = _plain_line(raw_line.lstrip("-").strip())
        if not line or len(line) < 12:
            continue
        if _is_recent_context_metadata_line(line):
            continue
        if not _is_protected_recent_anchor(line):
            continue
        human = _trim(_plain_line(humanize_internal_context_terms(line)), 260)
        key = _compact(human)
        if human and key not in seen:
            seen.add(key)
            anchors.append(human)
        if len(anchors) >= limit:
            break
    return anchors


def merge_protected_recent_anchors(text: str, anchors: list[str] | tuple[str, ...], *, max_items: int = 8) -> str:
    clean = _unwrap_content_envelope(text).strip()
    if not clean:
        clean = "# Recent Context"
    normalized_anchors: list[str] = []
    seen: set[str] = set()
    for anchor in anchors:
        human = _trim(_plain_line(humanize_internal_context_terms(anchor)), 260)
        key = _compact(human)
        if human and key not in seen:
            seen.add(key)
            normalized_anchors.append(human)
    if not normalized_anchors:
        return clean

    clean = _drop_protected_anchor_lines_outside_anchor_section(clean)
    heading = "## 持续锚点"
    pattern = rf"({re.escape(heading)}\n)(.*?)(?=\n## |\n# |\Z)"
    match = re.search(pattern, clean, flags=re.S)
    if match:
        existing = [
            _plain_line(line.lstrip("-").strip())
            for line in match.group(2).splitlines()
            if line.strip().lstrip().startswith("-")
        ]
        existing = [item for item in existing if item and not _is_recent_context_metadata_line(item)]
        merged = normalized_anchors + existing
    else:
        merged = normalized_anchors

    kept: list[str] = []
    seen.clear()
    for item in merged:
        key = _compact(item)
        if item and key not in seen:
            seen.add(key)
            kept.append(item)
        if len(kept) >= max_items:
            break

    body = "".join(f"- {item}\n" for item in kept)
    if match:
        return clean[: match.start(2)] + body + clean[match.end(2) :].rstrip()

    insert_at = _after_main_heading_index(clean)
    if insert_at >= 0:
        return (clean[:insert_at].rstrip() + f"\n\n{heading}\n{body}" + clean[insert_at:].rstrip()).strip()
    return clean.rstrip() + f"\n\n{heading}\n{body.rstrip()}"


def _read_context_sources(root: Path) -> str:
    parts: list[str] = []
    for rel in (RECENT_CONTEXT_REL, RECENT_CONTEXT_ANCHOR_REL):
        try:
            text = (root / rel).read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        if text.strip():
            parts.append(text)
    return "\n".join(parts)


def _unwrap_content_envelope(text: str) -> str:
    if text.startswith("content:---"):
        return text.removeprefix("content:")
    if text.startswith("content:\n"):
        return text.removeprefix("content:\n")
    if text.startswith("content=---"):
        return text.removeprefix("content=")
    if text.startswith("content=\n"):
        return text.removeprefix("content=\n")
    return text


def _is_protected_recent_anchor(text: str) -> bool:
    compact = _compact(text)
    return any(_compact(marker) in compact for marker in PROTECTED_RECENT_ANCHOR_MARKERS)


def _drop_protected_anchor_lines_outside_anchor_section(text: str) -> str:
    kept: list[str] = []
    in_anchor_section = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            in_anchor_section = stripped == "## 持续锚点"
            kept.append(line)
            continue
        if not in_anchor_section and stripped.lstrip().startswith("-") and _is_protected_recent_anchor(stripped):
            continue
        kept.append(line)
    return "\n".join(kept).strip()


def _is_recent_context_metadata_line(text: str) -> bool:
    lowered = text.strip().lower()
    if lowered.startswith("#"):
        return True
    return lowered.startswith(
        (
            "title:",
            "memory_type:",
            "time_scope:",
            "subject_ids:",
            "protected:",
            "source:",
            "updated_at:",
            "status:",
            "tags:",
        )
    )


def _after_main_heading_index(text: str) -> int:
    match = re.search(r"(?m)^# .+$", text)
    if not match:
        return -1
    next_heading = re.search(r"(?m)^## .+$", text[match.end() :])
    if next_heading:
        return match.end() + next_heading.start()
    return len(text)


def _humanized_anchor_lines(raw_context: str) -> list[str]:
    anchors: list[str] = []
    seen: set[str] = set()
    for raw_line in raw_context.splitlines():
        line = raw_line.strip().lstrip("-").strip()
        if not line or line.startswith("---") or line.startswith("#") or ":" not in line and len(line) < 24:
            continue
        if any(marker in line for marker in ("three quick fixes", "current priority", "最新", "当前优先级", "上下文")):
            human = _plain_line(humanize_internal_context_terms(line))
            if human and human not in seen:
                seen.add(human)
                anchors.append(human)
    return anchors[:4]


def _dialogue_tail_hint(dialogue_tail: list[dict[str, Any]]) -> str:
    cleaned: list[str] = []
    for item in dialogue_tail[-4:]:
        role = _safe_str(item.get("role"))
        content = _safe_str(item.get("content")).strip()
        if not content or role not in {"user", "assistant"}:
            continue
        speaker = "owner" if role == "user" else "XinYu"
        cleaned.append(f"{speaker}: {_trim(_plain_line(content), 90)}")
    if not cleaned:
        return ""
    return "Latest session tail: " + " | ".join(cleaned)


def _plain_line(text: str) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    clean = clean.replace("Current Runtime State", "current state")
    clean = clean.replace("Recent Continuity Anchors", "recent continuity")
    return clean.strip(" -*")


def _trim(text: str, limit: int) -> str:
    clean = text.strip()
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 1)].rstrip() + "…"


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text or "").lower()


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default
