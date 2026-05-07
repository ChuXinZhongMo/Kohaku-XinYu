from __future__ import annotations

from http import HTTPStatus

from xinyu_chat_service import ChatServiceError, PAYLOAD_TOO_LARGE_STATUS, build_chat_service


def _payload_text(payload: dict[str, object]) -> str:
    return str(payload.get("text") or "").strip()


def _session_key(payload: dict[str, object]) -> str:
    return str(payload.get("session_id") or "fallback")


def main() -> int:
    failures: list[str] = []
    service = build_chat_service()

    empty = service.prepare_request({}, max_text_chars=10, payload_text=_payload_text, session_key=_session_key)
    if empty.empty_response != {"accepted": True, "reply": "", "memory_changed": False, "notes": ["empty_text"]}:
        failures.append("empty text response changed")

    request = service.prepare_request(
        {"text": "hello", "session_id": "session-smoke"},
        max_text_chars=10,
        payload_text=_payload_text,
        session_key=_session_key,
    )
    if request.text != "hello" or request.session_key != "session-smoke" or request.empty_response is not None:
        failures.append("normal chat request was not prepared")

    try:
        service.prepare_request([], max_text_chars=10, payload_text=_payload_text, session_key=_session_key)
        failures.append("non-object payload was accepted")
    except ChatServiceError as exc:
        if exc.status != HTTPStatus.BAD_REQUEST:
            failures.append("non-object payload returned wrong status")

    try:
        service.prepare_request({"text": "x" * 11}, max_text_chars=10, payload_text=_payload_text, session_key=_session_key)
        failures.append("too-long text was accepted")
    except ChatServiceError as exc:
        if exc.status != PAYLOAD_TOO_LARGE_STATUS or "11 chars > 10" not in exc.message:
            failures.append("too-long text returned wrong error")

    clock = service.start_turn_clock()
    if clock.started_at <= 0 or "T" not in clock.started_wall:
        failures.append("turn clock was not populated")

    if failures:
        print("chat_service_smoke failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("chat_service_smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
