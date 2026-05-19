from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import sys
from pathlib import Path

from ops.diagnostics.diagnose_runtime_injection import NullInput, _ensure_repo_src, _load_local_env
from xinyu_core_bridge import XinYuBridgeRuntime
from xinyu_speech_controller import XinyuSpeechController


REMOVED_MARKERS = (
    "persona_" + "hard_constraints",
    "Inline Persona " + "Hard " + "Lock",
    "Persona " + "Hard " + "Constraints",
    "highest-priority persona " + "contract",
    "hard " + "constraints",
    "hard " + "lock",
    "identity " + "lock",
)

VISIBLE_TEMPLATE_MARKERS = (
    "你不是在" + "挑刺",
    "不能再" + "说轻了",
    "别急着把我整" + "个判没了",
    "说明书" + "糊你",
    "我去" + "改，不绕了",
    "我把你" + "放回普通用户的位置了",
    "我把前面的重量" + "说轻了",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace") if path.exists() else ""


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    root = ROOT
    _load_local_env(root)
    _ensure_repo_src(root)

    from xinyu_runtime.core.agent import Agent

    failures: list[str] = []
    removed_prompt = "prompts/persona_" + "hard_constraints.md"
    if (root / removed_prompt).exists():
        failures.append(f"{removed_prompt} should be removed")

    runtime_files = [
        root / "config.yaml",
        root / "prompts/system.md",
        root / "prompts/output.md",
        root / "xinyu_bridge_renderer.py",
        root / "xinyu_core_bridge.py",
        root / "xinyu_memory_weights.py",
        root / "xinyu_persona_runtime.py",
        root / "xinyu_speech_controller.py",
        root / "xinyu_turn_residue.py",
        root / "smoke_run.py",
        root / "memory/self/system_prompt_memory.md",
        root / "memory/context/memory_weight_state.md",
        root / "memory/context/life_month_slots.md",
        root / "memory/context/persona_surface_state.md",
        root / "memory-seeds/self/system_prompt_memory.md",
        root / "memory-seeds/context/life_month_slots.md",
    ]
    for path in runtime_files:
        text = _read(path)
        for marker in REMOVED_MARKERS:
            if marker in text:
                failures.append(f"{path.relative_to(root)} still contains removed contract marker: {marker}")
        for marker in VISIBLE_TEMPLATE_MARKERS:
            if marker in text:
                failures.append(f"{path.relative_to(root)} still contains removed visible template: {marker}")

    agent = Agent.from_path(str(root), input_module=NullInput(), pwd=str(root))
    prompt = agent.get_system_prompt()
    for marker in REMOVED_MARKERS:
        if marker in prompt:
            failures.append(f"system prompt still contains removed contract marker: {marker}")

    runtime = XinYuBridgeRuntime(
        xinyu_dir=root,
        turn_timeout_seconds=1,
        max_text_chars=1000,
        settle_seconds=0,
        outward_renderer=True,
        render_timeout_seconds=1,
    )
    context = runtime._renderer_memory_context()
    signature = runtime._session_prompt_signature()
    contract = XinyuSpeechController(root)._controller_contract()
    for source_name, text in (
        ("renderer context", context),
        ("session prompt signature", signature),
        ("speech controller contract", contract),
    ):
        for marker in REMOVED_MARKERS:
            if marker in text:
                failures.append(f"{source_name} still contains removed contract marker: {marker}")

    if failures:
        print("Persona contract absence smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Persona contract absence smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
