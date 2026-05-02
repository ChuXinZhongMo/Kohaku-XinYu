from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from xinyu_codex_delegate import extract_urls, looks_like_codex_request, preview_codex_delegate_paths


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[2]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    failures: list[str] = []
    codex = shutil.which("codex")
    if not codex:
        failures.append("codex CLI not found on PATH")
    else:
        completed = subprocess.run(
            [codex, "exec", "--help"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
        if completed.returncode != 0 or "Run Codex non-interactively" not in completed.stdout:
            failures.append("codex exec help is unavailable")

    if extract_urls("学习 https://example.com/a.pdf") != ["https://example.com/a.pdf"]:
        failures.append("URL extraction failed")
    if not looks_like_codex_request("用 codex 看一下这个项目"):
        failures.append("explicit codex request was not detected")
    if not looks_like_codex_request("学习这个论文 https://example.com/paper.pdf"):
        failures.append("learning URL request was not detected")
    if not looks_like_codex_request("心玉，帮我操作电脑，把本地文件整理一下"):
        failures.append("natural local-operation request was not detected")
    if not looks_like_codex_request(r"帮我读取 D:\XinYu\XinYu-Local-Scope\Workspace\notes.md 并写报告"):
        failures.append("local path operation request was not detected")
    if looks_like_codex_request("我该怎么操作电脑才安全？"):
        failures.append("question-only local operation was incorrectly detected as codex request")
    if looks_like_codex_request("普通聊一句，不要动电脑"):
        failures.append("ordinary chat was incorrectly detected as codex request")
    preview = preview_codex_delegate_paths(ROOT, {"job_id": "codex-qq-20260428T120000"})
    if not preview["report_path"].endswith(r"Outbox\codex-qq-20260428T120000-report.md"):
        failures.append("Codex delegate path preview failed")

    checks = {
        ROOT / "xinyu_bridge_http.py": ('"/codex/execute"', "runtime.codex_execute"),
        ROOT / "xinyu_core_bridge.py": (
            "async def codex_execute",
            "run_codex_delegate",
            "preview_codex_delegate_paths",
            "handoff_codex_to_dream",
            "codex_delegate_background:scheduled",
            "dream_handoff_on_timeout:armed",
            'BRIDGE_VERSION = "',
            "Path(report_path).name",
            "本地 Codex Outbox",
            "_enqueue_codex_completion_if_needed",
            "enqueue_qq_outbox_message",
        ),
        ROOT / "xinyu_qq_outbox.py": (
            "enqueue_qq_outbox_message",
            "claim_next_qq_outbox_message",
            "ack_qq_outbox_message",
            "QQ Outbox Dispatch State",
        ),
        ROOT / "xinyu_codex_dream_handoff.py": (
            "handoff_codex_to_dream",
            "dream_seeds.md",
            "reflection_queue.md",
            "run_dream_output",
        ),
        ROOT / "xinyu_codex_delegate.py": (
            "codex",
            "--full-auto",
            "--add-dir",
            "xinyu_learning_library.py",
            "github_pull_fallback",
            "sandbox_workspace_write.network_access=true",
            "enabled_for_task_urls",
            "visible_window_policy:required",
            "visible_window_request_overridden:true",
        ),
    }
    for path, markers in checks.items():
        text = path.read_text(encoding="utf-8-sig")
        for marker in markers:
            if marker not in text:
                failures.append(f"{path.name} missing marker: {marker}")

    gateway_text = (ROOT / "xinyu_qq_gateway.py").read_text(encoding="utf-8-sig")
    gateway_required = (
        "codex_command_prefixes",
        "qq_gateway_codex_execute_message",
        "codex_auxiliary_brain",
        "direct_cli_execution",
        "self.client.codex_execute",
        "_poll_qq_outbox",
        "qq_outbox_ack",
    )
    for marker in gateway_required:
        if marker not in gateway_text:
            failures.append(f"xinyu_qq_gateway.py missing safe Codex route marker: {marker}")
    for forbidden in ("subprocess.run", "shell=True", "--full-auto"):
        if forbidden in gateway_text:
            failures.append(f"xinyu_qq_gateway.py must not directly execute Codex CLI: {forbidden}")

    core_text = (ROOT / "xinyu_core_bridge.py").read_text(encoding="utf-8-sig")
    for marker in ('payload["visible_window"] = True', 'payload["window_title"]'):
        if marker not in core_text:
            failures.append(f"xinyu_core_bridge.py missing forced visible Codex window marker: {marker}")
    for forbidden in ("报告会写到：{report_path}", "报告在：{report_path}", "请求留在：{request_path}"):
        if forbidden in core_text:
            failures.append(f"xinyu_core_bridge.py visible Codex reply leaks raw local path marker: {forbidden}")

    if failures:
        print("Codex delegate smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Codex delegate smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
