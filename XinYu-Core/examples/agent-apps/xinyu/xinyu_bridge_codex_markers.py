from __future__ import annotations

import re
from typing import Pattern


def extract_model_codex_delegate(reply: str, patterns: tuple[Pattern[str], ...]) -> str:
    for pattern in patterns:
        match = pattern.search(reply or "")
        if not match:
            continue
        task = re.sub(r"\s+", " ", match.group("task")).strip()
        task = re.sub(r"(?i)^@@task\s*=\s*", "", task).strip()
        return task[:4000]
    return ""


def extract_self_code_approval_id(task_text: str) -> str:
    match = re.search(r"(?im)^\s*Self-code approval id:\s*([A-Za-z0-9_-]+)\s*$", task_text or "")
    return match.group(1).strip() if match else "unknown"
