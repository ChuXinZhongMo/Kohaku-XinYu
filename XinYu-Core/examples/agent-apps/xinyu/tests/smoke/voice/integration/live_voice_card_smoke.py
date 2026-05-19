from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import subprocess
import sys
from pathlib import Path

from ops.diagnostics.diagnose_runtime_injection import NullInput, _ensure_repo_src, _load_local_env
from xinyu_core_bridge import XinYuBridgeRuntime
from xinyu_persona_runtime import build_persona_runtime_state


RAW_OWNER_QQ = "".join(("2692", "167682"))
WRONG_NAME = "\u5fc3\u8bed"


def _git_check_ignored(root: Path, rel: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "-q", rel],
        cwd=root.parents[2],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


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
    card_rel = "examples/agent-apps/xinyu/prompts/live_voice_card.md"
    card_path = root / "prompts/live_voice_card.md"
    card = card_path.read_text(encoding="utf-8-sig")

    if "# XinYu Live Voice Seed" not in card:
        failures.append("live voice card title missing")
    if len(card) > 1200:
        failures.append(f"live voice card is too long: {len(card)} chars")
    if _git_check_ignored(root, card_rel):
        failures.append("live voice card is ignored by git; it should be tracked")
    for marker in (
        "心玉 / XinYu",
        "不是一张设定表",
        "正在形成",
        "说话先贴住眼前这句话",
        "直接换成此刻能成立的一句",
    ):
        if marker not in card:
            failures.append(f"live voice card missing marker: {marker}")
    for leaked_phrase in (
        "滑回",
        "小算",
        "我还没长到身上",
        "我只是记住了字",
    ):
        if leaked_phrase in card:
            failures.append(f"live voice card contains leak-prone phrase: {leaked_phrase}")
    if WRONG_NAME in card:
        failures.append("live voice card contains the wrong alternate name")
    if RAW_OWNER_QQ in card:
        failures.append("live voice card leaked raw owner QQ")

    agent = Agent.from_path(str(root), input_module=NullInput(), pwd=str(root))
    prompt = agent.get_system_prompt()
    if "# XinYu Live Voice Seed" not in prompt:
        failures.append("system prompt did not inject live_voice_card")
    if "{{ live_voice_card }}" in prompt:
        failures.append("live_voice_card template variable remained unresolved")
    live_pos = prompt.find("# XinYu Live Voice Seed")
    core_pos = prompt.find("memory_type: self_core")
    if not (0 <= live_pos < core_pos):
        failures.append("live voice card is not before core concept in system prompt")
    if RAW_OWNER_QQ in prompt:
        failures.append("system prompt leaked raw owner QQ")

    runtime = XinYuBridgeRuntime(
        xinyu_dir=root,
        turn_timeout_seconds=1,
        max_text_chars=1000,
        settle_seconds=0,
        outward_renderer=True,
        render_timeout_seconds=1,
    )
    context = runtime._renderer_memory_context()
    if "[prompts/live_voice_card.md]" not in context:
        failures.append("renderer context did not include live voice card")
    context_live_pos = context.find("[prompts/live_voice_card.md]")
    context_core_pos = context.find("[memory/self/core.md]")
    if not (0 <= context_live_pos < context_core_pos):
        failures.append("live voice card is not first in renderer context")

    signature = runtime._session_prompt_signature()
    if "prompts/live_voice_card.md" not in signature:
        failures.append("session prompt signature does not track live voice card")

    state = build_persona_runtime_state(
        root,
        payload={"metadata": {"is_owner_user": True}},
        user_text="怎么感觉没什么变化。",
        draft_reply="",
    )
    if state.scene != "owner_no_change_pressure":
        failures.append(f"no-change turn did not classify as no-change pressure: {state.scene}")
    if "change the next line itself" not in state.chinese_voice:
        failures.append("persona runtime did not expose concept-seed style pressure")

    if failures:
        print("Live voice card smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Live voice card smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
