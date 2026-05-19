from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from http import HTTPStatus
from typing import Any, Callable


PAYLOAD_TOO_LARGE_STATUS = getattr(HTTPStatus, "PAYLOAD_TOO_LARGE", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)


class ChatServiceError(RuntimeError):
    def __init__(self, status: HTTPStatus, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass(frozen=True, slots=True)
class ChatRequest:
    payload: dict[str, Any]
    text: str
    session_key: str
    empty_response: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ChatTurnClock:
    started_at: float
    started_wall: str


class ChatService:
    def prepare_request(
        self,
        payload: Any,
        *,
        max_text_chars: int,
        payload_text: Callable[[dict[str, Any]], str],
        session_key: Callable[[dict[str, Any]], str],
    ) -> ChatRequest:
        if not isinstance(payload, dict):
            raise ChatServiceError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")

        text = payload_text(payload)
        if not text:
            return ChatRequest(
                payload=payload,
                text="",
                session_key="",
                empty_response={
                    "accepted": True,
                    "reply": "",
                    "memory_changed": False,
                    "notes": ["empty_text"],
                },
            )
        if len(text) > max_text_chars:
            raise ChatServiceError(
                PAYLOAD_TOO_LARGE_STATUS,
                f"text is too long: {len(text)} chars > {max_text_chars}",
            )
        return ChatRequest(payload=payload, text=text, session_key=session_key(payload))

    @staticmethod
    def start_turn_clock() -> ChatTurnClock:
        return ChatTurnClock(
            started_at=time.perf_counter(),
            started_wall=datetime.now().astimezone().isoformat(),
        )


def build_chat_service() -> ChatService:
    return ChatService()
