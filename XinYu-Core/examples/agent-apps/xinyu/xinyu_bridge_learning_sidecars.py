from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_bridge_stores import append_codex_learning_followup_trace
from xinyu_bridge_values import safe_str


def run_learning_study_chain(root: Path, mode: str) -> dict[str, object]:
    custom_dir = Path(__file__).resolve().parent / "custom"
    if str(custom_dir) not in sys.path:
        sys.path.insert(0, str(custom_dir))

    from learner_integration_engine import run_learner_integration
    from learning_quality_engine import run_learning_quality
    from source_integration_gate_engine import run_source_integration_gate

    gate = run_source_integration_gate(root, mode=f"{mode}_source_gate")
    learner = run_learner_integration(root, mode=f"{mode}_learner")
    quality = run_learning_quality(root, mode=f"{mode}_quality")
    return {
        "source_integration_gate": gate,
        "learner_integration": learner,
        "learning_quality": quality,
    }


def int_result(mapping: dict[str, object], key: str) -> int:
    try:
        return int(mapping.get(key, 0))
    except (TypeError, ValueError):
        return 0


def should_run_learning_after_codex(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "学习",
            "学一下",
            "读一下",
            "阅读",
            "消化",
            "论文",
            "资料",
            "源码",
            "仓库",
        )
    )


async def codex_learning_followup(runtime: Any, mode: str) -> None:
    trace_path = runtime.memory_root / "knowledge/codex_learning_followup_trace.log"
    started_at = datetime.now().astimezone().isoformat()
    try:
        async with runtime._global_turn_lock:
            result = await asyncio.to_thread(run_learning_study_chain, runtime.xinyu_dir, mode)
        learner = result.get("learner_integration", {}) if isinstance(result, dict) else {}
        quality = result.get("learning_quality", {}) if isinstance(result, dict) else {}
        integrated = int_result(learner if isinstance(learner, dict) else {}, "newly_integrated_materials")
        quality_grade = safe_str(quality.get("quality_grade"), "unknown") if isinstance(quality, dict) else "unknown"
        line = (
            f"{datetime.now().astimezone().isoformat()} ok "
            f"started_at={started_at} integrated={integrated} quality={quality_grade}\n"
        )
    except Exception as exc:
        line = (
            f"{datetime.now().astimezone().isoformat()} error "
            f"started_at={started_at} {type(exc).__name__}: {exc}\n"
        )
    append_codex_learning_followup_trace(trace_path, line)
