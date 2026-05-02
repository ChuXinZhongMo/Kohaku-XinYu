from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_thought_seeds import ThoughtSeedSnapshot, refresh_thought_seeds


LOG_REL = "memory/self/private_thought_log.md"
STATE_REL = "memory/self/private_thought_state.md"
SELF_MODEL_REL = "memory/self/self_model_state.md"
FEEDBACK_REL = "memory/self/private_thought_feedback_state.md"

PRIVATE_THOUGHT_JSON_FIELDS = (
    "felt_conflict",
    "desire",
    "inhibition",
    "uncertainty",
    "intended_behavior",
    "expected_owner_reaction",
    "memory_links",
    "confidence",
)

PERSONA_REPAIR_MARKERS = (
    "不像人",
    "不自然",
    "机械",
    "模板",
    "客服",
    "助手味",
    "AI味",
    "ai味",
    "GPT",
    "gpt",
    "没变",
    "没有变",
    "还是没变",
    "没变化",
    "没接住",
    "假",
    "傻逼",
    "傻呗",
    "别这样",
    "不要这样",
)

PERSONA_SUCCESS_MARKERS = (
    "自然多了",
    "像人了",
    "像你了",
    "这句可以",
    "这样可以",
    "这次可以",
    "接住了",
    "有变化",
    "有点变化",
    "不是模板了",
    "没那么模板",
    "好多了",
    "对味",
    "继续这样",
)

GENERIC_PERSONA_SUCCESS_MARKERS = ("好多了",)
GENERIC_PERSONA_SUCCESS_MARKER_SET = set(GENERIC_PERSONA_SUCCESS_MARKERS)
SPECIFIC_PERSONA_SUCCESS_MARKERS = tuple(
    marker for marker in PERSONA_SUCCESS_MARKERS if marker not in GENERIC_PERSONA_SUCCESS_MARKER_SET
)
PERSONA_SUCCESS_CONTEXT_MARKERS = (
    "这句",
    "这次",
    "这样",
    "刚才",
    "回复",
    "说话",
    "语气",
    "自然",
    "像人",
    "像你",
    "模板",
    "模版",
    "接住",
    "对味",
)

WEAK_ACCEPTANCE_MARKERS = (
    "好",
    "可以",
    "行",
    "嗯",
    "对",
    "继续",
    "懂了",
)


@dataclass(frozen=True, slots=True)
class PrivateThoughtEventSnapshot:
    event_id: str
    generated_at: str
    source_kind: str
    trigger: str
    seed_id: str
    dominant_drive: str
    source_balance: str
    felt_conflict: str
    desire: str
    inhibition: str
    uncertainty: str
    intended_behavior: str
    expected_owner_reaction: str
    memory_links: tuple[str, ...]
    confidence: int
    text: str
    state_text: str
    self_model_text: str
    note_material: str


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    prefix = "\n\n" if path.exists() and path.stat().st_size > 0 else ""
    with path.open("a", encoding="utf-8") as handle:
        handle.write(prefix + text.rstrip() + "\n")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _hash_text(text: str, length: int = 16) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:length]


def _compact(value: Any, *, limit: int = 260, default: str = "none") -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if not text:
        return default
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _int(value: Any, default: int = 70) -> int:
    match = re.search(r"-?\d+", str(value or ""))
    if not match:
        return default
    try:
        return max(0, min(100, int(match.group(0))))
    except ValueError:
        return default


def _field(text: str, name: str, default: str = "none") -> str:
    match = re.search(rf"(?m)^- {re.escape(name)}:\s*(.*)$", text)
    if not match:
        return default
    value = match.group(1).strip()
    return value if value else default


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _persona_success_hit(compact_text: str) -> bool:
    if _contains_any(compact_text, SPECIFIC_PERSONA_SUCCESS_MARKERS):
        return True
    return _contains_any(compact_text, GENERIC_PERSONA_SUCCESS_MARKERS) and _contains_any(
        compact_text,
        PERSONA_SUCCESS_CONTEXT_MARKERS,
    )


