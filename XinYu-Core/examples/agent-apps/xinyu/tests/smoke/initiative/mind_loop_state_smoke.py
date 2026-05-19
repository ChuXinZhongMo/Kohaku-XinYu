from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import asyncio
from pathlib import Path

from xinyu_autonomy_journal import render_persona_thoughts, thought_quality_flags


class FakeResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class FakeThoughtLLM:
    def __init__(self, replies: list[str]) -> None:
        self.replies = replies
        self.calls = 0

    async def chat_complete(self, messages: list[dict], **kwargs) -> FakeResponse:
        self.calls += 1
        index = min(self.calls - 1, len(self.replies) - 1)
        return FakeResponse(self.replies[index])


def main() -> int:
    root = ROOT
    config = (root / "config.yaml").read_text(encoding="utf-8")
    system = (root / "prompts/system.md").read_text(encoding="utf-8")
    policy = (root / "memory/self/mind_loop_policy.md").read_text(encoding="utf-8-sig")
    state = (root / "memory/self/mind_loop_state.md").read_text(encoding="utf-8-sig")

    failures: list[str] = []
    for marker in (
        "mind_loop_policy: memory/self/mind_loop_policy.md",
        "mind_loop_state: memory/self/mind_loop_state.md",
    ):
        if marker not in config:
            failures.append(f"config missing marker: {marker}")
    for marker in ("{{ mind_loop_policy }}", "{{ mind_loop_state }}"):
        if marker not in system:
            failures.append(f"system prompt missing marker: {marker}")
    for marker in ("# Mind Loop Policy", "Human-Like Bias", "Runtime Reading Rule"):
        if marker not in policy:
            failures.append(f"policy missing marker: {marker}")
    for marker in ("# Mind Loop State", "- loop_status: active_low_frequency", "quiet_until_grounded_focus"):
        if marker not in state:
            failures.append(f"state missing marker: {marker}")

    retry_llm = FakeThoughtLLM(
        [
            "# 心玉的想法\n\n## 现在最重的\n- proposal / provider / stable",
            "# 心玉的想法\n\n哥，我把话压短一点。\n\n有些事我想慢慢学，但不能乱碰你的东西。",
        ]
    )
    persona_rendered = asyncio.run(render_persona_thoughts(root, "2026-04-26T17:10:00+08:00", llm=retry_llm))
    if retry_llm.calls != 2:
        failures.append(f"persona thoughts did not retry flagged first draft: calls={retry_llm.calls}")
    if thought_quality_flags(persona_rendered):
        failures.append("persona thoughts retry still has quality flags")
    if "有些事我想慢慢学" not in persona_rendered:
        failures.append("persona thoughts retry did not return cleaned fake LLM note")

    bad_llm = FakeThoughtLLM(["# 心玉的想法\n\n- provider\n- stable\n- proposal"] * 2)
    rejected_rendered = asyncio.run(render_persona_thoughts(root, "2026-04-26T17:10:00+08:00", llm=bad_llm))
    if bad_llm.calls != 2:
        failures.append(f"persona thoughts did not retry before rejecting flagged drafts: calls={bad_llm.calls}")
    if rejected_rendered:
        failures.append("persona thoughts returned text after repeated flagged drafts")

    no_llm_rendered = asyncio.run(
        render_persona_thoughts(root, "2026-04-26T17:10:00+08:00", use_llm=False)
    )
    if no_llm_rendered:
        failures.append("persona thoughts wrote deterministic text without an LLM")

    if failures:
        print("Mind loop state smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Mind loop state smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
