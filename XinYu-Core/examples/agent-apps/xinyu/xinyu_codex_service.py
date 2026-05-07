from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from xinyu_qq_outbox import enqueue_qq_outbox_image, enqueue_qq_outbox_message


CODEX_GENERATED_IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp"})


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def codex_status_reply(
    status: str,
    *,
    paths: dict[str, str],
    auto_study: bool,
    exit_code: int | None = None,
    task_text: str = "",
) -> str:
    report_path = _safe_str(paths.get("report_path")).strip()
    request_path = _safe_str(paths.get("request_path")).strip()
    report_label = Path(report_path).name if report_path else "Codex Outbox"
    request_label = Path(request_path).name if request_path else "Codex Requests"
    task_subject = codex_task_subject(task_text)
    variant_seed = "|".join(part for part in (task_subject, report_label, request_label, status) if part)
    if status == "started":
        return codex_reply_variant(
            variant_seed,
            (
                codex_started_reply(task_subject, 0),
                codex_started_reply(task_subject, 1),
                codex_started_reply(task_subject, 2),
            ),
        )
    if status == "done":
        return codex_reply_variant(
            variant_seed,
            (
                f"{task_subject}有结果了。报告名：{report_label}。",
                f"{task_subject}那边结束了。报告名：{report_label}。",
                f"{task_subject}跑完了。报告名：{report_label}。",
            ),
        )
    if status == "timeout_staged":
        return f"它卡住了，这次不算完整跑完；链接我先收进学习暂存。报告名：{report_label}。"
    if status == "timeout":
        return f"它卡住了，不算完成。请求我留着了：{request_label}。"
    if exit_code is not None:
        return f"这次没跑顺，退出码 {exit_code}。报告名：{report_label}。"
    return f"这次没正常跑起来。报告名：{report_label}。"

def codex_reply_variant(seed: str, options: tuple[str, ...]) -> str:
    if not options:
        return ""
    digest = hashlib.sha256(seed.encode("utf-8", errors="ignore")).digest()
    return options[digest[0] % len(options)]

def codex_owner_task_text(text: str) -> str:
    task = _safe_str(text).strip()
    current_match = re.search(r"(?is)Current owner Codex task:\s*(.+)$", task)
    if current_match:
        task = current_match.group(1).strip()
    task = re.sub(r"(?is)^Use Codex auxiliary brain for this owner-approved task:\s*", "", task).strip()
    task = task.split("Recent QQ context before this Codex request:", 1)[0].strip()
    task = re.sub(r"\s+", " ", task).strip()
    return task[:160]

def codex_task_subject(task_text: str) -> str:
    task = codex_owner_task_text(task_text)
    compact = re.sub(r"\s+", "", task).lower()
    titles = re.findall(r"《([^》]{1,32})》", task)
    if titles:
        named = "和".join(f"《{title}》" for title in titles[:2])
        if len(titles) > 2:
            named += "这些"
        return named
    if any(marker in compact for marker in ("搜索", "搜", "查", "了解", "联网", "资料", "番茄小说", "小说")):
        return "这轮检索"
    if any(marker in compact for marker in ("修", "改", "代码", "脚本", "测试", "报错", "配置")):
        return "代码那块"
    if any(marker in compact for marker in ("图片", "图像", "头像", "海报", "插画", "生成图", "做图")):
        return "图片那件事"
    if any(marker in compact for marker in ("没动", "没看见codex", "信任", "权限")):
        return "Codex 启动这块"
    return "这件事"

def codex_started_reply(task_subject: str, variant: int) -> str:
    subject = task_subject or "这件事"
    if subject.startswith("《"):
        options = (
            f"我去查{subject}，已经开跑。结果我接回来。",
            f"{subject}这轮检索交给 Codex 了，跑完我回你。",
            f"我让 Codex 去摸{subject}的资料了，先等它跑完。",
        )
    elif subject == "这轮检索":
        options = (
            "我去搜，已经开跑。结果出来我直接接着聊。",
            "检索开了，先让它跑；跑完我把重点拿回来。",
            "我把搜索交给 Codex 了，不在这儿念流程，等结果。",
        )
    elif subject == "代码那块":
        options = (
            "我让 Codex 看代码了，跑完我接结果。",
            "代码那块已经交给它查，等它跑完。",
            "我开了代码检查，结果回来我再说具体改了什么。",
        )
    elif subject == "Codex 启动这块":
        options = (
            "我去核 Codex 启动这块，已经开跑。",
            "我让它查启动问题了，跑完看结果。",
            "启动这块我交给 Codex 复查，结果回来再对。",
        )
    else:
        options = (
            f"{subject}我交给 Codex 了，跑完我回你。",
            f"{subject}已经开跑，结果我接回来。",
            f"我让 Codex 处理{subject}，先等它跑完。",
        )
    return options[variant % len(options)]

