from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from source_material_quality import claim_is_placeholder, claim_is_too_thin, claim_looks_garbled
from source_material_parser import integrated_source_material_ids as parse_integrated_source_material_ids
from source_material_parser import split_material_field_maps
from source_protocol_utils import split_source_requests
from xinyu_storage_paths import knowledge_file_path


def count_regex(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, re.M))


def count_quality_followup_candidates(text: str) -> int:
    return len(re.findall(r"(?m)^- repeated_question_host:\s+severity=review;\s+target=q-\d+@", text))


from xinyu_state_io import extract_value as extract_value, read_text as read_text, write_text as write_text


MATERIAL_FIELDS = (
    "question_id",
    "status",
    "reliability",
    "integration_scope",
    "comparison_status",
    "claim",
    "extraction_status",
)
MATERIAL_DEFAULTS = {
    "question_id": "none",
    "status": "hold",
    "reliability": "unknown",
    "integration_scope": "hold",
    "comparison_status": "not_compared",
    "claim": "none",
    "extraction_status": "unknown",
}


def _knowledge(root: Path, filename: str) -> Path:
    return knowledge_file_path(root, filename)


def owner_followthrough_granted(root: Path) -> bool:
    grants = read_text(root / "memory/context/owner_permission_grants.md")
    return (
        "grant_research_ready_request_followthrough: "
        "approved_fetch_compare_integrate_for_existing_ai_domain_ready_requests"
    ) in grants


def owner_high_autonomy_granted(root: Path) -> bool:
    grants = read_text(root / "memory/context/owner_permission_grants.md")
    return (
        "grant_high_autonomy_learning_search: "
        "approved_budgeted_ai_domain_and_quality_followup_search_through_gates"
    ) in grants


def learning_quality_is_stable(text: str) -> bool:
    grade = extract_value(text, "quality_grade", "unknown")
    warnings = extract_value(text, "warning_count", "0")
    return grade == "stable" and warnings in {"0", "unknown"}


def learning_quality_allows_owner_followthrough(root: Path, text: str) -> bool:
    if learning_quality_is_stable(text):
        return True
    if not owner_high_autonomy_granted(root):
        return False
    grade = extract_value(text, "quality_grade", "unknown")
    warnings = extract_value(text, "warning_count", "0")
    conflicts = extract_value(text, "conflict_hold_materials", "0")
    return grade == "review_needed" and warnings in {"0", "unknown"} and conflicts in {"0", "unknown"}


def is_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def split_requests(text: str) -> list[dict[str, str]]:
    return split_source_requests(
        text,
        fields=("question_id", "target", "url", "status"),
        skip_none_question=False,
    )


def split_materials(text: str) -> list[dict[str, str]]:
    return split_material_field_maps(text, fields=MATERIAL_FIELDS, defaults=MATERIAL_DEFAULTS)


def integrated_source_material_ids(text: str) -> set[str]:
    return parse_integrated_source_material_ids(text)


def existing_material_urls(text: str) -> set[str]:
    return set(re.findall(r"(?m)^- url:\s*(\S+)\s*$", text))


def ai_followthrough_request_ready(item: dict[str, str]) -> bool:
    return (
        item.get("status") == "ready"
        and item.get("target") == "ai-self-understanding"
        and is_http_url(item.get("url", "none"))
    )


def count_owner_ai_ready_requests(source_requests: str, source_materials: str) -> int:
    urls = existing_material_urls(source_materials)
    return sum(
        1
        for item in split_requests(source_requests)
        if ai_followthrough_request_ready(item) and item["url"] not in urls
    )


def count_pending_ai_followthrough_materials(source_materials: str, general: str) -> int:
    integrated = integrated_source_material_ids(general)
    count = 0
    for item in split_materials(source_materials):
        if item["material_id"] in integrated:
            continue
        if item["question_id"] != "q-006":
            continue
        if item["status"] != "ready":
            continue
        if item["integration_scope"] != "knowledge_only":
            continue
        if item["reliability"] not in {"medium_ready", "high_ready", "verified", "curated"}:
            continue
        if item.get("extraction_status") == "unreadable":
            continue
        if claim_looks_garbled(item["claim"]) or claim_is_placeholder(item["claim"]) or claim_is_too_thin(item["claim"]):
            continue
        count += 1
    return count


def count_pending_curated_materials(source_materials: str, general: str) -> int:
    integrated = integrated_source_material_ids(general)
    count = 0
    for item in split_materials(source_materials):
        if item["material_id"] in integrated:
            continue
        if item["status"] != "ready":
            continue
        if item["reliability"] != "curated" or item["comparison_status"] != "curated":
            continue
        if item["integration_scope"] != "knowledge_only":
            continue
        if item.get("extraction_status") == "unreadable":
            continue
        if claim_looks_garbled(item["claim"]) or claim_is_placeholder(item["claim"]) or claim_is_too_thin(item["claim"]):
            continue
        count += 1
    return count


