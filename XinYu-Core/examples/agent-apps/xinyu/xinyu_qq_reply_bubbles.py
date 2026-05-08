from __future__ import annotations

import re


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


def reply_sentence_units(text: str) -> list[str]:
    pattern = re.compile(
        r"\S[\s\S]*?(?:[\u3002\uff01\uff1f\uff1b]+[\)\]\}\"'\u201d\u2019]*|[.!?;]+[\)\]\}\"'\u201d\u2019]*(?:\s+|$)|\n+|$)"
    )
    units = [match.group(0) for match in pattern.finditer(text.strip()) if match.group(0).strip()]
    return units or [text.strip()]
