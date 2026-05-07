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
from xinyu_text_variants import readable_markers


URL_PATTERN = re.compile(r"https?://[^\s<>()\"'，。！？、]+", re.I)
DEFAULT_TIMEOUT_SECONDS = 3600
DEFAULT_VISIBLE_WINDOW_TITLE = "Xinyu codex"
IMAGEGEN_CLI_REL = Path("skills/.system/imagegen/scripts/image_gen.py")


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
    "没让你用codex",
    "没有让你用codex",
    "不是让你用codex",
    "不是叫你用codex",
    "不是让你调用codex",
    "不是叫你调用codex",
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

CODEX_META_OR_CORRECTION_MARKERS = (
    "不是提到codex",
    "不是说codex",
    "不是聊codex",
    "一提codex",
    "提到codex就",
    "说codex就",
    "聊codex就",
    "codex误触发",
    "codex误判",
    "自动开codex",
    "自动启动codex",
    "又开codex",
    "又启动codex",
    "硬约束",
    "触发器",
    "关键词触发",
    "我没让",
    "我没有让",
    "我不是让",
    "我不是叫",
    "不是让你",
    "不是叫你",
    "别再开",
    "不要再开",
    "先别开",
    "codex关了",
    "关掉codex",
    "把codex关了",
    "已经关了",
    "先停",
    "停下",
    "停止codex",
)

CODEX_DESCRIPTIVE_INTENT_MARKERS = (
    "我准备让codex",
    "我打算让codex",
    "我想让codex",
    "我要让codex",
    "我会让codex",
    "准备让codex",
    "打算让codex",
    "待会让codex",
    "等下让codex",
    "一会让codex",
    "我准备用codex",
    "我打算用codex",
    "我想用codex",
    "我要用codex",
)

CODEX_EXPLICIT_DELEGATION_MARKERS = (
    "用codex",
    "调用codex",
    "让codex",
    "叫codex",
    "交给codex",
    "找codex",
    "给codex",
    "开codex",
    "启动codex",
    "codex帮我",
    "codex来",
    "usecodex",
    "runcodex",
    "askcodex",
    "codexauxiliarybrain",
)

CODEX_EXPLICIT_ACTION_MARKERS = (
    "看一下",
    "看下",
    "查一下",
    "查下",
    "检查",
    "分析",
    "修",
    "改",
    "调试",
    "跑",
    "测试",
    "验证",
    "搜索",
    "联网",
    "浏览",
    "研究",
    "学习",
    "处理",
    "执行",
)

