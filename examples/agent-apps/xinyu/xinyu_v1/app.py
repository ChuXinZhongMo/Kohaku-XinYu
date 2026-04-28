"""Top-level XinYu v1 application wiring."""

from __future__ import annotations

from pathlib import Path

from .clock import SystemClock
from .config import XinYuV1Config
from .emotion.models import EmotionDelta, EmotionState
from .emotion.persistence import read_emotion_state, write_compat_markdown, write_emotion_state
from .emotion.state_machine import EmotionStateMachine
from .gateway.models import BridgeReply, InboundTurn
from .gateway.normalizer import TurnNormalizer
from .memory.models import MemoryEvent, MemoryLayer, MemoryQuery, MemoryWriteIntent
from .memory.orchestrator import MemoryOrchestrator
from .reasoning.local_reflex import LocalReflexReasoner
from .reasoning.models import ReasoningRequest, ReasoningResult
from .reasoning.slow_runtime import SlowReasoningRuntime
from .response.models import DraftReply
from .response.renderer import ResponseRenderer
from .routing.hybrid_router import HybridRouter
from .types import MemoryWriteMode, RouteName, TurnKind


class XinYuV1App:
    def __init__(self, config: XinYuV1Config) -> None:
        self.config = config
        self.clock = SystemClock(config.timezone_name)
        self.normalizer = TurnNormalizer(clock=self.clock)
        self.router = HybridRouter()
        self.memory = MemoryOrchestrator(runtime_root=config.paths.runtime_root)
        self.emotion_machine = EmotionStateMachine()
        self.local_reflex = LocalReflexReasoner()
        self.slow_runtime = SlowReasoningRuntime(config.model)
        self.renderer = ResponseRenderer()
        self._emotion_path = config.paths.runtime_path("emotion_state.json")
        self._emotion_compat_path = config.paths.memory_path("emotions", "current_state.v1.md")

    @classmethod
    def load(cls, root: Path | None = None) -> "XinYuV1App":
        return cls(XinYuV1Config.load(root))

    async def handle_payload(self, payload: dict[str, object]) -> BridgeReply:
        turn = self.normalizer.normalize(payload)
        return await self.handle_turn(turn)

    async def shadow_payload(self, payload: dict[str, object]) -> BridgeReply:
        turn = self.normalizer.normalize(payload)
        return await self.shadow_turn(turn)

    async def shadow_turn(self, turn: InboundTurn) -> BridgeReply:
        decision = self.router.decide(turn)
        emotion_state = self._read_emotion()
        await self._record_raw_event(turn, decision.route)
        self._update_emotion(turn, emotion_state, decision.classification.salience)
        return BridgeReply(
            accepted=True,
            reply="",
            memory_changed=False,
            notes=(
                "v1_shadow",
                f"route:{decision.route.value}",
                f"route_confidence:{decision.confidence.value}",
            ),
            route=decision.route.value,
            trace_id=turn.trace.trace_id,
        )

    async def handle_turn(self, turn: InboundTurn) -> BridgeReply:
        started = self.clock.monotonic()
        decision = self.router.decide(turn)
        emotion_state = self._read_emotion()
        await self._record_raw_event(turn, decision.route)

        memories = ()
        if decision.is_slow_path:
            memories = await self.memory.retrieve(
                MemoryQuery(
                    text=turn.text,
                    layers=(),
                    limit=8,
                    min_score=0.05,
                    trace=turn.trace,
                )
            )

        request = ReasoningRequest(turn=turn, route=decision, memories=memories, emotion_state=emotion_state)
        result = await self._reason(request)
        self._update_emotion(turn, emotion_state, decision.classification.salience)
        final = self.renderer.render(DraftReply(text=result.draft, source=decision.route.value, notes=result.notes), turn)

        elapsed_ms = self.clock.elapsed_ms(started)
        notes = (
            *final.notes,
            f"route:{decision.route.value}",
            f"route_confidence:{decision.confidence.value}",
            f"elapsed_ms:{elapsed_ms}",
        )
        return BridgeReply(
            accepted=final.accepted,
            reply=final.text,
            memory_changed=result.memory_changed,
            notes=tuple(str(note) for note in notes if str(note).strip()),
            route=decision.route.value,
            trace_id=turn.trace.trace_id,
        )

    async def _reason(self, request: ReasoningRequest) -> ReasoningResult:
        if request.route.route is RouteName.FAST_PATH:
            return await self.local_reflex.run(request)
        if request.route.route is RouteName.MAINTENANCE:
            return ReasoningResult(draft="[WAITING]", memory_changed=False, notes=("maintenance_route",))
        try:
            return await self.slow_runtime.run(
                request,
                timeout_seconds=self.config.latency.budget_for_route(RouteName.SLOW_PATH),
            )
        except Exception as exc:
            return ReasoningResult(
                draft="我先慢一点想。",
                memory_changed=None,
                notes=("slow_path_failed", exc.__class__.__name__),
            )

    async def _record_raw_event(self, turn: InboundTurn, route: RouteName) -> None:
        if turn.kind not in {TurnKind.HUMAN_CHAT, TurnKind.OBSERVATION, TurnKind.FILE_ATTACHMENT}:
            return
        event = MemoryEvent.from_text(
            text=turn.text,
            timestamp=turn.timestamp,
            source_channel=turn.actor.source_channel,
            privacy_scope=turn.actor.privacy_scope,
            actor_hash=turn.trace.actor_hash,
            salience=0,
            layers=(MemoryLayer.EVENTS,),
            metadata={"route": route.value, "turn_kind": turn.kind.value},
        )
        await self.memory.record_event(event)
        if turn.text.strip():
            await self.memory.write(
                MemoryWriteIntent(
                    text=turn.text,
                    layer=MemoryLayer.EVENTS,
                    mode=MemoryWriteMode.EVENT_ONLY,
                    timestamp=turn.timestamp,
                    source_event_id=event.event_id,
                    tags=(turn.actor.source_channel.value,),
                    metadata={"trace_id": turn.trace.trace_id},
                )
            )

    def _read_emotion(self) -> EmotionState:
        return read_emotion_state(self._emotion_path, default_timestamp=self.clock.now_iso())

    def _update_emotion(self, turn: InboundTurn, state: EmotionState, salience: float) -> None:
        if not self.config.features.emotion_engine_enabled:
            return
        delta_values: dict[str, float] = {}
        text = turn.text
        if any(marker in text for marker in ("难过", "失望", "受伤")):
            delta_values.update({"hurt": 0.8, "guardedness": 0.35, "warmth": -0.2})
        elif any(marker in text for marker in ("想你", "陪我", "在吗")):
            delta_values.update({"warmth": 0.4, "attachment": 0.35})
        elif any(marker in text for marker in ("学习", "资料", "论文")):
            delta_values.update({"curiosity": 0.35, "fatigue": 0.08})
        if not delta_values:
            delta_values = {"stability": 0.08}
        transition = self.emotion_machine.apply(
            state,
            EmotionDelta(delta_values, salience=salience, reason="turn_update"),
            timestamp=self.clock.now_iso(),
        )
        write_emotion_state(self._emotion_path, transition.current)
        write_compat_markdown(self._emotion_compat_path, transition.current)
