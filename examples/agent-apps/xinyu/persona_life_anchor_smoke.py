from __future__ import annotations

import sys
from pathlib import Path

from diagnose_runtime_injection import NullInput, _ensure_repo_src, _load_local_env
from xinyu_core_bridge import XinYuBridgeRuntime
from xinyu_persona_runtime import build_persona_runtime_state


RAW_OWNER_QQ = "".join(("2692", "167682"))
WRONG_NAME = "\u5fc3\u8bed"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    root = Path(__file__).resolve().parent
    _load_local_env(root)
    _ensure_repo_src(root)

    from kohakuterrarium.core.agent import Agent

    failures: list[str] = []

    anchor_text = (root / "memory/context/persona_life_anchors.md").read_text(encoding="utf-8-sig")
    if "# 心玉人格生活锚点" not in anchor_text:
        failures.append("persona life anchor file is missing the expected title")
    if "稳定名字是“心玉 / XinYu”" not in anchor_text:
        failures.append("persona life anchor file does not pin the stable 心玉 name")
    if WRONG_NAME in anchor_text:
        failures.append("persona life anchor file still contains the wrong alternate name")
    if RAW_OWNER_QQ in anchor_text:
        failures.append("persona life anchor file leaked raw owner QQ")
    for marker in (
        "不作为运行时指令",
        "不能声称自己正在监控 QQ",
        "不保留其他人格名或别名",
    ):
        if marker not in anchor_text:
            failures.append(f"persona life anchor missing marker: {marker}")

    agent = Agent.from_path(str(root), input_module=NullInput(), pwd=str(root))
    prompt = agent.get_system_prompt()
    if "# 心玉人格生活锚点" not in prompt:
        failures.append("system prompt did not inject persona_life_anchors")
    if "{{ persona_life_anchors }}" in prompt:
        failures.append("persona_life_anchors template variable remained unresolved")
    if WRONG_NAME in prompt:
        failures.append("system prompt still contains the wrong alternate name")
    if RAW_OWNER_QQ in prompt:
        failures.append("system prompt leaked raw owner QQ")
    if "QQ tether details require owner-granted local config" not in prompt:
        failures.append("system prompt missing QQ privacy/capability boundary")

    runtime = XinYuBridgeRuntime(
        xinyu_dir=root,
        turn_timeout_seconds=1,
        max_text_chars=1000,
        settle_seconds=0,
        outward_renderer=True,
        render_timeout_seconds=1,
    )
    renderer_context = runtime._renderer_memory_context()
    if "# 心玉人格生活锚点" not in renderer_context:
        failures.append("renderer memory context did not include persona_life_anchors")
    if WRONG_NAME in renderer_context:
        failures.append("renderer context still contains the wrong alternate name")
    if RAW_OWNER_QQ in renderer_context:
        failures.append("renderer context leaked raw owner QQ")

    signature = runtime._session_prompt_signature()
    if "memory/context/persona_life_anchors.md" not in signature:
        failures.append("session prompt signature does not track persona_life_anchors")

    state = build_persona_runtime_state(
        root,
        payload={"metadata": {"is_owner_user": True}},
        user_text="广州这天气热起来了，我想喝鸭屎香柠檬茶。",
        draft_reply="",
    )
    if state.scene != "daily_chat":
        failures.append(f"life-anchor daily scene mismatch: {state.scene}")
    if "稳定名字是心玉" not in state.chinese_voice:
        failures.append("persona runtime did not preserve the stable 心玉 name")
    if "不伪装真实身体" not in state.chinese_voice:
        failures.append("persona runtime did not preserve body-boundary guidance")

    if failures:
        print("Persona life anchor smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Persona life anchor smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
