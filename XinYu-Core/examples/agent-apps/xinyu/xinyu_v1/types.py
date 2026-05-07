"""Shared primitives for the XinYu v1 runtime.

This module is intentionally small and dependency-free. Domain-specific models
belong in their own packages; this file only carries cross-layer enums, aliases,
protocols, and tiny value objects that are safe to import from anywhere.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Final, Generic, Protocol, TypeAlias, TypeVar, runtime_checkable


JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]
JSONMapping: TypeAlias = Mapping[str, JSONValue]
MutableJSONMapping: TypeAlias = MutableMapping[str, JSONValue]
RawPayload: TypeAlias = Mapping[str, Any]
Headers: TypeAlias = Mapping[str, str]
Metadata: TypeAlias = dict[str, JSONValue]

TraceId: TypeAlias = str
RequestId: TypeAlias = str
SessionId: TypeAlias = str
MemoryId: TypeAlias = str
ActorId: TypeAlias = str
Vector: TypeAlias = tuple[float, ...]
Embedding: TypeAlias = tuple[float, ...]

DEFAULT_TRACE_ID: Final[str] = "trace-unset"
DEFAULT_REQUEST_ID: Final[str] = "request-unset"
MAX_RISK_SCORE: Final[float] = 1.0
MIN_RISK_SCORE: Final[float] = 0.0


class XinYuEnum(str, Enum):
    """Base enum with stable string values for logs, JSON, and configs."""

    @classmethod
    def values(cls) -> tuple[str, ...]:
        return tuple(member.value for member in cls)

    @classmethod
    def names(cls) -> tuple[str, ...]:
        return tuple(member.name for member in cls)

    def __str__(self) -> str:
        return self.value


EnumT = TypeVar("EnumT", bound=XinYuEnum)
T = TypeVar("T")


class RuntimeMode(XinYuEnum):
    LIVE = "live"
    SHADOW = "shadow"
    DRY_RUN = "dry_run"
    TEST = "test"


class SourceChannel(XinYuEnum):
    OWNER_PRIVATE = "owner_private"
    QQ_PRIVATE = "qq_private"
    QQ_GROUP = "qq_group"
    PRIORITY_LEARNING_GROUP = "priority_learning_group"
    CLI = "cli"
    MAINTENANCE = "maintenance"
    PROACTIVE = "proactive"
    BRIDGE_PROBE = "bridge_probe"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class ActorScope(XinYuEnum):
    OWNER = "owner"
    GROUP_MEMBER = "group_member"
    EXTERNAL_CONTACT = "external_contact"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class PrivacyScope(XinYuEnum):
    OWNER_PRIVATE = "owner_private"
    GROUP_CONTEXT = "group_context"
    EXTERNAL_PRIVATE = "external_private"
    PUBLIC_SOURCE = "public_source"
    SYSTEM_INTERNAL = "system_internal"
    UNKNOWN = "unknown"


class TurnKind(XinYuEnum):
    HUMAN_CHAT = "human_chat"
    OBSERVATION = "observation"
    LEARNING_INGEST = "learning_ingest"
    FILE_ATTACHMENT = "file_attachment"
    MAINTENANCE = "maintenance"
    PROACTIVE_CLAIM = "proactive_claim"
    PROACTIVE_ACK = "proactive_ack"
    PROBE = "probe"
    SYSTEM = "system"


class RouteName(XinYuEnum):
    FAST_PATH = "fast_path"
    SLOW_PATH = "slow_path"
    MAINTENANCE = "maintenance"
    SHADOW_ONLY = "shadow_only"
    BLOCKED = "blocked"


class RouteConfidence(XinYuEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SafetyDecision(XinYuEnum):
    ALLOW = "allow"
    REVIEW = "review"
    BLOCK = "block"


class Severity(XinYuEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class HealthState(XinYuEnum):
    OK = "ok"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    FAILED = "failed"
    UNKNOWN = "unknown"


class VectorBackendKind(XinYuEnum):
    QDRANT = "qdrant"
    CHROMA = "chroma"
    JSONL = "jsonl"
    DISABLED = "disabled"


class MemoryLayer(XinYuEnum):
    EVENTS = "events"
    CONTEXT = "context"
    SELF = "self"
    EMOTION = "emotion"
    RELATIONSHIP_OWNER = "relationship_owner"
    RELATIONSHIP_PEOPLE = "relationship_people"
    KNOWLEDGE = "knowledge"
    LEARNING = "learning"
    DREAMS = "dreams"
    ARCHIVE = "archive"
    SYSTEM = "system"


class MemoryWriteMode(XinYuEnum):
    NONE = "none"
    EVENT_ONLY = "event_only"
    REVIEW_QUEUE = "review_queue"
    COMPATIBILITY_SNAPSHOT = "compatibility_snapshot"
    STABLE_ALLOWED = "stable_allowed"


class MaintenanceJobKind(XinYuEnum):
    VECTOR_REPAIR = "vector_repair"
    EVENT_LOG_CHECK = "event_log_check"
    DREAM_CONSOLIDATION = "dream_consolidation"
    DEADLOCK_INSPECTION = "deadlock_inspection"
    ARCHIVE_PROPOSAL = "archive_proposal"
    HEALTHCHECK = "healthcheck"


@dataclass(frozen=True, slots=True)
class TraceContext:
    """Privacy-aware request trace metadata shared across runtime layers."""

    trace_id: TraceId = DEFAULT_TRACE_ID
    request_id: RequestId = DEFAULT_REQUEST_ID
    parent_id: TraceId | None = None
    session_hash: str = ""
    actor_hash: str = ""
    started_at: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)

    def with_tag(self, tag: str) -> "TraceContext":
        clean_tag = tag.strip()
        if not clean_tag or clean_tag in self.tags:
            return self
        return TraceContext(
            trace_id=self.trace_id,
            request_id=self.request_id,
            parent_id=self.parent_id,
            session_hash=self.session_hash,
            actor_hash=self.actor_hash,
            started_at=self.started_at,
            tags=(*self.tags, clean_tag),
        )

    def to_json(self) -> dict[str, JSONValue]:
        return {
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "parent_id": self.parent_id,
            "session_hash": self.session_hash,
            "actor_hash": self.actor_hash,
            "started_at": self.started_at,
            "tags": list(self.tags),
        }


@dataclass(frozen=True, slots=True)
class LatencyBudget:
    """Soft latency budgets in seconds."""

    total_seconds: float = 120.0
    fast_path_seconds: float = 1.5
    slow_path_seconds: float = 90.0
    vector_seconds: float = 3.0
    maintenance_seconds: float = 300.0

    def budget_for_route(self, route: RouteName) -> float:
        if route is RouteName.FAST_PATH:
            return self.fast_path_seconds
        if route is RouteName.SLOW_PATH:
            return self.slow_path_seconds
        if route is RouteName.MAINTENANCE:
            return self.maintenance_seconds
        return self.total_seconds


@dataclass(frozen=True, slots=True)
class TokenBudget:
    """Prompt and response token budget split."""

    total: int = 4096
    retrieved_memory: int = 1400
    prompt_context: int = 1800
    response: int = 600

    def validate(self) -> "TokenBudget":
        minimum = 1
        return TokenBudget(
            total=max(minimum, self.total),
            retrieved_memory=max(0, min(self.retrieved_memory, self.total)),
            prompt_context=max(0, min(self.prompt_context, self.total)),
            response=max(minimum, min(self.response, self.total)),
        )


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Small retry policy value object used by IO adapters."""

    attempts: int = 2
    base_delay_seconds: float = 0.25
    max_delay_seconds: float = 4.0
    retryable_statuses: tuple[int, ...] = (408, 429, 500, 502, 503, 504)

    def normalized(self) -> "RetryPolicy":
        attempts = max(1, self.attempts)
        base_delay = max(0.0, self.base_delay_seconds)
        max_delay = max(base_delay, self.max_delay_seconds)
        statuses = tuple(sorted(set(self.retryable_statuses)))
        return RetryPolicy(
            attempts=attempts,
            base_delay_seconds=base_delay,
            max_delay_seconds=max_delay,
            retryable_statuses=statuses,
        )


