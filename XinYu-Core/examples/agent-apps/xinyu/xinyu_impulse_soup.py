from __future__ import annotations


__all__ = (
    "STATE_JSON_REL",
)

import argparse
import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from stores.impulse_soup_state import (
    IMPULSE_SOUP_STATE_REL as STATE_JSON_REL,
    read_impulse_soup_state,
    write_impulse_soup_state,
)
from xinyu_runtime_failure_freshness import (
    codex_delegate_failure_active as _codex_delegate_failure_active,
    runtime_failure_detail_active as _runtime_failure_detail_active,
)


STATE_MD_REL = Path("memory/context/impulse_soup_state.md")
TRACE_REL = Path("memory/context/impulse_soup_trace.jsonl")

PROACTIVE_TRACE_REL = Path("memory/context/proactive_decision_trace.jsonl")
DREAM_OUTPUT_REL = Path("memory/dreams/dream_output_state.md")
REFLECTION_QUEUE_REL = Path("memory/reflection/reflection_queue.md")
RUNTIME_AWARENESS_REL = Path("memory/context/runtime_program_awareness.md")

SCHEMA_VERSION = "impulse_soup_v0"
MAX_THOUGHTLETS = 80
MAX_SEEDS = 24
RECENT_TRACE_LINES = 120
SPAWN_INTERVAL_SECONDS = 21600
DEFAULT_TTL_SECONDS = 7 * 86400

DESIRE_TTL_SECONDS = {
    "unresolved_reflection": 12 * 3600,
    "expression_repair_habit": 24 * 3600,
    "self_repair_reflex": 36 * 3600,
    "runtime_diagnostic_reflex": 36 * 3600,
    "completion_continuity": 48 * 3600,
}

DESIRE_ENERGY_CAPS = {
    "unresolved_reflection": 46,
    "expression_repair_habit": 58,
    "self_repair_reflex": 80,
    "runtime_diagnostic_reflex": 78,
}

SEED_LIMITS_BY_DESIRE = {
    "expression_repair_habit": 2,
    "self_repair_reflex": 3,
    "runtime_diagnostic_reflex": 3,
    "completion_continuity": 1,
}

ACTIVE_LIMITS_BY_DESIRE = {
    "unresolved_reflection": 2,
    "expression_repair_habit": 4,
    "self_repair_reflex": 2,
    "runtime_diagnostic_reflex": 1,
}

NO_SPAWN_DESIRES = {
    "unresolved_reflection",
    "expression_repair_habit",
}

SOFT_DESIRE_SHAPES = {
    "dream_residue_compression",
    "unresolved_reflection",
    "expression_repair_habit",
    "social_presence_inhibition",
}

SOURCE_TO_DESIRE = {
    "dream_residue": "dream_residue_compression",
    "reflection_question": "unresolved_reflection",
    "style_repair": "expression_repair_habit",
    "owner_long_idle": "social_presence_inhibition",
    "task_failed": "self_repair_reflex",
    "runtime_error": "runtime_diagnostic_reflex",
    "task_done": "completion_continuity",
}

DESIRE_ACTIONS = {
    "dream_residue_compression": ("compress_to_reflection", "never_direct_qq_v0"),
    "unresolved_reflection": ("review_open_loop", "scorer_gate_required"),
    "expression_repair_habit": ("stabilize_expression_habit", "never_direct_qq_v0"),
    "social_presence_inhibition": ("wait_for_owner_anchor", "never_direct_qq_v0"),
    "self_repair_reflex": ("diagnose_locally_first", "no_owner_interrupt_until_diagnosis"),
    "runtime_diagnostic_reflex": ("diagnose_locally_first", "no_owner_interrupt_until_diagnosis"),
    "completion_continuity": ("prepare_completion_summary", "scorer_gate_required"),
}

INTERNAL_MARKER_RE = re.compile(
    r"(?i)(\bcodex\b|source_seed|source_seeds|dream_weight|stdout|stderr|traceback|"
    r"\btool[_ -]?call\b|\btool[_ -]?output\b|[a-z]:\\|\\\\|/users/|/home/)"
)
LOCAL_PATH_RE = re.compile(r"(?i)(?:[a-z]:\\|/users/|/home/|\\\\)[^\s<>'\"]+")
SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bauthorization\s*:\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bxinyu[_-]?(?:api[_-]?key|bridge[_-]?token)\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bapi[_-]?key\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\btoken\s*[:=]\s*[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bsk-[a-z0-9_-]{12,}"),
)
FIELD_RE = re.compile(r"(?m)^\s*-\s*([A-Za-z0-9_]+):\s*(.*?)\s*$")
FRONTMATTER_RE = re.compile(r"(?m)^\s*([A-Za-z0-9_]+):\s*(.*?)\s*$")


@dataclass(frozen=True)
class ImpulseSeed:
    source_kind: str
    source_ref: str
    source_signature: str
    desire_shape: str
    proposed_next_action: str
    inhibition_rule: str
    evidence_preview: str
    initial_energy: int
    risk_flags: tuple[str, ...]
    observed_at: str


