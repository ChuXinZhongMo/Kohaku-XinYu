from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CodexDreamHandoffResult:
    accepted: bool
    seed_id: str
    reflection_item_id: str
    dream_output: dict[str, object]
    reflection_output: dict[str, object]
    slow_reprocess: dict[str, object]
    inner_cycle: dict[str, object]
    trace_path: str
    notes: list[str]


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _replace_frontmatter_field(text: str, field: str, value: str) -> str:
    if re.search(rf"(?m)^{re.escape(field)}:\s*", text):
        return re.sub(rf"(?m)^{re.escape(field)}:\s*.*$", f"{field}: {value}", text, count=1)
    return text


def _next_id(text: str, *, prefix: str, produced_at: str) -> str:
    day = produced_at[:10]
    pattern = re.compile(rf"(?m)^## {re.escape(prefix)}-{re.escape(day)}-(\d{{3}})\b")
    used = {int(match.group(1)) for match in pattern.finditer(text)}
    for index in range(1, 1000):
        if index not in used:
            return f"{prefix}-{day}-{index:03d}"
    return f"{prefix}-{day}-999"


def _insert_before_first_item(text: str, item_prefix: str, section: str) -> str:
    match = re.search(rf"(?m)^## {re.escape(item_prefix)}-", text)
    if not match:
        return text.rstrip() + "\n\n" + section.strip() + "\n"
    return text[: match.start()].rstrip() + "\n\n" + section.strip() + "\n\n" + text[match.start() :].lstrip()


def _trim(text: str, limit: int = 180) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    return compact if len(compact) <= limit else compact[: limit - 1] + "…"


def _urls_from_text(text: str) -> list[str]:
    return re.findall(r"https?://[^\s<>()\"'，。！？、]+", text)


def _write_dream_seed(
    root: Path,
    *,
    produced_at: str,
    task_text: str,
    report_path: str,
    request_path: str,
    timed_out: bool,
) -> str:
    path = root / "memory/dreams/dream_seeds.md"
    text = _read(path)
    if report_path and report_path in text:
        match = re.search(r"(?m)^## (seed-\d{4}-\d{2}-\d{2}-\d{3})\n(?:(?!^## ).)*" + re.escape(report_path), text, re.S)
        if match:
            return match.group(1)
    seed_id = _next_id(text, prefix="seed", produced_at=produced_at)
    urls = _urls_from_text(task_text)
    url_hint = urls[0] if urls else "no_url"
    status = "timed_out" if timed_out else "unfinished"
    section = f"""
## {seed_id}
- source_event: codex_delegate_{status}
- theme: Codex 未完成的学习任务不能被关掉
- residue: owner 明确要求别把超时当结束；{_trim(url_hint, 120)} 需要沉到梦和反思里继续消化
- emotional_weight: 88
- factual_status: runtime_event / codex_delegate_{status}
- dream_permission: can_recombine_unfinished_learning_pressure_but_not_invent_result
- source_report: {report_path or "none"}
- source_request: {request_path or "none"}
- task_excerpt: {_trim(task_text)}
"""
    text = _replace_frontmatter_field(text, "updated_at", produced_at)
    text = _replace_frontmatter_field(text, "last_confirmed_at", produced_at)
    text = _insert_before_first_item(text, "seed", section)
    _write(path, text)
    return seed_id


