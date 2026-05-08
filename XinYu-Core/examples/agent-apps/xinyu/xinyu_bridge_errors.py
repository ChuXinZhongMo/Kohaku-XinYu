from __future__ import annotations

from http import HTTPStatus


class BridgeRequestError(RuntimeError):
    def __init__(self, status: HTTPStatus, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
