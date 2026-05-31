from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from xinyu_attention_posture import read_attention_posture

ExpressionTarget = Literal["qq", "desktop", "avatar", "tts"]
ExpressionIntensity = Literal["low", "medium", "high"]
SpeakingIntention = Literal["silent", "note", "ask", "report", "comfort", "refuse"]

TARGETS: tuple[ExpressionTarget, ...] = ("qq", "desktop", "avatar", "tts")
SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bauthorization\s*:\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bapi[_-]?key\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\btoken\s*[:=]\s*[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bpassword\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bsk-[a-z0-9_-]{12,}"),
)


@dataclass(frozen=True, slots=True)
class ExpressionEvent:
    expression_id: str
    created_at: str
    adapter_target: ExpressionTarget
    text: str
    emotion_vector: dict[str, float]
    intensity: ExpressionIntensity
    speaking_intention: SpeakingIntention
    visible_posture: str
    action_residue: str
    source_event_id: str = "none"
    source_route: str = "none"
    owner_private_only: bool = True
    identity_layer: str = "core_only"
    adapter_decision_allowed: bool = False
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["notes"] = list(self.notes)
        return data


def compose_expression_event(
    root: Path,
    *,
    adapter_target: ExpressionTarget = "desktop",
    text: str = "",
    source_event_id: str = "",
    source_route: str = "",
    created_at: str | None = None,
) -> ExpressionEvent:
    created_at = created_at or datetime.now().astimezone().isoformat(timespec="seconds")
    if adapter_target not in TARGETS:
        adapter_target = "desktop"
    posture = read_attention_posture(root)
    notes: list[str] = []
    sanitized_text = _sanitize_text(text or _default_text(posture), limit=_target_limit(adapter_target))
    if not sanitized_text:
        sanitized_text = "我先安静记一下。"
        notes.append("empty_text_replaced")
    attention_mode = posture.get("attention_mode", "available")
    intention = _speaking_intention(attention_mode, sanitized_text)
    intensity = _intensity(posture)
    emotion = _emotion_vector(attention_mode, intensity)
    visible_posture = _visible_posture(attention_mode, adapter_target)
    action_residue = _sanitize_text(posture.get("last_proactive_reason", "none"), limit=120)
    expression_id = f"expr-{_safe_token(source_event_id or posture.get('last_event_id') or 'none')}-{adapter_target}"
    return ExpressionEvent(
        expression_id=expression_id,
        created_at=created_at,
        adapter_target=adapter_target,
        text=sanitized_text,
        emotion_vector=emotion,
        intensity=intensity,
        speaking_intention=intention,
        visible_posture=visible_posture,
        action_residue=action_residue or "none",
        source_event_id=_sanitize_text(source_event_id or posture.get("last_event_id", "none"), limit=96),
        source_route=_sanitize_text(source_route or posture.get("last_route", "none"), limit=64),
        owner_private_only=adapter_target in {"qq", "desktop", "avatar", "tts"},
        identity_layer="core_only",
        adapter_decision_allowed=False,
        notes=tuple(notes),
    )


def expression_for_targets(
    root: Path,
    *,
    text: str = "",
    source_event_id: str = "",
    source_route: str = "",
    targets: tuple[ExpressionTarget, ...] = TARGETS,
    created_at: str | None = None,
) -> list[dict[str, Any]]:
    return [
        compose_expression_event(
            root,
            adapter_target=target,
            text=text,
            source_event_id=source_event_id,
            source_route=source_route,
            created_at=created_at,
        ).to_dict()
        for target in targets
        if target in TARGETS
    ]


def _default_text(posture: dict[str, str]) -> str:
    mode = posture.get("attention_mode", "available")
    reason = posture.get("last_proactive_reason", "none")
    if mode == "wants_to_speak" and reason not in {"", "none", "unknown"}:
        return reason
    if mode == "holding_question":
        return "我有个问题先放在心里，等合适的时候再问。"
    if mode == "processing_residue":
        return "刚才那点余波我还在整理。"
    if mode == "quietly_noted":
        return "我看见了，先不打扰。"
    return "我在。"


def _speaking_intention(attention_mode: str, text: str) -> SpeakingIntention:
    if attention_mode == "available" and text in {"我在。", "我先安静记一下。"}:
        return "silent"
    if attention_mode == "wants_to_speak" or text.endswith(("?", "？")) or "要不要" in text:
        return "ask"
    if attention_mode == "processing_residue":
        return "report"
    return "note"


def _intensity(posture: dict[str, str]) -> ExpressionIntensity:
    if posture.get("owner_private_priority") == "high" or posture.get("interruptibility") == "high_for_owner_private":
        return "high"
    if posture.get("attention_mode") in {"holding_question", "processing_residue"}:
        return "medium"
    return "low"


def _emotion_vector(attention_mode: str, intensity: ExpressionIntensity) -> dict[str, float]:
    base = {"calm": 0.65, "curiosity": 0.25, "warmth": 0.35, "urgency": 0.05}
    if attention_mode == "wants_to_speak":
        base.update({"curiosity": 0.55, "warmth": 0.5, "urgency": 0.45})
    elif attention_mode == "holding_question":
        base.update({"curiosity": 0.5, "urgency": 0.2})
    elif attention_mode == "processing_residue":
        base.update({"calm": 0.5, "warmth": 0.4, "urgency": 0.18})
    elif attention_mode == "quietly_noted":
        base.update({"calm": 0.78, "urgency": 0.02})
    if intensity == "high":
        base["urgency"] = max(base["urgency"], 0.4)
    return base


def _visible_posture(attention_mode: str, target: ExpressionTarget) -> str:
    if target == "qq":
        return "short_private_text"
    if attention_mode == "wants_to_speak":
        return "leaning_forward"
    if attention_mode == "holding_question":
        return "thinking_wait"
    if attention_mode == "processing_residue":
        return "soft_processing"
    if attention_mode == "quietly_noted":
        return "quiet_presence"
    return "idle_breathing"


def _target_limit(target: ExpressionTarget) -> int:
    if target == "qq":
        return 360
    if target == "tts":
        return 220
    return 280


def _sanitize_text(value: Any, *, limit: int) -> str:
    text = re.sub(r"\s+", " ", "" if value is None else str(value)).strip()
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("<secret>", text)
    if len(text) > limit:
        return text[: max(0, limit - 3)].rstrip() + "..."
    return text


def _safe_token(value: Any) -> str:
    text = _sanitize_text(value, limit=80).lower().replace(" ", "-")
    text = re.sub(r"[^a-z0-9_.:-]+", "-", text).strip("-")
    return text or "none"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compose adapter-neutral XinYu expression events from attention posture.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--text", default="")
    parser.add_argument("--source-event-id", default="")
    parser.add_argument("--source-route", default="")
    parser.add_argument("--target", choices=TARGETS, default="desktop")
    parser.add_argument("--all-targets", action="store_true")
    args = parser.parse_args(argv)
    if args.all_targets:
        result: Any = expression_for_targets(
            args.root,
            text=args.text,
            source_event_id=args.source_event_id,
            source_route=args.source_route,
        )
    else:
        result = compose_expression_event(
            args.root,
            adapter_target=args.target,
            text=args.text,
            source_event_id=args.source_event_id,
            source_route=args.source_route,
        ).to_dict()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
