from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

from xinyu_bridge_autonomous_trace_helpers import append_autonomous_error

AfterResult = Callable[[dict[str, Any]], None]
SummaryRenderer = Callable[[dict[str, Any]], str]
ShadowRunFunc = Callable[..., dict[str, Any]]


@dataclass(frozen=True)
class ShadowAppendCall:
    note_kind: str
    run_func: ShadowRunFunc
    kwargs: dict[str, Any]
    render_summary: SummaryRenderer
    after_result: AfterResult | None = None


def append_shadow_result_note(
    runtime: Any,
    notes: list[str],
    *,
    note_kind: str,
    run_func: ShadowRunFunc,
    kwargs: dict[str, Any],
    render_summary: SummaryRenderer,
    after_result: AfterResult | None = None,
) -> dict[str, Any] | None:
    try:
        result = run_func(runtime.xinyu_dir, **kwargs)
    except Exception as exc:
        append_autonomous_error(runtime, notes, note_kind, exc)
        return None

    notes.append(render_summary(result))
    if after_result is not None:
        after_result(result)
    return result


def append_shadow_result_notes(
    runtime: Any,
    notes: list[str],
    calls: Iterable[ShadowAppendCall],
) -> None:
    for call in calls:
        append_shadow_result_note(
            runtime,
            notes,
            note_kind=call.note_kind,
            run_func=call.run_func,
            kwargs=call.kwargs,
            render_summary=call.render_summary,
            after_result=call.after_result,
        )
