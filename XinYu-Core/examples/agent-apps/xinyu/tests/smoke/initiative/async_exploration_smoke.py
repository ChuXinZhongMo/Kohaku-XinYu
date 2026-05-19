from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

from pathlib import Path
import tempfile
from types import SimpleNamespace

from xinyu_async_exploration import (
    async_exploration_outbox_message,
    build_async_exploration_prompt_block,
    create_async_exploration_closure,
    update_async_exploration_from_codex,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    failures: list[str] = []

    with tempfile.TemporaryDirectory(prefix="xinyu-async-exploration-") as tmp:
        root = Path(tmp)
        payload = {"user_id": "owner", "metadata": {"is_owner_user": True}}
        closure = create_async_exploration_closure(
            root,
            payload,
            session_key="qq:private:owner",
            user_text="这个问题我不确定，先验证",
            draft_reply="[WAIT_TO_THINK: verify exact behavior]",
            task_text="Verify exact behavior with read-only checks.",
            execution_plan="risk_level: read_only\nsteps: 1. inspect only",
        )
        resume_id = closure["resume_id"]
        state = _read(root / "memory/context/async_exploration_state.md")
        if not resume_id.startswith("wait-"):
            failures.append(f"resume id shape invalid: {resume_id}")
        for marker in (
            "Async Exploration State",
            "status: delegated_to_codex",
            "execution_plan: risk_level: read_only",
            f"resume_id: {resume_id}",
        ):
            if marker not in state:
                failures.append(f"closure state missing marker: {marker}")

        update = update_async_exploration_from_codex(
            root,
            resume_id=resume_id,
            result=None,
            error="RuntimeError: boom with token=secret",
            owner_intervention="owner narrowed scope",
        )
        state = _read(root / "memory/context/async_exploration_state.md")
        prompt = build_async_exploration_prompt_block(root)
        message = async_exploration_outbox_message(update)
        for marker in (
            "status: failed_snapshot_saved",
            "failure_kind: bridge_error",
            "owner_intervention: owner narrowed scope",
            "result_quality: failed",
        ):
            if marker not in state:
                failures.append(f"failed state missing marker: {marker}")
        for marker in (
            "truth_rules:",
            "expression_rules:",
            "owner_intervention:",
            "owner-guided recovery",
        ):
            if marker not in prompt:
                failures.append(f"prompt block missing marker: {marker}")
        if "resume_id:" in message or resume_id in message:
            failures.append("outbox message leaked resume id")
        if "引用这条" not in message:
            failures.append("outbox message did not explain quote-based continuation")
        if "stdout" in message.lower() or "stderr" in message.lower():
            failures.append("outbox message leaked raw output wording")
        if "token=secret" in message:
            failures.append("outbox message leaked sensitive token")

    with tempfile.TemporaryDirectory(prefix="xinyu-async-report-") as tmp:
        root = Path(tmp)
        report = root / "report.md"
        _write(
            report,
            """# Report

- checked fixture A
- verified scope: only parser branch
- unknowns remain: network branch
- local path C:\\secret\\x.txt should be scrubbed
""",
        )
        create_async_exploration_closure(
            root,
            {"user_id": "owner", "metadata": {"is_owner_user": True}},
            session_key="qq:private:owner",
            user_text="继续",
            draft_reply="[WAIT_TO_THINK]",
            task_text="Read report.",
        )
        resume_id = _read(root / "memory/context/async_exploration_state.md").split("resume_id: ", 1)[1].splitlines()[0]
        result = SimpleNamespace(accepted=True, timed_out=False, exit_code=0, report_path=str(report), request_path="request.md")
        update = update_async_exploration_from_codex(root, resume_id=resume_id, result=result)
        prompt = build_async_exploration_prompt_block(root)
        if update["result_quality"] != "usable_partial":
            failures.append(f"usable report should be usable_partial: {update}")
        if "verified scope" not in prompt:
            failures.append("usable report summary did not reach prompt block")
        if "C:\\secret" in prompt:
            failures.append("prompt block leaked local path")

    if failures:
        print("FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("OK async_exploration_smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
