from __future__ import annotations

import shutil
from pathlib import Path

from xinyu_codex_delegate import CodexDelegateResult
from xinyu_core_bridge import XinYuBridgeRuntime
from xinyu_qq_outbox import claim_next_qq_outbox_message


def main() -> int:
    root = Path(__file__).resolve().parent / ".codex_completion_outbox_smoke_runtime"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    try:
        runtime = XinYuBridgeRuntime(
            xinyu_dir=root,
            turn_timeout_seconds=1,
            max_text_chars=1200,
            settle_seconds=0,
            outward_renderer=False,
            autonomous_maintenance_enabled=False,
        )
        report_path = root / "codex-qq-smoke-report.md"
        request_path = root / "codex-qq-smoke.md"
        report_path.write_text("Summary: smoke completed\n", encoding="utf-8")
        request_path.write_text("Task: smoke\n", encoding="utf-8")
        result = CodexDelegateResult(
            accepted=True,
            reply="smoke completed",
            request_path=str(request_path),
            workspace_path=str(root),
            report_path=str(report_path),
            last_message_path="",
            exit_code=0,
            timed_out=False,
            stdout_tail="",
            stderr_tail="",
            notes=[],
        )
        runtime._enqueue_codex_completion_if_needed(
            {
                "source": "qq_gateway_codex_execute_message",
                "user_id": "42",
                "job_id": "codex-qq-smoke",
                "metadata": {},
            },
            result=result,
            text="smoke codex completion",
            auto_study=True,
            handoff_notes=[],
        )

        message_claim = claim_next_qq_outbox_message(root, {"claim_id": "claim-message", "adapter": "smoke"})
        if not message_claim.get("message_claimed"):
            print("codex_completion_outbox_smoke failed: completion message not queued")
            return 1
        if message_claim.get("source") != "codex_completion":
            print(f"codex_completion_outbox_smoke failed: wrong message source {message_claim.get('source')!r}")
            return 1
        if "codex-qq-smoke-report.md" not in str(message_claim.get("message", "")):
            print("codex_completion_outbox_smoke failed: report label missing from completion message")
            return 1

        file_claim = claim_next_qq_outbox_message(root, {"claim_id": "claim-file", "adapter": "smoke"})
        if not file_claim.get("message_claimed"):
            print("codex_completion_outbox_smoke failed: report attachment not queued")
            return 1
        if file_claim.get("message_type") != "file":
            print(f"codex_completion_outbox_smoke failed: expected file claim, got {file_claim.get('message_type')!r}")
            return 1
        if file_claim.get("file_name") != "codex-qq-smoke-report.md":
            print(f"codex_completion_outbox_smoke failed: wrong report file name {file_claim.get('file_name')!r}")
            return 1

        print("codex_completion_outbox_smoke: ok")
        return 0
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
