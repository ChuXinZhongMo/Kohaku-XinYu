from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from xinyu_qq_outbox import enqueue_qq_outbox_image, enqueue_qq_outbox_message
from xinyu_visible_persona_voice import (
    compose_codex_background_error_message,
    compose_codex_completion_message,
    compose_codex_image_caption,
    compose_codex_started_reply,
    compose_codex_status_reply,
    visible_codex_owner_task_text,
    visible_codex_reply_variant,
    visible_codex_task_subject,
)


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
    return compose_codex_status_reply(
        status,
        paths=paths,
        auto_study=auto_study,
        exit_code=exit_code,
        task_text=task_text,
    )

def codex_reply_variant(seed: str, options: tuple[str, ...]) -> str:
    return visible_codex_reply_variant(seed, options)

def codex_owner_task_text(text: str) -> str:
    return visible_codex_owner_task_text(text)

def codex_task_subject(task_text: str) -> str:
    return visible_codex_task_subject(task_text)

def codex_started_reply(task_subject: str, variant: int) -> str:
    return compose_codex_started_reply(task_subject, variant)

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
            line = re.sub(r"(?i)^summary:\s*", "", line).strip()
            lower_line = line.lower()
            if lower_line.startswith(
                ("request:", "created:", "owner task:", "report:", "report name:", "generated image path:")
            ):
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
    exit_code = getattr(result, "exit_code", None)
    timed_out = bool(getattr(result, "timed_out", False))
    accepted = bool(getattr(result, "accepted", False))
    summary = codex_completion_summary(xinyu_dir, result)
    return compose_codex_completion_message(
        summary=summary,
        accepted=accepted,
        timed_out=timed_out,
        exit_code=exit_code,
        auto_study=auto_study,
        handoff_notes=handoff_notes,
        text=text,
    )

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
        message = compose_codex_background_error_message(error)
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
            caption=compose_codex_image_caption(image_file.name),
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
