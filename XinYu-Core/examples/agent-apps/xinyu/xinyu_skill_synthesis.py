"""Deterministic skill synthesis: distil corroborated memory candidates into
reusable skill artifacts.

This mirrors the existing engine contract (``run_*(root, *, <timestamp>, mode)
-> dict``) and is intentionally model-free, like the dream/consolidation engines,
so it can run on the isolated maintenance worker without an LLM turn.

A skill is only emitted when a claim is *corroborated* (repeated evidence, no
open conflict), reusing the same review thresholds the candidate analyzer already
computes. Emitted skills are ``review_only`` — recallable hints, never an
automatic identity rewrite.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from xinyu_dialogue_archive import list_memory_candidates
from xinyu_memory_candidate_analysis import candidate_review_context
from xinyu_skill_library import read_skill, slugify, tokenize, write_skill

try:
    from xinyu_method_immunity import MethodImmunityBlocked
except ImportError:  # pragma: no cover
    class MethodImmunityBlocked(Exception):
        pass

# candidate_type -> (skill title prefix, situation framing, routine verb)
_TYPE_FRAMING = {
    "voice_correction": ("说话风格", "主人对说话风格/语气给出过反馈时", "按主人纠正过的风格说话"),
    "owner_preference": ("主人偏好", "话题命中主人表达过的偏好时", "遵循主人的既有偏好"),
    "relationship_signal": ("关系信号", "涉及与主人关系的语境时", "按已确认的关系信号回应"),
    "project_fact": ("项目事实", "讨论相关项目/运行时细节时", "依据已记录的项目事实作答"),
    "project": ("项目事实", "讨论相关项目/运行时细节时", "依据已记录的项目事实作答"),
}
_DEFAULT_FRAMING = ("经验", "命中相似语境时", "复用过去验证有效的做法")

_CORROBORATED_RECOMMENDATIONS = {
    "repeated_evidence_ready_for_owner_review",
    "corroborated_candidate_review",
}
_GATHER_STATUSES = (
    "self_approved_recent_context",
    "self_approved_voice_review",
    "owner_review_required",
    "approved",
)


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _trigger_keys(rows: list[dict[str, Any]]) -> list[str]:
    stop = {"owner", "turn", "visible", "reply", "candidate", "xinyu", "memory"}
    counts: dict[str, int] = {}
    for row in rows:
        for token in tokenize(row.get("candidate_text", "")):
            if len(token) < 2 or token in stop:
                continue
            counts[token] = counts.get(token, 0) + 1
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [token for token, _ in ordered[:8]]


def _synthesize_skill(topic_key: str, rows: list[dict[str, Any]], review: dict[str, Any]) -> dict[str, Any]:
    primary = rows[0]
    ctype = _safe_str(primary.get("candidate_type")).strip() or "experience"
    prefix, situation_frame, routine_verb = _TYPE_FRAMING.get(ctype, _DEFAULT_FRAMING)
    triggers = _trigger_keys(rows)
    trigger_hint = "、".join(triggers[:4]) if triggers else "相似话题"
    reason = _safe_str(primary.get("reason")).strip()
    sample = _safe_str(primary.get("candidate_text")).strip().replace("\n", " ")

    routine = routine_verb
    if reason:
        routine += f"；依据：{reason}"
    if sample:
        routine += f"；佐证片段：{sample[:160]}"

    evidence_ids = sorted(
        {_safe_str(row.get("candidate_id")).strip() for row in rows if _safe_str(row.get("candidate_id")).strip()}
    )
    evidence_count = int(review.get("evidence_count", len(rows)) or len(rows))
    return {
        "skill_id": slugify(f"{ctype}-{topic_key[:12]}"),
        "title": f"{prefix}·{trigger_hint}",
        "situation": f"{situation_frame}（关键词：{trigger_hint}）。",
        "routine": routine,
        "evidence": f"corroborated by {evidence_count} candidate(s): {', '.join(evidence_ids)}",
        "trigger_keys": triggers,
        "evidence_candidate_ids": evidence_ids,
        "evidence_count": evidence_count,
        "confidence": min(evidence_count, 5),
        "tags": [ctype],
        "status": "review_only",
    }


def run_skill_synthesis(
    root: Path,
    *,
    checked_at: str | None = None,
    mode: str = "skill_synthesis",
    min_evidence: int = 2,
    limit: int = 200,
) -> dict[str, Any]:
    root = Path(root)
    del checked_at  # accepted for engine-contract symmetry; synthesis is timestamp-free

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for status in _GATHER_STATUSES:
        for row in list_memory_candidates(root, status=status, limit=limit):
            candidate_id = _safe_str(row.get("candidate_id")).strip()
            if not candidate_id or candidate_id in seen:
                continue
            seen.add(candidate_id)
            rows.append(row)

    clusters: dict[str, dict[str, Any]] = {}
    for row in rows:
        review = candidate_review_context(row, rows)
        if int(review.get("conflict_count", 0) or 0) > 0:
            continue
        if review.get("recommendation") not in _CORROBORATED_RECOMMENDATIONS:
            continue
        if int(review.get("evidence_count", 0) or 0) < max(1, int(min_evidence)):
            continue
        topic = _safe_str(review.get("claim_topic_key")).strip() or _safe_str(row.get("candidate_id"))
        bucket = clusters.setdefault(topic, {"rows": [], "review": review})
        bucket["rows"].append(row)
        if int(review.get("evidence_count", 0) or 0) > int(bucket["review"].get("evidence_count", 0) or 0):
            bucket["review"] = review

    created = 0
    updated = 0
    skipped = 0
    skill_ids: list[str] = []
    for topic, info in clusters.items():
        skill = _synthesize_skill(topic, info["rows"], info["review"])
        triggers = [t for t in (skill.get("trigger_keys") or []) if len(str(t).strip()) >= 2]
        evidence_count = int(skill.get("evidence_count") or 0)
        tags = {str(t).strip().lower() for t in (skill.get("tags") or [])}
        # Quality gate: weak triggers or thin project-fact noise → skip.
        if len(triggers) < 2:
            skipped += 1
            continue
        if "project_fact" in tags or "project" in tags:
            if evidence_count < max(2, int(min_evidence)):
                skipped += 1
                continue
        skill["trigger_keys"] = triggers
        existed = bool(read_skill(root, skill["skill_id"]))
        try:
            write_skill(root, skill)
        except MethodImmunityBlocked:
            skipped += 1
            continue
        skill_ids.append(skill["skill_id"])
        if existed:
            updated += 1
        else:
            created += 1

    return {
        "mode": mode,
        "candidates_scanned": len(rows),
        "clusters": len(clusters),
        "created": created,
        "updated": updated,
        "skipped_quality_gate": skipped,
        "skill_ids": skill_ids,
    }
