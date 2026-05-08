from __future__ import annotations

import sys
from pathlib import Path


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
