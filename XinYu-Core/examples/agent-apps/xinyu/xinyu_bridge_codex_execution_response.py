from __future__ import annotations

from typing import Any


def codex_background_scheduled_response(
    paths: dict[str, Any],
    *,
    reply: str,
    auto_study: bool,
    cleanup: dict[str, Any],
    session_count: int,
) -> dict[str, Any]:
    notes = [
        "codex_delegate",
        "codex_delegate_background:scheduled",
        "dream_handoff_on_timeout:armed",
        f"job_id:{paths['job_id']}",
        "learning_after_codex:" + ("scheduled_after_finish" if auto_study else "skipped"),
    ]
    if cleanup["cleaned_sessions"]:
        notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")
    return {
        "accepted": True,
        "reply": reply,
        "memory_changed": False,
        "library_changed": False,
        "session_created": False,
        "sessions": session_count,
        "request_path": paths["request_path"],
        "workspace_path": paths["workspace_path"],
        "report_path": paths["report_path"],
        "last_message_path": paths["last_message_path"],
        "codex_exit_code": None,
        "codex_timed_out": False,
        "stdout_tail": "",
        "stderr_tail": "",
        "source_integration_gate": {},
        "learner_integration": {},
        "learning_quality": {},
        "integrated_materials": 0,
        "ready_materials": 0,
        "blocked_unreadable_materials": 0,
        "quality_grade": "background",
        "notes": notes,
    }