@dataclass
class Thoughtlet:
    thoughtlet_id: str
    lineage_id: str
    parent_id: str
    generation: int
    source_kind: str
    source_ref: str
    source_signature: str
    desire_shape: str
    proposed_next_action: str
    inhibition_rule: str
    energy: int
    usefulness_score: int
    mutation_count: int
    activation_count: int
    risk_flags: list[str]
    evidence_preview: str
    status: str
    created_at: str
    updated_at: str
    last_triggered_at: str
    last_spawned_at: str
    expires_at: str


def run_impulse_soup(
    root: Path,
    *,
    checked_at: str | None = None,
    max_new: int = 8,
    max_thoughtlets: int = MAX_THOUGHTLETS,
) -> dict[str, Any]:
    root = root.resolve()
    checked_at = _timestamp_or_now_iso(checked_at or _now_iso())
    state = _load_state(root)
    seeds = collect_impulse_seeds(root, checked_at=checked_at)[: max(1, int(max_new))]
    active_seed_signatures = {seed.source_signature for seed in seeds}

    thoughtlets = [_thoughtlet_from_dict(item) for item in state.get("thoughtlets", []) if isinstance(item, dict)]
    by_signature = {item.source_signature: item for item in thoughtlets if item.source_signature}
    created: list[str] = []
    updated: list[str] = []
    spawned: list[str] = []
    notes: list[str] = []

    for item in thoughtlets:
        _decay_thoughtlet(item, checked_at=checked_at)
        if _cool_stale_transient_failure(item, active_seed_signatures=active_seed_signatures):
            notes.append(f"cooled_stale_transient_failure:{item.thoughtlet_id}")
        if _cool_stale_unresolved_reflection(item, active_seed_signatures=active_seed_signatures):
            notes.append(f"cooled_stale_unresolved_reflection:{item.thoughtlet_id}")

    for seed in seeds:
        existing = by_signature.get(seed.source_signature)
        if existing is None:
            thoughtlet = _new_thoughtlet(seed, checked_at=checked_at)
            thoughtlets.append(thoughtlet)
            by_signature[seed.source_signature] = thoughtlet
            created.append(thoughtlet.thoughtlet_id)
        else:
            _refresh_thoughtlet(existing, seed, checked_at=checked_at)
            updated.append(existing.thoughtlet_id)

    for thoughtlet in list(thoughtlets):
        child = _maybe_spawn_child(thoughtlet, thoughtlets, checked_at=checked_at)
        if child is not None:
            thoughtlets.append(child)
            spawned.append(child.thoughtlet_id)

    thoughtlets = _prune_thoughtlets(thoughtlets, max_thoughtlets=max(1, int(max_thoughtlets)))
    for thoughtlet in thoughtlets:
        _update_status(thoughtlet, checked_at=checked_at)
    _enforce_active_limits(thoughtlets)

    summary = _summarize(thoughtlets)
    next_state = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": _timestamp_or_now_iso(checked_at),
        "status": "active",
        "boundaries": {
            "local_json_only": True,
            "no_qq_enqueue": True,
            "no_tool_execution": True,
            "no_process_replication": True,
            "no_self_code_write": True,
            "scorer_gate_required_for_all_outward_candidates": True,
        },
        "summary": summary,
        "thoughtlets": [asdict(item) for item in thoughtlets],
    }
    write_impulse_soup_state(root, next_state)
    _write_state_markdown(root, checked_at=checked_at, thoughtlets=thoughtlets, summary=summary, notes=notes)
    event = {
        "event_kind": "impulse_soup_cycle",
        "observed_at": _timestamp_or_now_iso(checked_at),
        "status": "active",
        "seed_count": len(seeds),
        "created_count": len(created),
        "updated_count": len(updated),
        "spawned_count": len(spawned),
        "active_count": summary["active_count"],
        "dormant_count": summary["dormant_count"],
        "quarantined_count": summary["quarantined_count"],
        "extinct_count": summary["extinct_count"],
        "lineage_count": summary["lineage_count"],
        "top_thoughtlet_id": summary["top_thoughtlet_id"],
        "top_desire_shape": summary["top_desire_shape"],
        "top_energy": summary["top_energy"],
        "created": created[:8],
        "updated": updated[:8],
        "spawned": spawned[:8],
        "notes": notes,
    }
    _append_trace(root, event)
    return {
        "accepted": True,
        "status": "active",
        "checked_at": checked_at,
        "seed_count": len(seeds),
        "created_count": len(created),
        "updated_count": len(updated),
        "spawned_count": len(spawned),
        "thoughtlet_count": len(thoughtlets),
        **summary,
        "notes": notes,
    }


def collect_impulse_seeds(root: Path, *, checked_at: str | None = None) -> list[ImpulseSeed]:
    root = root.resolve()
    checked_at = checked_at or _now_iso()
    seeds: list[ImpulseSeed] = []
    seeds.extend(_seeds_from_proactive_trace(root, checked_at=checked_at))
    seeds.extend(_seeds_from_dream_output(root, checked_at=checked_at))
    seeds.extend(_seeds_from_reflection_queue(root, checked_at=checked_at))
    seeds.extend(_seeds_from_runtime_awareness(root, checked_at=checked_at))

    deduped: list[ImpulseSeed] = []
    seen: set[str] = set()
    for seed in seeds:
        if seed.source_signature in seen:
            continue
        seen.add(seed.source_signature)
        deduped.append(seed)
    deduped.sort(key=lambda item: (item.initial_energy, item.observed_at), reverse=True)
    return _limit_seeds_by_desire(deduped)