def _weak_acceptance_hit(compact_text: str) -> bool:
    if not compact_text or len(compact_text) > 12:
        return False
    if compact_text in WEAK_ACCEPTANCE_MARKERS:
        return True
    return compact_text in {"好继续", "嗯继续", "可以继续", "行继续", "对继续"}


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    lowered = str(value or "").strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return default


def _owner_private(payload: dict[str, Any]) -> bool:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    is_owner = _as_bool(payload.get("is_owner_user") or metadata.get("is_owner_user"), default=False)
    group_id = str(payload.get("group_id") or "").strip()
    message_type = str(payload.get("message_type") or "").strip().lower()
    return is_owner and not group_id and not message_type.startswith("group")


def classify_persona_trial_feedback(
    *,
    payload: dict[str, Any],
    text: str,
    evaluation: dict[str, Any],
    prediction_error: float,
) -> dict[str, Any]:
    compact_text = re.sub(r"\s+", "", text or "")
    owner_private = _owner_private(payload)
    notes = [str(note) for note in evaluation.get("notes", []) if str(note).strip()]
    actual = evaluation.get("actual_next") if isinstance(evaluation.get("actual_next"), dict) else {}
    high_error = prediction_error >= 0.55 or "dialogue_curiosity_high_error" in notes
    repair_hit = _contains_any(compact_text, PERSONA_REPAIR_MARKERS)
    success_hit = _persona_success_hit(compact_text)
    weak_acceptance = _weak_acceptance_hit(compact_text) and not success_hit

    if repair_hit or high_error:
        reason = "owner reaction still contains style/persona repair pressure" if repair_hit else "dialogue prediction error was high"
        return {
            "persona_trial_feedback": "repair_needed",
            "promotion_signal": False,
            "repair_signal": True,
            "feedback_confidence": 88 if repair_hit else 78,
            "feedback_reason": reason,
        }

    if success_hit and owner_private and evaluation.get("evaluated") and prediction_error <= 0.45:
        return {
            "persona_trial_feedback": "promotion_observed",
            "promotion_signal": True,
            "repair_signal": False,
            "feedback_confidence": 82,
            "feedback_reason": "owner explicitly heard a visible behavior improvement after the trial reply",
        }

    if success_hit and owner_private:
        return {
            "persona_trial_feedback": "supportive_but_not_enough",
            "promotion_signal": False,
            "repair_signal": False,
            "feedback_confidence": 64,
            "feedback_reason": "owner used supportive wording, but evaluation evidence is not strong enough",
        }

    if weak_acceptance:
        return {
            "persona_trial_feedback": "weak_acceptance_continue",
            "promotion_signal": False,
            "repair_signal": False,
            "feedback_confidence": 42,
            "feedback_reason": "short acceptance or continuation is not proof of personality change",
        }

    if owner_private and actual.get("softening") and evaluation.get("evaluated") and prediction_error <= 0.35:
        return {
            "persona_trial_feedback": "softening_observed",
            "promotion_signal": False,
            "repair_signal": False,
            "feedback_confidence": 58,
            "feedback_reason": "owner softened, but no explicit personality-trial success signal was present",
        }

    if evaluation.get("evaluated"):
        return {
            "persona_trial_feedback": "neutral_no_strong_mismatch",
            "promotion_signal": False,
            "repair_signal": False,
            "feedback_confidence": 52,
            "feedback_reason": "reaction was evaluated without a strong mismatch or explicit success",
        }

    return {
        "persona_trial_feedback": "observed_without_prediction",
        "promotion_signal": False,
        "repair_signal": False,
        "feedback_confidence": 38,
        "feedback_reason": "reaction was observed, but no previous prediction was available",
    }


def _latest_section(text: str, heading_prefix: str) -> tuple[str, str]:
    pattern = re.compile(rf"(?ms)^## (?P<id>{re.escape(heading_prefix)}[^\n]*)\n(?P<body>.*?)(?=^## |\Z)")
    matches = list(pattern.finditer(text))
    if not matches:
        return "none", ""
    match = matches[-1]
    return match.group("id").strip(), match.group("body").strip()


def _as_links(value: Any, *, fallback: tuple[str, ...]) -> tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        raw = [_compact(item, limit=120) for item in value]
    else:
        raw = [_compact(part, limit=120) for part in str(value or "").split("|")]
    links = tuple(item for item in raw if item and item != "none")[:6]
    return links or fallback