CODEX_QUESTION_ONLY_MARKERS = (
    "怎么用codex",
    "如何用codex",
    "codex怎么用",
    "codex是什么",
    "codex什么意思",
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
    "头像",
    "海报",
    "壁纸",
    "插画",
    "表情包",
    "立绘",
    "banner",
    "logo",
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
READABLE_CODEX_NEGATIVE_MARKERS = (
    "别用codex",
    "不要用codex",
    "不用codex",
    "先别用codex",
    "没让你用codex",
    "没让你开codex",
    "没让你启动codex",
    "不是让你用codex",
    "不是叫你用codex",
    "不是让你开codex",
)
READABLE_CODEX_META_OR_CORRECTION_MARKERS = (
    "不是提到codex",
    "说起来你运行codex",
    "运行codex好像",
    "codex好像每次都没成功",
    "codex每次都没成功",
    "codex没成功",
    "没成功的样子",
    "codex没跑顺",
    "没跑顺",
    "退出码",
    "怎么直接就开codex",
    "直接就开codex",
    "直接开codex",
    "怎么开codex",
    "为什么开codex",
    "为啥开codex",
    "开codex了",
    "开了codex",
    "又开codex",
    "又开了codex",
    "自动开codex",
    "自动开了codex",
    "误触发",
    "固定模板",
    "标准ai报告腔",
    "报告腔",
)
READABLE_CODEX_DESCRIPTIVE_INTENT_MARKERS = (
    "准备让codex",
    "打算让codex",
    "想让codex",
    "我要让codex",
    "之后让codex",
    "等下让codex",
    "一会让codex",
)
READABLE_CODEX_EXPLICIT_DELEGATION_MARKERS = (
    "用codex",
    "调用codex",
    "让codex",
    "叫codex",
    "交给codex",
    "开codex",
    "启动codex",
    "usecodex",
    "runcodex",
    "askcodex",
)
READABLE_CODEX_EXPLICIT_ACTION_MARKERS = (
    "查",
    "看",
    "检查",
    "分析",
    "改",
    "修",
    "调试",
    "跑",
    "测试",
    "验证",
    "搜索",
    "搜",
    "研究",
    "处理",
)

TRUSTED_PUBLIC_SEARCH_MARKERS = (
    "搜索",
    "搜一下",
    "搜下",
    "搜东西",
    "联网",
    "查一下",
    "查下",
    "查资料",
    "核对",
    "验证",
    "找资料",
    "公开资料",
    "网页",
    "新闻",
    "资料来源",
    "source",
    "search",
    "web",
    "verify",
)
TRUSTED_LOCAL_BLOCK_MARKERS = (
    "本机",
    "本地",
    "电脑",
    "文件",
    "目录",
    "路径",
    "代码",
    "项目",
    "仓库",
    "安装",
    "pip",
    "修改",
    "删除",
    "移动",
    "上传",
    "token",
    "密钥",
    "密码",
    "cookie",
    "日志",
    "配置",
    "local",
    "localhost",
    "127.0.0.1",
    "file://",
    "localfile",
    "localpath",
    "localconfig",
    "config.yaml",
    ".env",
    "code",
    "repo",
    "repository",
    "project",
    "install",
    "package",
    "admin",
    "permission",
    "delete",
    "modify",
    "write",
    "readfile",
    "openfile",
    "log",
    "secret",
    "api_key",
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

OWNER_LOCAL_WRITE_ACTION_MARKERS = (
    *readable_markers(
        "落盘",
        "写入",
        "写到",
        "保存",
        "修改",
        "更改",
        "编辑",
        "替换",
        "创建",
        "新建",
        "生成文件",
        "补丁",
        "修复",
        "补上",
        "改一下",
        "改文件",
        "改代码",
    ),
    "write",
    "modify",
    "edit",
    "patch",
    "create",
    "save",
    "persist",
    "change",
    "fix",
    "update",
)
OWNER_LOCAL_WRITE_TARGET_MARKERS = (
    *readable_markers(
        "本地",
        "本机",
        "本地文件",
        "文件",
        "文件夹",
        "目录",
        "项目",
        "代码",
        "仓库",
        "前端",
        "后端",
        "落盘",
        "工作区",
        "XinYu",
        "心玉",
    ),
    "local",
    "file",
    "folder",
    "directory",
    "workspace",
    "project",
    "repo",
    "repository",
    "code",
    "frontend",
    "backend",
    "xinyu",
)
OWNER_LOCAL_WRITE_NEGATIVE_MARKERS = (
    *readable_markers(
        "不要改",
        "别改",
        "不要写",
        "别写",
        "不要落盘",
        "别落盘",
        "只读",
        "仅报告",
        "先别动文件",
        "不要动文件",
    ),
    "read only",
    "read-only",
    "report only",
    "no changes",
    "do not edit",
    "don't edit",
    "do not write",
    "don't write",
)
OWNER_LOCAL_WRITE_IMPERATIVE_MARKERS = (
    *readable_markers("帮我", "请", "直接", "开始", "去", "把", "让 Codex", "用 Codex", "调用 Codex"),
    "please",
    "go ahead",
    "run codex",
    "use codex",
    "ask codex",
)
OWNER_LOCAL_WRITE_QUESTION_ONLY_MARKERS = (
    *readable_markers("能不能", "可以吗", "行不行", "是不是", "为什么", "怎么", "如何"),
    "can it",
    "could it",
    "why",
    "how",
)

LOCAL_PATH_PATTERN = re.compile(r"(?i)(?:[a-z]:[\\/]|\\\\|(?:^|[\s`'\"“”‘’])\.{1,2}[\\/])")


def _compact_for_request_detection(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _contains_compact_marker(normalized: str, markers: tuple[str, ...]) -> bool:
    return any(_compact_for_request_detection(marker) in normalized for marker in markers if marker)


def _trusted_public_search_task_allowed(task_text: str) -> bool:
    normalized = _compact_for_request_detection(task_text)
    if not normalized:
        return False
    if LOCAL_PATH_PATTERN.search(task_text):
        return False
    if any(marker.lower() in normalized for marker in TRUSTED_LOCAL_BLOCK_MARKERS):
        return False
    return any(marker.lower() in normalized for marker in TRUSTED_PUBLIC_SEARCH_MARKERS)


def _codex_home() -> Path:
    configured = _safe_str(os.environ.get("CODEX_HOME")).strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".codex"


def _imagegen_cli_path() -> Path:
    return _codex_home() / IMAGEGEN_CLI_REL


def _load_delegate_local_env(xinyu_dir: Path) -> list[str]:
    notes: list[str] = []
    env_path = xinyu_dir / "xinyu.local.env"
    if env_path.exists():
        try:
            for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                current = _safe_str(os.environ.get(key)).strip()
                if key and value and (key not in os.environ or not current):
                    os.environ[key] = value
            notes.append("local_env_loaded")
        except OSError as exc:
            notes.append(f"local_env_load_failed:{type(exc).__name__}")

    image_key = _safe_str(os.environ.get("OPENAI_API_KEY")).strip()
    xinyu_image_key = _safe_str(os.environ.get("XINYU_OPENAI_API_KEY")).strip()
    if not image_key and xinyu_image_key:
        os.environ["OPENAI_API_KEY"] = xinyu_image_key
        image_key = xinyu_image_key
        notes.append("openai_image_key_mirrored_from_xinyu_openai")
    notes.append("openai_image_key:" + ("available" if image_key else "missing"))
    return notes


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


def _blocks_codex_delegation_intent(normalized: str) -> bool:
    return (
        _contains_any(normalized, CODEX_META_OR_CORRECTION_MARKERS)
        or _contains_any(normalized, READABLE_CODEX_META_OR_CORRECTION_MARKERS)
        or _contains_any(normalized, CODEX_DESCRIPTIVE_INTENT_MARKERS)
        or _contains_any(normalized, READABLE_CODEX_DESCRIPTIVE_INTENT_MARKERS)
    )


def _looks_like_explicit_codex_delegation(text: str, normalized: str) -> bool:
    if "codex" not in normalized:
        return False
    if _blocks_codex_delegation_intent(normalized):
        return False
    if _contains_any(normalized, CODEX_QUESTION_ONLY_MARKERS):
        return False
    if _contains_any(normalized, CODEX_EXPLICIT_DELEGATION_MARKERS) or _contains_any(
        normalized,
        READABLE_CODEX_EXPLICIT_DELEGATION_MARKERS,
    ):
        return True
    has_action = _contains_any(normalized, CODEX_EXPLICIT_ACTION_MARKERS) or _contains_any(
        normalized,
        READABLE_CODEX_EXPLICIT_ACTION_MARKERS,
    )
    has_target = _has_local_path_hint(text, normalized) or bool(extract_urls(text))
    return has_action and has_target


def looks_like_codex_request(text: str) -> bool:
    normalized = _compact_for_request_detection(text)
    if not normalized:
        return False
    if _contains_any(normalized, CODEX_NEGATIVE_MARKERS) or _contains_any(
        normalized,
        READABLE_CODEX_NEGATIVE_MARKERS,
    ):
        return False
    if _looks_like_explicit_codex_delegation(text, normalized):
        return True
    if extract_urls(text) and _contains_any(text, CODEX_URL_MARKERS):
        return True
    return _looks_like_local_operation_request(text, normalized)


def looks_like_owner_local_write_request(text: str) -> bool:
    normalized = _compact_for_request_detection(text)
    if not normalized:
        return False
    if _contains_compact_marker(normalized, OWNER_LOCAL_WRITE_NEGATIVE_MARKERS):
        return False
    if _contains_compact_marker(normalized, OWNER_LOCAL_WRITE_QUESTION_ONLY_MARKERS) and not _contains_compact_marker(
        normalized,
        OWNER_LOCAL_WRITE_IMPERATIVE_MARKERS,
    ):
        return False
    if not _contains_compact_marker(normalized, OWNER_LOCAL_WRITE_ACTION_MARKERS):
        return False
    return _has_local_path_hint(text, normalized) or _contains_compact_marker(
        normalized,
        OWNER_LOCAL_WRITE_TARGET_MARKERS,
    )


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
        "agent_report_path": str(workspace / f"{job_name}-report.md"),
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
    local_write_approved: bool = False,
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
- local_write_approved: {str(local_write_approved).lower()}
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
- If local_write_approved is true and the task asks for file changes, make the bounded file changes instead of report-only output.
""",
        encoding="utf-8",
    )


def _is_self_code_task(task_text: str) -> bool:
    lowered = task_text.lower()
    return any(
        marker in lowered
        for marker in (
            "self-code approval id:",
            "self-code execution path",
            "self_code_iteration",
            "modify her own code",
            "modify xin yu's own code",
            "modify xinyu's own code",
        )
    )


def _is_image_artifact_task(task_text: str) -> bool:
    compact = re.sub(r"\s+", "", task_text).lower()
    action_markers = (
        "生成",
        "画",
        "作图",
        "做图",
        "绘制",
        "create",
        "draw",
        "generate",
        "render",
    )
    image_markers = (
        "图片",
        "图像",
        "图",
        "插画",
        "插图",
        "示意图",
        "流程图",
        "形象",
        "头像",
        "海报",
        "壁纸",
        "表情包",
        "立绘",
        "banner",
        "logo",
        "png",
        "jpg",
        "jpeg",
        "webp",
        "image",
        "diagram",
        "illustration",
    )
    return any(marker in compact for marker in action_markers) and any(marker in compact for marker in image_markers)


def _build_prompt(
    *,
    xinyu_dir: Path,
    local_scope: Path,
    request_path: Path,
    workspace: Path,
    report_path: Path,
    task_text: str,
    urls: list[str],
    local_write_approved: bool = False,
) -> str:
    python_exe = xinyu_dir / ".venv" / "Scripts" / "python.exe"
    learning_script = xinyu_dir / "xinyu_learning_library.py"
    imagegen_cli = _imagegen_cli_path()
    imagegen_output = workspace / "output" / "imagegen" / "xinyu-gpt-image-2.png"
    imagegen_prompt_file = workspace / "image_prompt.txt"
    imagegen_status = "available" if imagegen_cli.exists() else "missing"
    urls_block = "\n".join(f"- {url}" for url in urls) or "- none"
    self_code_task = _is_self_code_task(task_text)
    self_code_allowed = (
        "\n- For self-code approval tasks, edit focused files under the XinYu project, especially "
        "`examples/agent-apps/xinyu`, and add/update focused tests or smokes."
        if self_code_task
        else ""
    )
    self_code_expected = (
        "\nSelf-code implementation mode:\n"
        "- This task has owner-private self-code approval; do not reduce it to research-only output.\n"
        "- Inspect the relevant XinYu modules, make one bounded patch, and keep edits reversible.\n"
        "- Prefer improving owner-private self-code intent detection, Codex delegation prompt clarity, "
        "watchdog snapshot/reporting, QQ outbox report-back, or focused validation.\n"
        "- Run targeted tests/smokes and include exact commands/results in the report.\n"
        "- If a dirty file conflict or running Codex job blocks the patch, write the blocker and do not fake completion.\n"
        if self_code_task
        else ""
    )
    local_write_allowed = (
        "\n- For owner-approved local write tasks, create or edit bounded files only under the XinYu project "
        "or the local authorized scope. Keep changes minimal and directly tied to the owner task."
        if local_write_approved and not self_code_task
        else ""
    )
    local_write_expected = (
        "\nOwner-approved local write mode:\n"
        "- This owner-private task is allowed to affect local files; do not reduce it to report-only output.\n"
        "- Make only the smallest necessary create/edit changes inside the listed writable roots.\n"
        "- If the requested path is outside the XinYu project and local authorized scope, stop and report the boundary blocker.\n"
        "- Do not delete, move, rename, publish, upload, or push files.\n"
        "- Run focused validation when practical and include changed paths plus exact commands/results in the report.\n"
        if local_write_approved and not self_code_task
        else ""
    )
    image_artifact_task = _is_image_artifact_task(task_text)
    image_artifact_allowed = (
        "\n- For owner-requested image/diagram generation tasks, call GPT image generation through the installed "
        "`imagegen` fallback CLI. Do not create a one-off SDK runner and do not install new dependencies."
        if image_artifact_task
        else ""
    )
    image_artifact_expected = (
        "\nImage artifact mode:\n"
        f"- Installed imagegen CLI: {imagegen_cli} ({imagegen_status}).\n"
        "- Use GPT image model `gpt-image-2` through that CLI for picture, diagram, flowchart, illustration, "
        "avatar, poster, wallpaper, or other visual artifact requests.\n"
        f"- Recommended command shape: `{python_exe} {imagegen_cli} generate --model gpt-image-2 "
        f"--prompt-file {imagegen_prompt_file} --size 1024x1024 --quality medium --output-format png "
        f"--out {imagegen_output} --force`.\n"
        "- Write the visual prompt into the prompt file first; keep it faithful to the owner request and avoid "
        "adding arbitrary characters, brands, or slogans.\n"
        "- This path requires `OPENAI_API_KEY`; the launcher may load it from `xinyu.local.env` or mirror "
        "`XINYU_OPENAI_API_KEY`. Never print or copy the key into the report.\n"
        "- Produce at least one normal-size local `.png`, `.jpg`, `.jpeg`, or `.webp` file. Do not use a placeholder.\n"
        "- Put generated image files under the workspace or the authorized local scope.\n"
        "- In the report, include a line exactly like `Generated image path: <absolute-or-workspace-relative-path>` for each image.\n"
        "- If the CLI or API key is unavailable, or generation fails, write the concrete blocker in the report "
        "instead of pretending it succeeded.\n"
        if image_artifact_task
        else ""
    )
    return f"""You are Codex running as XinYu's bounded local delegate from an owner request.

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
{self_code_allowed}
{local_write_allowed}

Hard blocks:
- Do not execute downloaded code.
- Do not install dependencies.
- Do not delete, move, upload, publish, push, or impersonate.
- Do not broaden URL-fetch tasks into open web crawling. If no URL is supplied, summarize public search findings and write the report without local URL downloads.
- Do not read credentials, cookies, tokens, browser/session files, password stores, or private folders outside the granted scope.
- Do not bypass XinYu source, learning, privacy, or stable-personality gates.
- Do not send private local files to external APIs. For image generation, send only the owner-approved text prompt.
{image_artifact_allowed}

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
{self_code_expected}
{local_write_expected}
{image_artifact_expected}
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


def _local_fallback_report_from_text(text: str) -> Path | None:
    root = Path(__file__).resolve().parent
    try:
        root_resolved = root.resolve()
    except OSError:
        root_resolved = root
    for match in re.finditer(r"(?im)([A-Z]:\\[^\r\n`\"']+?\.md)", _safe_str(text)):
        candidate_text = match.group(1).strip().rstrip(".,;:)")
        if not candidate_text:
            continue
        candidate = Path(candidate_text)
        if not candidate.name.startswith("codex-") or not candidate.name.endswith("-report.md"):
            continue
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        try:
            if not resolved.is_relative_to(root_resolved):
                continue
        except ValueError:
            continue
        if resolved.is_file():
            return resolved
    return None


def _write_missing_report_from_last_message(
    *,
    report_path: Path,
    task_text: str,
    last_message_path: Path,
    stdout_tail: str,
    stderr_tail: str,
) -> bool:
    last_message = _read_text_tail(last_message_path, limit=40_000)
    fallback_report = _local_fallback_report_from_text(last_message)
    if fallback_report is not None:
        report_text = fallback_report.read_text(encoding="utf-8-sig", errors="replace")
        if report_text.strip():
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(report_text, encoding="utf-8")
            return True
    if not last_message.strip() and not stdout_tail.strip() and not stderr_tail.strip():
        return False
    report_lines = [
        "---",
        "title: QQ Codex Delegation Captured Report",
        "status: captured_from_last_message",
        f"generated_at: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        "---",
        "",
        "# QQ Codex Delegation Captured Report",
        "",
        "## Task",
        f"- {task_text}",
        "",
        "## Capture Reason",
        "- Codex exited without writing the requested report path.",
        "- XinYu captured the final Codex message so learning follow-up can still receive a material id.",
        "",
        "## Codex Last Message",
        "```text",
        last_message,
        "```",
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
        "- captured_report_only: true",
        "- stable_memory_write: not_direct",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    return True


def _promote_agent_report(*, agent_report_path: Path, report_path: Path) -> bool:
    if report_path.exists():
        return True
    if agent_report_path == report_path or not agent_report_path.exists():
        return False
    report_text = agent_report_path.read_text(encoding="utf-8-sig", errors="replace")
    if not report_text.strip():
        return False
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    return report_path.exists()


def run_codex_delegate(root: Path, payload: dict[str, Any]) -> CodexDelegateResult:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    is_owner = _as_bool(metadata.get("is_owner_user"), default=False)
    is_trusted_public_search = _as_bool(metadata.get("trusted_public_search_task"), default=False)
    if not is_owner and not is_trusted_public_search:
        return CodexDelegateResult(
            accepted=False,
            reply="这类 Codex 本机动作只接受 owner 私聊触发；可信联系人只允许公开资料搜索。",
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
    if is_trusted_public_search and not _trusted_public_search_task_allowed(task_text):
        return CodexDelegateResult(
            accepted=False,
            reply="这个请求超出了可信联系人可用的公开搜索权限。",
            request_path="",
            workspace_path="",
            report_path="",
            last_message_path="",
            exit_code=None,
            timed_out=False,
            stdout_tail="",
            stderr_tail="",
            notes=["codex_delegate_rejected:trusted_scope"],
        )

    raw_owner_task = _safe_str(payload.get("raw_owner_task")).strip()
    write_intent_text = "\n".join(part for part in (raw_owner_task, task_text) if part)
    owner_local_write_approved = bool(
        is_owner
        and (
            _as_bool(metadata.get("owner_local_write_approved"), default=False)
            or (
                _as_bool(metadata.get("delegated_by_action_layer"), default=False)
                and looks_like_owner_local_write_request(write_intent_text)
            )
            or (
                _safe_str(payload.get("message_type")).strip().lower()
                in {"private_codex_command", "desktop_codex_command"}
                and looks_like_owner_local_write_request(write_intent_text)
            )
        )
    )
    image_artifact_task = _is_image_artifact_task(task_text)
    env_notes = _load_delegate_local_env(root) if image_artifact_task else []

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
    agent_report_path = Path(paths.get("agent_report_path") or report_path)
    last_message_path = Path(paths["last_message_path"])
    urls = extract_urls(task_text)
    _write_request(
        request_path=request_path,
        task_text=task_text,
        urls=urls,
        workspace=workspace,
        report_path=agent_report_path,
        owner_approved=is_owner,
        local_write_approved=owner_local_write_approved,
    )
    prompt = _build_prompt(
        xinyu_dir=root,
        local_scope=local_scope,
        request_path=request_path,
        workspace=workspace,
        report_path=agent_report_path,
        task_text=task_text,
        urls=urls,
        local_write_approved=owner_local_write_approved,
    )

    timeout_seconds = max(30, min(3600, _as_int(payload.get("timeout_seconds"), DEFAULT_TIMEOUT_SECONDS)))
    requested_visible_window = _as_bool(payload.get("visible_window"), default=True)
    visible_window = True
    window_title = _safe_str(payload.get("window_title"), DEFAULT_VISIBLE_WINDOW_TITLE).strip() or DEFAULT_VISIBLE_WINDOW_TITLE
    requested_network_access = _as_bool(payload.get("network_access"), default=False)
    web_search_access = requested_network_access
    network_access = requested_network_access and (bool(urls) or image_artifact_task)
    command = [codex]
    if web_search_access:
        command.append("--search")
    command.extend(["--ask-for-approval", "never"])
    command.append("exec")
    if network_access:
        command.extend(["-c", "sandbox_workspace_write.network_access=true"])
    command.extend(
        [
        "--sandbox",
        "workspace-write",
        "--skip-git-repo-check",
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
        report_path=agent_report_path,
    )

    report_exists = _promote_agent_report(agent_report_path=agent_report_path, report_path=report_path)
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
    captured_missing_report = False
    if not report_exists and exit_code == 0:
        captured_missing_report = _write_missing_report_from_last_message(
            report_path=report_path,
            task_text=task_text,
            last_message_path=last_message_path,
            stdout_tail=stdout_tail,
            stderr_tail=stderr_tail,
        )
        report_exists = report_path.exists()

    notes = [
        "codex_delegate",
        "real_codex_cli_invoked",
        "visible_window_policy:required",
        *env_notes,
        f"codex_exit:{exit_code if exit_code is not None else 'timeout'}",
        f"agent_report:{'written' if agent_report_path.exists() else 'missing'}",
        f"report:{'written' if report_exists else 'missing'}",
    ]
    if image_artifact_task:
        notes.append("imagegen_cli:" + ("available" if _imagegen_cli_path().exists() else "missing"))
    if owner_local_write_approved:
        notes.append("owner_local_write:approved")
    if not requested_visible_window:
        notes.append("visible_window_request_overridden:true")
    if urls:
        notes.append(f"url_count:{len(urls)}")
    if requested_network_access:
        notes.append("web_search:enabled" if web_search_access else "web_search:disabled")
        if network_access and image_artifact_task and not urls:
            notes.append("network_access:enabled_for_image_generation")
        else:
            notes.append("network_access:" + ("enabled_for_task_urls" if network_access else "not_enabled:no_task_urls"))
    if visible_window:
        notes.append("visible_window:" + ("opened" if os.name == "nt" else "unsupported"))
        notes.append(f"visible_window_title:{window_title}")
        notes.append("visible_transcript:codex-visible-transcript.txt")
    if fallback_actions:
        notes.append("fallback_learning_registration:" + ("staged" if fallback_staged else "failed"))
    if captured_missing_report:
        notes.append("missing_report_captured_from_last_message")

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
                "agent_report_path": str(agent_report_path),
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
