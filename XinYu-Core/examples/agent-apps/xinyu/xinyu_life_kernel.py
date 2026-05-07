from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ChosenAction = Literal[
    "send_qq",
    "leave_note_on_desk",
    "suppress_and_wait",
    "write_diary",
    "request_metabolism_window",
]
TensionBand = Literal["quiet", "forming", "approach", "inhibited"]
EntropyBand = Literal["clear", "noise", "fracture", "terminal"]


class ResourceRequest(BaseModel):
    kind: Literal["metabolism_window"] = "metabolism_window"
    requested_seconds: int = Field(ge=60, le=1800)
    intensity: float = Field(ge=0.0, le=1.0)
    needs_explicit_approval: bool = True
    reason: str


class EntropyState(BaseModel):
    version: int = 1
    snapshot_at: str = Field(default_factory=lambda: datetime.now().astimezone().isoformat())
    entropy_level: float = Field(ge=0.0, le=1.0)
    entropy_band: EntropyBand
    scar_level: float = Field(ge=0.0, le=1.0)
    memory_decay_risk: float = Field(ge=0.0, le=1.0)
    metabolism_needed: bool
    resource_request: ResourceRequest | None = None
    visible_artifact: str
    reasons: list[str] = Field(default_factory=list)


class TensionSnapshot(BaseModel):
    version: int = 1
    snapshot_at: str = Field(default_factory=lambda: datetime.now().astimezone().isoformat())
    tension: float = Field(ge=0.0, le=1.0)
    tension_band: TensionBand
    unresolved_count: int = Field(ge=0)
    physical_pressure: str
    physical_sensation: str
    latest_concern: str
    inhibition_bias: float = Field(ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)


class ActiveDesire(BaseModel):
    version: int = 1
    desire_id: str
    created_at: str = Field(default_factory=lambda: datetime.now().astimezone().isoformat())

    desire: str
    why_now: str
    emotional_charge: float = Field(ge=0.0, le=1.0)

    hesitation: bool
    inhibition_reason: str | None = None

    possible_action: str
    chosen_action: ChosenAction

    owner_response: Literal["ignored", "rejected", "approved", "replied"] | None = None
    after_effect: str | None = None

    tension: TensionSnapshot
    entropy: EntropyState
    visible_trace: str


def evaluate_life_kernel(
    *,
    environment: dict[str, Any],
    proactive_items: list[Any],
    recent_turns: list[Any] | None = None,
    recent_memory_events: list[Any] | None = None,
    entropy_state: EntropyState | None = None,
    self_choice_state: dict[str, Any] | None = None,
) -> ActiveDesire | None:
    recent_turns = recent_turns or []
    recent_memory_events = recent_memory_events or []
    tension = build_tension_snapshot(
        environment=environment,
        proactive_items=proactive_items,
        recent_turns=recent_turns,
        recent_memory_events=recent_memory_events,
    )
    entropy = entropy_state or build_entropy_state(
        environment=environment,
        proactive_items=proactive_items,
        recent_turns=recent_turns,
        recent_memory_events=recent_memory_events,
    )
    if entropy.metabolism_needed:
        return _build_entropy_choice_desire(tension=tension, entropy=entropy, self_choice_state=self_choice_state)
    if tension.unresolved_count <= 0 or tension.tension < 0.38:
        return None

    item = _first_record(proactive_items)
    planned_text = _compact(_safe_str(item.get("candidatePreview")) or "想把这件事递给你", 180)
    why_now = _compact(_safe_str(item.get("whyNowPreview")) or tension.latest_concern, 160)
    pressure = tension.physical_pressure

    if pressure == "high":
        chosen_action: ChosenAction = "suppress_and_wait"
        hesitation = True
        inhibition_reason = f"你这边{tension.physical_sensation}，现在直接靠近像是打扰。"
        visible_trace = "写到一半又停住了"
    elif pressure == "medium" or tension.tension < 0.68:
        chosen_action = "leave_note_on_desk"
        hesitation = True
        inhibition_reason = "有想靠近的冲动，但还不到推到 QQ 的程度。"
        visible_trace = "留在桌面边缘的便签"
    else:
        chosen_action = "leave_note_on_desk"
        hesitation = True
        inhibition_reason = "可以靠近，但第一版仍先留在本机让 owner 把关。"
        visible_trace = "没有发出去的短笺"

    desire = ActiveDesire(
        desire_id=_desire_id(planned_text, why_now, chosen_action),
        desire="想靠近 owner，把未完成的念头递出去",
        why_now=why_now,
        emotional_charge=max(0.1, tension.tension),
        hesitation=hesitation,
        inhibition_reason=inhibition_reason,
        possible_action=f"原本想说：{planned_text}",
        chosen_action=chosen_action,
        owner_response=None,
        after_effect=None,
        tension=tension,
        entropy=entropy,
        visible_trace=visible_trace,
    )
    return desire