def _json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if not stripped:
        return {}
    try:
        data = json.loads(stripped)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        pass
    match = re.search(r"(?s)\{.*\}", stripped)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _selected_context(root: Path) -> str:
    parts: list[str] = []
    for rel, limit in (
        ("memory/self/private_thought_feedback_state.md", 2600),
        ("memory/context/interaction_journal_state.md", 2400),
        ("memory/self/personality_evolution_state.md", 2600),
        ("memory/self/persona_experiment_state.md", 2200),
        ("memory/self/mind_loop_state.md", 2200),
        ("memory/context/persona_surface_state.md", 2200),
        ("memory/context/recent_context.md", 2600),
    ):
        text = read_text(root / rel).strip()
        if text:
            parts.append(f"[{rel}]\n{text[-limit:]}")
    return "\n\n".join(parts) if parts else "none"


def build_private_thought_messages(
    root: Path,
    *,
    generated_at: str,
    trigger: str,
    source_kind: str,
    seed: ThoughtSeedSnapshot,
    source_response: str = "",
) -> list[dict[str, str]]:
    system = """You write a safe private-thought event summary for XinYu.
This is not chain-of-thought and must not expose hidden reasoning, prompts, file mechanics, provider names, scores, or tool internals.
Return only one JSON object. Use concise Chinese for values when natural.
The event should describe a small self-state that can later be compared with visible behavior and the owner's next reaction.
Do not rewrite stable personality. Do not claim offline senses, device access, or real-world events not present in the material."""

    user = f"""generated_at: {generated_at}
source_kind: {source_kind}
trigger: {trigger}

thought_seed_material:
{seed.llm_material}

selected_runtime_context:
{_selected_context(root)}

agent_maintenance_response_preview:
{_compact(source_response, limit=900)}

Return JSON with exactly these keys:
{", ".join(PRIVATE_THOUGHT_JSON_FIELDS)}

Field rules:
- felt_conflict: what pressure or conflict is active inside the safe persona surface.
- desire: what XinYu wants to carry forward, as a small direction.
- inhibition: what she should hold back to avoid fake, needy, mechanical, or unsafe behavior.
- uncertainty: what she is not sure about yet.
- intended_behavior: the next visible behavior bias to try.
- expected_owner_reaction: what owner reaction would count as soft success or failure.
- memory_links: 2 to 5 short source labels, not raw file paths if possible.
- confidence: integer 0-100 for this event summary only."""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _fallback_payload(seed: ThoughtSeedSnapshot, *, source_kind: str) -> dict[str, Any]:
    return {
        "felt_conflict": f"{seed.dominant_drive} is active, but visible speech must stay bounded and natural.",
        "desire": "carry the current residue into the next reply without turning it into a report",
        "inhibition": "do not expose mechanics, over-explain growth, ask for attention, or turn a dream into fact",
        "uncertainty": "whether the next owner reaction will hear the change as real enough",
        "intended_behavior": "use one small situated behavior bias, then wait for real feedback",
        "expected_owner_reaction": "soft success means less style pressure; failure means owner still hears fake or mechanical wording",
        "memory_links": ["thought seed", seed.dominant_drive, seed.source_balance],
        "confidence": 58 if source_kind.startswith("deterministic") else 70,
    }


def render_event_text(
    *,
    generated_at: str,
    event_id: str,
    source_kind: str,
    trigger: str,
    seed: ThoughtSeedSnapshot,
    felt_conflict: str,
    desire: str,
    inhibition: str,
    uncertainty: str,
    intended_behavior: str,
    expected_owner_reaction: str,
    memory_links: tuple[str, ...],
    confidence: int,
) -> str:
    links = "\n".join(f"- {link}" for link in memory_links) or "- none"
    return f"""## {event_id}
- generated_at: {generated_at}
- source: xinyu_private_thought_events
- source_kind: {source_kind}
- trigger: {trigger}
- seed_id: {seed.seed_id}
- dominant_drive: {seed.dominant_drive}
- source_balance: {seed.source_balance}
- felt_conflict: {felt_conflict}
- desire: {desire}
- inhibition: {inhibition}
- uncertainty: {uncertainty}
- intended_behavior: {intended_behavior}
- expected_owner_reaction: {expected_owner_reaction}
- confidence: {confidence}
- hidden_reasoning_stored: no
- stable_personality_write: no
- outcome_status: pending

### memory_links
{links}"""