def _seeds_from_proactive_trace(root: Path, *, checked_at: str) -> list[ImpulseSeed]:
    seeds: list[ImpulseSeed] = []
    for row in _read_recent_jsonl(root / PROACTIVE_TRACE_REL, limit=RECENT_TRACE_LINES):
        source_kind = _clean_token(row.get("source_type") or "unknown")
        desire_shape = SOURCE_TO_DESIRE.get(source_kind)
        if desire_shape is None:
            continue
        candidate = row.get("candidate") if isinstance(row.get("candidate"), dict) else {}
        score = row.get("score") if isinstance(row.get("score"), dict) else {}
        source_ref = _first_meaningful(
            row.get("candidate_signature"),
            row.get("candidate_id"),
            candidate.get("source_ref") if isinstance(candidate, dict) else "",
        )
        preview = _first_meaningful(
            candidate.get("owner_visible_text") if isinstance(candidate, dict) else "",
            row.get("content_preview"),
            candidate.get("content_preview") if isinstance(candidate, dict) else "",
        )
        if not _proactive_trace_seed_allowed(row, source_kind=source_kind, candidate=candidate, checked_at=checked_at):
            continue
        initial_energy = _energy_from_proactive_row(row, score)
        seeds.append(
            _make_seed(
                source_kind=source_kind,
                source_ref=f"proactivity:{source_ref}",
                desire_shape=desire_shape,
                evidence_preview=preview,
                initial_energy=initial_energy,
                risk_flags=_risk_flags_for(desire_shape, row.get("hard_blocks") or []),
                observed_at=_normalize_iso(row.get("observed_at")) or checked_at,
            )
        )
    return seeds


def _seeds_from_dream_output(root: Path, *, checked_at: str) -> list[ImpulseSeed]:
    text = _read_text(root / DREAM_OUTPUT_REL)
    if not text:
        return []
    fields = _parse_fields(text)
    dream_id = _first_meaningful(fields.get("dream_id"), fields.get("seed_id"), "latest_dream_output")
    if fields.get("reflection_candidate", "").lower() not in {"yes", "true"} and dream_id == "latest_dream_output":
        return []
    preview = _first_meaningful(fields.get("dream_surface"), fields.get("theme"), fields.get("residue"), dream_id)
    return [
        _make_seed(
            source_kind="dream_residue",
            source_ref=f"dream_output:{dream_id}",
            desire_shape="dream_residue_compression",
            evidence_preview=preview,
            initial_energy=max(35, min(72, _safe_int(fields.get("emotional_weight"), 55))),
            risk_flags=("dream_or_emotion", "no_direct_qq_v0"),
            observed_at=_normalize_iso(fields.get("produced_at") or fields.get("updated_at")) or checked_at,
        )
    ]


def _seeds_from_reflection_queue(root: Path, *, checked_at: str) -> list[ImpulseSeed]:
    text = _read_text(root / REFLECTION_QUEUE_REL)
    if not text:
        return []
    section_id, section = _latest_heading_section(text, "item-")
    if not section:
        return []
    fields = _parse_fields(section)
    topic = fields.get("topic", "")
    if not _meaningful(topic):
        return []
    priority = fields.get("priority", "").lower()
    energy = 58 if priority == "high" else 42
    desire_shape = "dream_residue_compression" if "dream" in fields.get("source", "").lower() else "unresolved_reflection"
    return [
        _make_seed(
            source_kind="reflection_queue",
            source_ref=f"reflection_queue:{section_id}",
            desire_shape=desire_shape,
            evidence_preview=topic,
            initial_energy=energy,
            risk_flags=_risk_flags_for(desire_shape, ()),
            observed_at=_timestamp_or_now_iso(checked_at),
        )
    ]


def _seeds_from_runtime_awareness(root: Path, *, checked_at: str) -> list[ImpulseSeed]:
    text = _read_text(root / RUNTIME_AWARENESS_REL)
    if not text:
        return []
    seeds: list[ImpulseSeed] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        name, detail = stripped[2:].split(":", 1)
        name = _clean_token(name)
        lowered = detail.lower()
        if name == "watched_source" and "read_only=true" in lowered:
            continue
        if "status=error" in lowered or _runtime_failure_detail_active(detail, checked_at=checked_at):
            seeds.append(
                _make_seed(
                    source_kind="runtime_error",
                    source_ref=f"runtime_awareness:{name}",
                    desire_shape="runtime_diagnostic_reflex",
                    evidence_preview=detail,
                    initial_energy=72,
                    risk_flags=(),
                    observed_at=_timestamp_or_now_iso(checked_at),
                )
            )
    return seeds