def codex_completion_summary(xinyu_dir: Path, result: Any, *, limit: int = 220) -> str:
    candidates: list[str] = []
    for path_text in (_safe_str(getattr(result, "last_message_path", "")), _safe_str(getattr(result, "report_path", ""))):
        if not path_text:
            continue
        path = Path(path_text)
        if not path.is_absolute():
            path = xinyu_dir / path
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line in {"---", "```", "```text"}:
                continue
            line = re.sub(r"^\s*(?:[-*•>]+|\d+[.)])\s*", "", line).strip()
            lower_line = line.lower()
            if line.startswith(("#", "title:", "status:", "generated_at:", "## Stdout", "## Stderr")):
                continue
            if lower_line.startswith(("request:", "created:", "owner task:", "report:", "report name:")):
                continue
            if re.search(r"(?i)(codex-qq-\d|\.md\b|outbox|request_path|report_path|last_message_path)", line):
                continue
            if re.search(r"(?i)([a-z]:\\|/users/|/home/|\\\\|token|api[_-]?key|stderr|stdout)", line):
                continue
            line = re.sub(r"(?i)([a-z]:\\[^\\s]+|/users/\\S+|/home/\\S+|\\\\\\S+)", "<local_path>", line)
            line = re.sub(r"\s+", " ", line).strip("- ").strip()
            if line and line.lower() not in {"none", "unknown"}:
                candidates.append(line)
            if len(candidates) >= 3:
                break
        if candidates:
            break

    summary = "；".join(candidates[:3]).strip()
    if len(summary) > limit:
        summary = summary[: limit - 3].rstrip() + "..."
    return summary

def codex_completion_outbox_message(
    xinyu_dir: Path,
    result: Any,
    *,
    text: str,
    auto_study: bool,
    handoff_notes: list[str],
) -> str:
    report_path = _safe_str(getattr(result, "report_path", ""))
    report_label = Path(report_path).name if report_path else "Codex Outbox"
    report_file = Path(report_path) if report_path else None
    if report_file is not None and not report_file.is_absolute():
        report_file = xinyu_dir / report_file
    report_exists = bool(report_file and report_file.exists())
    exit_code = getattr(result, "exit_code", None)
    timed_out = bool(getattr(result, "timed_out", False))
    accepted = bool(getattr(result, "accepted", False))
    summary = codex_completion_summary(xinyu_dir, result)
    if timed_out:
        return "那边超时了，这次不算完成。"
    if exit_code is not None and not accepted:
        return f"Codex 没跑顺，退出码 {exit_code}。"
    if accepted and summary:
        return re.sub(r"\s+", " ", f"查完了。{summary}").strip()
    if accepted:
        return "查完了，但没有提炼出能直接转述的结论。"
    if handoff_notes:
        return "这次没正常完成，我先不把它当结果讲。"
    return "这次没有正常完成。"

    variant_seed = report_label or _safe_str(getattr(result, "request_path", "")) or text
    if timed_out:
        head = codex_reply_variant(
            variant_seed,
            (
                "Codex 卡住了，这次不算完成。",
                "它那边超时了，先不算跑完。",
                "Codex 没等到结果，我先把这事留住。",
            ),
        )
    elif accepted:
        head = codex_reply_variant(
            variant_seed,
            (
                "Codex 回来了。",
                "它那边跑完了。",
                "结果出来了。",
            ),
        )
    elif exit_code is not None:
        head = f"Codex 没跑顺，退出码 {exit_code}。"
    else:
        head = "Codex 这次没有正常完成。"

    parts = [head]
    if summary:
        parts.append(summary)
    if timed_out or handoff_notes:
        parts.append("我先把这件事留住，后面继续查。")
    elif accepted and auto_study:
        parts.append("后面的学习整合我放后台。")
    if report_exists:
        parts.append(f"报告名：{report_label}。")
    else:
        parts.append("这次没有写出报告，trace 我留在本地。")
    return re.sub(r"\s+", " ", "".join(parts)).strip()