def render_state_text(snapshot: PrivateThoughtEventSnapshot | None, *, generated_at: str) -> str:
    if snapshot is None:
        return f"""---
title: Private Thought State
memory_type: private_thought_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: xinyu_private_thought_events
updated_at: {generated_at}
importance_score: 78
impact_score: 84
confidence_score: 60
status: active
tags: [self, private_thought, autonomy, feedback]
---

# Private Thought State

## Active Private Thought Event
- event_id: none
- source_kind: none
- trigger: none
- dominant_drive: none
- felt_conflict: none
- desire: none
- inhibition: none
- uncertainty: none
- intended_behavior: none
- expected_owner_reaction: none
- outcome_status: no_event

## Boundary
- this_file_is: safe private-thought event summary, not hidden chain-of-thought
- stable_personality_write: no
- visible_speech_rule: use only as a quiet behavior bias when relevant
"""
    links = "\n".join(f"- {link}" for link in snapshot.memory_links) or "- none"
    return f"""---
title: Private Thought State
memory_type: private_thought_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: xinyu_private_thought_events
updated_at: {generated_at}
last_confirmed_at: {snapshot.generated_at}
importance_score: 84
impact_score: 88
confidence_score: {snapshot.confidence}
status: active
tags: [self, private_thought, autonomy, feedback]
---

# Private Thought State

## Active Private Thought Event
- event_id: {snapshot.event_id}
- generated_at: {snapshot.generated_at}
- source_kind: {snapshot.source_kind}
- trigger: {snapshot.trigger}
- seed_id: {snapshot.seed_id}
- dominant_drive: {snapshot.dominant_drive}
- source_balance: {snapshot.source_balance}
- felt_conflict: {snapshot.felt_conflict}
- desire: {snapshot.desire}
- inhibition: {snapshot.inhibition}
- uncertainty: {snapshot.uncertainty}
- intended_behavior: {snapshot.intended_behavior}
- expected_owner_reaction: {snapshot.expected_owner_reaction}
- outcome_status: pending

## Memory Links
{links}

## Boundary
- this_file_is: safe private-thought event summary, not hidden chain-of-thought
- stable_personality_write: no
- visible_speech_rule: use only as a quiet behavior bias when relevant
"""


def render_feedback_state(
    *,
    updated_at: str,
    event_id: str = "none",
    session_key: str = "none",
    status: str = "none",
    linked_reply_hash: str = "none",
    owner_reaction_hash: str = "none",
    outcome: str = "none",
    persona_trial_feedback: str = "none",
    promotion_signal: bool = False,
    repair_signal: bool = False,
    feedback_confidence: int = 0,
    feedback_reason: str = "none",
    notes: tuple[str, ...] = (),
) -> str:
    note_lines = "\n".join(f"- {note}" for note in notes) or "- none"
    return f"""---
title: Private Thought Feedback State
memory_type: private_thought_feedback_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: xinyu_private_thought_events
updated_at: {updated_at}
importance_score: 78
impact_score: 84
confidence_score: 70
status: active
tags: [self, private_thought, outcome, feedback]
---

# Private Thought Feedback State

## Latest Feedback Link
- event_id: {event_id}
- session_key: {session_key}
- status: {status}
- linked_reply_hash: {linked_reply_hash}
- owner_reaction_hash: {owner_reaction_hash}
- outcome: {outcome}
- persona_trial_feedback: {persona_trial_feedback}
- promotion_signal: {str(promotion_signal).lower()}
- repair_signal: {str(repair_signal).lower()}
- feedback_confidence: {feedback_confidence}
- feedback_reason: {_compact(feedback_reason, limit=180)}

## Notes
{note_lines}
"""


