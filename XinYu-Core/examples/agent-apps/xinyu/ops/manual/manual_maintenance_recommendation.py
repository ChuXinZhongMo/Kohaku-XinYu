from __future__ import annotations

from datetime import datetime
from pathlib import Path

from _manual_paths import APP_ROOT


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _extract_value(text: str, key: str, fallback: str = "unknown") -> str:
    prefix = f"- {key}: "
    for line in text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return fallback


def _main() -> int:
    root = APP_ROOT
    runtime_bridge = _read(root / "memory/context/runtime_bridge_state.md")
    now = datetime.now().astimezone().isoformat()

    inner_sync = _extract_value(runtime_bridge, "inner_sync", "hold")
    question_pipeline = _extract_value(runtime_bridge, "question_pipeline", "hold")
    slow_reprocess = _extract_value(runtime_bridge, "slow_reprocess", "hold")
    reflection_output = _extract_value(runtime_bridge, "reflection_output", "hold")
    source_gate = _extract_value(runtime_bridge, "source_gate", "hold")

    text = f"""---
title: Maintenance Recommendations
memory_type: maintenance_recommendations
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {now}
last_confirmed_at: {now}
importance_score: 84
impact_score: 83
confidence_score: 100
status: active
tags: [maintenance, recommendations, bridge]
---

# Maintenance Recommendations

## Current Phase
- phase: post_inner_bridge
- evaluated_at: {now}

## Immediate Priorities
- inner_sync: {inner_sync}
- question_pipeline: {question_pipeline}

## Near-Term Priorities
- slow_reprocess: {slow_reprocess}
- reflection_output: {reflection_output}

## Deferred Priorities
- source_gate: {source_gate}
- external learning should remain gated
- archive and dream should remain behind lived continuity

## Runtime Note
- This file is advisory only.
- It should guide low-frequency maintenance, not force high-frequency execution.
"""
    (root / "memory/context/maintenance_recommendations.md").write_text(text, encoding="utf-8")
    print("maintenance recommendations updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
