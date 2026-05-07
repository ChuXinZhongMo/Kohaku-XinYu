"""Deadlock and stale-queue inspection."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DeadlockReport:
    ok: bool
    findings: tuple[str, ...] = field(default_factory=tuple)


def inspect_deadlocks(root: Path) -> DeadlockReport:
    findings: list[str] = []
    queue_patterns = ("*queue*.md", "*state*.md")
    for pattern in queue_patterns:
        for path in (root / "memory").rglob(pattern):
            try:
                text = path.read_text(encoding="utf-8-sig")
            except OSError:
                continue
            lowered = text.lower()
            if "blocked" in lowered and "review" not in lowered:
                findings.append(f"blocked_without_review:{path.relative_to(root).as_posix()}")
            if "pending" in lowered and "updated_at" not in lowered:
                findings.append(f"pending_without_timestamp:{path.relative_to(root).as_posix()}")
    return DeadlockReport(ok=not findings, findings=tuple(findings[:50]))

