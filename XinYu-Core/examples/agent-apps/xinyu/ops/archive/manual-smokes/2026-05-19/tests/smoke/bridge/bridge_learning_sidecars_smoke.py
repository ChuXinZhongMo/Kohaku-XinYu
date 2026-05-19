from __future__ import annotations

import sys
import types
from pathlib import Path

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

import xinyu_bridge_learning
from xinyu_bridge_learning_sidecars import int_result, run_learning_study_chain, should_run_learning_after_codex
from xinyu_core_bridge import _int_result, _run_learning_study_chain, _should_run_learning_after_codex


def _module(name: str, function_name: str, result_key: str) -> types.ModuleType:
    module = types.ModuleType(name)

    def run(root: Path, mode: str) -> dict[str, object]:
        return {"root": str(root), "mode": mode, result_key: 1}

    setattr(module, function_name, run)
    return module


def main() -> int:
    failures: list[str] = []
    old_path = list(sys.path)
    module_names = (
        "learner_integration_engine",
        "learning_quality_engine",
        "source_integration_gate_engine",
    )
    old_modules = {name: sys.modules.get(name) for name in module_names}
    try:
        sys.modules["learner_integration_engine"] = _module(
            "learner_integration_engine",
            "run_learner_integration",
            "newly_integrated_materials",
        )
        sys.modules["learning_quality_engine"] = _module(
            "learning_quality_engine",
            "run_learning_quality",
            "warning_count",
        )
        sys.modules["source_integration_gate_engine"] = _module(
            "source_integration_gate_engine",
            "run_source_integration_gate",
            "accepted_sources",
        )

        result = run_learning_study_chain(Path("D:/XinYu"), "smoke")
        if result.get("source_integration_gate", {}).get("mode") != "smoke_source_gate":
            failures.append("learning source gate mode changed")
        if result.get("learner_integration", {}).get("mode") != "smoke_learner":
            failures.append("learning learner mode changed")
        if result.get("learning_quality", {}).get("mode") != "smoke_quality":
            failures.append("learning quality mode changed")
    finally:
        sys.path[:] = old_path
        for name, old_module in old_modules.items():
            if old_module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old_module

    if int_result({"count": "7"}, "count") != 7 or int_result({"count": "bad"}, "count") != 0:
        failures.append("learning int result helper changed")
    if not should_run_learning_after_codex("帮我读一下这份资料"):
        failures.append("Codex learning followup trigger missed learning request")
    if should_run_learning_after_codex("只开一个本地窗口"):
        failures.append("Codex learning followup trigger matched unrelated request")

    if (
        _run_learning_study_chain is not run_learning_study_chain
        or xinyu_bridge_learning._run_learning_study_chain is not run_learning_study_chain
        or _int_result is not int_result
        or xinyu_bridge_learning._int_result is not int_result
        or _should_run_learning_after_codex is not should_run_learning_after_codex
    ):
        failures.append("learning sidecar aliases no longer delegate")

    if failures:
        print("XinYu bridge learning sidecars smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu bridge learning sidecars smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
