from __future__ import annotations


LEGACY_MOJIBAKE_ENCODINGS = ("gbk", "gb18030", "cp936")

COMMON_CJK_CHARS = (
    "中文学习资料报告记忆人格声音情绪生活不是不要说话"
    "用户主人客户关系问题回答系统文件计划现在知道真实"
    "修复阶段关键来源搜索研究对话自然机械模板知识"
    "能力边界内容方式结果整理摘要主题经验具体"
)

LEGACY_MOJIBAKE_FRAGMENTS = (
    "\u951b",
    "\u9286",
    "\u9225",
    "\u6d93",
    "\u9428",
    "\u9366",
    "\u9352",
    "\u6769",
    "\u7487",
    "\u7459",
    "\u7ecb",
    "\u6d94",
    "\u59af",
    "\u93c8",
    "\u95ab",
    "\u6d63",
    "\u935a",
    "\u5bee",
    "\u93c4",
    "\u59dd",
    "\u5bb8",
    "\u704f",
    "\u699b",
    "\u68f0",
    "\u6fc2",
    "\u9a9e",
)


def legacy_mojibake_variants(text: str) -> tuple[str, ...]:
    """Return legacy mojibake forms without storing unreadable markers in source."""
    variants: list[str] = []
    seen: set[str] = {text}
    raw = text.encode("utf-8")
    for encoding in LEGACY_MOJIBAKE_ENCODINGS:
        for errors in ("strict", "replace", "ignore"):
            try:
                variant = raw.decode(encoding, errors=errors)
            except UnicodeDecodeError:
                continue
            for candidate in (variant, variant.replace("\ufffd", "?")):
                if candidate and candidate not in seen:
                    seen.add(candidate)
                    variants.append(candidate)
    return tuple(variants)


def _common_cjk_hits(text: str) -> int:
    return sum(text.count(char) for char in COMMON_CJK_CHARS)


def _mojibake_fragment_hits(text: str) -> int:
    return sum(text.count(fragment) for fragment in LEGACY_MOJIBAKE_FRAGMENTS)


def repair_legacy_mojibake(text: str) -> str:
    """Repair common UTF-8-as-GBK/CP936 Chinese mojibake when the fix is clear."""
    if not text:
        return text
    sample = text[:6000]
    before_fragments = _mojibake_fragment_hits(sample)
    try:
        repaired = text.encode("gb18030").decode("utf-8")
    except UnicodeError:
        return text
    if repaired == text:
        return text
    repaired_sample = repaired[:6000]
    common_gain = _common_cjk_hits(repaired_sample) - _common_cjk_hits(sample)
    fragment_drop = before_fragments - _mojibake_fragment_hits(repaired_sample)
    if before_fragments >= 3 and (common_gain >= 2 or fragment_drop >= 3):
        return repaired
    if common_gain >= 6 and fragment_drop > 0:
        return repaired
    return text


def looks_like_legacy_mojibake(text: str) -> bool:
    sample = (text or "").strip()[:6000]
    chars = [char for char in sample if not char.isspace()]
    if len(chars) < 24:
        return False

    repaired = repair_legacy_mojibake(sample)
    if repaired != sample:
        return True

    fragment_hits = _mojibake_fragment_hits(sample)
    if fragment_hits >= 4 and fragment_hits / max(1, len(chars)) > 0.035:
        return True
    if fragment_hits >= 12:
        return True
    return False


def readable_markers(*markers: str) -> tuple[str, ...]:
    """Keep marker lists readable while still matching old corrupted input/logs."""
    expanded: list[str] = []
    seen: set[str] = set()
    for marker in markers:
        for candidate in (marker, *legacy_mojibake_variants(marker)):
            if candidate and candidate not in seen:
                seen.add(candidate)
                expanded.append(candidate)
    return tuple(expanded)
