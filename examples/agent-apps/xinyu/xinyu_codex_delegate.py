from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from xinyu_learning_library import DEFAULT_MAX_BYTES, add_url_material, stage_manifest_record
from xinyu_local_scope import default_local_scope_root, ensure_local_scope, resolve_local_scope_path


URL_PATTERN = re.compile(r"https?://[^\s<>()\"'，。！？、]+", re.I)
DEFAULT_TIMEOUT_SECONDS = 3600
DEFAULT_VISIBLE_WINDOW_TITLE = "Xinyu codex"


@dataclass(frozen=True)
class CodexDelegateResult:
    accepted: bool
    reply: str
    request_path: str
    workspace_path: str
    report_path: str
    last_message_path: str
    exit_code: int | None
    timed_out: bool
    stdout_tail: str
    stderr_tail: str
    notes: list[str]


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    if value is None:
        return default
    return bool(value)


def _as_int(value: Any, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def extract_urls(text: str) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for match in URL_PATTERN.finditer(text):
        url = match.group(0).rstrip(".,;:!?，。；：！？")
        if url and url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


CODEX_NEGATIVE_MARKERS = (
    "别用codex",
    "不要用codex",
    "不用codex",
    "先别用codex",
    "别操作电脑",
    "不要操作电脑",
    "不用操作电脑",
    "先别操作电脑",
    "别动电脑",
    "不要动电脑",
    "不用动电脑",
    "先别动电脑",
    "别改文件",
    "不要改文件",
    "不用改文件",
    "先别改文件",
)

CODEX_URL_MARKERS = (
    "学习",
    "学一下",
    "读一下",
    "阅读",
    "看一下",
    "下载",
    "源码",
    "仓库",
    "论文",
    "网址",
    "链接",
    "网页",
    "消化",
    "整理",
)

CODEX_LOCAL_ACTION_MARKERS = (
    "操作",
    "处理",
    "读取",
    "读一下",
    "打开",
    "查看",
    "看一下",
    "分析",
    "识别",
    "整理",
    "写入",
    "写到",
    "记录到",
    "保存",
    "修改",
    "改一下",
    "编辑",
    "替换",
    "创建",
    "新建",
    "生成",
    "下载",
    "克隆",
    "拉取",
    "同步",
    "更新",
    "运行",
    "跑一下",
    "跑测试",
    "测试",
    "验证",
)

CODEX_LOCAL_TARGET_MARKERS = (
    "本机",
    "本地",
    "电脑",
    "计算机",
    "文件",
    "文件夹",
    "目录",
    "路径",
    "磁盘",
    "硬盘",
    "项目",
    "代码",
    "源码",
    "仓库",
    "脚本",
    "配置",
    "日志",
    "图片",
    "截图",
    "文档",
    "workspace",
    "xinyu-local-scope",
    "local-scope",
    "outbox",
    "requests",
)

CODEX_DIRECT_LOCAL_MARKERS = (
    "操作电脑",
    "控制电脑",
    "动电脑",
    "改本地文件",
    "改文件",
    "整理文件",
    "读取文件",
    "读文件",
    "写文件",
    "写入文件",
    "下载资料",
    "下载论文",
    "下载仓库",
    "克隆仓库",
    "拉取仓库",
)

CODEX_QUESTION_MARKERS = ("怎么", "如何", "为什么", "是什么", "什么意思", "？", "?")
CODEX_IMPERATIVE_MARKERS = (
    "帮我",
    "帮忙",
    "替我",
    "给我",
    "把",
    "请",
    "麻烦",
    "去",
    "用",
    "让",
    "开始",
    "执行",
    "处理",
    "改",
    "整理",
    "下载",
    "读取",
    "打开",
    "写入",
    "创建",
    "修",
    "跑",
    "检查",
    "分析",
)

LOCAL_PATH_PATTERN = re.compile(r"(?i)(?:[a-z]:[\\/]|\\\\|(?:^|[\s`'\"“”‘’])\.{1,2}[\\/])")


def _compact_for_request_detection(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _looks_like_question_only(text: str, normalized: str) -> bool:
    if not _contains_any(normalized, CODEX_QUESTION_MARKERS):
        return False
    return not _contains_any(normalized, CODEX_IMPERATIVE_MARKERS)


def _has_local_path_hint(text: str, normalized: str) -> bool:
    return bool(LOCAL_PATH_PATTERN.search(text)) or _contains_any(normalized, CODEX_LOCAL_TARGET_MARKERS)


def _looks_like_local_operation_request(text: str, normalized: str) -> bool:
    if _looks_like_question_only(text, normalized):
        return False
    has_action = _contains_any(normalized, CODEX_LOCAL_ACTION_MARKERS)
    has_target = _has_local_path_hint(text, normalized)
    if has_action and has_target:
        return True
    return _contains_any(normalized, CODEX_DIRECT_LOCAL_MARKERS)


def looks_like_codex_request(text: str) -> bool:
    normalized = _compact_for_request_detection(text)
    if not normalized:
        return False
    if _contains_any(normalized, CODEX_NEGATIVE_MARKERS):
        return False
    if "codex" in normalized:
        return True
    if extract_urls(text) and _contains_any(text, CODEX_URL_MARKERS):
        return True
    return _looks_like_local_operation_request(text, normalized)


def _stamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")


def _job_name(value: Any = None) -> str:
    text = _safe_str(value).strip()
    if re.fullmatch(r"codex-qq-\d{8}T\d{6}", text):
        return text
    if re.fullmatch(r"\d{8}T\d{6}", text):
        return f"codex-qq-{text}"
    return f"codex-qq-{_stamp()}"


def _tail(text: str, limit: int = 5000) -> str:
    return text[-limit:] if len(text) > limit else text


def _read_text_tail(path: Path, limit: int = 5000) -> str:
    if not path.exists():
        return ""
    for encoding in ("utf-8-sig", "utf-16"):
        try:
            return _tail(path.read_text(encoding=encoding, errors="replace"), limit=limit)
        except OSError:
            return ""
        except UnicodeError:
            continue
    return ""


def _rel_or_abs(path: Path) -> str:
    return str(path)


def preview_codex_delegate_paths(root: Path, payload: dict[str, Any] | None = None) -> dict[str, str]:
    payload = payload or {}
    local_scope = ensure_local_scope(default_local_scope_root(root))
    job_name = _job_name(payload.get("job_id"))
    requests_dir = resolve_local_scope_path(local_scope, "Requests")
    workspace = resolve_local_scope_path(local_scope, Path("Workspace") / job_name)
    outbox = resolve_local_scope_path(local_scope, "Outbox")
    return {
        "job_id": job_name,
        "request_path": str(requests_dir / f"{job_name}.md"),
        "workspace_path": str(workspace),
        "report_path": str(outbox / f"{job_name}-report.md"),
        "last_message_path": str(outbox / f"{job_name}-last-message.txt"),
        "trace_path": str(outbox / f"{job_name}-trace.json"),
    }


def _write_request(
    *,
    request_path: Path,
    task_text: str,
    urls: list[str],
    workspace: Path,
    report_path: Path,
    owner_approved: bool,
) -> None:
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    url_lines = "\n".join(f"- {url}" for url in urls) or "- none"
    request_path.write_text(
        f"""---
title: QQ Codex Delegation Request
request_type: codex_delegate_request
status: requested
created_at: {now}
source: qq_owner_request
---

# QQ Codex Delegation Request

## Goal
- {task_text}

## Input URLs
{url_lines}

## Scope
- owner_approved: {str(owner_approved).lower()}
- workspace: {workspace}
- output_report: {report_path}

## Required Behavior
- Use real Codex execution, not a simulated report.
- Download or inspect public URLs when requested.
- For GitHub pull request URLs, prefer the `.patch` or `.diff` text and stage that as source material.
- For GitHub repositories, use `xinyu_learning_library.py github ... --stage --curated`.
- For papers, raw files, and web pages, use `xinyu_learning_library.py url ... --stage --curated`.
- Do not execute downloaded code.
- Do not read credentials, cookies, tokens, password stores, private full-disk folders, or unrelated personal files.
- Write a concise report to the output report path.
""",
        encoding="utf-8",
    )


def _build_prompt(
    *,
    xinyu_dir: Path,
    local_scope: Path,
    request_path: Path,
    workspace: Path,
    report_path: Path,
    task_text: str,
    urls: list[str],
) -> str:
    python_exe = xinyu_dir / ".venv" / "Scripts" / "python.exe"
    learning_script = xinyu_dir / "xinyu_learning_library.py"
    urls_block = "\n".join(f"- {url}" for url in urls) or "- none"
    return f"""You are Codex running as XinYu's bounded local delegate from a QQ owner request.

This is real execution, not a roleplay. Complete the bounded computer task and write the audit report.

Task text:
{task_text}

URLs:
{urls_block}

Paths:
- XinYu project: {xinyu_dir}
- Local authorized scope: {local_scope}
- Request file: {request_path}
- Workspace: {workspace}
- Required report: {report_path}
- Python: {python_exe}
- Learning library script: {learning_script}

Allowed actions:
- Inspect public URLs from the task.
- Download public pages, papers, raw files, or GitHub repository archives into the workspace/local learning library.
- Use local URL download/staging commands only for owner-specified URLs from the task or recent context; do not crawl or stage arbitrary search-result URLs.
- For GitHub pull request URLs, download the `.patch` or `.diff` text and stage that URL material; do not clone the full repository unless the owner explicitly asks.
- For GitHub repository URLs, run the learning library's `github` subcommand with `--stage --curated --origin owner_supplied`.
- For paper/raw/page URLs, run the learning library's `url` subcommand with `--stage --curated --origin owner_supplied`.
- Read downloaded text for triage.
- Run non-destructive validation/status commands.

Hard blocks:
- Do not execute downloaded code.
- Do not install dependencies.
- Do not delete, move, upload, publish, push, or impersonate.
- Do not broaden URL-fetch tasks into open web crawling. If no URL is supplied, summarize public search findings and write the report without local URL downloads.
- Do not read credentials, cookies, tokens, browser/session files, password stores, or private folders outside the granted scope.
- Do not bypass XinYu source, learning, privacy, or stable-personality gates.

Expected implementation:
1. Create/use the workspace directory.
2. If URLs are present, process each relevant URL.
3. Stage useful learning material through `xinyu_learning_library.py`; do not write stable knowledge directly.
4. Write `{report_path}` with:
   - actions performed
   - downloaded/staged paths
   - material ids or stage ids if created
   - learning triage
   - boundary checks
   - failures if any
5. Final response should be a short status summary and mention the report path.
"""


def _kill_process_tree(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
        return
    try:
        os.kill(pid, 9)
    except OSError:
        pass


def _ps_literal(value: Any) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _write_visible_codex_script(
    *,
    script_path: Path,
    command: list[str],
    cwd: Path,
    prompt_path: Path,
    transcript_path: Path,
    exit_path: Path,
    report_path: Path,
    window_title: str,
) -> None:
    exe = command[0]
    args = command[1:]
    args_block = ", ".join(_ps_literal(arg) for arg in args)
    script_path.write_text(
        "\n".join(
            [
                "$ErrorActionPreference = 'Continue'",
                "$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)",
                "[Console]::InputEncoding = $Utf8NoBom",
                "[Console]::OutputEncoding = $Utf8NoBom",
                "$OutputEncoding = $Utf8NoBom",
                f"try {{ $Host.UI.RawUI.WindowTitle = {_ps_literal(window_title)} }} catch {{ }}",
                f"try {{ [Console]::Title = {_ps_literal(window_title)} }} catch {{ }}",
                f"$Exe = {_ps_literal(exe)}",
                f"$CmdArgs = @({args_block})",
                f"$PromptPath = {_ps_literal(prompt_path)}",
                f"$TranscriptPath = {_ps_literal(transcript_path)}",
                f"$ExitPath = {_ps_literal(exit_path)}",
                f"$ReportPath = {_ps_literal(report_path)}",
                f"Set-Location -LiteralPath {_ps_literal(cwd)}",
                "if (Test-Path -LiteralPath $TranscriptPath) { Remove-Item -LiteralPath $TranscriptPath -Force }",
                "if (Test-Path -LiteralPath $ExitPath) { Remove-Item -LiteralPath $ExitPath -Force }",
                "[Console]::WriteLine('[XinYu Codex] visible Codex CLI window')",
                f"[Console]::WriteLine({_ps_literal('[XinYu Codex] title: ' + window_title)})",
                "[Console]::WriteLine('[XinYu Codex] command started; close this window only if you want to interrupt it.')",
                "[Console]::WriteLine('')",
                "$ExitCode = 1",
                "try {",
                "    Get-Content -LiteralPath $PromptPath -Raw -Encoding UTF8 | & $Exe @CmdArgs 2>&1 | ForEach-Object {",
                "        $Text = ($_ | Out-String)",
                "        [Console]::Write($Text)",
                "        [System.IO.File]::AppendAllText($TranscriptPath, $Text, $Utf8NoBom)",
                "    }",
                "    if ($null -eq $LASTEXITCODE) { $ExitCode = 0 } else { $ExitCode = [int]$LASTEXITCODE }",
                "} catch {",
                "    $Text = ($_ | Out-String)",
                "    [Console]::Write($Text)",
                "    [System.IO.File]::AppendAllText($TranscriptPath, $Text, $Utf8NoBom)",
                "    $ExitCode = 1",
                "}",
                "[System.IO.File]::WriteAllText($ExitPath, [string]$ExitCode, $Utf8NoBom)",
                "[Console]::WriteLine('')",
                "[Console]::WriteLine('[XinYu Codex] exit code: ' + $ExitCode)",
                "[Console]::WriteLine('[XinYu Codex] report: ' + $ReportPath)",
                "[Console]::WriteLine('[XinYu Codex] Press Enter to close this window.')",
                "try { [Console]::ReadLine() | Out-Null } catch { Start-Sleep -Seconds 30 }",
                "exit $ExitCode",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _run_codex_command_visible(
    command: list[str],
    *,
    prompt: str,
    cwd: Path,
    timeout_seconds: int,
    transcript_dir: Path,
    report_path: Path,
    window_title: str,
) -> tuple[int | None, bool, str, str]:
    transcript_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = transcript_dir / "codex-visible-prompt.txt"
    transcript_path = transcript_dir / "codex-visible-transcript.txt"
    exit_path = transcript_dir / "codex-visible-exit.txt"
    script_path = transcript_dir / "codex-visible-launch.ps1"
    prompt_path.write_text(prompt, encoding="utf-8")
    _write_visible_codex_script(
        script_path=script_path,
        command=command,
        cwd=cwd,
        prompt_path=prompt_path,
        transcript_path=transcript_path,
        exit_path=exit_path,
        report_path=report_path,
        window_title=window_title,
    )

    powershell = shutil.which("pwsh") or shutil.which("powershell") or "powershell.exe"
    creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    proc = subprocess.Popen(
        [powershell, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path)],
        cwd=str(cwd),
        creationflags=creationflags,
    )
    deadline = time.monotonic() + timeout_seconds
    while True:
        if exit_path.exists():
            exit_text = _read_text_tail(exit_path, limit=100).strip()
            try:
                exit_code = int(exit_text.splitlines()[-1])
            except (IndexError, ValueError):
                exit_code = proc.poll()
            return exit_code, False, _read_text_tail(transcript_path), ""

        polled = proc.poll()
        if polled is not None:
            return polled, False, _read_text_tail(transcript_path), ""

        if time.monotonic() >= deadline:
            _kill_process_tree(proc.pid)
            return (
                None,
                True,
                _read_text_tail(transcript_path),
                f"visible Codex window timed out after {timeout_seconds} seconds",
            )

        time.sleep(0.5)


def _run_codex_command(
    command: list[str],
    *,
    prompt: str,
    cwd: Path,
    timeout_seconds: int,
    visible_window: bool = True,
    window_title: str = DEFAULT_VISIBLE_WINDOW_TITLE,
    transcript_dir: Path | None = None,
    report_path: Path | None = None,
) -> tuple[int | None, bool, str, str]:
    if visible_window and os.name == "nt":
        return _run_codex_command_visible(
            command,
            prompt=prompt,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            transcript_dir=transcript_dir or cwd,
            report_path=report_path or Path("Codex Outbox"),
            window_title=window_title,
        )
    if visible_window and os.name != "nt":
        return None, False, "", "visible Codex window is required but unsupported on this platform"

    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    proc = subprocess.Popen(
        command,
        cwd=str(cwd),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
    )
    try:
        stdout, stderr = proc.communicate(input=prompt, timeout=timeout_seconds)
        return proc.returncode, False, _tail(stdout), _tail(stderr)
    except subprocess.TimeoutExpired as exc:
        _kill_process_tree(proc.pid)
        stdout = _safe_str(exc.stdout)
        stderr = _safe_str(exc.stderr)
        try:
            extra_stdout, extra_stderr = proc.communicate(timeout=20)
            stdout += _safe_str(extra_stdout)
            stderr += _safe_str(extra_stderr)
        except Exception:
            pass
        return None, True, _tail(stdout), _tail(stderr)


def _is_github_repo_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc.lower() != "github.com":
        return False
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        return False
    if len(parts) >= 3 and parts[2].lower() in {"blob", "raw", "tree", "issues", "pull", "releases"}:
        return False
    return True


def _is_github_pull_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc.lower() != "github.com":
        return False
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    return len(parts) >= 4 and parts[2].lower() == "pull" and parts[3].isdigit()


def _github_pull_patch_url(url: str) -> str:
    base = url.split("#", 1)[0].split("?", 1)[0].rstrip("/")
    if base.endswith((".patch", ".diff")):
        return base
    return base + ".patch"


def _fallback_stage_urls(
    *,
    root: Path,
    task_text: str,
    urls: list[str],
    report_path: Path,
    workspace: Path,
    exit_code: int | None,
    timed_out: bool,
    stdout_tail: str,
    stderr_tail: str,
) -> tuple[bool, list[str]]:
    actions: list[str] = []
    staged_any = False
    python_exe = root / ".venv" / "Scripts" / "python.exe"
    learning_script = root / "xinyu_learning_library.py"

    for url in urls:
        reason = f"QQ Codex delegation fallback: {task_text[:240]}"
        try:
            if _is_github_pull_url(url):
                staged_urls = [(url, "qq-codex-github-pr"), (_github_pull_patch_url(url), "qq-codex-github-pr-patch")]
                for material_url, label in staged_urls:
                    metadata = add_url_material(
                        root=root,
                        url=material_url,
                        origin="owner_supplied",
                        reason=reason,
                        question_id="qq-codex-delegation",
                        label=label,
                        max_bytes=DEFAULT_MAX_BYTES,
                    )
                    material_id = stage_manifest_record(root, metadata, curated=True)
                    staged_any = True
                    actions.append(
                        f"- github_pull_fallback: url={material_url} item={metadata.get('id', '')} "
                        f"material={material_id} extracted={bool(metadata.get('extracted_text_path'))}"
                    )
            elif _is_github_repo_url(url):
                command = [
                    str(python_exe),
                    str(learning_script),
                    "github",
                    url,
                    "--stage",
                    "--curated",
                    "--origin",
                    "owner_supplied",
                    "--question-id",
                    "qq-codex-delegation",
                    "--reason",
                    reason,
                    "--root",
                    str(root),
                ]
                completed = subprocess.run(
                    command,
                    cwd=str(root),
                    check=False,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=120,
                )
                staged_any = staged_any or completed.returncode == 0
                actions.append(
                    f"- github_fallback: url={url} exit={completed.returncode} "
                    f"stdout={_tail(completed.stdout, 900)!r} stderr={_tail(completed.stderr, 900)!r}"
                )
            else:
                metadata = add_url_material(
                    root=root,
                    url=url,
                    origin="owner_supplied",
                    reason=reason,
                    question_id="qq-codex-delegation",
                    label="qq-codex-url",
                    max_bytes=DEFAULT_MAX_BYTES,
                )
                material_id = stage_manifest_record(root, metadata, curated=True)
                staged_any = True
                actions.append(
                    f"- url_fallback: url={url} item={metadata.get('id', '')} "
                    f"material={material_id} extracted={bool(metadata.get('extracted_text_path'))}"
                )
        except Exception as exc:
            actions.append(f"- fallback_failed: url={url} error={type(exc).__name__}: {exc}")

    downloaded = []
    if workspace.exists():
        for path in workspace.rglob("*"):
            if path.is_file():
                downloaded.append(f"- {path}")

    report_lines = [
        "---",
        "title: QQ Codex Delegation Report",
        "status: fallback_report",
        f"generated_at: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        "---",
        "",
        "# QQ Codex Delegation Report",
        "",
        "## Task",
        f"- {task_text}",
        "",
        "## Codex CLI Result",
        f"- exit_code: {exit_code if exit_code is not None else 'timeout'}",
        f"- timed_out: {str(timed_out).lower()}",
        "",
        "## Fallback Learning Registration",
        *(actions or ["- none"]),
        "",
        "## Workspace Files",
        *(downloaded or ["- none"]),
        "",
        "## Stdout Tail",
        "```text",
        stdout_tail,
        "```",
        "",
        "## Stderr Tail",
        "```text",
        stderr_tail,
        "```",
        "",
        "## Boundary",
        "- downloaded_code_execution: not_used",
        "- credentials_or_tokens: not_read",
        "- private_full_disk_access: not_used",
    ]
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    return staged_any, actions


def run_codex_delegate(root: Path, payload: dict[str, Any]) -> CodexDelegateResult:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    is_owner = _as_bool(metadata.get("is_owner_user"), default=False)
    if not is_owner:
        return CodexDelegateResult(
            accepted=False,
            reply="这类 Codex 本机动作只接受 owner 私聊触发。",
            request_path="",
            workspace_path="",
            report_path="",
            last_message_path="",
            exit_code=None,
            timed_out=False,
            stdout_tail="",
            stderr_tail="",
            notes=["codex_delegate_rejected:not_owner"],
        )

    task_text = _safe_str(payload.get("text") or payload.get("raw_message")).strip()
    if not task_text:
        return CodexDelegateResult(
            accepted=False,
            reply="没有收到要交给 Codex 的任务。",
            request_path="",
            workspace_path="",
            report_path="",
            last_message_path="",
            exit_code=None,
            timed_out=False,
            stdout_tail="",
            stderr_tail="",
            notes=["codex_delegate_rejected:empty_text"],
        )

    codex = shutil.which("codex")
    if not codex:
        return CodexDelegateResult(
            accepted=False,
            reply="本机找不到 codex 命令，暂时没法真正启动 Codex。",
            request_path="",
            workspace_path="",
            report_path="",
            last_message_path="",
            exit_code=None,
            timed_out=False,
            stdout_tail="",
            stderr_tail="",
            notes=["codex_delegate_rejected:codex_cli_missing"],
        )

    local_scope = ensure_local_scope(default_local_scope_root(root))
    paths = preview_codex_delegate_paths(root, payload)
    job_id = paths["job_id"]
    requests_dir = Path(paths["request_path"]).parent
    workspace = Path(paths["workspace_path"])
    outbox = Path(paths["report_path"]).parent
    requests_dir.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)
    request_path = Path(paths["request_path"])
    report_path = Path(paths["report_path"])
    last_message_path = Path(paths["last_message_path"])
    urls = extract_urls(task_text)
    _write_request(
        request_path=request_path,
        task_text=task_text,
        urls=urls,
        workspace=workspace,
        report_path=report_path,
        owner_approved=is_owner,
    )
    prompt = _build_prompt(
        xinyu_dir=root,
        local_scope=local_scope,
        request_path=request_path,
        workspace=workspace,
        report_path=report_path,
        task_text=task_text,
        urls=urls,
    )

    timeout_seconds = max(30, min(3600, _as_int(payload.get("timeout_seconds"), DEFAULT_TIMEOUT_SECONDS)))
    requested_visible_window = _as_bool(payload.get("visible_window"), default=True)
    visible_window = True
    window_title = _safe_str(payload.get("window_title"), DEFAULT_VISIBLE_WINDOW_TITLE).strip() or DEFAULT_VISIBLE_WINDOW_TITLE
    requested_network_access = _as_bool(payload.get("network_access"), default=False)
    network_access = requested_network_access and bool(urls)
    command = [
        codex,
        "exec",
    ]
    if network_access:
        command.extend(["-c", "sandbox_workspace_write.network_access=true"])
    command.extend(
        [
        "--full-auto",
        "--sandbox",
        "workspace-write",
        "-C",
        str(root),
        "--add-dir",
        str(local_scope),
        "--output-last-message",
        str(last_message_path),
        "--color",
        "never",
        "-",
        ]
    )
    exit_code, timed_out, stdout_tail, stderr_tail = _run_codex_command(
        command,
        prompt=prompt,
        cwd=root,
        timeout_seconds=timeout_seconds,
        visible_window=visible_window,
        window_title=window_title,
        transcript_dir=workspace,
        report_path=report_path,
    )

    report_exists = report_path.exists()
    fallback_staged = False
    fallback_actions: list[str] = []
    if urls and not report_exists:
        fallback_staged, fallback_actions = _fallback_stage_urls(
            root=root,
            task_text=task_text,
            urls=urls,
            report_path=report_path,
            workspace=workspace,
            exit_code=exit_code,
            timed_out=timed_out,
            stdout_tail=stdout_tail,
            stderr_tail=stderr_tail,
        )
        report_exists = report_path.exists()

    notes = [
        "codex_delegate",
        "real_codex_cli_invoked",
        "visible_window_policy:required",
        f"codex_exit:{exit_code if exit_code is not None else 'timeout'}",
        f"report:{'written' if report_exists else 'missing'}",
    ]
    if not requested_visible_window:
        notes.append("visible_window_request_overridden:true")
    if urls:
        notes.append(f"url_count:{len(urls)}")
    if requested_network_access:
        notes.append("network_access:" + ("enabled_for_task_urls" if network_access else "not_enabled:no_task_urls"))
    if visible_window:
        notes.append("visible_window:" + ("opened" if os.name == "nt" else "unsupported"))
        notes.append(f"visible_window_title:{window_title}")
        notes.append("visible_transcript:codex-visible-transcript.txt")
    if fallback_actions:
        notes.append("fallback_learning_registration:" + ("staged" if fallback_staged else "failed"))

    if fallback_staged:
        if timed_out:
            reply = f"Codex 那边卡住了，我已经把链接先收进学习库。报告在：{report_path}。"
        elif exit_code != 0:
            reply = f"Codex 没跑顺，退出码 {exit_code}。链接已经先收进学习库，报告在：{report_path}。"
        else:
            reply = f"跑完了，链接已经进学习库。报告在：{report_path}。"
        accepted = True
    elif timed_out:
        reply = f"Codex 那边卡住了，还不能算完成。请求留在：{request_path}。"
        accepted = False
    elif exit_code != 0:
        reply = f"这次没跑顺，退出码 {exit_code}。报告在：{report_path if report_exists else '未写出'}。"
        accepted = False
    else:
        reply = f"跑完了。报告在：{report_path}。"
        accepted = True

    trace_path = Path(paths["trace_path"])
    trace_path.write_text(
        json.dumps(
            {
                "job_id": job_id,
                "command": command,
                "request_path": str(request_path),
                "workspace": str(workspace),
                "report_path": str(report_path),
                "last_message_path": str(last_message_path),
                "exit_code": exit_code,
                "timed_out": timed_out,
                "stdout_tail": stdout_tail,
                "stderr_tail": stderr_tail,
                "notes": notes,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return CodexDelegateResult(
        accepted=accepted,
        reply=reply,
        request_path=_rel_or_abs(request_path),
        workspace_path=_rel_or_abs(workspace),
        report_path=_rel_or_abs(report_path),
        last_message_path=_rel_or_abs(last_message_path),
        exit_code=exit_code,
        timed_out=timed_out,
        stdout_tail=stdout_tail,
        stderr_tail=stderr_tail,
        notes=notes,
    )
