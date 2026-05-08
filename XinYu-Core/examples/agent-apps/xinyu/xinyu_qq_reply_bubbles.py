from __future__ import annotations

import re
from typing import Any

from xinyu_qq_gateway_utils import safe_str


def looks_like_structured_visible_reply(text: str) -> bool:
    lowered = text.lower()
    structured_markers = (
        "```",
        "http://",
        "https://",
        "file://",
        "traceback",
        "exception",
        "error:",
        "exit code",
        "powershell",
        "pytest",
        "codex",
        "runtime/",
        "runtime\\",
        ".py",
        ".ps1",
        ".json",
        ".md",
        ".log",
    )
    if any(marker in lowered for marker in structured_markers):
        return True
    if any(marker in text for marker in ("\u62a5\u544a\u540d", "\u9000\u51fa\u7801", "\u9519\u8bef:")):
        return True
    if re.search(r"(?m)^\s*(?:[-*+]|\d+[.)])\s+\S", text):
        return True
    return text.count("|") >= 4 and "\n" in text


def forced_reply_bubble_units(source: dict[str, Any], *, max_bubbles: int) -> list[str]:
    raw_units = source.get("reply_bubble_force_units")
    if not isinstance(raw_units, list):
        return []
    units: list[str] = []
    for raw in raw_units:
        text = safe_str(raw).strip()
        if not text:
            continue
        if "\n" in text or "\r" in text:
            return []
        if len(text) > 80:
            return []
        units.append(text)
        if len(units) >= max_bubbles:
            break
    return units if len(units) >= 2 else []


def gateway_forced_reply_bubble_units(gateway: Any, source: dict[str, Any]) -> list[str]:
    return forced_reply_bubble_units(
        source,
        max_bubbles=gateway.config.reply_bubble_force_max_bubbles,
    )


def reply_sentence_units(text: str) -> list[str]:
    pattern = re.compile(
        r"\S[\s\S]*?(?:[\u3002\uff01\uff1f\uff1b]+[\)\]\}\"'\u201d\u2019]*|[.!?;]+[\)\]\}\"'\u201d\u2019]*(?:\s+|$)|\n+|$)"
    )
    units = [match.group(0) for match in pattern.finditer(text.strip()) if match.group(0).strip()]
    return units or [text.strip()]


def join_reply_fragments(left: str, right: str) -> str:
    left = left.rstrip()
    right = right.lstrip()
    if not left:
        return right
    if not right:
        return left
    separator = " " if re.search(r"[A-Za-z0-9]$", left) and re.match(r"[A-Za-z0-9]", right) else ""
    return f"{left}{separator}{right}".strip()


def hard_split_reply_text(text: str, *, soft_max: int, max_bubbles: int) -> list[str]:
    chunks: list[str] = []
    rest = text.strip()
    min_cut = max(30, soft_max // 2)
    separators = ("\n", "\u3002", "\uff01", "\uff1f", "\uff1b", ";", ".", "!", "?", "\uff0c", ",", "\u3001", " ")
    while len(rest) > soft_max and len(chunks) < max_bubbles - 1:
        window = rest[: soft_max + 20]
        cut = -1
        for separator in separators:
            position = rest[: soft_max + 1].rfind(separator)
            candidate = position + len(separator)
            if position >= 0 and len(rest) - candidate >= max(8, soft_max // 5):
                cut = max(cut, candidate)
        if cut < min_cut:
            for separator in separators:
                position = window.rfind(separator)
                candidate = position + len(separator)
                if position >= 0 and len(rest) - candidate >= max(8, soft_max // 5):
                    cut = max(cut, candidate)
        if cut < min_cut:
            cut = soft_max
        chunks.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    if rest:
        chunks.append(rest)
    return chunks


def merge_tiny_reply_chunks(chunks: list[str], *, min_piece: int) -> list[str]:
    merged = [chunk.strip() for chunk in chunks if chunk.strip()]
    while len(merged) > 1 and len(merged[-1]) < min_piece:
        tail = merged.pop()
        merged[-1] = join_reply_fragments(merged[-1], tail)
    while len(merged) > 1 and len(merged[0]) < min_piece:
        head = merged.pop(0)
        merged[0] = join_reply_fragments(head, merged[0])
    return merged