def _write_reflection_item(
    root: Path,
    *,
    produced_at: str,
    seed_id: str,
    task_text: str,
    report_path: str,
    timed_out: bool,
) -> str:
    path = root / "memory/reflection/reflection_queue.md"
    text = _read(path)
    if report_path and report_path in text:
        match = re.search(r"(?m)^## (item-\d{4}-\d{2}-\d{2}-\d{3})\n(?:(?!^## ).)*" + re.escape(report_path), text, re.S)
        if match:
            return match.group(1)
    item_id = _next_id(text, prefix="item", produced_at=produced_at)
    status = "timed_out" if timed_out else "unfinished"
    section = f"""
## {item_id}
- topic: Codex 学习任务超时后不能关闭，要进入梦/反思继续处理
- source: codex_delegate_{status} / {seed_id}
- priority: high
- suggested_writer: reflection_writer
- report_path: {report_path or "none"}
- task_excerpt: {_trim(task_text)}
- boundary: 只能作为未完成任务和情绪残留处理，不能伪造成已经完整学会
"""
    text = _replace_frontmatter_field(text, "updated_at", produced_at)
    text = _replace_frontmatter_field(text, "last_confirmed_at", produced_at)
    text = _insert_before_first_item(text, "item", section)
    _write(path, text)
    return item_id


def _run_cycle(
    root: Path,
    produced_at: str,
    *,
    seed_id: str,
) -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    custom_dir = root / "custom"
    if str(custom_dir) not in sys.path:
        sys.path.insert(0, str(custom_dir))

    from dream_output_engine import run_dream_output
    from inner_cycle_engine import run_inner_cycle_summary
    from reflection_output_engine import run_reflection_output
    from slow_reprocess_engine import run_slow_reprocess

    slow = run_slow_reprocess(root, checked_at=produced_at, mode="codex_timeout_dream_handoff")
    dream = run_dream_output(
        root,
        produced_at=produced_at,
        mode="codex_timeout_dream_handoff",
        preferred_seed_id=seed_id,
    )
    reflection = run_reflection_output(root, produced_at=produced_at, mode="codex_timeout_dream_handoff")
    inner = run_inner_cycle_summary(root, checked_at=produced_at, mode="codex_timeout_dream_handoff")
    return slow, dream, reflection, inner


def handoff_codex_to_dream(
    root: Path,
    *,
    task_text: str,
    report_path: str = "",
    request_path: str = "",
    workspace_path: str = "",
    timed_out: bool = False,
    exit_code: int | None = None,
    produced_at: str | None = None,
    run_cycle: bool = True,
) -> CodexDreamHandoffResult:
    produced_at = produced_at or datetime.now().astimezone().isoformat()
    seed_id = _write_dream_seed(
        root,
        produced_at=produced_at,
        task_text=task_text,
        report_path=report_path,
        request_path=request_path,
        timed_out=timed_out,
    )
    item_id = _write_reflection_item(
        root,
        produced_at=produced_at,
        seed_id=seed_id,
        task_text=task_text,
        report_path=report_path,
        timed_out=timed_out,
    )
    slow: dict[str, object] = {}
    dream: dict[str, object] = {}
    reflection: dict[str, object] = {}
    inner: dict[str, object] = {}
    notes = ["codex_dream_handoff", f"seed:{seed_id}", f"reflection_item:{item_id}"]
    if run_cycle:
        slow, dream, reflection, inner = _run_cycle(root, produced_at, seed_id=seed_id)
        notes.extend(
            [
                f"dream_wrote:{dream.get('wrote_log')}",
                f"dream_weight_delta:{dream.get('weight_delta')}",
                f"reflection_wrote:{reflection.get('wrote_reflection')}",
                f"growth_wrote:{reflection.get('wrote_growth')}",
            ]
        )

    trace_path = root / "memory/dreams/codex_dream_handoff_trace.log"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    with trace_path.open("a", encoding="utf-8") as fh:
        fh.write(
            f"{produced_at} accepted=true seed={seed_id} item={item_id} "
            f"timed_out={str(timed_out).lower()} exit={exit_code if exit_code is not None else 'none'} "
            f"report={report_path or 'none'} workspace={workspace_path or 'none'} task={_trim(task_text, 220)!r}\n"
        )

    return CodexDreamHandoffResult(
        accepted=True,
        seed_id=seed_id,
        reflection_item_id=item_id,
        dream_output=dream,
        reflection_output=reflection,
        slow_reprocess=slow,
        inner_cycle=inner,
        trace_path=str(trace_path),
        notes=notes,
    )
