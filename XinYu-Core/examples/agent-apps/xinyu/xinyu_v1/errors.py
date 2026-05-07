"""Typed exception boundaries for XinYu v1."""

from __future__ import annotations

from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any

from .types import JSONValue, Severity


@dataclass(frozen=True, slots=True)
class ErrorDetail:
    code: str
    message: str
    severity: Severity = Severity.ERROR
    status: HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR
    details: dict[str, JSONValue] = field(default_factory=dict)

    def to_json(self) -> dict[str, JSONValue]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "status": int(self.status),
            "details": dict(self.details),
        }


class XinYuV1Error(RuntimeError):
    """Base class for expected v1 runtime failures."""

    code = "xinyu_v1_error"
    status = HTTPStatus.INTERNAL_SERVER_ERROR
    severity = Severity.ERROR

    def __init__(self, message: str, *, details: dict[str, JSONValue] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_detail(self) -> ErrorDetail:
        return ErrorDetail(
            code=self.code,
            message=self.message,
            severity=self.severity,
            status=self.status,
            details=self.details,
        )

    def to_json(self) -> dict[str, JSONValue]:
        return self.to_detail().to_json()


class ConfigurationError(XinYuV1Error):
    code = "configuration_error"
    status = HTTPStatus.INTERNAL_SERVER_ERROR


class PathPolicyError(XinYuV1Error):
    code = "path_policy_error"
    status = HTTPStatus.FORBIDDEN
    severity = Severity.WARNING


class BridgeProtocolError(XinYuV1Error):
    code = "bridge_protocol_error"
    status = HTTPStatus.BAD_REQUEST
    severity = Severity.WARNING


class AuthenticationError(XinYuV1Error):
    code = "authentication_error"
    status = HTTPStatus.UNAUTHORIZED
    severity = Severity.WARNING


class RoutingError(XinYuV1Error):
    code = "routing_error"
    status = HTTPStatus.INTERNAL_SERVER_ERROR


class MemoryBackendError(XinYuV1Error):
    code = "memory_backend_error"
    status = HTTPStatus.SERVICE_UNAVAILABLE


class VectorStoreUnavailableError(MemoryBackendError):
    code = "vector_store_unavailable"


class EmotionStateError(XinYuV1Error):
    code = "emotion_state_error"


class ReasoningError(XinYuV1Error):
    code = "reasoning_error"
    status = HTTPStatus.BAD_GATEWAY


class ResponseSafetyError(XinYuV1Error):
    code = "response_safety_error"
    status = HTTPStatus.FORBIDDEN
    severity = Severity.WARNING


class MaintenanceLockError(XinYuV1Error):
    code = "maintenance_lock_error"
    status = HTTPStatus.CONFLICT
    severity = Severity.INFO


def error_to_json(exc: BaseException) -> dict[str, Any]:
    """Convert arbitrary exceptions to a stable bridge-safe JSON object."""

    if isinstance(exc, XinYuV1Error):
        return exc.to_json()
    return ErrorDetail(
        code="unexpected_error",
        message=str(exc) or exc.__class__.__name__,
        severity=Severity.ERROR,
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
    ).to_json()