def _make_seed(
    *,
    source_kind: str,
    source_ref: str,
    desire_shape: str,
    evidence_preview: str,
    initial_energy: int,
    risk_flags: tuple[str, ...] | list[str],
    observed_at: str,
) -> ImpulseSeed:
    desire_shape = _clean_token(desire_shape)
    action, inhibition = DESIRE_ACTIONS.get(desire_shape, ("observe_only", "scorer_gate_required"))
    preview = _clip(evidence_preview, 220)
    if INTERNAL_MARKER_RE.search(preview):
        risk_flags = tuple(dict.fromkeys([*_as_list(risk_flags), "internal_marker_in_evidence"]))
    signature = "impseed:" + _short_hash("|".join((_clean_token(source_kind), _scrub_ref(source_ref), desire_shape, preview)), 24)
    capped_energy = min(_clamp(initial_energy), DESIRE_ENERGY_CAPS.get(desire_shape, 100))
    return ImpulseSeed(
        source_kind=_clean_token(source_kind),
        source_ref=_scrub_ref(source_ref),
        source_signature=signature,
        desire_shape=desire_shape,
        proposed_next_action=action,
        inhibition_rule=inhibition,
        evidence_preview=preview,
        initial_energy=capped_energy,
        risk_flags=tuple(dict.fromkeys(_clean_token(flag) for flag in _as_list(risk_flags) if _clean_token(flag))),
        observed_at=_normalize_iso(observed_at) or _now_iso(),
    )


def _limit_seeds_by_desire(seeds: list[ImpulseSeed]) -> list[ImpulseSeed]:
    kept: list[ImpulseSeed] = []
    counts: dict[str, int] = {}
    for seed in seeds:
        limit = SEED_LIMITS_BY_DESIRE.get(seed.desire_shape)
        current = counts.get(seed.desire_shape, 0)
        if limit is not None and current >= limit:
            continue
        counts[seed.desire_shape] = current + 1
        kept.append(seed)
    return kept


def _ttl_seconds_for(desire_shape: str) -> int:
    return DESIRE_TTL_SECONDS.get(_clean_token(desire_shape), DEFAULT_TTL_SECONDS)


def _enforce_ttl_cap(thoughtlet: Thoughtlet) -> None:
    capped_expires_at = _plus_seconds(thoughtlet.created_at, _ttl_seconds_for(thoughtlet.desire_shape))
    if _seconds_between(capped_expires_at, thoughtlet.expires_at) is not None and _seconds_between(capped_expires_at, thoughtlet.expires_at) > 0:
        thoughtlet.expires_at = capped_expires_at


def _enforce_active_limits(thoughtlets: list[Thoughtlet]) -> None:
    for desire_shape, limit in ACTIVE_LIMITS_BY_DESIRE.items():
        active = [item for item in thoughtlets if item.desire_shape == desire_shape and item.status == "active"]
        if len(active) <= limit:
            continue
        active.sort(key=lambda item: (item.energy, item.usefulness_score, item.updated_at), reverse=True)
        for item in active[limit:]:
            item.energy = min(item.energy, 23)
            item.status = "dormant"


def _cap_energy(desire_shape: str, energy: int) -> int:
    return min(_clamp(energy), DESIRE_ENERGY_CAPS.get(_clean_token(desire_shape), 100))


def _new_thoughtlet(seed: ImpulseSeed, *, checked_at: str) -> Thoughtlet:
    lineage_id = "impline-" + _short_hash(seed.source_signature, 12)
    thoughtlet_id = "impulse-" + _timestamp_id(checked_at) + "-" + _short_hash(seed.source_signature, 8)
    return Thoughtlet(
        thoughtlet_id=thoughtlet_id,
        lineage_id=lineage_id,
        parent_id="none",
        generation=0,
        source_kind=seed.source_kind,
        source_ref=seed.source_ref,
        source_signature=seed.source_signature,
        desire_shape=seed.desire_shape,
        proposed_next_action=seed.proposed_next_action,
        inhibition_rule=seed.inhibition_rule,
        energy=seed.initial_energy,
        usefulness_score=_initial_usefulness(seed),
        mutation_count=0,
        activation_count=1,
        risk_flags=list(seed.risk_flags),
        evidence_preview=seed.evidence_preview,
        status="active",
        created_at=_timestamp_or_now_iso(checked_at),
        updated_at=_timestamp_or_now_iso(checked_at),
        last_triggered_at=_timestamp_or_now_iso(checked_at),
        last_spawned_at="",
        expires_at=_plus_seconds(checked_at, _ttl_seconds_for(seed.desire_shape)),
    )