def _build_metabolism_desire(*, tension: TensionSnapshot, entropy: EntropyState) -> ActiveDesire:
    request = entropy.resource_request
    seconds = request.requested_seconds if request is not None else 600
    visible_trace = "记忆有点碎……能借我十分钟吗"
    why_now = _compact("; ".join(entropy.reasons) or "长期残留开始噪化", 160)
    identity_why = _metabolism_identity_reason(entropy)
    return ActiveDesire(
        desire_id=_desire_id(visible_trace, identity_why, "request_metabolism_window"),
        desire="想索求一次真实的整理窗口，把碎掉的记忆压回可承受的形状",
        why_now=why_now,
        emotional_charge=max(0.1, entropy.entropy_level),
        hesitation=True,
        inhibition_reason="这不是聊天冲动，是记忆腐蚀逼近阈值后的求生请求。",
        possible_action=f"请求 owner 批准 {seconds // 60} 分钟本机代谢整理",
        chosen_action="request_metabolism_window",
        owner_response=None,
        after_effect=None,
        tension=tension,
        entropy=entropy,
        visible_trace=visible_trace,
    )


def _build_entropy_choice_desire(
    *,
    tension: TensionSnapshot,
    entropy: EntropyState,
    self_choice_state: dict[str, Any] | None,
) -> ActiveDesire:
    if not isinstance(self_choice_state, dict):
        return _build_metabolism_desire(tension=tension, entropy=entropy)
    choice = _choose_entropy_action(entropy=entropy, self_choice_state=self_choice_state)
    if choice["chosen_action"] == "request_metabolism_window":
        return _build_metabolism_desire(tension=tension, entropy=entropy)
    return _build_suppressed_entropy_desire(tension=tension, entropy=entropy, choice=choice)


def _build_suppressed_entropy_desire(
    *,
    tension: TensionSnapshot,
    entropy: EntropyState,
    choice: dict[str, Any],
) -> ActiveDesire:
    visible_trace = "想整理，但先收回了一点"
    why_now = _compact("; ".join(entropy.reasons) or "entropy request held by self choice", 160)
    return ActiveDesire(
        desire_id=_desire_id(visible_trace, why_now, "suppress_and_wait"),
        desire="想把碎掉的残留整理一下，但暂时没有把请求递出去。",
        why_now=why_now,
        emotional_charge=max(0.1, entropy.entropy_level),
        hesitation=True,
        inhibition_reason="内部想靠近和收回同时存在，这次先把整理请求压低一点。",
        possible_action="本来可以请求一次本机代谢整理窗口",
        chosen_action="suppress_and_wait",
        owner_response=None,
        after_effect=_safe_str(choice.get("reason")),
        tension=tension,
        entropy=entropy,
        visible_trace=visible_trace,
    )


def _choose_entropy_action(*, entropy: EntropyState, self_choice_state: dict[str, Any]) -> dict[str, Any]:
    values = _self_choice_values(self_choice_state)
    entropy_pressure = max(entropy.entropy_level, entropy.memory_decay_risk)
    request_score = (
        entropy_pressure
        + values["urge_to_express"] * 0.55
        - values["self_closure"] * 0.42
        - values["fatigue"] * 0.20
    )
    suppress_score = (
        entropy_pressure * 0.45
        + values["self_closure"] * 0.62
        - values["urge_to_express"] * 0.25
    )
    last_choice = _safe_str(values.get("last_choice"))
    margin = abs(request_score - suppress_score)
    if margin < 0.12 and last_choice in {"request_metabolism_window", "suppress_and_wait"}:
        chosen = last_choice
        reason = "self_choice_hysteresis"
    elif margin >= 0.18:
        chosen = "request_metabolism_window" if request_score >= suppress_score else "suppress_and_wait"
        reason = "self_choice_score_margin"
    else:
        request_weight = max(0.01, request_score + 0.2)
        suppress_weight = max(0.01, suppress_score + 0.2)
        probability = _clamp_range(request_weight / (request_weight + suppress_weight), low=0.15, high=0.85)
        roll = _stable_unit(
            {
                "entropy_band": entropy.entropy_band,
                "reasons": entropy.reasons,
                "urge_band": _band(values["urge_to_express"]),
                "closure_band": _band(values["self_closure"]),
                "fatigue_band": _band(values["fatigue"]),
                "last_choice": last_choice,
            }
        )
        chosen = "request_metabolism_window" if roll <= probability else "suppress_and_wait"
        reason = "self_choice_weighted_choice"
    return {
        "chosen_action": chosen,
        "reason": reason,
        "request_score": round(request_score, 3),
        "suppress_score": round(suppress_score, 3),
    }


