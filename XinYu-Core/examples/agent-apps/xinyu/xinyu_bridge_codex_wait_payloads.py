from __future__ import annotations

from collections.abc import Callable
from typing import Any


def _watchdog_restart_command(manifest_path: str) -> str:
    return (
        "powershell -NoProfile -ExecutionPolicy Bypass -File .\\start_xinyu_core_bridge.ps1 "
        f"-ForceRestart -SelfCodeSnapshotPath \"{manifest_path}\" -HealthTimeoutSeconds 60"
    )


def _watchdog_block(
    *,
    snapshot_id: str,
    manifest_path: str,
    normalize_func: Callable[[str], str],
) -> str:
    return normalize_func(
        "\n".join(
            [
                "",
                "Self-code watchdog:",
                f"- snapshot_id: {snapshot_id}",
                f"- snapshot_manifest: {manifest_path}",
                "- before changing files, keep this snapshot unchanged.",
                "- after implementing and testing the self-code patch, reload Core through the PowerShell health gate.",
                f"- reload_command: {_watchdog_restart_command(manifest_path)}",
                "- the PowerShell gate waits up to 30 seconds for /health; on failure it restores the snapshot and restarts Core.",
                "- do not bypass this reload command for a runtime code patch.",
            ]
        )
    )


def _append_watchdog_block(
    payload: dict[str, Any],
    *,
    watchdog_block: str,
    safe_str_func: Callable[[Any], str],
) -> None:
    for key in ("text", "raw_owner_task"):
        payload[key] = safe_str_func(payload.get(key)).rstrip() + "\n\n" + watchdog_block


def _watchdog_snapshot_fields(
    snapshot: dict[str, Any],
    *,
    safe_str_func: Callable[[Any], str],
) -> tuple[str, str]:
    manifest_path = safe_str_func(snapshot.get("manifest_path")).strip()
    snapshot_id = safe_str_func(snapshot.get("snapshot_id")).strip()
    if not manifest_path or not snapshot_id:
        raise RuntimeError("self-code watchdog snapshot did not return a manifest path")
    return snapshot_id, manifest_path


def _mark_watchdog_metadata(
    payload: dict[str, Any],
    *,
    snapshot_id: str,
    manifest_path: str,
) -> None:
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        metadata["self_code_watchdog_snapshot_id"] = snapshot_id
        metadata["self_code_watchdog_manifest_path"] = manifest_path
        metadata["self_code_watchdog_restart_required"] = True


def prepare_self_code_watchdog_payload(
    runtime: Any,
    payload: dict[str, Any],
    *,
    approval_id: str,
    snapshot_func: Callable[..., dict[str, Any]],
    normalize_func: Callable[[str], str],
    safe_str_func: Callable[[Any], str],
) -> dict[str, Any]:
    snapshot = snapshot_func(
        runtime.xinyu_dir,
        approval_id=approval_id,
        reason="owner_self_code_iteration_before_codex_patch",
    )
    snapshot_id, manifest_path = _watchdog_snapshot_fields(snapshot, safe_str_func=safe_str_func)
    block = _watchdog_block(snapshot_id=snapshot_id, manifest_path=manifest_path, normalize_func=normalize_func)
    _append_watchdog_block(payload, watchdog_block=block, safe_str_func=safe_str_func)
    _mark_watchdog_metadata(payload, snapshot_id=snapshot_id, manifest_path=manifest_path)
    return snapshot


def _wait_to_think_task_text(
    wait_task: str,
    *,
    resume_id: str,
    user_text: str,
    execution_plan_func: Callable[..., str],
) -> str:
    task_text = wait_task
    if resume_id:
        task_text = f"{task_text}\n\nSuspension resume_id: {resume_id}"
    plan = execution_plan_func(task_text, user_text=user_text)
    return f"{task_text}\n\nStructured execution plan:\n{plan}"


def _mark_wait_to_think_metadata(codex_payload: dict[str, Any], *, resume_id: str) -> None:
    metadata = codex_payload["metadata"]
    metadata["delegated_by_wait_to_think"] = True
    metadata["async_resume_id"] = resume_id
    codex_payload["auto_study"] = False


def build_wait_to_think_codex_payload(
    payload: dict[str, Any],
    *,
    session_key: str,
    wait_task: str,
    resume_id: str,
    user_text: str,
    timeout_seconds: int,
    window_title: str,
    execution_plan_func: Callable[..., str],
    build_model_payload_func: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    task_text = _wait_to_think_task_text(
        wait_task,
        resume_id=resume_id,
        user_text=user_text,
        execution_plan_func=execution_plan_func,
    )
    codex_payload = build_model_payload_func(
        payload,
        session_key=session_key,
        task_text=task_text,
        timeout_seconds=timeout_seconds,
        window_title=window_title,
    )
    _mark_wait_to_think_metadata(codex_payload, resume_id=resume_id)
    return codex_payload