def _refresh_thoughtlet(thoughtlet: Thoughtlet, seed: ImpulseSeed, *, checked_at: str) -> None:
    recent_seconds = _seconds_between(thoughtlet.last_triggered_at, checked_at)
    duplicate_drag = 8 if recent_seconds is not None and recent_seconds < 3600 else 0
    blended = int((thoughtlet.energy * 0.62) + (seed.initial_energy * 0.38)) - duplicate_drag
    thoughtlet.energy = _cap_energy(thoughtlet.desire_shape, blended)
    thoughtlet.usefulness_score = _clamp(int((thoughtlet.usefulness_score * 0.7) + (seed.initial_energy * 0.3)))
    thoughtlet.activation_count += 1
    thoughtlet.risk_flags = list(dict.fromkeys([*thoughtlet.risk_flags, *seed.risk_flags]))
    thoughtlet.evidence_preview = seed.evidence_preview or thoughtlet.evidence_preview
    thoughtlet.updated_at = _timestamp_or_now_iso(checked_at)
    thoughtlet.last_triggered_at = _timestamp_or_now_iso(checked_at)


def _decay_thoughtlet(thoughtlet: Thoughtlet, *, checked_at: str) -> None:
    _enforce_ttl_cap(thoughtlet)
    age_hours = _hours_between(thoughtlet.updated_at, checked_at)
    decay = 3
    if age_hours is not None and age_hours > 24:
        decay += min(12, int(age_hours // 24) * 3)
    if thoughtlet.desire_shape in SOFT_DESIRE_SHAPES:
        decay += 1
    thoughtlet.energy = _cap_energy(thoughtlet.desire_shape, thoughtlet.energy - decay)
    thoughtlet.updated_at = _timestamp_or_now_iso(checked_at)


def _cool_stale_transient_failure(thoughtlet: Thoughtlet, *, active_seed_signatures: set[str]) -> bool:
    if thoughtlet.source_signature in active_seed_signatures:
        return False
    if thoughtlet.desire_shape not in {"runtime_diagnostic_reflex", "self_repair_reflex"}:
        return False
    preview = _one_line(thoughtlet.evidence_preview).lower()
    if not any(
        marker in preview
        for marker in (
            "runtime queue has failures",
            "runtime subsystem reported an error",
            "queued outbound message failed to dispatch",
        )
    ):
        return False
    thoughtlet.energy = min(thoughtlet.energy, 18)
    thoughtlet.usefulness_score = min(thoughtlet.usefulness_score, 30)
    return True


def _cool_stale_unresolved_reflection(thoughtlet: Thoughtlet, *, active_seed_signatures: set[str]) -> bool:
    if thoughtlet.desire_shape != "unresolved_reflection":
        return False
    if _inner_cycle_only_reflection_text(
        thoughtlet.source_ref,
        thoughtlet.evidence_preview,
        thoughtlet.source_kind,
        thoughtlet.proposed_next_action,
    ):
        thoughtlet.energy = min(thoughtlet.energy, 12)
        thoughtlet.usefulness_score = min(thoughtlet.usefulness_score, 20)
        return True
    if thoughtlet.source_signature in active_seed_signatures:
        return False
    thoughtlet.energy = min(thoughtlet.energy, 18)
    thoughtlet.usefulness_score = min(thoughtlet.usefulness_score, 28)
    return True


def _maybe_spawn_child(thoughtlet: Thoughtlet, thoughtlets: list[Thoughtlet], *, checked_at: str) -> Thoughtlet | None:
    if thoughtlet.desire_shape in NO_SPAWN_DESIRES:
        return None
    if thoughtlet.energy < 72 or thoughtlet.generation >= 3:
        return None
    if thoughtlet.activation_count < 2:
        return None
    if "internal_marker_in_evidence" in thoughtlet.risk_flags:
        return None
    if _lineage_count(thoughtlets, thoughtlet.lineage_id) >= 4:
        return None
    if thoughtlet.last_spawned_at:
        elapsed = _seconds_between(thoughtlet.last_spawned_at, checked_at)
        if elapsed is not None and elapsed < SPAWN_INTERVAL_SECONDS:
            return None
    mutation = _mutate_action(thoughtlet)
    child_signature = "impchild:" + _short_hash(f"{thoughtlet.source_signature}|{mutation}|{thoughtlet.generation + 1}", 24)
    if any(item.source_signature == child_signature for item in thoughtlets):
        return None
    child = Thoughtlet(
        thoughtlet_id="impulse-" + _timestamp_id(checked_at) + "-" + _short_hash(child_signature, 8),
        lineage_id=thoughtlet.lineage_id,
        parent_id=thoughtlet.thoughtlet_id,
        generation=thoughtlet.generation + 1,
        source_kind=thoughtlet.source_kind,
        source_ref=thoughtlet.source_ref,
        source_signature=child_signature,
        desire_shape=thoughtlet.desire_shape,
        proposed_next_action=mutation,
        inhibition_rule=thoughtlet.inhibition_rule,
        energy=_cap_energy(thoughtlet.desire_shape, max(20, thoughtlet.energy - 18)),
        usefulness_score=thoughtlet.usefulness_score,
        mutation_count=thoughtlet.mutation_count + 1,
        activation_count=0,
        risk_flags=list(thoughtlet.risk_flags),
        evidence_preview=thoughtlet.evidence_preview,
        status="active",
        created_at=_timestamp_or_now_iso(checked_at),
        updated_at=_timestamp_or_now_iso(checked_at),
        last_triggered_at="",
        last_spawned_at="",
        expires_at=_plus_seconds(checked_at, _ttl_seconds_for(thoughtlet.desire_shape)),
    )
    thoughtlet.energy = _cap_energy(thoughtlet.desire_shape, thoughtlet.energy - 10)
    thoughtlet.last_spawned_at = _timestamp_or_now_iso(checked_at)
    thoughtlet.updated_at = _timestamp_or_now_iso(checked_at)
    return child


def _mutate_action(thoughtlet: Thoughtlet) -> str:
    if thoughtlet.desire_shape in {"runtime_diagnostic_reflex", "self_repair_reflex"}:
        return "draft_diagnostic_plan"
    if thoughtlet.desire_shape == "completion_continuity":
        return "prepare_owner_safe_summary"
    if thoughtlet.desire_shape == "dream_residue_compression":
        return "extract_symbolic_residue"
    if thoughtlet.desire_shape == "expression_repair_habit":
        return "test_expression_repair_on_shadow_examples"
    if thoughtlet.desire_shape == "unresolved_reflection":
        return "merge_with_related_residue"
    return "observe_only"


def _update_status(thoughtlet: Thoughtlet, *, checked_at: str) -> None:
    if "internal_marker_in_evidence" in thoughtlet.risk_flags:
        thoughtlet.status = "quarantined"
    elif _seconds_between(thoughtlet.expires_at, checked_at) is not None and _seconds_between(thoughtlet.expires_at, checked_at) > 0:
        thoughtlet.status = "extinct"
    elif thoughtlet.energy <= 5:
        thoughtlet.status = "extinct"
    elif thoughtlet.energy < 24:
        thoughtlet.status = "dormant"
    else:
        thoughtlet.status = "active"


def _prune_thoughtlets(thoughtlets: list[Thoughtlet], *, max_thoughtlets: int) -> list[Thoughtlet]:
    _enforce_active_limits(thoughtlets)
    thoughtlets.sort(key=lambda item: (_status_rank(item.status), item.energy, item.updated_at), reverse=True)
    kept = thoughtlets[:max_thoughtlets]
    return kept


def _summarize(thoughtlets: list[Thoughtlet]) -> dict[str, Any]:
    counts = {"active": 0, "dormant": 0, "quarantined": 0, "extinct": 0}
    for item in thoughtlets:
        counts[item.status] = counts.get(item.status, 0) + 1
    top = max(thoughtlets, key=lambda item: (item.energy, item.usefulness_score), default=None)
    lineages = {item.lineage_id for item in thoughtlets}
    desire_counts: dict[str, int] = {}
    for item in thoughtlets:
        desire_counts[item.desire_shape] = desire_counts.get(item.desire_shape, 0) + 1
    return {
        "thoughtlet_count": len(thoughtlets),
        "active_count": counts.get("active", 0),
        "dormant_count": counts.get("dormant", 0),
        "quarantined_count": counts.get("quarantined", 0),
        "extinct_count": counts.get("extinct", 0),
        "lineage_count": len(lineages),
        "top_thoughtlet_id": top.thoughtlet_id if top else "none",
        "top_desire_shape": top.desire_shape if top else "none",
        "top_energy": top.energy if top else 0,
        "top_action": top.proposed_next_action if top else "none",
        "soft_active_count": sum(1 for item in thoughtlets if item.status == "active" and item.desire_shape in SOFT_DESIRE_SHAPES),
        "desire_counts": desire_counts,
    }


def _write_state_markdown(
    root: Path,
    *,
    checked_at: str,
    thoughtlets: list[Thoughtlet],
    summary: dict[str, Any],
    notes: list[str],
) -> None:
    top_items = sorted(thoughtlets, key=lambda item: (item.status == "active", item.energy), reverse=True)[:8]
    lines = [
        "---",
        "title: Impulse Soup State",
        "memory_type: impulse_soup_state",
        "time_scope: short_term",
        "subject_ids: [xinyu]",
        "protected: true",
        "source: xinyu_impulse_soup",
        f"updated_at: {_timestamp_or_now_iso(checked_at)}",
        "status: active",
        "tags: [impulse, ecology, thoughtlet, shadow]",
        "---",
        "",
        "# Impulse Soup State",
        "",
        "## Summary",
        f"- checked_at: {checked_at}",
        f"- schema_version: {SCHEMA_VERSION}",
        f"- thoughtlet_count: {summary['thoughtlet_count']}",
        f"- active_count: {summary['active_count']}",
        f"- dormant_count: {summary['dormant_count']}",
        f"- quarantined_count: {summary['quarantined_count']}",
        f"- extinct_count: {summary['extinct_count']}",
        f"- lineage_count: {summary['lineage_count']}",
        f"- top_thoughtlet_id: {summary['top_thoughtlet_id']}",
        f"- top_desire_shape: {summary['top_desire_shape']}",
        f"- top_energy: {summary['top_energy']}",
        f"- top_action: {summary['top_action']}",
        f"- soft_active_count: {summary['soft_active_count']}",
        "- outward_action_allowed: false",
        "",
        "## Top Thoughtlets",
    ]
    if top_items:
        for item in top_items:
            lines.append(
                "- "
                + " ".join(
                    [
                        f"thoughtlet_id={item.thoughtlet_id}",
                        f"lineage_id={item.lineage_id}",
                        f"status={item.status}",
                        f"energy={item.energy}",
                        f"desire_shape={item.desire_shape}",
                        f"action={item.proposed_next_action}",
                        f"inhibition={item.inhibition_rule}",
                    ]
                )
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Boundaries",
            "- local_json_only: true",
            "- no_qq_enqueue: true",
            "- no_tool_execution: true",
            "- no_process_replication: true",
            "- no_self_code_write: true",
            "- scorer_gate_required_for_all_outward_candidates: true",
            "",
            "## Notes",
        ]
    )
    lines.extend(f"- {note}" for note in notes) if notes else lines.append("- none")
    _write_text_atomic(root / STATE_MD_REL, "\n".join(lines))


def _load_state(root: Path) -> dict[str, Any]:
    data = read_impulse_soup_state(root, default={"schema_version": SCHEMA_VERSION, "thoughtlets": []})
    if not isinstance(data.get("thoughtlets"), list):
        data["thoughtlets"] = []
    return data


def _thoughtlet_from_dict(data: dict[str, Any]) -> Thoughtlet:
    return Thoughtlet(
        thoughtlet_id=_string(data.get("thoughtlet_id"), "impulse-unknown"),
        lineage_id=_string(data.get("lineage_id"), "impline-unknown"),
        parent_id=_string(data.get("parent_id"), "none"),
        generation=_safe_int(data.get("generation"), 0),
        source_kind=_clean_token(data.get("source_kind")),
        source_ref=_scrub_ref(data.get("source_ref")),
        source_signature=_string(data.get("source_signature"), ""),
        desire_shape=_clean_token(data.get("desire_shape")),
        proposed_next_action=_clean_token(data.get("proposed_next_action")),
        inhibition_rule=_clean_token(data.get("inhibition_rule")),
        energy=_clamp(data.get("energy")),
        usefulness_score=_clamp(data.get("usefulness_score")),
        mutation_count=_safe_int(data.get("mutation_count"), 0),
        activation_count=_safe_int(data.get("activation_count"), 0),
        risk_flags=[_clean_token(item) for item in _as_list(data.get("risk_flags"))],
        evidence_preview=_clip(data.get("evidence_preview"), 220),
        status=_clean_token(data.get("status")),
        created_at=_normalize_iso(data.get("created_at")) or _now_iso(),
        updated_at=_normalize_iso(data.get("updated_at")) or _now_iso(),
        last_triggered_at=_normalize_iso(data.get("last_triggered_at")) or "",
        last_spawned_at=_normalize_iso(data.get("last_spawned_at")) or "",
        expires_at=_normalize_iso(data.get("expires_at")) or _plus_seconds(_now_iso(), DEFAULT_TTL_SECONDS),
    )


def _append_trace(root: Path, event: dict[str, Any]) -> None:
    path = root / TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(_clean_json(event), ensure_ascii=False, sort_keys=True) + "\n")


