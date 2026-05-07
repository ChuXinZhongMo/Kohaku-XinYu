from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

from xinyu_codex_delegate import (
    _build_prompt,
    _imagegen_cli_path,
    _is_image_artifact_task,
    _load_delegate_local_env,
    _promote_agent_report,
    _trusted_public_search_task_allowed,
    _write_missing_report_from_last_message,
    extract_urls,
    looks_like_codex_request,
    looks_like_owner_local_write_request,
    preview_codex_delegate_paths,
    run_codex_delegate,
)
from xinyu_core_bridge import XinYuBridgeRuntime
from xinyu_tool_intent_router import ToolIntentRouter
from xinyu_tool_targets import TargetRegistry


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
    if not looks_like_codex_request("用codex去搜搜吧"):
        failures.append("compact explicit Codex search request was not detected")
    if not looks_like_codex_request("Use Codex auxiliary brain for this owner-approved task:\n搜索该怎么确定自己想成为什么样的人"):
        failures.append("internal model Codex delegate payload was not detected")
    if not looks_like_codex_request(r"让 Codex 在新窗口里看 D:\XinYu 的代码并改一下"):
        failures.append("direct Codex local code request was not detected")
    if not looks_like_codex_request("学习这个论文 https://example.com/paper.pdf"):
        failures.append("learning URL request was not detected")
    if not looks_like_codex_request("心玉，帮我操作电脑，把本地文件整理一下"):
        failures.append("natural local-operation request was not detected")
    if not looks_like_codex_request(r"帮我读取 D:\XinYu\XinYu-Local-Scope\Workspace\notes.md 并写报告"):
        failures.append("local path operation request was not detected")
    if not looks_like_owner_local_write_request(r"让 Codex 修改 D:\XinYu\XinYu-Local-Scope\Workspace\notes.md 并保存"):
        failures.append("owner local write request was not detected")
    if looks_like_owner_local_write_request("Codex 不能内置到 XinYu 的前端吗"):
        failures.append("owner local write detector treated a question as write approval")
    if looks_like_codex_request("我该怎么操作电脑才安全？"):
        failures.append("question-only local operation was incorrectly detected as codex request")
    if looks_like_codex_request("普通聊一句，不要动电脑"):
        failures.append("ordinary chat was incorrectly detected as codex request")
    if looks_like_codex_request("我没让你用 codex 干活"):
        failures.append("Codex correction was incorrectly detected as a request")
    if looks_like_codex_request("不是提到 codex 干活就是让你用 codex 干活"):
        failures.append("Codex meta-discussion was incorrectly detected as a request")
    if looks_like_codex_request("准备让 codex 开始干活了"):
        failures.append("future owner intention was incorrectly detected as a Codex request")
    if looks_like_codex_request("Codex 没跑顺，退出码 3221225786"):
        failures.append("Codex failure report was incorrectly detected as a request")
    readable_meta_text = "说起来你运行codex好像每次都没成功的样子"
    if looks_like_codex_request(readable_meta_text):
        failures.append("readable Codex failure meta-discussion was incorrectly detected as a request")
    if looks_like_codex_request("怎么直接就开codex了，然后还是标准AI报告腔"):
        failures.append("readable Codex report-tone correction was incorrectly detected as a request")
    if looks_like_codex_request("怎么开codex了，我没让你启动codex"):
        failures.append("readable Codex accidental-start correction was incorrectly detected as a request")
    if not looks_like_codex_request("让 Codex 查一下这个启动问题"):
        failures.append("readable explicit Codex task was not detected")
    if not looks_like_codex_request("开 Codex 查一下这个启动问题"):
        failures.append("readable explicit Codex start task was not detected")
    owner_payload = {"message_type": "private", "metadata": {"is_owner_user": True}}
    router = ToolIntentRouter(TargetRegistry(ROOT, targets={}))
    if router.route(readable_meta_text, owner_payload).kind == "action_request":
        failures.append("action router treated Codex failure meta-discussion as a tool request")
    if router.route("怎么直接就开codex了，然后还是标准AI报告腔", owner_payload).kind == "action_request":
        failures.append("action router treated Codex report-tone correction as a tool request")
    if router.route("怎么开codex了，我没让你启动codex", owner_payload).kind == "action_request":
        failures.append("action router treated Codex accidental-start correction as a tool request")
    explicit_route = router.route("让 Codex 查一下这个启动问题", owner_payload)
    if explicit_route.kind != "action_request" or not explicit_route.request or explicit_route.request.tool != "codex_delegate":
        failures.append("action router missed readable explicit Codex task")
    desktop_codex_route = router.route(
        "修改 XinYu_Desktop 前端输入栏并保存",
        {"message_type": "desktop_private", "metadata": {"is_owner_user": True, "desktop_codex_mode": True}},
    )
    if desktop_codex_route.kind != "action_request" or not desktop_codex_route.request or desktop_codex_route.request.tool != "codex_delegate":
        failures.append("action router missed desktop Codex mode task")
    if not _trusted_public_search_task_allowed("search public web sources for PyMuPDF docs"):
        failures.append("trusted public-search task was not allowed")
    if _trusted_public_search_task_allowed(r"search public web sources and read D:\XinYu\config.yaml"):
        failures.append("trusted local file task was incorrectly allowed")
    trusted_scope_reject = run_codex_delegate(
        ROOT,
        {
            "text": r"search public web sources and read D:\XinYu\config.yaml",
            "metadata": {"trusted_public_search_task": True},
        },
    )
    if trusted_scope_reject.notes != ["codex_delegate_rejected:trusted_scope"]:
        failures.append(f"trusted local task did not stop at delegate boundary: {trusted_scope_reject.notes}")
    preview = preview_codex_delegate_paths(ROOT, {"job_id": "codex-qq-20260428T120000"})
    if not preview["report_path"].endswith(r"Outbox\codex-qq-20260428T120000-report.md"):
        failures.append("Codex delegate path preview failed")
    if r"Workspace\codex-qq-20260428T120000\codex-qq-20260428T120000-report.md" not in preview["agent_report_path"]:
        failures.append("Codex delegate agent report path preview failed")
    with tempfile.TemporaryDirectory(prefix="xinyu-codex-promote-") as tmp:
        tmp_root = Path(tmp)
        agent_report = tmp_root / "workspace-report.md"
        final_report = tmp_root / "outbox" / "final-report.md"
        agent_report.write_text("# Agent report\n\nready\n", encoding="utf-8")
        if not _promote_agent_report(agent_report_path=agent_report, report_path=final_report):
            failures.append("agent report promotion returned false")
        elif "ready" not in final_report.read_text(encoding="utf-8"):
            failures.append("agent report promotion did not copy content")
    with tempfile.TemporaryDirectory(prefix="xinyu-codex-capture-") as tmp:
        tmp_root = Path(tmp)
        last_message = tmp_root / "last-message.txt"
        captured_report = tmp_root / "captured-report.md"
        last_message.write_text("final codex message\n", encoding="utf-8")
        if not _write_missing_report_from_last_message(
            report_path=captured_report,
            task_text="capture smoke",
            last_message_path=last_message,
            stdout_tail="",
            stderr_tail="",
        ):
            failures.append("missing Codex report capture returned false")
        elif "final codex message" not in captured_report.read_text(encoding="utf-8"):
            failures.append("missing Codex report capture did not include last message")
    fallback_source = ROOT / "runtime" / "codex-smoke-fallback-report.md"
    try:
        fallback_source.parent.mkdir(parents=True, exist_ok=True)
        fallback_source.write_text("# Full fallback report\n\nkept details\n", encoding="utf-8")
        with tempfile.TemporaryDirectory(prefix="xinyu-codex-fallback-copy-") as tmp:
            tmp_root = Path(tmp)
            last_message = tmp_root / "last-message.txt"
            captured_report = tmp_root / "captured-report.md"
            last_message.write_text(f"Fallback report written here:\n`{fallback_source}`\n", encoding="utf-8")
            if not _write_missing_report_from_last_message(
                report_path=captured_report,
                task_text="fallback copy smoke",
                last_message_path=last_message,
                stdout_tail="",
                stderr_tail="",
            ):
                failures.append("fallback report copy returned false")
            elif "kept details" not in captured_report.read_text(encoding="utf-8"):
                failures.append("fallback report copy did not preserve full report")
    finally:
        fallback_source.unlink(missing_ok=True)
    self_code_prompt = _build_prompt(
        xinyu_dir=ROOT,
        local_scope=ROOT,
        request_path=ROOT / "request.md",
        workspace=ROOT / "workspace",
        report_path=ROOT / "report.md",
        task_text="Self-code approval id: selfcode-direct-smoke\nOwner says self-code/code modification ability is weak.",
        urls=[],
    )
    if "Self-code implementation mode" not in self_code_prompt or "do not reduce it to research-only output" not in self_code_prompt:
        failures.append("self-code Codex prompt did not enable implementation mode")
    local_write_prompt = _build_prompt(
        xinyu_dir=ROOT,
        local_scope=ROOT,
        request_path=ROOT / "request.md",
        workspace=ROOT / "workspace",
        report_path=ROOT / "report.md",
        task_text="让 Codex 修改 XinYu_Desktop 前端文件并保存",
        urls=[],
        local_write_approved=True,
    )
    if "Owner-approved local write mode" not in local_write_prompt or "do not reduce it to report-only output" not in local_write_prompt:
        failures.append("owner local write Codex prompt did not enable implementation mode")
    image_prompt = _build_prompt(
        xinyu_dir=ROOT,
        local_scope=ROOT,
        request_path=ROOT / "request.md",
        workspace=ROOT / "workspace",
        report_path=ROOT / "report.md",
        task_text="用 Codex 生成一张流程图图片并发给我",
        urls=[],
    )
    if not _is_image_artifact_task("用 Codex 生成一张流程图图片并发给我"):
        failures.append("image artifact Codex task was not detected")
    if "Image artifact mode" not in image_prompt or "Generated image path:" not in image_prompt:
        failures.append("image artifact Codex prompt did not request generated image paths")
    if "gpt-image-2" not in image_prompt or "OPENAI_API_KEY" not in image_prompt or "XINYU_OPENAI_API_KEY" not in image_prompt:
        failures.append("image artifact Codex prompt did not describe GPT image API environment")
    if not looks_like_codex_request("帮我生成一张头像"):
        failures.append("natural avatar image generation was not detected as Codex-capable")
    if _imagegen_cli_path().name != "image_gen.py":
        failures.append("imagegen CLI path resolution failed")
    book_task = "\u641c\u7d22\u756a\u8304\u5c0f\u8bf4\uff1a\u300a\u5168\u5458\u6076\u4ed9\u300b\u548c\u300a\u7cfb\u7edf\u5f03\u6211\u4e0d\u987e\uff0c\u6211\u8ba4\u5929\u9053\u4e3a\u7236\u300b"
    book_subject = XinYuBridgeRuntime._codex_task_subject(book_task)
    book_reply = XinYuBridgeRuntime._codex_started_reply(book_subject, 0)
    if "\u300a\u5168\u5458\u6076\u4ed9\u300b" not in book_subject or "\u7ed3\u679c\u6211\u63a5\u56de\u6765" not in book_reply:
        failures.append("Codex start reply did not use the owner task context")
    if "Xinyu codex" in book_reply or "Outbox" in book_reply or "\u7a97\u53e3\u6807\u9898" in book_reply:
        failures.append("Codex start reply still exposes mechanical window/report template text")
    with tempfile.TemporaryDirectory(prefix="xinyu-codex-visible-") as tmp:
        tmp_root = Path(tmp)
        report = tmp_root / "codex-qq-20260507T020900-report.md"
        report.write_text(
            "Request: `codex-qq-20260507T020900`; Created: 2026-05-07; Owner task: `说起来你运行codex好像每次都没成功的样子`\n"
            "* 这次没有真正的新任务，只是一次误触发。\n",
            encoding="utf-8",
        )
        runtime = object.__new__(XinYuBridgeRuntime)
        runtime.xinyu_dir = ROOT
        visible = runtime._codex_completion_outbox_message(
            SimpleNamespace(
                report_path=str(report),
                last_message_path="",
                accepted=True,
                timed_out=False,
                exit_code=None,
            ),
            text="说起来你运行codex好像每次都没成功的样子",
            auto_study=True,
            handoff_notes=[],
        )
        forbidden_visible = ("Request:", "Created:", "Owner task:", "报告名", "Outbox", "codex-qq-", ".md", "* ")
        if any(marker in visible for marker in forbidden_visible):
            failures.append(f"Codex completion visible reply leaked report metadata: {visible}")

    original_openai = os.environ.pop("OPENAI_API_KEY", None)
    original_xinyu_openai = os.environ.pop("XINYU_OPENAI_API_KEY", None)
    try:
        with tempfile.TemporaryDirectory(prefix="xinyu-image-env-") as tmp:
            env_root = Path(tmp)
            (env_root / "xinyu.local.env").write_text("XINYU_OPENAI_API_KEY=smoke-openai-key\n", encoding="utf-8")
            env_notes = _load_delegate_local_env(env_root)
            if os.environ.get("OPENAI_API_KEY") != "smoke-openai-key":
                failures.append("XINYU_OPENAI_API_KEY was not mirrored to OPENAI_API_KEY")
            if "openai_image_key:available" not in env_notes:
                failures.append("image API key availability note was not recorded")
    finally:
        if original_openai is not None:
            os.environ["OPENAI_API_KEY"] = original_openai
        else:
            os.environ.pop("OPENAI_API_KEY", None)
        if original_xinyu_openai is not None:
            os.environ["XINYU_OPENAI_API_KEY"] = original_xinyu_openai
        else:
            os.environ.pop("XINYU_OPENAI_API_KEY", None)

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
            "_codex_reply_variant",
            "_codex_task_subject",
            "_enqueue_codex_completion_if_needed",
            "enqueue_qq_outbox_message",
            "enqueue_qq_outbox_image",
            "_codex_generated_image_artifacts",
            "_looks_like_codex_image_generation_task",
        ),
        ROOT / "xinyu_codex_service.py": (
            "codex_status_reply",
            "codex_completion_outbox_message",
            "enqueue_codex_completion_if_needed",
            "enqueue_qq_outbox_message",
            "enqueue_qq_outbox_image",
            "codex_generated_image_artifacts",
            "looks_like_codex_image_generation_task",
            "结果我接回来",
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
            "--ask-for-approval",
            "--skip-git-repo-check",
            "--search",
            "--add-dir",
            "xinyu_learning_library.py",
            "github_pull_fallback",
            "sandbox_workspace_write.network_access=true",
            "web_search:enabled",
            "enabled_for_task_urls",
            "enabled_for_image_generation",
            "visible_window_policy:required",
            "visible_window_request_overridden:true",
            "For self-code approval tasks",
            "Self-code implementation mode",
            "gpt-image-2",
            "XINYU_OPENAI_API_KEY",
            "imagegen_cli",
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
    for forbidden in (
        "开了，我让 Codex 在新窗口里跑",
        "窗口标题是 {CODEX_VISIBLE_WINDOW_TITLE}",
        "报告会落到本地 Codex Outbox",
        "报告会写到：{report_path}",
        "报告在：{report_path}",
        "请求留在：{request_path}",
    ):
        if forbidden in core_text:
            failures.append(f"xinyu_core_bridge.py visible Codex reply leaks raw local path marker: {forbidden}")
    if "codex_completion_report" in core_text:
        failures.append("xinyu_core_bridge.py still queues Codex report files to QQ")

    if failures:
        print("Codex delegate smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Codex delegate smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