def render_self_model_state(
    *,
    updated_at: str,
    private_state: str,
    feedback_state: str,
) -> str:
    event_id = _field(private_state, "event_id", "none")
    desire = _field(private_state, "desire", "none")
    inhibition = _field(private_state, "inhibition", "none")
    uncertainty = _field(private_state, "uncertainty", "none")
    intended = _field(private_state, "intended_behavior", "none")
    expected = _field(private_state, "expected_owner_reaction", "none")
    feedback_status = _field(feedback_state, "status", "none")
    outcome = _field(feedback_state, "outcome", "none")
    persona_trial_feedback = _field(feedback_state, "persona_trial_feedback", "none")
    promotion_signal = _field(feedback_state, "promotion_signal", "false")
    repair_signal = _field(feedback_state, "repair_signal", "false")
    feedback_confidence = _field(feedback_state, "feedback_confidence", "0")
    return f"""---
title: Self Model State
memory_type: self_model_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: xinyu_private_thought_events
updated_at: {updated_at}
importance_score: 86
impact_score: 90
confidence_score: 72
status: active
tags: [self, self_model, personality_growth, feedback]
---

# Self Model State

## Current Self Model
- model_scope: behavior tendencies and active experiments, not immutable identity
- active_private_thought_event: {event_id}
- current_desire: {desire}
- current_inhibition: {inhibition}
- current_uncertainty: {uncertainty}
- intended_behavior: {intended}
- expected_owner_reaction: {expected}
- feedback_status: {feedback_status}
- latest_outcome: {outcome}
- persona_trial_feedback: {persona_trial_feedback}
- promotion_signal: {promotion_signal}
- repair_signal: {repair_signal}
- feedback_confidence: {feedback_confidence}

## Growth Rule
- compare_loop: private thought event -> visible behavior link -> next owner reaction -> self-model update
- stable_profile_write: blocked unless repeated events, visible stability, and no owner veto support promotion
- trial_habit_rule: use only small reversible behavior bias during live turns
- failure_rule: if owner still hears fake, mechanical, over-framed, needy, or unchanged behavior, lower confidence and revise the behavior bias
"""


def build_private_thought_event_snapshot(
    root: Path,
    *,
    generated_at: str,
    source_kind: str,
    trigger: str,
    source_response: str = "",
    llm_payload: dict[str, Any] | None = None,
) -> PrivateThoughtEventSnapshot:
    seed = refresh_thought_seeds(root, generated_at=generated_at)
    payload = dict(_fallback_payload(seed, source_kind=source_kind))
    if llm_payload:
        for key in PRIVATE_THOUGHT_JSON_FIELDS:
            if key in llm_payload:
                payload[key] = llm_payload[key]

    felt_conflict = _compact(payload.get("felt_conflict"))
    desire = _compact(payload.get("desire"))
    inhibition = _compact(payload.get("inhibition"))
    uncertainty = _compact(payload.get("uncertainty"))
    intended_behavior = _compact(payload.get("intended_behavior"))
    expected_owner_reaction = _compact(payload.get("expected_owner_reaction"))
    memory_links = _as_links(
        payload.get("memory_links"),
        fallback=("thought seed", seed.dominant_drive, seed.source_balance),
    )
    confidence = _int(payload.get("confidence"), default=70 if llm_payload else 58)
    event_id = "private-thought-" + _hash_text(
        "|".join(
            [
                generated_at,
                source_kind,
                trigger,
                seed.seed_id,
                felt_conflict,
                desire,
                source_response[:500],
                str(time.time_ns()),
            ]
        ),
        18,
    )

    text = render_event_text(
        generated_at=generated_at,
        event_id=event_id,
        source_kind=source_kind,
        trigger=trigger,
        seed=seed,
        felt_conflict=felt_conflict,
        desire=desire,
        inhibition=inhibition,
        uncertainty=uncertainty,
        intended_behavior=intended_behavior,
        expected_owner_reaction=expected_owner_reaction,
        memory_links=memory_links,
        confidence=confidence,
    )
    placeholder = PrivateThoughtEventSnapshot(
        event_id=event_id,
        generated_at=generated_at,
        source_kind=source_kind,
        trigger=trigger,
        seed_id=seed.seed_id,
        dominant_drive=seed.dominant_drive,
        source_balance=seed.source_balance,
        felt_conflict=felt_conflict,
        desire=desire,
        inhibition=inhibition,
        uncertainty=uncertainty,
        intended_behavior=intended_behavior,
        expected_owner_reaction=expected_owner_reaction,
        memory_links=memory_links,
        confidence=confidence,
        text=text,
        state_text="",
        self_model_text="",
        note_material="",
    )
    state_text = render_state_text(placeholder, generated_at=generated_at)
    feedback_state = read_text(root / FEEDBACK_REL) or render_feedback_state(updated_at=generated_at)
    self_model_text = render_self_model_state(
        updated_at=generated_at,
        private_state=state_text,
        feedback_state=feedback_state,
    )
    note_material = build_private_thought_note_material(
        root,
        generated_at=generated_at,
        event_state=state_text,
        seed_text=seed.text,
    )
    return PrivateThoughtEventSnapshot(
        event_id=event_id,
        generated_at=generated_at,
        source_kind=source_kind,
        trigger=trigger,
        seed_id=seed.seed_id,
        dominant_drive=seed.dominant_drive,
        source_balance=seed.source_balance,
        felt_conflict=felt_conflict,
        desire=desire,
        inhibition=inhibition,
        uncertainty=uncertainty,
        intended_behavior=intended_behavior,
        expected_owner_reaction=expected_owner_reaction,
        memory_links=memory_links,
        confidence=confidence,
        text=text,
        state_text=state_text,
        self_model_text=self_model_text,
        note_material=note_material,
    )


