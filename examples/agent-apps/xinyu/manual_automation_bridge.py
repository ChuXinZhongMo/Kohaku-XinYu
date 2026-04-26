from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path


def _load_manifest(xinyu_dir: Path):
    sys.path.insert(0, str(xinyu_dir / "custom"))
    from automation_bridge_manifest import AUTOMATION_BRIDGE_INPUTS, AUTOMATION_BRIDGE_OUTPUTS

    return AUTOMATION_BRIDGE_INPUTS, AUTOMATION_BRIDGE_OUTPUTS


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _needs_refresh(text: str, marker: str) -> bool:
    return marker not in text


def _infer_suggestions(xinyu_dir: Path) -> dict[str, str]:
    inner_sync = _read(xinyu_dir / "memory/context/inner_sync_state.md")
    question_pipe = _read(xinyu_dir / "memory/context/question_pipeline_state.md")
    slow_state = _read(xinyu_dir / "memory/reflection/reprocessing_state.md")
    reflection_out = _read(xinyu_dir / "memory/reflection/reflection_output_state.md")
    source_gate = _read(xinyu_dir / "memory/knowledge/source_gate_state.md")

    return {
        "suggest_inner_sync": "yes" if "meaningful: true" in inner_sync else "no",
        "suggest_question_pipeline": "yes" if "ready_for_exploration:" in question_pipe else "no",
        "suggest_slow_reprocess": "yes" if "reflection_queue_items:" in slow_state else "no",
        "suggest_reflection_output": "yes" if "最近主题\n- none" not in reflection_out else "hold",
        "suggest_source_gate": "yes" if "当前候选\n- none" not in source_gate else "hold",
    }


def _update_state(path: Path, evaluated_at: str, suggestions: dict[str, str]) -> None:
    text = f"""---
title: 自动衔接状态
memory_type: automation_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {evaluated_at}
last_confirmed_at: {evaluated_at}
importance_score: 83
impact_score: 83
confidence_score: 100
status: active
tags: [automation, state, bridge]
---

# 当前自动衔接状态

## 最近一次评估
- evaluated_at: {evaluated_at}
- mode: manual_automation_bridge

## 当前建议
- suggest_inner_sync: {suggestions['suggest_inner_sync']}
- suggest_question_pipeline: {suggestions['suggest_question_pipeline']}
- suggest_slow_reprocess: {suggestions['suggest_slow_reprocess']}
- suggest_reflection_output: {suggestions['suggest_reflection_output']}
- suggest_source_gate: {suggestions['suggest_source_gate']}

## 当前结论
- 当前阶段更适合低频自动建议，而不是无条件高频自动执行
"""
    _write(path, text)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate Xinyu automation bridge suggestions.")
    parser.add_argument("--show-state", action="store_true", help="Print automation state after update.")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    xinyu_dir = Path(__file__).resolve().parent
    _inputs, _outputs = _load_manifest(xinyu_dir)
    evaluated_at = datetime.now().astimezone().isoformat()
    suggestions = _infer_suggestions(xinyu_dir)
    _update_state(xinyu_dir / "memory/context/automation_state.md", evaluated_at, suggestions)

    print("Xinyu manual automation bridge complete.")
    for key, value in suggestions.items():
        print(f"{key}: {value}")

    if args.show_state:
        path = xinyu_dir / "memory/context/automation_state.md"
        print(f"\n--- memory/context/automation_state.md ---")
        print(path.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