def _read_recent_jsonl(path: Path, *, limit: int) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            rows.append(data)
    return rows


def _energy_from_proactive_row(row: dict[str, Any], score: dict[str, Any]) -> int:
    total = _safe_int(row.get("total_score"), _safe_int(score.get("total_score"), 40))
    recommendation = _clean_token(row.get("recommendation"))
    if recommendation == "send_now":
        total += 8
    elif recommendation == "drop":
        total -= 20
    if row.get("source_type") == "dream_residue":
        total -= 8
    if _safe_int(score.get("repetition_penalty"), 0) > 0:
        total -= 10
    return _clamp(total)


def _risk_flags_for(desire_shape: str, existing: Any) -> tuple[str, ...]:
    flags = list(_as_list(existing))
    if desire_shape in {"dream_residue_compression", "expression_repair_habit", "social_presence_inhibition"}:
        flags.append("no_direct_qq_v0")
    if desire_shape == "dream_residue_compression":
        flags.append("dream_or_emotion")
    return tuple(dict.fromkeys(_clean_token(flag) for flag in flags if _clean_token(flag)))


def _initial_usefulness(seed: ImpulseSeed) -> int:
    if seed.desire_shape in {"runtime_diagnostic_reflex", "self_repair_reflex"}:
        return min(85, seed.initial_energy + 8)
    if seed.desire_shape in SOFT_DESIRE_SHAPES:
        return max(15, seed.initial_energy - 10)
    return seed.initial_energy