@dataclass(frozen=True, slots=True)
class GateDecision:
    """Generic allow/review/block decision with audit-friendly reasons."""

    decision: SafetyDecision
    reason: str
    severity: Severity = Severity.INFO
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def allowed(self) -> bool:
        return self.decision is SafetyDecision.ALLOW

    @property
    def blocked(self) -> bool:
        return self.decision is SafetyDecision.BLOCK

    def to_json(self) -> dict[str, JSONValue]:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "severity": self.severity.value,
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class ServiceHealth:
    """Machine-readable status for one runtime component."""

    component: str
    state: HealthState
    message: str = ""
    checked_at: str = ""
    details: dict[str, JSONValue] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.state is HealthState.OK

    def to_json(self) -> dict[str, JSONValue]:
        return {
            "component": self.component,
            "state": self.state.value,
            "message": self.message,
            "checked_at": self.checked_at,
            "details": dict(self.details),
        }


@dataclass(frozen=True, slots=True)
class ResourceUsage:
    """Per-turn resource usage summary."""

    input_tokens: int = 0
    output_tokens: int = 0
    model_calls: int = 0
    vector_queries: int = 0
    elapsed_ms: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def to_json(self) -> dict[str, JSONValue]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "model_calls": self.model_calls,
            "vector_queries": self.vector_queries,
            "elapsed_ms": self.elapsed_ms,
        }


