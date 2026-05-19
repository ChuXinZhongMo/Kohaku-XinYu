from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import sys
from pathlib import Path

from ops.diagnostics.diagnose_runtime_injection import NullInput, _ensure_repo_src, _load_local_env
from xinyu_core_bridge import XinYuBridgeRuntime
from xinyu_persona_runtime import build_persona_runtime_state


RAW_OWNER_QQ = "".join(("2692", "167682"))
WRONG_NAME = "\u5fc3\u8bed"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    root = ROOT
    _load_local_env(root)
    _ensure_repo_src(root)

    from xinyu_runtime.core.agent import Agent

    failures: list[str] = []

    anchor_text = (root / "memory/context/persona_life_anchors.md").read_text(encoding="utf-8-sig")
    if "# Background Texture Seed" not in anchor_text:
        failures.append("persona life anchor file is missing the expected seed title")
    if WRONG_NAME in anchor_text:
        failures.append("persona life anchor file still contains the wrong alternate name")
    if RAW_OWNER_QQ in anchor_text:
        failures.append("persona life anchor file leaked raw owner QQ")

    agent = Agent.from_path(str(root), input_module=NullInput(), pwd=str(root))
    prompt = agent.get_system_prompt()
    if "# Background Texture Seed" in prompt:
        failures.append("system prompt should not inject persona_life_anchors as a hard template")
    if "{{ persona_life_anchors }}" in prompt:
        failures.append("persona_life_anchors template variable remained unresolved")
    if RAW_OWNER_QQ in prompt:
        failures.append("system prompt leaked raw owner QQ")
    if "QQ tether details require adapter events or owner-granted local config" in prompt:
        failures.append("system prompt still contains old QQ privacy/capability boundary")

    runtime = XinYuBridgeRuntime(
        xinyu_dir=root,
        turn_timeout_seconds=1,
        max_text_chars=1000,
        settle_seconds=0,
        outward_renderer=True,
        render_timeout_seconds=1,
    )
    renderer_context = runtime._renderer_memory_context()
    if "# Background Texture Seed" in renderer_context:
        failures.append("renderer context should not include persona_life_anchors")
    if RAW_OWNER_QQ in renderer_context:
        failures.append("renderer context leaked raw owner QQ")

    signature = runtime._session_prompt_signature()
    if "memory/context/persona_life_anchors.md" in signature:
        failures.append("session prompt signature should not track persona_life_anchors")
    for volatile_rel in (
        "memory/context/persona_surface_state.md",
        "memory/context/recent_context.md",
        "memory/self/voice_calibration_log.md",
        "memory/context/memory_weight_state.md",
    ):
        if volatile_rel in signature:
            failures.append(f"session prompt signature should not track volatile file: {volatile_rel}")

    state = build_persona_runtime_state(
        root,
        payload={"metadata": {"is_owner_user": True}},
        user_text="\u5e7f\u5dde\u8fd9\u5929\u6c14\u70ed\u8d77\u6765\u4e86\uff0c\u6211\u60f3\u559d\u9e2d\u5c4e\u9999\u67e0\u6aac\u8336\u3002",
        draft_reply="",
    )
    if state.scene != "daily_chat":
        failures.append(f"life-anchor daily scene mismatch: {state.scene}")
    if "hard" in state.to_prompt_block().lower() and "not a personality contract" not in state.to_prompt_block().lower():
        failures.append("persona runtime should stay a soft current-state hint")

    if failures:
        print("Persona life anchor smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Persona life anchor smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