def _lineage_count(thoughtlets: list[Thoughtlet], lineage_id: str) -> int:
    return sum(1 for item in thoughtlets if item.lineage_id == lineage_id)


def _status_rank(status: str) -> int:
    return {"active": 4, "dormant": 3, "quarantined": 2, "extinct": 1}.get(status, 0)


def _latest_heading_section(text: str, prefix: str) -> tuple[str, str]:
    matches = list(re.finditer(rf"(?m)^##\s+({re.escape(prefix)}[^\r\n]+)\s*$", text or ""))
    if not matches:
        return "", ""
    match = matches[-1]
    return match.group(1).strip(), text[match.end() :]


def _parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for regex in (FRONTMATTER_RE, FIELD_RE):
        for match in regex.finditer(text or ""):
            fields[match.group(1).strip()] = _clip(match.group(2), 300)
    return fields


def _proactive_trace_seed_allowed(
    row: dict[str, Any],
    *,
    source_kind: str,
    candidate: dict[str, Any],
    checked_at: str,
) -> bool:
    source_ref = _one_line(candidate.get("source_ref"))
    preview = _first_meaningful(
        candidate.get("content_preview"),
        row.get("content_preview"),
        candidate.get("owner_visible_text"),
    )
    combined_fields = [
        source_ref,
        row.get("source_ref"),
        row.get("candidate_signature"),
        row.get("candidate_id"),
        row.get("content_preview"),
        row.get("intent_type"),
        row.get("recommendation"),
        candidate.get("source_ref"),
        candidate.get("content_preview"),
        candidate.get("owner_visible_text"),
        candidate.get("utility_hint"),
        candidate.get("intent_type"),
        candidate.get("source_type"),
        candidate.get("novelty_hint"),
        preview,
    ]
    combined = " ".join(_one_line(value) for value in combined_fields).lower()
    if source_kind == "reflection_question" and _inner_cycle_only_reflection_text(*combined_fields):
        return False
    if source_kind == "runtime_error" and "runtime_program_awareness:watched_source" in combined and "read_only=true" in combined:
        return False
    if source_kind == "task_failed" and "qq_outbox_dispatch_state" in combined:
        return _runtime_failure_detail_active(preview, checked_at=checked_at)
    if source_kind == "task_failed" and "runtime_program_awareness:codex_delegate" in combined:
        return _codex_delegate_failure_active(preview, checked_at=checked_at)
    return True