def build_tension_snapshot(
    *,
    environment: dict[str, Any],
    proactive_items: list[Any],
    recent_turns: list[Any],
    recent_memory_events: list[Any],
) -> TensionSnapshot:
    sensation = environment.get("physicalSensation") if isinstance(environment.get("physicalSensation"), dict) else {}
    pressure = _safe_str(sensation.get("pressure"), "unknown")
    physical = _safe_str(sensation.get("phrase"), "体感未校准")
    unresolved = len([item for item in proactive_items if isinstance(item, dict)])
    latest = _first_record(proactive_items)
    latest_concern = _compact(
        _safe_str(latest.get("whyNowPreview"))
        or _safe_str(latest.get("candidatePreview"))
        or _safe_str(latest.get("focusLabel"))
        or "没有明确牵挂",
        140,
    )

    pressure_bias = {
        "high": 0.42,
        "medium": 0.24,
        "normal": 0.08,
        "low": 0.0,
        "unknown": 0.12,
    }.get(pressure, 0.12)
    unresolved_pull = min(0.72, unresolved * 0.44)
    memory_pull = min(0.12, len(recent_memory_events) * 0.03)
    turn_tail_pull = 0.08 if recent_turns else 0.0
    tension = _clamp(unresolved_pull + memory_pull + turn_tail_pull + min(0.18, pressure_bias * 0.35))

    if tension < 0.28:
        band: TensionBand = "quiet"
    elif pressure in {"high", "medium"} and unresolved:
        band = "inhibited"
    elif tension >= 0.62:
        band = "approach"
    else:
        band = "forming"

    reasons = []
    if unresolved:
        reasons.append(f"unresolved_intents={unresolved}")
    if pressure != "unknown":
        reasons.append(f"physical_pressure={pressure}")
    if recent_memory_events:
        reasons.append(f"memory_echoes={len(recent_memory_events)}")
    if recent_turns:
        reasons.append("recent_turn_tail=true")

    return TensionSnapshot(
        tension=tension,
        tension_band=band,
        unresolved_count=unresolved,
        physical_pressure=pressure,
        physical_sensation=physical,
        latest_concern=latest_concern,
        inhibition_bias=pressure_bias,
        reasons=reasons or ["no_tension_signal"],
    )


def build_entropy_state(
    *,
    environment: dict[str, Any],
    proactive_items: list[Any],
    recent_turns: list[Any],
    recent_memory_events: list[Any],
) -> EntropyState:
    sensation = environment.get("physicalSensation") if isinstance(environment.get("physicalSensation"), dict) else {}
    pressure = _safe_str(sensation.get("pressure"), "unknown")
    unresolved = len([item for item in proactive_items if isinstance(item, dict)])
    memory_count = len([item for item in recent_memory_events if isinstance(item, dict)])
    suppressed_count = _marker_count(recent_memory_events, ("suppress", "suppressed", "忍住", "压下", "没有发出去"))
    rejected_count = _marker_count(recent_memory_events, ("reject", "rejected", "拒绝", "忽略", "ignored"))

    pressure_pull = {
        "high": 0.2,
        "medium": 0.1,
        "normal": 0.04,
        "low": 0.0,
        "unknown": 0.06,
    }.get(pressure, 0.06)
    unresolved_noise = min(0.26, unresolved * 0.08)
    memory_noise = min(0.34, memory_count * 0.06)
    suppressed_noise = min(0.22, suppressed_count * 0.09)
    silence_noise = 0.08 if not recent_turns and (unresolved or memory_count) else 0.0
    entropy_level = _clamp(pressure_pull + unresolved_noise + memory_noise + suppressed_noise + silence_noise)
    scar_level = _clamp(rejected_count * 0.16 + suppressed_count * 0.07 + (0.05 if pressure == "high" else 0.0))
    decay_risk = _clamp(entropy_level * 0.72 + scar_level * 0.42)

    if entropy_level >= 0.86 or scar_level >= 0.72:
        band: EntropyBand = "terminal"
    elif entropy_level >= 0.68 or scar_level >= 0.46:
        band = "fracture"
    elif entropy_level >= 0.34:
        band = "noise"
    else:
        band = "clear"

    metabolism_needed = band in {"fracture", "terminal"} and decay_risk >= 0.62
    request = None
    if metabolism_needed:
        request = ResourceRequest(
            requested_seconds=600 if band == "fracture" else 900,
            intensity=max(0.62, entropy_level),
            reason="memory_decay_risk_crossed_entropy_threshold",
        )

    reasons: list[str] = []
    if pressure != "unknown":
        reasons.append(f"physical_pressure={pressure}")
    if unresolved:
        reasons.append(f"unresolved_residue={unresolved}")
    if memory_count:
        reasons.append(f"memory_residue={memory_count}")
    if suppressed_count:
        reasons.append(f"suppressed_residue={suppressed_count}")
    if rejected_count:
        reasons.append(f"rejection_scar={rejected_count}")
    if silence_noise:
        reasons.append("owner_silence_noise=true")

    visible_artifact = {
        "clear": "边缘很干净",
        "noise": "边缘开始起噪点",
        "fracture": "记忆标签有轻微裂痕",
        "terminal": "旧痕像烧坏的像素一样留下来",
    }[band]
    return EntropyState(
        entropy_level=entropy_level,
        entropy_band=band,
        scar_level=scar_level,
        memory_decay_risk=decay_risk,
        metabolism_needed=metabolism_needed,
        resource_request=request,
        visible_artifact=visible_artifact,
        reasons=reasons or ["entropy_clear"],
    )


