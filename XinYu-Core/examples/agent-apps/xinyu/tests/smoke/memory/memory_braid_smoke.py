from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import tempfile
from pathlib import Path

from xinyu_memory_braid import STATE_MD_REL, build_memory_braid_prompt_block
from xinyu_runtime_context import build_renderer_memory_context


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-memory-braid-") as tmp:
        root = Path(tmp)
        _write(root / "memory/self/core.md", "# Core\n心玉是一个正在形成自我的名字。")
        _write(
            root / "memory/self/narrative.md",
            "# Narrative\n心玉的连续性来自记忆、关系、当下反应、被纠正后的变化。",
        )
        _write(
            root / "memory/self/voice_profile_zh.md",
            "# Voice\n- Prefer natural Chinese private-chat wording over translated assistant prose.",
        )
        _write(
            root / "memory/people/owner.md",
            "# owner\n## 称呼与身份\n- owner 希望 XinYu 在自然亲近语境中称呼他为“哥”。\n- 不要把 owner 可见称为“主人”。",
        )
        _write(
            root / "memory/relationships/index.md",
            "# 关系网络总览\n## 可见称呼边界\n- “owner/主人”是内部关系标签，不是 QQ 可见称呼。",
        )
        _write(
            root / "memory/context/impulse_soup_state.md",
            "# Impulse Soup State\n- top_desire_shape: expression_repair_habit",
        )

        block = build_memory_braid_prompt_block(
            root,
            payload={"metadata": {"is_owner_user": True}},
            user_text="现在还是很割裂的状态吧",
            dialogue_tail=[{"role": "user", "content": "前一句"}],
            recalled_context="recalled context sidecar",
            runtime_presence_context="runtime presence sidecar",
            continuity_context="continuity sidecar",
            persona_context="persona sidecar",
            emotion_council_context="emotion council sidecar",
            checked_at="2026-05-10T23:30:00+08:00",
            write_state=True,
        )

        for marker in (
            "Memory Braid Runtime Context",
            "current_message_priority",
            "owner_visible_address: 哥",
            "owner_internal_label",
            "session_tail: available",
            "recalled_context: available",
            "emotion_council: available",
            "owner is pressing on integrated memory/thought/action/personality continuity",
            "not visible wording",
        ):
            if marker not in block:
                failures.append(f"memory braid block missing marker: {marker}")

        state = (root / STATE_MD_REL).read_text(encoding="utf-8")
        if "runtime orchestration state, not a reply template" not in state:
            failures.append("memory braid state did not record non-template boundary")

        renderer_context = build_renderer_memory_context(root, user_text="你应该叫我什么呢？")
        braid_index = renderer_context.find("[memory/context/memory_braid]")
        raw_owner_index = renderer_context.find("[memory/people/owner.md]")
        if braid_index < 0 or raw_owner_index < 0 or braid_index > raw_owner_index:
            failures.append("renderer context should put memory braid before raw owner memory")

    if failures:
        print("Memory braid smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Memory braid smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