def write_private_thought_snapshot(root: Path, snapshot: PrivateThoughtEventSnapshot) -> None:
    log_path = root / LOG_REL
    if not log_path.exists():
        write_text(
            log_path,
            """---
title: Private Thought Log
memory_type: private_thought_log
time_scope: mid_term
subject_ids: [xinyu]
protected: true
source: xinyu_private_thought_events
status: active
tags: [self, private_thought, autonomy, feedback]
---

# Private Thought Log""",
        )
    append_text(log_path, snapshot.text)
    write_text(root / STATE_REL, snapshot.state_text)
    write_text(root / SELF_MODEL_REL, snapshot.self_model_text)
    if not (root / FEEDBACK_REL).exists():
        write_text(root / FEEDBACK_REL, render_feedback_state(updated_at=snapshot.generated_at))


async def refresh_private_thought_event(
    root: Path,
    *,
    generated_at: str | None = None,
    llm: Any | None = None,
    source_kind: str = "deterministic_seed_summary",
    trigger: str = "manual_refresh",
    source_response: str = "",
    use_llm: bool = True,
) -> PrivateThoughtEventSnapshot:
    generated = generated_at or _now_iso()
    seed = refresh_thought_seeds(root, generated_at=generated)
    llm_payload: dict[str, Any] | None = None
    if llm is not None and use_llm:
        try:
            response = await llm.chat_complete(
                build_private_thought_messages(
                    root,
                    generated_at=generated,
                    trigger=trigger,
                    source_kind=source_kind,
                    seed=seed,
                    source_response=source_response,
                ),
                temperature=0.62,
                max_tokens=700,
            )
            llm_payload = _json_object(str(getattr(response, "content", "") or ""))
        except Exception:
            llm_payload = None
    snapshot = build_private_thought_event_snapshot(
        root,
        generated_at=generated,
        source_kind=source_kind if llm_payload else f"deterministic_fallback_from_{source_kind}",
        trigger=trigger,
        source_response=source_response,
        llm_payload=llm_payload,
    )
    write_private_thought_snapshot(root, snapshot)
    return snapshot


def refresh_private_thought_event_sync(
    root: Path,
    *,
    generated_at: str | None = None,
    source_kind: str = "deterministic_seed_summary",
    trigger: str = "manual_refresh",
) -> PrivateThoughtEventSnapshot:
    generated = generated_at or _now_iso()
    snapshot = build_private_thought_event_snapshot(
        root,
        generated_at=generated,
        source_kind=source_kind,
        trigger=trigger,
    )
    write_private_thought_snapshot(root, snapshot)
    return snapshot


