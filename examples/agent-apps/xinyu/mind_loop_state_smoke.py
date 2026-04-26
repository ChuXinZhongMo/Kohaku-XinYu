from __future__ import annotations

from pathlib import Path

from xinyu_autonomy_journal import render_thoughts


def main() -> int:
    root = Path(__file__).resolve().parent
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
    for marker in ("经历 -> 记忆 -> 反思", "非复制原则", "可选行动"):
        if marker not in policy:
            failures.append(f"policy missing marker: {marker}")
    for marker in ("current_focus:", "blocked: autonomous_web_search", "build_persona_runtime"):
        if marker not in state:
            failures.append(f"state missing marker: {marker}")

    rendered = render_thoughts(root, "2026-04-26T17:10:00+08:00")
    for marker in ("# 心玉的想法", "当前主线：", "我自己做不到", "mind_loop_state.md"):
        if marker not in rendered:
            failures.append(f"desktop thoughts rendering missing marker: {marker}")

    if failures:
        print("Mind loop state smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Mind loop state smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
