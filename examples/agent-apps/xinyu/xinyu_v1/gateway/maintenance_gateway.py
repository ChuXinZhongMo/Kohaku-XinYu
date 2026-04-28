"""Synthetic maintenance turn construction."""

from __future__ import annotations

from ..clock import SystemClock
from ..types import ActorScope, PrivacyScope, SourceChannel, TraceContext, TurnKind
from .models import ActorContext, GatewayMetadata, InboundTurn


MAINTENANCE_TEXT = (
    "Maintenance-only pass. Do not initiate visible chat. Refresh state, inspect queues, "
    "and produce reviewable maintenance artifacts only."
)


def build_maintenance_turn(reason: str = "idle_maintenance", *, clock: SystemClock | None = None) -> InboundTurn:
    active_clock = clock or SystemClock()
    timestamp = active_clock.now_iso()
    actor = ActorContext(
        actor_id="system",
        session_id="maintenance",
        source_channel=SourceChannel.MAINTENANCE,
        actor_scope=ActorScope.SYSTEM,
        privacy_scope=PrivacyScope.SYSTEM_INTERNAL,
    )
    trace = TraceContext(
        trace_id=f"tr-maintenance-{timestamp}",
        request_id=f"req-maintenance-{timestamp}",
        actor_hash="system",
        session_hash="maintenance",
        started_at=timestamp,
        tags=("maintenance", reason),
    )
    return InboundTurn(
        text=MAINTENANCE_TEXT,
        kind=TurnKind.MAINTENANCE,
        actor=actor,
        timestamp=timestamp,
        trace=trace,
        metadata=GatewayMetadata(platform="system", adapter="xinyu_v1", message_type="maintenance"),
        raw_payload={"reason": reason},
    )

