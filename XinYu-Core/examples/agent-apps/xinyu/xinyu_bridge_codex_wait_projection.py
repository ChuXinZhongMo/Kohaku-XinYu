from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any


def extract_wait_to_think_task(
    reply: str,
    *,
    user_text: str,
    session_key: str,
    patterns: tuple[re.Pattern[str], ...],
    normalize_func: Callable[[str], str],
    safe_str_func: Callable[[Any], str],
) -> str:
    for pattern in patterns:
        match = pattern.search(reply or "")
        if not match:
            continue
        raw_task = re.sub(r"\s+", " ", safe_str_func(match.groupdict().get("task"))).strip()
        if not raw_task:
            raw_task = "verify the uncertain owner request before answering"
        return normalize_func(
            "\n".join(
                [
                    "XinYu paused instead of faking certainty. Use Codex as asynchronous exploration.",
                    f"Owner message: {user_text}",
                    f"XinYu pause marker: {reply}",
                    f"Session: {session_key}",
                    (
                        "Task: investigate the concrete uncertainty, using web search, local repository inspection, "
                        "or small non-destructive validation commands only when relevant. Write a concise report with "
                        "what was checked, what is still uncertain, and the exact next answer XinYu can safely give. "
                        "Do not change files unless the owner has separately approved a self-code modification."
                    ),
                    f"Specific uncertainty: {raw_task}",
                ]
            )
        )[:4000]
    return ""


def wait_to_think_execution_plan(
    wait_task: str,
    *,
    user_text: str,
    write_risk_markers: tuple[str, ...],
    normalize_func: Callable[[str], str],
) -> str:
    text = f"{wait_task}\n{user_text}".lower()
    write_risk = any(marker in text for marker in write_risk_markers)
    if write_risk:
        risk = "high"
        plan_shape = "precise command/script draft required; Codex may only adjust paths/quoting and must not expand scope"
    else:
        risk = "read_only"
        plan_shape = "semi-structured read-only plan is acceptable; Codex translates final local commands"
    return normalize_func(
        "\n".join(
            [
                f"risk_level: {risk}",
                f"plan_shape: {plan_shape}",
                "steps:",
                "1. Restate the concrete uncertainty and expected evidence before running anything.",
                "2. Execute only the smallest read-only checks needed unless a separate owner-approved ticket permits writes.",
                "3. If a step fails, record the failure kind and stop or choose the listed fallback; do not invent success.",
                "4. Return a sanitized summary, verified scope, unknowns, and whether owner narrowing is needed.",
                "forbidden:",
                "- no credential/cookie/token reading",
                "- no destructive file operations",
                "- no dependency install or code modification unless an explicit approval ticket is present",
                "- no raw stdout/stderr injection into the final answer",
            ]
        )
    )