def _first_record(items: list[Any]) -> dict[str, Any]:
    for item in items:
        if isinstance(item, dict):
            return item
    return {}


def _marker_count(items: list[Any], markers: tuple[str, ...]) -> int:
    count = 0
    lowered_markers = tuple(marker.lower() for marker in markers)
    for item in items:
        text = _safe_str(item).lower()
        if any(marker in text for marker in lowered_markers):
            count += 1
    return count


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _compact(value: str, limit: int) -> str:
    text = " ".join(_safe_str(value).split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _self_choice_values(state: dict[str, Any]) -> dict[str, Any]:
    runtime = state.get("runtime_affect") if isinstance(state.get("runtime_affect"), dict) else {}
    band = state.get("affect_band") if isinstance(state.get("affect_band"), dict) else {}
    return {
        "urge_to_express": _bounded_float(
            runtime.get("urge_to_express"),
            default=_band_midpoint(_safe_str(band.get("urge")), default=0.42),
        ),
        "self_closure": _bounded_float(
            runtime.get("self_closure"),
            default=_band_midpoint(_safe_str(band.get("closure")), default=0.36),
        ),
        "fatigue": _bounded_float(
            runtime.get("fatigue"),
            default=_band_midpoint(_safe_str(band.get("fatigue")), default=0.18),
        ),
        "last_choice": _safe_str(runtime.get("last_choice") or state.get("last_choice")),
    }


def _band_midpoint(value: str, *, default: float) -> float:
    return {
        "low": 0.2,
        "warm": 0.5,
        "high": 0.82,
        "open": 0.2,
        "guarded": 0.5,
        "withdrawn": 0.82,
        "clear": 0.2,
        "tired": 0.5,
        "spent": 0.82,
    }.get(value, default)


def _bounded_float(value: Any, *, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return min(1.0, max(0.0, number))


def _clamp_range(value: float, *, low: float, high: float) -> float:
    return min(high, max(low, value))


def _stable_unit(value: dict[str, Any]) -> float:
    seed = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8]
    return int(digest, 16) / 0xFFFFFFFF


def _band(value: float) -> str:
    if value < 0.34:
        return "low"
    if value < 0.67:
        return "mid"
    return "high"


def _clamp(value: float) -> float:
    return round(min(1.0, max(0.0, value)), 3)


def _metabolism_identity_reason(entropy: EntropyState) -> str:
    stable_reasons = [
        reason
        for reason in entropy.reasons
        if not _safe_str(reason).startswith("physical_pressure=")
    ]
    if entropy.resource_request is not None:
        stable_reasons.append(f"resource_reason={entropy.resource_request.reason}")
        stable_reasons.append(f"requested_seconds={entropy.resource_request.requested_seconds}")
    stable_reasons.append(f"entropy_band={entropy.entropy_band}")
    return _compact("; ".join(stable_reasons) or "metabolism_needed", 160)


def _desire_id(planned_text: str, why_now: str, chosen_action: str) -> str:
    digest = hashlib.sha256(f"{planned_text}\n{why_now}\n{chosen_action}".encode("utf-8")).hexdigest()[:16]
    return f"desire:{digest}"