def render_state(
    checked_at: str,
    mode: str,
    integration_permission: str,
    gate_reason: str,
    ready_candidates: int,
    source_gate_candidates: int,
    reliability_ready: int,
    quality_followup_candidates: int,
    curated_ready_materials: int,
    owner_ai_followthrough_candidates: int,
) -> str:
    return f"""---
title: Source Integration Gate State
memory_type: source_integration_gate_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {checked_at}
last_confirmed_at: {checked_at}
importance_score: 82
impact_score: 81
confidence_score: 100
status: active
tags: [knowledge, integration, gate]
---

# Source Integration Gate State

## Last Evaluation
- checked_at: {checked_at}
- mode: {mode}

## Gate Decision
- integration_permission: {integration_permission}
- gate_reason: {gate_reason}
- ready_candidates: {ready_candidates}

## Inputs
- source_gate_candidates: {source_gate_candidates}
- reliability_ready: {reliability_ready}
- quality_followup_candidates: {quality_followup_candidates}
- curated_ready_materials: {curated_ready_materials}
- owner_ai_followthrough_candidates: {owner_ai_followthrough_candidates}

## Rules
- Integration gate is preparatory only and does not ingest external knowledge.
- Even when candidates are ready, self and relationship layers remain protected.
- Owner-curated learning materials may open the learner path for knowledge-only integration.
- Learning-quality follow-up candidates may reopen sourcing for already learned questions, but only as new source requests.
- External knowledge may only move toward knowledge/general after this gate is open and a future sourcing path exists.
"""


def run_source_integration_gate(
    root: Path,
    checked_at: str | None = None,
    mode: str = "runtime_source_integration_gate",
) -> dict[str, object]:
    checked_at = checked_at or datetime.now().astimezone().isoformat()

    source_gate = read_text(_knowledge(root, "source_gate_state.md"))
    source_reliability = read_text(_knowledge(root, "source_reliability_state.md"))
    learning_quality = read_text(_knowledge(root, "learning_quality_state.md"))
    source_materials = read_text(_knowledge(root, "source_materials.md"))
    general = read_text(_knowledge(root, "general.md"))
    source_requests = read_text(_knowledge(root, "source_requests.md"))

    source_gate_candidates = count_regex(source_gate, r"^- q-\d+:")
    reliability_ready = count_regex(source_reliability, r"^- q-\d+:\s+(medium_ready|high_ready)$")
    quality_followup_candidates = count_quality_followup_candidates(learning_quality) if source_gate_candidates <= 0 else 0
    curated_ready_materials = count_pending_curated_materials(source_materials, general)
    owner_ai_followthrough_candidates = 0
    if (
        source_gate_candidates <= 0
        and quality_followup_candidates <= 0
        and owner_followthrough_granted(root)
        and learning_quality_allows_owner_followthrough(root, learning_quality)
    ):
        owner_ai_followthrough_candidates = count_owner_ai_ready_requests(
            source_requests,
            source_materials,
        ) + count_pending_ai_followthrough_materials(source_materials, general)
    ready_candidates = (
        min(source_gate_candidates, reliability_ready)
        + quality_followup_candidates
        + curated_ready_materials
        + owner_ai_followthrough_candidates
    )

    if ready_candidates <= 0:
        integration_permission = "hold"
        gate_reason = "no_reliable_candidates"
    elif owner_ai_followthrough_candidates > 0 and source_gate_candidates <= 0 and quality_followup_candidates <= 0:
        integration_permission = "prepare_only"
        gate_reason = "owner_approved_ai_ready_followthrough"
    elif curated_ready_materials > 0 and source_gate_candidates <= 0 and quality_followup_candidates <= 0:
        integration_permission = "prepare_only"
        gate_reason = "curated_source_materials_ready"
    elif quality_followup_candidates > 0 and source_gate_candidates <= 0:
        integration_permission = "prepare_only"
        gate_reason = "quality_followup_candidates_prepared"
    else:
        integration_permission = "prepare_only"
        gate_reason = "candidates_prepared_but_not_ingested"

    write_text(
        _knowledge(root, "source_integration_gate_state.md"),
        render_state(
            checked_at,
            mode,
            integration_permission,
            gate_reason,
            ready_candidates,
            source_gate_candidates,
            reliability_ready,
            quality_followup_candidates,
            curated_ready_materials,
            owner_ai_followthrough_candidates,
        ),
    )

    return {
        "checked_at": checked_at,
        "integration_permission": integration_permission,
        "gate_reason": gate_reason,
        "ready_candidates": ready_candidates,
        "source_gate_candidates": source_gate_candidates,
        "reliability_ready": reliability_ready,
        "quality_followup_candidates": quality_followup_candidates,
        "curated_ready_materials": curated_ready_materials,
        "owner_ai_followthrough_candidates": owner_ai_followthrough_candidates,
    }
