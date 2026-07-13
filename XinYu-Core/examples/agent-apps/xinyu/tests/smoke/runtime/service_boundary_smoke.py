from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import asyncio
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import xinyu_learning_service as learning_mod
from xinyu_chat_service import ChatServiceError, PAYLOAD_TOO_LARGE_STATUS, build_chat_service
from xinyu_codex_service import (
    codex_completion_summary,
    codex_generated_image_artifacts,
    codex_owner_task_text,
    codex_reply_variant,
)
from xinyu_desktop_service import (
    DesktopService,
    desktop_event_state,
    desktop_events_recent,
    desktop_limit,
    desktop_recent_items,
    desktop_services,
)
from xinyu_learning_service import build_learning_service
from xinyu_qq_sender import file_upload_action, image_message_action, text_message_action


def _check(condition: bool, failures: list[str], message: str) -> None:
    if not condition:
        failures.append(message)


def _payload_text(payload: dict[str, object]) -> str:
    return str(payload.get("text") or "").strip()


def _session_key(payload: dict[str, object]) -> str:
    return str(payload.get("session_id") or "fallback")


def _check_qq_sender(failures: list[str]) -> None:
    private = SimpleNamespace(message_kind="private", user_id="42", group_id="")
    action, params = text_message_action(private, "hello")
    _check(action == "send_private_msg", failures, "private text action changed")
    _check(params.get("user_id") == 42, failures, "private numeric user id was not converted")
    _check(params.get("message") == [{"type": "text", "data": {"text": "hello"}}], failures, "text segment changed")

    group = SimpleNamespace(message_kind="group", user_id="42", group_id="10001")
    action, params = image_message_action(group, "file:///tmp/preview.png")
    _check(action == "send_group_msg", failures, "group image action changed")
    _check(params.get("group_id") == 10001, failures, "group id was not converted")
    _check(
        params.get("message") == [{"type": "image", "data": {"file": "file:///tmp/preview.png"}}],
        failures,
        "image segment changed",
    )

    private_named = SimpleNamespace(message_kind="private", user_id="owner", group_id="")
    action, params = file_upload_action(private_named, "report.txt", name="owner_report.txt")
    _check(action == "upload_private_file", failures, "private file upload action changed")
    _check(params.get("user_id") == "owner", failures, "non-numeric user id should remain a string")
    _check(params.get("file") == "report.txt" and params.get("name") == "owner_report.txt", failures, "file params changed")


async def _check_desktop_service(failures: list[str]) -> None:
    _check(desktop_limit(None, default=7, maximum=20) == 7, failures, "desktop_limit default changed")
    _check(desktop_limit("999", default=7, maximum=20) == 20, failures, "desktop_limit maximum clamp changed")
    _check(desktop_limit("0", default=7, maximum=20) == 1, failures, "desktop_limit lower clamp changed")

    offline_state = await desktop_event_state(None)
    _check(offline_state.get("available") is False, failures, "offline desktop event state changed")
    offline_recent = await desktop_events_recent(None, {"limit": "2"})
    _check(offline_recent.get("items") == [], failures, "offline desktop recent items changed")
    _check(
        offline_recent.get("notes") == ["desktop_event_bus_unavailable"],
        failures,
        "offline desktop recent notes changed",
    )

    recent = desktop_recent_items(
        [{"id": "one"}, {"id": "two"}, {"id": "three"}],
        {"limit": "2"},
        default=10,
        maximum=10,
        notes=["service_boundary_smoke"],
    )
    _check([item["id"] for item in recent["items"]] == ["two", "three"], failures, "desktop recent slicing changed")

    ws_server = SimpleNamespace(server=object(), bound_port=8766)
    services = desktop_services(ws_server=ws_server, closed=False, memory_root_exists=False)
    by_name = {item["service"]: item for item in services}
    _check(by_name["core"]["status"] == "ready", failures, "core service status changed")
    _check(by_name["desktop_events"]["status"] == "ready", failures, "desktop ws service status changed")
    _check(by_name["memory"]["status"] == "degraded", failures, "memory service degraded status changed")

    runtime = SimpleNamespace()
    service = DesktopService()
    service.attach_runtime(runtime)
    _check(runtime.desktop_event_bus is None and runtime.desktop_ws_server is None, failures, "desktop attach_runtime changed")
    _check(service.listener_url() == "", failures, "disabled desktop listener url changed")


def _check_chat_service(failures: list[str]) -> None:
    service = build_chat_service()
    empty = service.prepare_request({}, max_text_chars=5, payload_text=_payload_text, session_key=_session_key)
    _check(empty.empty_response is not None and empty.empty_response["notes"] == ["empty_text"], failures, "empty chat response changed")

    prepared = service.prepare_request(
        {"text": "hello", "session_id": "s1"},
        max_text_chars=5,
        payload_text=_payload_text,
        session_key=_session_key,
    )
    _check(prepared.text == "hello" and prepared.session_key == "s1", failures, "chat request preparation changed")

    try:
        service.prepare_request([], max_text_chars=5, payload_text=_payload_text, session_key=_session_key)
        failures.append("non-object chat payload was accepted")
    except ChatServiceError as exc:
        _check(exc.status.value == 400, failures, "non-object chat payload status changed")

    try:
        service.prepare_request({"text": "toolong"}, max_text_chars=5, payload_text=_payload_text, session_key=_session_key)
        failures.append("too-long chat payload was accepted")
    except ChatServiceError as exc:
        _check(exc.status == PAYLOAD_TOO_LARGE_STATUS, failures, "too-long chat payload status changed")