def enqueue_codex_completion_if_needed(
    xinyu_dir: Path,
    payload: dict[str, Any],
    *,
    result: Any | None,
    text: str,
    auto_study: bool,
    handoff_notes: list[str],
    error: str = "",
) -> None:
    if _safe_str(payload.get("source")) != "qq_gateway_codex_execute_message":
        return
    metadata = payload.get("metadata")
    if isinstance(metadata, dict) and _safe_str(metadata.get("async_resume_id")).strip():
        return
    user_id = _safe_str(payload.get("user_id")).strip()
    if not user_id:
        return
    job_id = _safe_str(payload.get("job_id")).strip()
    if not job_id and result is not None:
        job_id = Path(_safe_str(getattr(result, "report_path", ""))).stem or "codex-qq"

    if error:
        message = f"Codex 辅助脑这次在后台报错了：{error}。我没有把它当成完成，会留在本地日志里继续查。"
    elif result is not None:
        message = codex_completion_outbox_message(
            xinyu_dir,
            result,
            text=text,
            auto_study=auto_study,
            handoff_notes=handoff_notes,
        )
    else:
        return

    enqueue_qq_outbox_message(
        xinyu_dir,
        user_id=user_id,
        message=message,
        source="codex_completion",
        dedupe_key=f"codex_completion:{job_id or text[:80]}",
        metadata={
            "job_id": job_id,
            "task_preview": text[:240],
            "auto_study": auto_study,
            "has_error": bool(error),
        },
    )
    for image_file in codex_generated_image_artifacts(xinyu_dir, result, task_text=text):
        enqueue_qq_outbox_image(
            xinyu_dir,
            user_id=user_id,
            image_path=str(image_file),
            caption=f"Codex 生成的图片：{image_file.name}",
            source="codex_generated_image",
            dedupe_key=f"codex_generated_image:{job_id or text[:80]}:{image_file.name}",
            metadata={
                "job_id": job_id,
                "task_preview": text[:240],
                "auto_study": auto_study,
                "generated_image": True,
            },
        )

def codex_generated_image_artifacts(xinyu_dir: Path, result: Any | None, *, task_text: str, limit: int = 3) -> list[Path]:
    if result is None or not looks_like_codex_image_generation_task(task_text):
        return []
    roots: list[Path] = []
    for path_text in (
        _safe_str(getattr(result, "workspace_path", "")),
        _safe_str(getattr(result, "report_path", "")),
        _safe_str(getattr(result, "last_message_path", "")),
    ):
        if not path_text:
            continue
        path = Path(path_text)
        if not path.is_absolute():
            path = xinyu_dir / path
        root = path if path.is_dir() else path.parent
        if root.exists() and root not in roots:
            roots.append(root)

    candidates: dict[str, Path] = {}
    for root in roots:
        try:
            for path in root.rglob("*"):
                if len(candidates) >= limit:
                    break
                if not path.is_file() or path.suffix.lower() not in CODEX_GENERATED_IMAGE_SUFFIXES:
                    continue
                try:
                    resolved = path.resolve(strict=True)
                except OSError:
                    continue
                candidates[str(resolved)] = resolved
        except OSError:
            continue

    report_path = _safe_str(getattr(result, "report_path", ""))
    report_file = Path(report_path) if report_path else None
    if report_file is not None and not report_file.is_absolute():
        report_file = xinyu_dir / report_file
    if report_file is not None and report_file.is_file():
        report_text = report_file.read_text(encoding="utf-8-sig", errors="replace")
        for match in re.finditer(r"(?im)^\s*Generated image path:\s*(.+?)\s*$", report_text):
            path_text = match.group(1).strip().strip("`\"'")
            path = Path(path_text)
            if not path.is_absolute():
                path = report_file.parent / path
            try:
                resolved = path.resolve(strict=True)
            except OSError:
                continue
            if resolved.is_file() and resolved.suffix.lower() in CODEX_GENERATED_IMAGE_SUFFIXES:
                candidates[str(resolved)] = resolved
            if len(candidates) >= limit:
                break

    return list(candidates.values())[:limit]

def looks_like_codex_image_generation_task(text: str) -> bool:
    compact = re.sub(r"\s+", "", _safe_str(text)).lower()
    action_markers = ("生成", "画", "作图", "做图", "绘制", "create", "draw", "generate", "render")
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