@dataclass(frozen=True, slots=True)
class Outcome(Generic[T]):
    """Typed operation result for boundaries that should not raise casually."""

    ok: bool
    value: T | None = None
    error: str = ""
    notes: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def success(cls, value: T, notes: Sequence[str] = ()) -> "Outcome[T]":
        return cls(ok=True, value=value, notes=tuple(str(item) for item in notes))

    @classmethod
    def failure(cls, error: str, notes: Sequence[str] = ()) -> "Outcome[T]":
        return cls(ok=False, error=error.strip() or "unknown_error", notes=tuple(str(item) for item in notes))


@dataclass(frozen=True, slots=True)
class TextSpan:
    """A source text span with optional offsets."""

    text: str
    start: int | None = None
    end: int | None = None

    def normalized(self) -> "TextSpan":
        clean_text = " ".join(self.text.split())
        start = self.start if isinstance(self.start, int) and self.start >= 0 else None
        end = self.end if isinstance(self.end, int) and self.end >= 0 else None
        if start is not None and end is not None and end < start:
            end = start
        return TextSpan(text=clean_text, start=start, end=end)

    def to_json(self) -> dict[str, JSONValue]:
        return {"text": self.text, "start": self.start, "end": self.end}


@runtime_checkable
class SupportsJSON(Protocol):
    def to_json(self) -> dict[str, JSONValue]:
        """Return a JSON-serializable dictionary."""


@runtime_checkable
class AsyncLifecycle(Protocol):
    async def start(self) -> None:
        """Start the component."""

    async def stop(self) -> None:
        """Stop the component and release resources."""


@runtime_checkable
class Clock(Protocol):
    def now_iso(self) -> str:
        """Return a timezone-aware ISO timestamp."""

    def monotonic(self) -> float:
        """Return a monotonic timestamp for duration measurement."""


@runtime_checkable
class MetricsSink(Protocol):
    def increment(self, name: str, value: int = 1, tags: Mapping[str, str] | None = None) -> None:
        """Increment a counter-like metric."""

    def observe(self, name: str, value: float, tags: Mapping[str, str] | None = None) -> None:
        """Record a timing or distribution metric."""


@runtime_checkable
class AuditSink(Protocol):
    def record(self, event_type: str, payload: JSONMapping, trace: TraceContext | None = None) -> None:
        """Append an audit event."""


def clamp_float(value: float, minimum: float, maximum: float) -> float:
    """Clamp a float with defensive handling for invalid ranges."""

    if maximum < minimum:
        minimum, maximum = maximum, minimum
    return max(minimum, min(maximum, value))


def normalize_risk_score(value: object, default: float = 0.0) -> float:
    """Coerce a value into the shared 0.0-1.0 risk-score range."""

    try:
        score = float(value)
    except (TypeError, ValueError):
        score = default
    return clamp_float(score, MIN_RISK_SCORE, MAX_RISK_SCORE)


def coerce_enum(enum_type: type[EnumT], value: object, default: EnumT) -> EnumT:
    """Coerce strings from configs or payloads into a XinYu enum member."""

    if isinstance(value, enum_type):
        return value
    text = str(value or "").strip()
    if not text:
        return default

    try:
        return enum_type(text)
    except ValueError:
        pass

    lowered = text.lower()
    for member in enum_type:
        if lowered == member.name.lower() or lowered == member.value.lower():
            return member
    return default


def coerce_str_tuple(value: object) -> tuple[str, ...]:
    """Coerce config/list-like values into a clean immutable string tuple."""

    if value is None:
        return ()
    if isinstance(value, str):
        items = value.split(",")
    elif isinstance(value, Sequence):
        items = value
    else:
        items = (value,)

    cleaned: list[str] = []
    for item in items:
        text = str(item).strip()
        if text:
            cleaned.append(text)
    return tuple(cleaned)


def safe_json_mapping(value: object) -> dict[str, JSONValue]:
    """Best-effort shallow JSON mapping coercion for untrusted payload metadata."""

    if not isinstance(value, Mapping):
        return {}

    result: dict[str, JSONValue] = {}
    for raw_key, raw_value in value.items():
        key = str(raw_key).strip()
        if not key:
            continue
        coerced = _coerce_json_value(raw_value)
        if coerced is not _SKIP:
            result[key] = coerced
    return result


class _SkipValue:
    pass


_SKIP: Final[_SkipValue] = _SkipValue()


def _coerce_json_value(value: object) -> JSONValue | _SkipValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return safe_json_mapping(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        items: list[JSONValue] = []
        for item in value:
            coerced = _coerce_json_value(item)
            if coerced is not _SKIP:
                items.append(coerced)
        return items
    return str(value)

