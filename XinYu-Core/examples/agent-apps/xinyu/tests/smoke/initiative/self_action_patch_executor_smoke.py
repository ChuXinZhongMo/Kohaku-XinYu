from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import tempfile
from pathlib import Path

from xinyu_self_action_gateway import decide_self_action_approval, run_self_action_gateway
from xinyu_self_action_patch_executor import STATE_MD_REL, TASK_MD_REL, run_self_action_patch_executor
from xinyu_self_chosen_goal_ecology import run_self_chosen_goal_ecology


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-self-action-patch-") as tmp:
        root = Path(tmp)
        _write(root / "xinyu_self_chosen_goal_ecology.py", "def ok():\n    return 'goal'\n")
        _write(root / "xinyu_goal_outcome_observer.py", "def ok():\n    return 'observer'\n")
        _write(root / "xinyu_self_action_gateway.py", "def ok():\n    return 'action'\n")
        _write(root / "memory/context/recent_context.md", "Codex runtime pytest work remains active.")
        run_self_chosen_goal_ecology(root, checked_at="2026-05-16T10:00:00+08:00", trigger="smoke")
        run_self_action_gateway(root, checked_at="2026-05-16T10:01:00+08:00", trigger="smoke")
        decide_self_action_approval(
            root,
            queue_id="latest",
            decision="approved",
            decided_at="2026-05-16T10:02:00+08:00",
            execute=True,
        )
        result = run_self_action_patch_executor(
            root,
            checked_at="2026-05-16T10:03:00+08:00",
            execution_level="prepare",
        )
        if result.get("status") != "prepared":
            failures.append(f"expected prepared patch task, got {result}")
        state = _read(root / STATE_MD_REL)
        task = _read(root / TASK_MD_REL)
        if "execute_codex_mode" not in state:
            failures.append("patch executor state missing execution boundary")
        if "Owner-approved Self Action Gateway patch executor task" not in task:
            failures.append("patch executor task missing approved task text")

    core_text = _read(ROOT / "xinyu_core_bridge.py")
    context_text = _read(ROOT / "xinyu_runtime_context.py")
    presence_text = _read(ROOT / "xinyu_runtime_presence.py")
    if "run_self_action_patch_executor(" not in core_text:
        failures.append("xinyu_core_bridge.py does not prepare self action patch executor")
    if "memory/context/self_action_patch_executor_state.md" not in context_text:
        failures.append("runtime context does not include patch executor state")
    if "runtime/self_action_patch_executor/trace.jsonl" not in presence_text:
        failures.append("runtime presence does not summarize patch executor trace")

    if failures:
        print("Self action patch executor smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Self action patch executor smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
