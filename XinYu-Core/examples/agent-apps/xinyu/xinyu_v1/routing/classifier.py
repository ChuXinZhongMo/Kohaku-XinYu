"""Deterministic turn pre-classifier."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..gateway.models import InboundTurn
from ..types import RouteName, TurnKind


GREETING_MARKERS = ("hi", "hello", "hey", "早", "早安", "晚上好", "你好", "在吗")
ACK_MARKERS = ("嗯", "哦", "好", "行", "知道了", "ok", "OK")
RELATIONSHIP_MARKERS = ("难过", "生气", "失望", "想你", "讨厌", "别这样", "不像你", "陪我", "关系")
LEARNING_MARKERS = ("学习", "资料", "论文", "源码", "仓库", "读一下", "总结")
CONFLICT_MARKERS = ("矛盾", "冲突", "为什么", "你刚才", "不对", "不是这样")


GREETING_MARKERS = (
    "hi",
    "hello",
    "hey",
    "good morning",
    "good evening",
    "早",
    "早安",
    "晚上好",
    "你好",
    "在吗",
    "こんにちは",
    "こんばんは",
    "おはよう",
)
ACK_MARKERS = ("嗯", "哦", "好", "行", "知道了", "ok", "okay", "got it", "了解", "うん", "はい")
RELATIONSHIP_MARKERS = (
    "难过",
    "生气",
    "失望",
    "想你",
    "讨厌",
    "别这样",
    "不像你",
    "陪我",
    "关系",
    "disappointed",
    "upset",
    "angry",
    "寂しい",
    "失望した",
)
LEARNING_MARKERS = (
    "学习",
    "资料",
    "论文",
    "源码",
    "仓库",
    "读一下",
    "总结",
    "research",
    "paper",
    "source code",
    "repository",
    "調べて",
    "まとめて",
)
CONFLICT_MARKERS = (
    "矛盾",
    "冲突",
    "为什么",
    "你刚才",
    "不对",
    "不是这样",
    "why",
    "conflict",
    "違う",
    "さっき",
)


@dataclass(frozen=True, slots=True)
class TurnClassification:
    route_hint: RouteName
    intents: tuple[str, ...]
    salience: float
    needs_memory: bool
    needs_model: bool
    notes: tuple[str, ...] = field(default_factory=tuple)


class TurnClassifier:
    def classify(self, turn: InboundTurn) -> TurnClassification:
        text = turn.compact_text(500)
        intents: list[str] = []
        notes: list[str] = []

        if turn.kind in {TurnKind.MAINTENANCE, TurnKind.PROACTIVE_CLAIM, TurnKind.PROACTIVE_ACK}:
            return TurnClassification(RouteName.MAINTENANCE, ("maintenance",), 0.2, False, False)
        if turn.kind is TurnKind.PROBE:
            return TurnClassification(RouteName.FAST_PATH, ("probe",), 0.0, False, False)
        if turn.has_attachments:
            intents.append("attachment")
        if _contains_any(text, GREETING_MARKERS) and len(text) <= 20:
            intents.append("greeting")
        if "greeting" not in intents and _contains_any(text, ACK_MARKERS) and len(text) <= 12:
            intents.append("ack")
        if _contains_any(text, RELATIONSHIP_MARKERS):
            intents.append("relationship_pressure")
        if _contains_any(text, LEARNING_MARKERS):
            intents.append("learning")
        if _contains_any(text, CONFLICT_MARKERS):
            intents.append("conflict")

        high_risk = bool({"attachment", "relationship_pressure", "learning", "conflict"}.intersection(intents))
        if not text.strip():
            return TurnClassification(RouteName.FAST_PATH, ("empty",), 0.0, False, False, ("blank_text",))
        if high_risk:
            salience = 0.8 if "relationship_pressure" in intents else 0.65
            return TurnClassification(RouteName.SLOW_PATH, tuple(intents), salience, True, True, tuple(notes))
        if "greeting" in intents or "ack" in intents:
            return TurnClassification(RouteName.FAST_PATH, tuple(intents), 0.15, False, False, tuple(notes))
        return TurnClassification(RouteName.SLOW_PATH, tuple(intents or ["ordinary_chat"]), 0.35, True, True, tuple(notes))


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in markers)
