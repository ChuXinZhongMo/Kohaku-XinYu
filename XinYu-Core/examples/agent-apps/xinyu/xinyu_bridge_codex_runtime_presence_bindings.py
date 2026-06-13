from __future__ import annotations

from typing import Any, Mapping


def record_codex_delegate_presence_state_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> None:
    deps["_record_codex_delegate_presence_state"](
        values["xinyu_dir"],
        values["payload"],
        presence_paths=values["presence_paths"],
        status=values["status"],
        window_title=values["window_title"],
        presence_recorder=deps["record_codex_presence"],
    )


def record_codex_delegate_presence_result_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> None:
    deps["_record_codex_delegate_presence_result"](
        values["xinyu_dir"],
        values["payload"],
        result=values["result"],
        presence_paths=values["presence_paths"],
        window_title=values["window_title"],
        presence_recorder=deps["record_codex_presence"],
    )
