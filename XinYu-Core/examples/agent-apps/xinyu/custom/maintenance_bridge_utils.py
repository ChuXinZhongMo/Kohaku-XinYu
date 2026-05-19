"""Shared helpers for low-frequency maintenance bridge plugins."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable

from xinyu_runtime.modules.plugin.base import PluginContext

from turn_mode_utils import read_turn_mode


def default_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resolve_root(ctx: PluginContext | None) -> Path:
    candidate = Path(ctx.working_dir) if ctx else default_root()
    if (candidate / "memory").exists():
        return candidate
    return default_root()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def read_text_optional(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def append_trace(root: Path, trace_rel: str | Path, line: str) -> None:
    trace_path = root / trace_rel
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().isoformat()
    with trace_path.open("a", encoding="utf-8") as fh:
        fh.write(f"{stamp} {line}\n")


def maintenance_should_run(
    ctx: PluginContext | None,
    root: Path,
    *,
    state_key: str,
    min_interval_seconds: int,
    recommendation_markers: Iterable[str] = (),
    dispatch_markers: Iterable[str] = (),
    dispatch_missing_reason: str = "dispatch_not_ready",
    turn_mode_missing_reason: str = "",
) -> tuple[bool, str]:
    should_continue, reason = maintenance_preflight(
        ctx,
        root,
        recommendation_markers=recommendation_markers,
        dispatch_markers=dispatch_markers,
        dispatch_missing_reason=dispatch_missing_reason,
        turn_mode_missing_reason=turn_mode_missing_reason,
    )
    if not should_continue:
        return False, reason
    return cooldown_ready(ctx, state_key=state_key, min_interval_seconds=min_interval_seconds)


def maintenance_preflight(
    ctx: PluginContext | None,
    root: Path,
    *,
    recommendation_markers: Iterable[str] = (),
    dispatch_markers: Iterable[str] = (),
    dispatch_missing_reason: str = "dispatch_not_ready",
    turn_mode_missing_reason: str = "",
) -> tuple[bool, str]:
    if not ctx:
        return False, "no_context"

    turn_mode = read_turn_mode(root)
    if turn_mode != "maintenance_schedule_turn":
        if turn_mode_missing_reason:
            return False, turn_mode_missing_reason
        return False, f"turn_mode:{turn_mode or 'unknown'}"

    dispatch_markers = tuple(dispatch_markers)
    if dispatch_markers:
        dispatch = read_text(root / "memory/context/maintenance_dispatch_state.md")
        if not any(marker in dispatch for marker in dispatch_markers):
            return False, dispatch_missing_reason

    recommendation_markers = tuple(recommendation_markers)
    if recommendation_markers:
        recommendations = read_text(root / "memory/context/maintenance_recommendations.md")
        if not any(marker in recommendations for marker in recommendation_markers):
            return False, "recommendation_not_yes"
    return True, "ready"


def cooldown_ready(
    ctx: PluginContext | None,
    *,
    state_key: str,
    min_interval_seconds: int,
) -> tuple[bool, str]:
    if not ctx:
        return False, "no_context"
    last_run = ctx.get_state(state_key)
    if last_run:
        try:
            last_dt = datetime.fromisoformat(str(last_run))
            delta = (datetime.now().astimezone() - last_dt).total_seconds()
            if delta < min_interval_seconds:
                return False, f"cooldown:{int(delta)}"
        except Exception:
            pass
    return True, "ready"


def run_maintenance_bridge_once(
    ctx: PluginContext | None,
    root: Path,
    *,
    trace_rel: str | Path,
    should_run: Callable[[Path], tuple[bool, str]],
    state_key: str,
    engine: Callable[..., dict[str, Any]],
    timestamp_arg: str,
    mode: str,
    trace_label: str,
    result_summary: Callable[[dict[str, Any]], str],
) -> None:
    if not ctx:
        return
    try:
        append_trace(root, trace_rel, "post_llm_call entered")
        allowed, reason = should_run(root)
        append_trace(root, trace_rel, f"post_llm_call should_run={allowed} reason={reason}")
        if not allowed:
            return

        timestamp = datetime.now().astimezone().isoformat()
        result = engine(root, **{timestamp_arg: timestamp, "mode": mode})
        ctx.set_state(state_key, timestamp)
        summary = result_summary(result)
        append_trace(root, trace_rel, f"{trace_label} {summary}".rstrip())
    except Exception as exc:
        append_trace(root, trace_rel, f"error={exc!r}")
