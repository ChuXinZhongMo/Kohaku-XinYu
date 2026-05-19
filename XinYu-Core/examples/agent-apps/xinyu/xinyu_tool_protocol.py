from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


PROTOCOL_VERSION = "xinyu.tool.v1"
ALLOWED_TOOLS = frozenset({"status_probe", "log_scan", "codex_delegate", "external_plugin_call"})
READ_ONLY_RISK = "read_only"
DELEGATED_LOCAL_RISK = "delegated_local"
EXTERNAL_RUNTIME_RISK = "external_runtime"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def new_turn_id() -> str:
    return f"turn-{uuid.uuid4().hex[:16]}"


def new_action_id() -> str:
    return f"act-{uuid.uuid4().hex[:16]}"


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


@dataclass
class ToolIntent:
    kind: str
    confidence: float
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ToolTarget:
    alias: str = ""
    time_hint: str = "recent"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ToolRequest:
    turn_id: str
    source: str
    intent: ToolIntent
    tool: str
    target: ToolTarget = field(default_factory=ToolTarget)
    risk: str = READ_ONLY_RISK
    requires_approval: bool = False
    fallback: str = "chat"
    params: dict[str, Any] = field(default_factory=dict)
    protocol: str = PROTOCOL_VERSION
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": self.protocol,
            "turn_id": self.turn_id,
            "created_at": self.created_at,
            "source": self.source,
            "intent": self.intent.to_dict(),
            "tool": self.tool,
            "target": self.target.to_dict(),
            "risk": self.risk,
            "requires_approval": self.requires_approval,
            "fallback": self.fallback,
            "params": dict(self.params),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ToolRequest":
        intent_value = value.get("intent") if isinstance(value.get("intent"), dict) else {}
        target_value = value.get("target") if isinstance(value.get("target"), dict) else {}
        return cls(
            protocol=_safe_str(value.get("protocol"), PROTOCOL_VERSION),
            turn_id=_safe_str(value.get("turn_id")) or new_turn_id(),
            created_at=_safe_str(value.get("created_at")) or now_iso(),
            source=_safe_str(value.get("source"), "unknown"),
            intent=ToolIntent(
                kind=_safe_str(intent_value.get("kind"), "unknown"),
                confidence=float(intent_value.get("confidence") or 0.0),
                evidence=[_safe_str(item) for item in intent_value.get("evidence", []) if _safe_str(item)],
            ),
            tool=_safe_str(value.get("tool")),
            target=ToolTarget(
                alias=_safe_str(target_value.get("alias")),
                time_hint=_safe_str(target_value.get("time_hint"), "recent"),
            ),
            risk=_safe_str(value.get("risk"), READ_ONLY_RISK),
            requires_approval=bool(value.get("requires_approval")),
            fallback=_safe_str(value.get("fallback"), "chat"),
            params=value.get("params") if isinstance(value.get("params"), dict) else {},
        )


@dataclass
class ActionOutcome:
    ok: bool
    tool: str
    summary: list[str]
    action_id: str = field(default_factory=new_action_id)
    target_alias: str = ""
    report_path: str = ""
    duration_ms: int = 0
    risk: str = READ_ONLY_RISK
    result: str = "success"
    load: dict[str, Any] = field(default_factory=dict)
    error_code: str = ""
    notes: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "action_id": self.action_id,
            "created_at": self.created_at,
            "tool": self.tool,
            "target_alias": self.target_alias,
            "summary": list(self.summary),
            "report_path": self.report_path,
            "duration_ms": int(self.duration_ms),
            "risk": self.risk,
            "result": self.result,
            "load": dict(self.load),
            "error_code": self.error_code,
            "notes": list(self.notes),
        }

    @classmethod
    def blocked(
        cls,
        *,
        tool: str,
        target_alias: str = "",
        summary: str | list[str],
        error_code: str,
        risk: str = READ_ONLY_RISK,
        duration_ms: int = 0,
        notes: list[str] | None = None,
    ) -> "ActionOutcome":
        return cls(
            ok=False,
            tool=tool,
            target_alias=target_alias,
            summary=[summary] if isinstance(summary, str) else list(summary),
            duration_ms=duration_ms,
            risk=risk,
            result="blocked_by_boundary",
            load={"timeout": False},
            error_code=error_code,
            notes=list(notes or []),
        )

    @classmethod
    def failed(
        cls,
        *,
        tool: str,
        target_alias: str = "",
        summary: str | list[str],
        error_code: str,
        risk: str = READ_ONLY_RISK,
        duration_ms: int = 0,
        load: dict[str, Any] | None = None,
        notes: list[str] | None = None,
    ) -> "ActionOutcome":
        return cls(
            ok=False,
            tool=tool,
            target_alias=target_alias,
            summary=[summary] if isinstance(summary, str) else list(summary),
            duration_ms=duration_ms,
            risk=risk,
            result="failure",
            load=dict(load or {}),
            error_code=error_code,
            notes=list(notes or []),
        )
