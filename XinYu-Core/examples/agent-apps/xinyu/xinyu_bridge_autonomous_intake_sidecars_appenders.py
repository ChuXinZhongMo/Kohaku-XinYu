from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_autonomous_intake_sidecars_payloads import (
    creative_writing_kwargs,
    daily_digest_kwargs,
    github_learning_kwargs,
    goldmark_dehydrate_kwargs,
    review_inbox_kwargs,
    watched_source_kwargs,
)
from xinyu_bridge_autonomous_intake_sidecars_rendering import (
    creative_writing_summary,
    daily_digest_summary,
    github_learning_summary,
    goldmark_dehydrate_summary,
    review_inbox_summary,
    watched_source_summary,
)
from xinyu_bridge_autonomous_trace_helpers import append_autonomous_error


SummaryRenderer = Callable[[dict[str, Any]], str | None]


def _append_intake_result_note(
    runtime: Any,
    notes: list[str],
    *,
    note_kind: str,
    run_func: Callable[..., dict[str, Any]],
    kwargs: dict[str, Any],
    render_summary: SummaryRenderer,
) -> None:
    try:
        result = run_func(runtime.xinyu_dir, **kwargs)
        summary = render_summary(result)
        if summary is not None:
            notes.append(summary)
    except Exception as exc:
        append_autonomous_error(runtime, notes, note_kind, exc)


def append_watched_source_note(
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
    run_watched_source_check_func: Callable[..., dict[str, Any]],
) -> None:
    _append_intake_result_note(
        runtime,
        notes,
        note_kind="watched_source",
        run_func=run_watched_source_check_func,
        kwargs=watched_source_kwargs(runtime, checked_at=checked_at),
        render_summary=watched_source_summary,
    )


def append_github_learning_note(
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
    sys_module: Any,
    load_run_github_autonomous_learning_func: Callable[[], Callable[..., dict[str, Any]]],
) -> None:
    try:
        custom_dir = runtime.xinyu_dir / "custom"
        if str(custom_dir) not in sys_module.path:
            sys_module.path.insert(0, str(custom_dir))
        run_github_autonomous_learning = load_run_github_autonomous_learning_func()
    except Exception as exc:
        append_autonomous_error(runtime, notes, "github_learning", exc)
        return
    _append_intake_result_note(
        runtime,
        notes,
        note_kind="github_learning",
        run_func=run_github_autonomous_learning,
        kwargs=github_learning_kwargs(runtime, checked_at=checked_at),
        render_summary=github_learning_summary,
    )


def append_daily_digest_note(
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
    run_daily_digest_maintenance_func: Callable[..., dict[str, Any]],
) -> None:
    _append_intake_result_note(
        runtime,
        notes,
        note_kind="daily_digest",
        run_func=run_daily_digest_maintenance_func,
        kwargs=daily_digest_kwargs(checked_at=checked_at),
        render_summary=daily_digest_summary,
    )


def append_creative_writing_note(
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
    run_creative_writing_maintenance_func: Callable[..., dict[str, Any]],
) -> None:
    _append_intake_result_note(
        runtime,
        notes,
        note_kind="creative_writing",
        run_func=run_creative_writing_maintenance_func,
        kwargs=creative_writing_kwargs(checked_at=checked_at),
        render_summary=creative_writing_summary,
    )


def append_review_inbox_note(
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
    run_review_inbox_maintenance_func: Callable[..., dict[str, Any]],
) -> None:
    _append_intake_result_note(
        runtime,
        notes,
        note_kind="review_inbox",
        run_func=run_review_inbox_maintenance_func,
        kwargs=review_inbox_kwargs(runtime),
        render_summary=review_inbox_summary,
    )


def append_goldmark_dehydrate_note(
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
    run_goldmark_dehydration_maintenance_func: Callable[..., dict[str, Any]],
) -> None:
    _append_intake_result_note(
        runtime,
        notes,
        note_kind="goldmark_dehydrate",
        run_func=run_goldmark_dehydration_maintenance_func,
        kwargs=goldmark_dehydrate_kwargs(),
        render_summary=goldmark_dehydrate_summary,
    )
