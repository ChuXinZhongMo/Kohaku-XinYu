from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

from pathlib import Path
import tempfile

from xinyu_self_code_approval import (
    active_self_code_approval_request,
    consume_self_code_approval,
    create_direct_self_code_approval,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _seed_pending_request(root: Path) -> None:
    _write(
        root / "memory/context/proactive_request_state.md",
        """# Proactive Request State

## Current Request
- request_id: proreq-self-code-smoke
- created_at: 2026-05-02T10:00:00+08:00
- status: ready
- kind: permission
- source: self_thought
- focus_kind: self_code_approval
- focus_label: self-code-runtime-fix
- evidence_label: XinYu wants to patch one runtime continuity bug
- evidence_hash: sha256:abcdef1234567890
- concrete_question: 我想申请让 Codex 改一个小范围运行时代码补丁，可以吗？
- requested_action: owner_permission
- after_owner_replies: if owner approves, consume one-time ticket and execute
""",
    )


def main() -> int:
    failures: list[str] = []
    payload = {"message_type": "private", "user_id": "owner", "metadata": {"is_owner_user": True}}

    with tempfile.TemporaryDirectory(prefix="xinyu-self-code-no-ticket-") as tmp:
        root = Path(tmp)
        result = consume_self_code_approval(
            root,
            payload,
            owner_text="同意，可以进行修改",
            session_key="qq:private:owner",
        )
        if result.get("approved"):
            failures.append("approval without pending QQ application should not be accepted")

    with tempfile.TemporaryDirectory(prefix="xinyu-self-code-direct-") as tmp:
        root = Path(tmp)
        result = create_direct_self_code_approval(
            root,
            payload,
            owner_text="可以，直接主动修改你的代码，我授权了。",
            session_key="qq:private:owner",
            reply="那我可以试试。",
        )
        if not result.get("approved") or "task_text" not in result:
            failures.append(f"direct owner-private grant was not accepted: {result}")
        state = _read(root / "memory/context/self_code_approval_state.md")
        for marker in (
            "status: approved_once",
            "approval_route: direct_owner_private_qq_request",
            "require_prior_qq_application: false",
            "direct_owner_private_grant: explicit_owner_private_request_allowed_once",
            "direct_silent_self_edit: blocked",
        ):
            if marker not in state:
                failures.append(f"direct grant state missing marker: {marker}")
        task_text = result.get("task_text", "")
        if "Owner directly requested or authorized XinYu to modify her own code" not in task_text:
            failures.append("direct grant task did not carry direct owner-private boundary")

    with tempfile.TemporaryDirectory(prefix="xinyu-self-code-approval-") as tmp:
        root = Path(tmp)
        _seed_pending_request(root)
        active = active_self_code_approval_request(root)
        if active.get("request_id") != "proreq-self-code-smoke":
            failures.append(f"pending self-code request not detected: {active}")
        result = consume_self_code_approval(
            root,
            payload,
            owner_text="同意，可以进行修改",
            session_key="qq:private:owner",
            reply="收到",
        )
        if not result.get("approved") or "task_text" not in result:
            failures.append(f"pending request approval was not consumed: {result}")
        state = _read(root / "memory/context/self_code_approval_state.md")
        for marker in (
            "status: approved_once",
            "require_prior_qq_application: true",
            "approval_is_one_time: true",
            "direct_silent_self_edit: blocked",
        ):
            if marker not in state:
                failures.append(f"approval state missing marker: {marker}")
        if "one-time bounded approval" not in result.get("task_text", ""):
            failures.append("codex task did not carry one-time approval boundary")

    with tempfile.TemporaryDirectory(prefix="xinyu-self-code-deny-") as tmp:
        root = Path(tmp)
        _seed_pending_request(root)
        result = consume_self_code_approval(
            root,
            payload,
            owner_text="不同意，先别改",
            session_key="qq:private:owner",
        )
        if not result.get("denied") or result.get("approved"):
            failures.append(f"denial was not recorded correctly: {result}")
        state = _read(root / "memory/context/self_code_approval_state.md")
        if "status: denied" not in state:
            failures.append("denied state missing")

    if failures:
        print("FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("OK self_code_approval_smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
