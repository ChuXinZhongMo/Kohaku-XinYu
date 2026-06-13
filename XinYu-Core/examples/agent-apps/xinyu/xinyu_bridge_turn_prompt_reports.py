from __future__ import annotations

from typing import Any


def append_prompt_and_reports(
    deps: Any,
    runtime: Any,
    agent: Any,
    pending: list[Any],
    *,
    payload: dict[str, Any],
    text: str,
    turn_id: str,
    live_state: Any,
    live_system_prompt: str,
    pressure_selection: Any,
    short_term_continuity_block: str,
) -> None:
    pending.append(
        {
            "role": "system",
            "content": live_system_prompt,
        }
    )
    runtime._maybe_dump_live_system_prompt(
        agent,
        payload=payload,
        session_key=live_state.session_key,
        turn_id=turn_id,
        live_system_prompt=live_system_prompt,
    )
    pressure_report = pressure_selection.to_report(
        live_prompt_chars=len(live_system_prompt),
        session_key=live_state.session_key,
        turn_id=turn_id,
        source=live_state.source_line,
        speaker_relation=live_state.relationship_line,
        user_text_chars=len(deps.safe_str(text)),
    )
    try:
        deps.write_prompt_pressure_report(runtime.xinyu_dir, pressure_report)
    except OSError as exc:
        print(f"[xinyu_core_bridge] prompt pressure report failed: {type(exc).__name__}: {exc}", flush=True)
    else:
        if short_term_continuity_block:
            try:
                recall_report = deps.build_short_term_recall_diagnostics(runtime.xinyu_dir)
                deps.write_short_term_recall_diagnostics(runtime.xinyu_dir, recall_report)
            except Exception as exc:
                print(
                    f"[xinyu_core_bridge] short-term recall diagnostics failed: {type(exc).__name__}: {exc}",
                    flush=True,
                )