def read_private_thought_state(root: Path, *, generated_at: str | None = None) -> str:
    existing = read_text(root / STATE_REL).strip()
    if existing:
        return existing
    state = render_state_text(None, generated_at=generated_at or "not_written")
    write_text(root / STATE_REL, state)
    if not (root / FEEDBACK_REL).exists():
        write_text(root / FEEDBACK_REL, render_feedback_state(updated_at=generated_at or "not_written"))
    if not (root / SELF_MODEL_REL).exists():
        write_text(
            root / SELF_MODEL_REL,
            render_self_model_state(
                updated_at=generated_at or "not_written",
                private_state=state,
                feedback_state=read_text(root / FEEDBACK_REL),
            ),
        )
    return state


def read_self_model_state(root: Path, *, generated_at: str | None = None) -> str:
    existing = read_text(root / SELF_MODEL_REL).strip()
    if existing:
        return existing
    private_state = read_private_thought_state(root, generated_at=generated_at)
    feedback_state = read_text(root / FEEDBACK_REL) or render_feedback_state(updated_at=generated_at or "not_written")
    state = render_self_model_state(
        updated_at=generated_at or "not_written",
        private_state=private_state,
        feedback_state=feedback_state,
    )
    write_text(root / SELF_MODEL_REL, state)
    return state


def build_private_thought_note_material(
    root: Path,
    *,
    generated_at: str,
    event_state: str | None = None,
    seed_text: str | None = None,
) -> str:
    private_state = event_state if event_state is not None else read_private_thought_state(root, generated_at=generated_at)
    seed = seed_text if seed_text is not None else refresh_thought_seeds(root, generated_at=generated_at).text
    return f"""# Private Thought Event Material For XinYu Owner-Visible Note

generated_at: {generated_at}
material_boundary: This is a safe summary of a private thought event, not hidden chain-of-thought.
desktop_note_role: render the active private thought as a natural owner-visible note, without exposing field names or mechanics.

private_thought_event_state:
{private_state}

supporting_thought_seed_snapshot:
{seed}
"""


def latest_private_thought_event_id(root: Path) -> str:
    state = read_text(root / STATE_REL)
    return _field(state, "event_id", "none")


def mark_private_thought_desktop_written(
    root: Path,
    *,
    event_id: str,
    note_path: Path,
    generated_at: str | None = None,
) -> None:
    updated = generated_at or _now_iso()
    append_text(
        root / LOG_REL,
        f"""## desktop-note-{_hash_text(str(note_path), 12)}
- event_id: {event_id}
- written_at: {updated}
- note_path_hash: {_hash_text(str(note_path), 16)}
- note_path_name: {note_path.name}
- visible_note_source: owner_visible_private_note
- stable_personality_write: no""",
    )


def record_private_thought_reply_link(
    root: Path,
    payload: dict[str, Any],
    *,
    user_text: str,
    reply: str,
    session_key: str,
    linked_at: str | None = None,
) -> dict[str, Any]:
    event_id = latest_private_thought_event_id(root)
    if event_id == "none" or not reply.strip():
        return {"linked": False, "notes": ["private_thought_no_active_event"]}
    updated = linked_at or _now_iso()
    reply_hash = _hash_text(reply, 24)
    user_hash = _hash_text(user_text, 24)
    notes = (
        "visible reply may have been shaped by active private thought bias",
        "await next owner/user reaction before self-model confidence change",
    )
    feedback = render_feedback_state(
        updated_at=updated,
        event_id=event_id,
        session_key=session_key,
        status="pending_next_reaction",
        linked_reply_hash=reply_hash,
        owner_reaction_hash="none",
        outcome="pending",
        persona_trial_feedback="pending_next_owner_reaction",
        feedback_confidence=0,
        feedback_reason="await next owner/user reaction",
        notes=notes,
    )
    write_text(root / FEEDBACK_REL, feedback)
    private_state = read_private_thought_state(root, generated_at=updated)
    write_text(
        root / SELF_MODEL_REL,
        render_self_model_state(updated_at=updated, private_state=private_state, feedback_state=feedback),
    )
    append_text(
        root / LOG_REL,
        f"""## reply-link-{_hash_text(event_id + reply_hash, 12)}
- event_id: {event_id}
- linked_at: {updated}
- session_key: {session_key}
- user_hash: {user_hash}
- reply_hash: {reply_hash}
- influenced_reply: possible
- outcome_status: pending_next_reaction""",
    )
    return {"linked": True, "event_id": event_id, "notes": ["private_thought_reply_linked"]}