def _check_codex_service(failures: list[str]) -> None:
    task_text = (
        "Current owner Codex task:\n"
        "Use Codex auxiliary brain for this owner-approved task: Search project\n"
        "Recent QQ context before this Codex request:\nprivate context"
    )
    _check(codex_owner_task_text(task_text) == "Search project", failures, "Codex owner task extraction changed")
    _check(
        codex_reply_variant("stable-seed", ("a", "b", "c")) == codex_reply_variant("stable-seed", ("a", "b", "c")),
        failures,
        "Codex reply variant is not deterministic",
    )

    with tempfile.TemporaryDirectory(prefix="xinyu-service-boundary-") as tmp:
        xinyu_dir = Path(tmp)
        report_path = xinyu_dir / "codex-report.md"
        image_path = xinyu_dir / "preview.png"
        image_path.write_bytes(b"png-smoke")
        report_path.write_text(
            "\n".join(
                [
                    "---",
                    "title: local report",
                    "report_path: C:\\private\\report.md",
                    "- Useful conclusion",
                    "Generated image path: preview.png",
                ]
            ),
            encoding="utf-8",
        )
        result = SimpleNamespace(report_path=str(report_path), last_message_path="", workspace_path="")
        _check(codex_completion_summary(xinyu_dir, result) == "Useful conclusion", failures, "Codex summary filtering changed")
        artifacts = codex_generated_image_artifacts(xinyu_dir, result, task_text="generate image", limit=3)
        _check(artifacts == [image_path.resolve()], failures, "Codex generated image discovery changed")


async def _check_learning_service(failures: list[str]) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    async def fake_ingest(**kwargs: Any) -> dict[str, Any]:
        calls.append(("ingest", kwargs))
        return {"accepted": True}

    async def fake_study(**kwargs: Any) -> dict[str, Any]:
        calls.append(("study", kwargs))
        return {"studied": True}

    async def fake_observe(**kwargs: Any) -> dict[str, Any]:
        calls.append(("observe", kwargs))
        return {"observed": True}

    def fake_record_recent_attachment_context(xinyu_dir: Path, payload: dict[str, Any], result: dict[str, Any]) -> bool:
        calls.append(("record_recent_attachment_context", {"xinyu_dir": xinyu_dir, "payload": payload, "result": result}))
        return True

    old_ingest = learning_mod.learning_ingest_bridge
    old_study = learning_mod.learning_study_bridge
    old_observe = learning_mod.learning_observe_bridge
    old_record = learning_mod.record_recent_attachment_context
    learning_mod.learning_ingest_bridge = fake_ingest
    learning_mod.learning_study_bridge = fake_study
    learning_mod.learning_observe_bridge = fake_observe
    learning_mod.record_recent_attachment_context = fake_record_recent_attachment_context
    try:
        lock = object()
        xinyu_dir = Path("xinyu-root")
        memory_root = Path("xinyu-root/memory")
        service = build_learning_service(
            xinyu_dir=xinyu_dir,
            memory_root=memory_root,
            cleanup_idle_sessions=lambda: None,
            session_count=lambda: 0,
            lock=lock,
            load_local_env=lambda path: None,
        )
        ingest_result = await service.ingest({"source": "smoke"})
        study_result = await service.study({"topic": "boundary"})
        observe_result = await service.observe({"kind": "note"})
    finally:
        learning_mod.learning_ingest_bridge = old_ingest
        learning_mod.learning_study_bridge = old_study
        learning_mod.learning_observe_bridge = old_observe
        learning_mod.record_recent_attachment_context = old_record

    _check(ingest_result.get("notes") == ["recent_attachment_context_recorded"], failures, "learning ingest context note changed")
    _check(study_result == {"studied": True}, failures, "learning study delegation changed")
    _check(observe_result == {"observed": True}, failures, "learning observe delegation changed")
    _check([name for name, _ in calls] == ["ingest", "record_recent_attachment_context", "study", "observe"], failures, "learning call order changed")
    _check(calls[0][1]["xinyu_dir"] == Path("xinyu-root"), failures, "learning xinyu_dir dependency changed")
    _check(calls[0][1]["memory_root"] == Path("xinyu-root/memory"), failures, "learning memory_root dependency changed")
    _check(calls[0][1]["lock"] is lock, failures, "learning lock dependency changed")


async def _main_async(failures: list[str]) -> None:
    await _check_desktop_service(failures)
    await _check_learning_service(failures)


def main() -> int:
    failures: list[str] = []
    _check_qq_sender(failures)
    _check_chat_service(failures)
    _check_codex_service(failures)
    asyncio.run(_main_async(failures))

    if failures:
        print("service_boundary_smoke failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("service_boundary_smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
