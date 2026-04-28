from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


STYLE_CORRECTION_MARKERS = (
    "AI味",
    "GPT味",
    "gpt",
    "GPT",
    "不像人",
    "不自然",
    "机械",
    "模板",
    "客服",
    "写作文",
    "分段",
    "端着",
    "用词",
    "中文互联网",
    "红温",
    "白做",
    "默认助手",
    "现成腔",
    "助手腔",
    "滑回",
    "小算",
)

PRODUCT_WORD_MARKERS = (
    "用户",
    "反馈",
    "体验",
    "预期",
    "优化",
    "调整",
    "输出",
    "模型",
    "系统",
    "架构",
    "层面",
    "维度",
    "核心问题",
    "承接",
    "支持",
)

SURFACE_LEAK_WORD_MARKERS = (
    "默认助手",
    "内部判断词",
    "分类词",
    "质量门",
    "语气门禁",
    "滑回",
    "小算",
)


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _entry_id(user_text: str) -> str:
    # Stable enough for de-dup without importing hashing just for a log id.
    total = sum((idx + 1) * ord(ch) for idx, ch in enumerate(user_text))
    return f"voice-{total % 1_000_000:06d}"


def _markers(text: str, markers: tuple[str, ...]) -> list[str]:
    return [marker for marker in markers if marker in text]


def _trim(text: str, limit: int = 160) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _visible_reply_note(reply: str) -> str:
    product_hits = _markers(reply, PRODUCT_WORD_MARKERS)
    leak_hits = _markers(reply, SURFACE_LEAK_WORD_MARKERS)
    if not product_hits and not leak_hits:
        return _trim(reply)
    parts: list[str] = []
    if product_hits:
        parts.append("product/support wording")
    if leak_hits:
        parts.append("internal-diagnosis wording")
    return "bad_example_omitted: contained " + " and ".join(parts) + "; do not imitate."


def _direction_for(user_text: str, reply: str) -> str:
    if _contains_any(user_text, SURFACE_LEAK_WORD_MARKERS) or _contains_any(reply, SURFACE_LEAK_WORD_MARKERS):
        return "不要把内部分类、质量门、失败原因或校准过程搬到表面回复里。"
    if "中文互联网" in user_text or "用词" in user_text:
        return "优先校准中文私聊词感：少写报告词，少写翻译腔，让词落到 owner 的真实语境。"
    if "客服" in user_text or "反馈" in user_text:
        return "关系压力不要写成客服接待或产品反馈处理。"
    if "GPT" in user_text or "AI味" in user_text:
        return "减少默认模型自我诊断和完整解释，让回复从心玉当前姿态出来。"
    if "白做" in user_text or "红温" in user_text:
        return "先承认这是真失望和真上火，不要马上进入技术复盘。"
    if _contains_any(reply, PRODUCT_WORD_MARKERS):
        return "上一句或候选回复仍可能带产品/系统词，需要后续更硬地避开。"
    return "把这次纠正作为中文发声压力记录，后续短批次继续观察。"


def should_record_voice_correction(user_text: str) -> bool:
    return _contains_any(user_text, STYLE_CORRECTION_MARKERS)


def record_voice_correction(
    root: Path,
    *,
    user_text: str,
    reply: str,
    source: str = "runtime",
    recorded_at: str | None = None,
) -> bool:
    if not should_record_voice_correction(user_text):
        return False

    path = root / "memory/self/voice_calibration_log.md"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    entry_id = _entry_id(user_text)
    if f"## {entry_id}" in text:
        return False

    recorded_at = recorded_at or datetime.now().astimezone().isoformat()
    correction_markers = _markers(user_text, STYLE_CORRECTION_MARKERS)
    product_hits = _markers(reply, PRODUCT_WORD_MARKERS)
    entry = f"""

## {entry_id}
- recorded_at: {recorded_at}
- source: {source}
- owner_correction: {_trim(user_text)}
- latest_visible_reply: {_visible_reply_note(reply)}
- correction_markers: {", ".join(correction_markers) or "none"}
- reply_product_word_hits: {", ".join(product_hits) or "none"}
- calibration_direction: {_direction_for(user_text, reply)}
- stable_profile_write: blocked
- next_review: accumulate_with_lived_qq_batches
"""
    if "- none" in text:
        text = text.replace("- none", entry.strip(), 1)
    else:
        text = text.rstrip() + entry
    text = re.sub(r"(?m)^updated_at:\s*.+$", f"updated_at: {recorded_at}", text, count=1)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    try:
        from xinyu_voice_promotion_gate import build_voice_promotion_review

        build_voice_promotion_review(root, evaluated_at=recorded_at)
    except Exception:
        pass
    return True