def record_private_thought_outcome(
    root: Path,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    evaluation: dict[str, Any] | None = None,
    observed_at: str | None = None,
) -> dict[str, Any]:
    feedback = read_text(root / FEEDBACK_REL)
    event_id = _field(feedback, "event_id", "none")
    status = _field(feedback, "status", "none")
    if event_id == "none" or status != "pending_next_reaction":
        return {"recorded": False, "notes": ["private_thought_no_pending_feedback"]}
    if _field(feedback, "session_key", "none") != session_key:
        return {"recorded": False, "notes": ["private_thought_feedback_session_mismatch"]}

    evaluation = evaluation or {}
    try:
        prediction_error = float(evaluation.get("prediction_error", 0.0))
    except (TypeError, ValueError):
        prediction_error = 0.0
    notes = [str(note) for note in evaluation.get("notes", []) if str(note).strip()]
    persona_feedback = classify_persona_trial_feedback(
        payload=payload,
        text=text,
        evaluation=evaluation,
        prediction_error=prediction_error,
    )
    if persona_feedback["repair_signal"]:
        outcome = "needs_repair"
        notes.append("private_thought_outcome_needs_repair")
    elif evaluation.get("evaluated"):
        outcome = "no_strong_mismatch"
        notes.append("private_thought_outcome_no_strong_mismatch")
    else:
        outcome = "reaction_observed_without_prediction"
        notes.append("private_thought_outcome_observed")
    notes.append(f"persona_trial_feedback:{persona_feedback['persona_trial_feedback']}")
    if persona_feedback["promotion_signal"]:
        notes.append("persona_trial_promotion_signal")

    updated = observed_at or _now_iso()
    reaction_hash = _hash_text(text, 24)
    new_feedback = render_feedback_state(
        updated_at=updated,
        event_id=event_id,
        session_key=session_key,
        status="evaluated",
        linked_reply_hash=_field(feedback, "linked_reply_hash", "none"),
        owner_reaction_hash=reaction_hash,
        outcome=outcome,
        persona_trial_feedback=str(persona_feedback["persona_trial_feedback"]),
        promotion_signal=bool(persona_feedback["promotion_signal"]),
        repair_signal=bool(persona_feedback["repair_signal"]),
        feedback_confidence=int(persona_feedback["feedback_confidence"]),
        feedback_reason=str(persona_feedback["feedback_reason"]),
        notes=tuple(notes[:8]),
    )
    write_text(root / FEEDBACK_REL, new_feedback)
    private_state = read_private_thought_state(root, generated_at=updated)
    write_text(
        root / SELF_MODEL_REL,
        render_self_model_state(updated_at=updated, private_state=private_state, feedback_state=new_feedback),
    )
    append_text(
        root / LOG_REL,
        f"""## outcome-{_hash_text(event_id + reaction_hash, 12)}
- event_id: {event_id}
- observed_at: {updated}
- session_key: {session_key}
- owner_reaction_hash: {reaction_hash}
- prediction_error: {prediction_error:.2f}
- outcome: {outcome}
- persona_trial_feedback: {persona_feedback['persona_trial_feedback']}
- promotion_signal: {str(bool(persona_feedback['promotion_signal'])).lower()}
- repair_signal: {str(bool(persona_feedback['repair_signal'])).lower()}
- stable_personality_write: no""",
    )
    return {
        "recorded": True,
        "event_id": event_id,
        "outcome": outcome,
        "persona_trial_feedback": persona_feedback["persona_trial_feedback"],
        "promotion_signal": persona_feedback["promotion_signal"],
        "repair_signal": persona_feedback["repair_signal"],
        "notes": ["private_thought_outcome_recorded"],
    }
