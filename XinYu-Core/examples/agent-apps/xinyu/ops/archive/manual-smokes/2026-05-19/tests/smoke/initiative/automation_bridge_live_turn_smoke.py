from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import asyncio
import sys
import tempfile
from pathlib import Path


def _ensure_import_paths(root: Path) -> None:
    repo_src = root.parents[2] / "src"
    custom = root / "custom"
    for path in (repo_src, custom):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


class FakeContext:
    def __init__(self, working_dir: Path) -> None:
        self.working_dir = str(working_dir)


async def _exercise(temp_root: Path) -> list[str]:
    from automation_bridge_plugin import AutomationBridgePlugin

    failures: list[str] = []
    ctx = FakeContext(temp_root)
    plugin = AutomationBridgePlugin(options={"enabled": True})
    await plugin.on_load(ctx)  # type: ignore[arg-type]

    bridge_state = temp_root / "memory/context/runtime_bridge_state.md"
    _write(bridge_state, "# Runtime Bridge\n\n- question_pipeline: yes\n")
    _write(temp_root / "memory/context/turn_mode_state.md", "- mode: live_user_turn\n")

    live_result = await plugin.pre_llm_call([{"role": "user", "content": "hi"}])
    if live_result is not None:
        failures.append("runtime bridge was injected into live_user_turn")

    before = bridge_state.read_text(encoding="utf-8")
    await plugin.post_llm_call([{"role": "user", "content": "hi"}], "visible reply", {})
    after = bridge_state.read_text(encoding="utf-8")
    if after != before:
        failures.append("live_user_turn rewrote runtime_bridge_state")

    _write(temp_root / "memory/context/turn_mode_state.md", "- mode: maintenance_schedule_turn\n")
    maintenance_result = await plugin.pre_llm_call([{"role": "user", "content": "timer"}])
    if not maintenance_result:
        failures.append("runtime bridge was not injected into maintenance_schedule_turn")
    elif maintenance_result[-1].get("role") != "system" or "[runtime_bridge]" not in str(
        maintenance_result[-1].get("content", "")
    ):
        failures.append("maintenance runtime bridge prompt shape is wrong")

    return failures


def main() -> int:
    root = ROOT
    _ensure_import_paths(root)
    with tempfile.TemporaryDirectory(prefix="xinyu-automation-live-") as tmp:
        failures = asyncio.run(_exercise(Path(tmp)))

    if failures:
        print("Automation bridge live-turn smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Automation bridge live-turn smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