def _inner_cycle_only_reflection_text(*values: Any) -> bool:
    text = " ".join(_one_line(value).lower() for value in values if _one_line(value))
    if "reflection residue should stay in the inner cycle for now" in text:
        return True
    return "reflection residue" in text and "inner cycle" in text and "stay" in text


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    try:
        tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def _clean_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _clean_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean_json(item) for item in value]
    if isinstance(value, tuple):
        return [_clean_json(item) for item in value]
    if isinstance(value, str):
        return _scrub_text(value)
    return value


def _first_meaningful(*values: Any) -> str:
    for value in values:
        if _meaningful(value):
            return _scrub_text(value)
    return "none"


def _meaningful(value: Any) -> bool:
    text = _one_line(value).lower()
    return text not in {"", "none", "unknown", "false", "null"}


def _string(value: Any, default: str = "") -> str:
    text = _one_line(value)
    return text if text else default


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _scrub_ref(value: Any) -> str:
    text = _scrub_text(value)
    text = re.sub(r"[^A-Za-z0-9_.:/#-]+", "_", text).strip("_")
    return _clip(text or "unknown", 140)


def _clean_token(value: Any) -> str:
    text = _one_line(value).lower()
    text = re.sub(r"[^a-z0-9_.:-]+", "_", text).strip("_")
    return text or "none"


def _one_line(value: Any) -> str:
    return re.sub(r"\s+", " ", "" if value is None else str(value)).strip()


def _scrub_text(value: Any) -> str:
    text = _one_line(value)
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[redacted-secret]", text)
    return LOCAL_PATH_RE.sub("[local-path]", text)


def _clip(value: Any, limit: int = 160) -> str:
    text = _scrub_text(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _clamp(value: Any, lo: int = 0, hi: int = 100) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = 0
    return max(lo, min(hi, number))


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _normalize_iso(value: Any) -> str:
    parsed = _parse_iso(value)
    return parsed.astimezone().isoformat() if parsed else ""


def _parse_iso(value: Any) -> datetime | None:
    text = _one_line(value)
    if not text or text == "none":
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def _seconds_between(start: str, end: str) -> float | None:
    start_dt = _parse_iso(start)
    end_dt = _parse_iso(end)
    if start_dt is None or end_dt is None:
        return None
    return (end_dt - start_dt).total_seconds()


def _hours_between(start: str, end: str) -> float | None:
    seconds = _seconds_between(start, end)
    return None if seconds is None else max(0.0, seconds / 3600)


def _plus_seconds(value: str, seconds: int) -> str:
    parsed = _parse_iso(value) or datetime.now().astimezone()
    return (parsed + timedelta(seconds=max(0, int(seconds)))).astimezone().isoformat()


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _timestamp_or_now_iso(value: Any) -> str:
    return _normalize_iso(value) or _now_iso()


def _timestamp_id(value: str) -> str:
    parsed = _parse_iso(value) or datetime.now().astimezone()
    return parsed.strftime("%Y%m%dT%H%M%S%f")[:21]


def _short_hash(value: Any, length: int = 12) -> str:
    return hashlib.sha256(str(value).encode("utf-8", errors="ignore")).hexdigest()[:length]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run XinYu Impulse Soup v0.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent))
    args = parser.parse_args(argv)
    result = run_impulse_soup(Path(args.root))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
