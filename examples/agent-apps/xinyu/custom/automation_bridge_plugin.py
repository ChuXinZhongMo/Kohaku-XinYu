"""Low-frequency automation suggestion bridge for Xinyu."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import os
import re
from typing import Any

from kohakuterrarium.modules.plugin.base import BasePlugin, PluginContext

from dream_output_engine import has_unconsumed_dream_seed
from turn_mode_utils import read_turn_mode


def _default_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _resolve_root(ctx: PluginContext | None) -> Path:
    candidate = Path(ctx.working_dir) if ctx else _default_root()
    if (candidate / "memory").exists():
        return candidate
    return _default_root()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _trace(root: Path, line: str) -> None:
    trace_path = root / "memory/context/automation_trace.log"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().isoformat()
    with trace_path.open("a", encoding="utf-8") as fh:
        fh.write(f"{stamp} {line}\n")


def _owner_ready_followthrough_granted(root: Path) -> bool:
    grants = _read(root / "memory/context/owner_permission_grants.md")
    return (
        "grant_research_ready_request_followthrough: "
        "approved_fetch_compare_integrate_for_existing_ai_domain_ready_requests"
    ) in grants


def _owner_high_autonomy_granted(root: Path) -> bool:
    grants = _read(root / "memory/context/owner_permission_grants.md")
    return (
        "grant_high_autonomy_learning_search: "
        "approved_budgeted_ai_domain_and_quality_followup_search_through_gates"
    ) in grants


def _extract_value(block: str, field: str, default: str = "unknown") -> str:
    match = re.search(rf"(?m)^- {re.escape(field)}:\s*(.+)$", block)
    return match.group(1).strip() if match else default


def _split_source_request_blocks(text: str) -> list[dict[str, str]]:
    parts = re.split(r"(?m)^## (request-\d{4}-\d{2}-\d{2}-\d{3}|request-[\w-]+)\n", text)
    requests: list[dict[str, str]] = []
    if len(parts) < 3:
        return requests
    for i in range(1, len(parts), 2):
        request_id = parts[i].strip()
        if request_id == "request-none":
            continue
        body = parts[i + 1]
        requests.append(
            {
                "request_id": request_id,
                "question_id": _extract_value(body, "question_id", "none"),
                "target": _extract_value(body, "target", "unknown"),
                "url": _extract_value(body, "url", "none"),
                "status": _extract_value(body, "status", "hold"),
            }
        )
    return requests


def _ready_request_has_unstaged_url(source_requests: str, source_materials: str, *, ai_only: bool = False) -> bool:
    material_urls = set(re.findall(r"(?m)^- url:\s*(\S+)\s*$", source_materials))
    for request in _split_source_request_blocks(source_requests):
        url = request.get("url", "")
        if ai_only and request.get("target") != "ai-self-understanding":
            continue
        if request.get("status") == "ready" and url.startswith(("http://", "https://")) and url not in material_urls:
            return True
    return False


def _owner_ai_followthrough_waiting(root: Path, source_requests: str, source_materials: str, learning_quality: str) -> bool:
    if not _owner_ready_followthrough_granted(root):
        return False
    quality_stable = "- quality_grade: stable" in learning_quality and "- warning_count: 0" in learning_quality
    high_review_allowed = (
        _owner_high_autonomy_granted(root)
        and "- quality_grade: review_needed" in learning_quality
        and "- warning_count: 0" in learning_quality
        and "- conflict_hold_materials: 0" in learning_quality
    )
    if not quality_stable and not high_review_allowed:
        return False
    material_urls = set(re.findall(r"(?m)^- url:\s*(\S+)\s*$", source_materials))
    for request in _split_source_request_blocks(source_requests):
        url = request.get("url", "")
        if (
            request.get("status") == "ready"
            and request.get("target") == "ai-self-understanding"
            and url.startswith(("http://", "https://"))
            and url not in material_urls
        ):
            return True
    return False


def _has_learning_quality_followup_candidate(learning_quality: str) -> bool:
    return bool(re.search(r"(?m)^- repeated_question_host:\s+severity=review;\s+target=q-\d+@", learning_quality))


def _has_candidate_search_result_for_pending(source_requests: str, source_search_results: str) -> bool:
    pending_ids = {
        item["request_id"]
        for item in _split_source_request_blocks(source_requests)
        if item.get("status") == "pending_url"
    }
    if not pending_ids:
        return False
    parts = re.split(r"(?m)^## (result-\d{4}-\d{2}-\d{2}-\d{3}|result-[\w-]+)\n", source_search_results)
    if len(parts) < 3:
        return False
    for i in range(1, len(parts), 2):
        body = parts[i + 1]
        if _extract_value(body, "status", "hold") == "candidate" and _extract_value(body, "request_id", "none") in pending_ids:
            return True
    return False


def _infer_suggestions(root: Path) -> dict[str, str]:
    inner_sync = _read(root / "memory/context/inner_sync_state.md")
    question_pipe = _read(root / "memory/context/question_pipeline_state.md")
    slow_state = _read(root / "memory/reflection/reprocessing_state.md")
    reflection_queue = _read(root / "memory/reflection/reflection_queue.md")
    reflection_log = _read(root / "memory/reflection/reflection_log.md")
    growth_log = _read(root / "memory/reflection/growth_log.md")
    dream_seeds = _read(root / "memory/dreams/dream_seeds.md")
    dream_weight = _read(root / "memory/dreams/dream_weight_state.md")
    retention_gate = _read(root / "memory/archive/retention_gate_state.md")
    reflection_out = _read(root / "memory/reflection/reflection_output_state.md")
    dream_output = _read(root / "memory/dreams/dream_output_state.md")
    source_gate = _read(root / "memory/knowledge/source_gate_state.md")
    source_integration = _read(root / "memory/knowledge/source_integration_gate_state.md")
    source_request_planner = _read(root / "memory/knowledge/source_request_planner_state.md")
    source_materials = _read(root / "memory/knowledge/source_materials.md")
    source_requests = _read(root / "memory/knowledge/source_requests.md")
    source_search_results = _read(root / "memory/knowledge/source_search_results.md")
    general_knowledge = _read(root / "memory/knowledge/general.md")
    learning_quality = _read(root / "memory/knowledge/learning_quality_state.md")
    autonomous_search_activation = _read(root / "memory/knowledge/autonomous_search_activation_state.md")
    capability = _read(root / "memory/context/capability_zones_state.md")
    owner_grants = _read(root / "memory/context/owner_permission_grants.md")
    archive_queue = _read(root / "memory/archive/archive_queue.md")
    archive_output = _read(root / "memory/archive/archive_output_state.md")

    source_gate_open = "- integration_permission: prepare_only" in source_integration or "- integration_permission: integrate_ready" in source_integration
    source_integration_reason = _extract_value(source_integration, "gate_reason", "unknown")
    owner_ai_gate_scope = source_integration_reason == "owner_approved_ai_ready_followthrough"
    has_source_candidates = bool(re.search(r"^- q-\d+:", source_gate, re.M))
    has_ready_source_material = "- status: ready" in source_materials
    has_real_source_material = bool(re.search(r"(?m)^## material-\d{4}-\d{2}-\d{2}-\d{3}", source_materials))
    has_learned_entries = bool(re.search(r"(?m)^## learned-\d{4}-\d{2}-\d{2}-\d{3}", general_knowledge))
    has_q006_learned_entries = "- question_id: q-006" in general_knowledge
    learning_quality_stable = "- quality_grade: stable" in learning_quality
    material_blocks = re.findall(r"(?ms)^## material-[^\n]+\n(.*?)(?=^## |\Z)", source_materials)
    has_uncompared_ready_material = any(
        "- status: ready" in block and "- comparison_checked_at:" not in block
        for block in material_blocks
    )
    has_planned_source_request = bool(re.search(r"^- question_id: q-\d+", source_requests, re.M))
    source_candidate_ids = set(re.findall(r"(?m)^- (q-\d+):", source_gate))
    planned_source_question_ids = set(re.findall(r"(?m)^- question_id:\s*(q-\d+)$", source_requests))
    has_unplanned_source_candidate = bool(source_candidate_ids - planned_source_question_ids)
    has_pending_source_request = "- status: pending_url" in source_requests
    has_ready_source_request = "- status: ready" in source_requests or bool(os.environ.get("XINYU_OUTWARD_SOURCE_URLS", "").strip())
    has_unstaged_ready_source_request = _ready_request_has_unstaged_url(
        source_requests,
        source_materials,
        ai_only=owner_ai_gate_scope,
    )
    owner_ai_followthrough_waiting = _owner_ai_followthrough_waiting(
        root,
        source_requests,
        source_materials,
        learning_quality,
    )
    has_quality_followup_candidate = _has_learning_quality_followup_candidate(learning_quality)
    has_candidate_search_result = _has_candidate_search_result_for_pending(source_requests, source_search_results)
    has_controlled_search_input = bool(os.environ.get("XINYU_SOURCE_SEARCH_RESULTS", "").strip())
    source_search_provider = os.environ.get("XINYU_SOURCE_SEARCH_PROVIDER", "").strip().lower()
    owner_source_collect_granted = (
        "autonomous_search_provider: enabled_duckduckgo_html_bounded_ai_domain" in capability
        and "grant_autonomous_source_collect: approved_bounded_candidate_material_only" in owner_grants
    )
    has_search_provider = source_search_provider not in {"", "disabled", "none", "off"} or owner_source_collect_granted
    autonomous_search_mode = os.environ.get("XINYU_AUTONOMOUS_SEARCH", "").strip().lower()
    autonomous_search_active = autonomous_search_mode in {"enabled", "dry_run"} or (
        autonomous_search_mode in {"", "auto"} and owner_source_collect_granted
    )
    dream_weight_active = bool(re.search(r"^- weight_delta:\s*[1-9]\d*$", dream_weight, re.M))
    has_growth_entries = bool(re.search(r"(?m)^## growth-", growth_log))
    has_reflection_entries = bool(re.search(r"(?m)^## reflection-", reflection_log))

    return {
        "suggest_inner_sync": "yes" if "meaningful: true" in inner_sync else "no",
        "suggest_question_pipeline": "yes" if "ready_for_exploration:" in question_pipe else "no",
        "suggest_slow_reprocess": "yes" if "reflection_queue_items:" in slow_state else "no",
        "suggest_consolidation": "yes"
        if ("## item-" in reflection_queue or "## seed-" in dream_seeds or "## item-" in archive_queue or dream_weight_active)
        else "hold",
        "suggest_long_term_memory_gate": "yes"
        if ("## item-" in archive_queue or "## item-" in reflection_queue or "## seed-" in dream_seeds or dream_weight_active)
        else "hold",
        "suggest_personality_growth_gate": "yes"
        if (has_growth_entries or has_reflection_entries or dream_weight_active)
        else "hold",
        "suggest_retention_gate": "yes"
        if "- archive_permission: " in retention_gate
        and ("## item-" in archive_queue or "## seed-" in dream_seeds or "## item-" in reflection_queue or dream_weight_active)
        else "hold",
        "suggest_reflection_output": "yes" if "- item_id:" in reflection_out else "hold",
        "suggest_dream_output": "yes" if has_unconsumed_dream_seed(dream_seeds) else "hold",
        "suggest_source_gate": "yes" if re.search(r"^- q-\d+:", source_gate, re.M) else "hold",
        "suggest_source_reliability": "yes"
        if re.search(r"^- q-\d+:", source_gate, re.M)
        else "hold",
        "suggest_source_integration_gate": "yes"
        if (
            "- q-" in _read(root / "memory/knowledge/source_reliability_state.md")
            or owner_ai_followthrough_waiting
            or has_quality_followup_candidate
        )
        else "hold",
        "suggest_source_request_planner": "yes"
        if (
            source_gate_open
            and (
                (
                    has_source_candidates
                    and not has_ready_source_material
                    and (not has_planned_source_request or has_unplanned_source_candidate)
                )
                or has_quality_followup_candidate
            )
        )
        else "hold",
        "suggest_source_search_resolver": "yes"
        if (source_gate_open and has_pending_source_request and not has_ready_source_request and has_controlled_search_input)
        else "hold",
        "suggest_autonomous_search_activation": "yes"
        if (source_gate_open and has_pending_source_request and not has_ready_source_request and not has_candidate_search_result and has_search_provider and autonomous_search_active)
        else "hold",
        "suggest_source_search_provider": "yes"
        if (source_gate_open and has_pending_source_request and not has_ready_source_request and not has_candidate_search_result and has_search_provider and autonomous_search_active)
        else "hold",
        "suggest_search_result_gate": "yes"
        if (source_gate_open and has_candidate_search_result and not has_ready_source_request)
        else "hold",
        "suggest_outward_source": "yes"
        if (
            source_gate_open
            and (
                has_unstaged_ready_source_request
                or (not has_ready_source_material and has_ready_source_request)
            )
        )
        else "hold",
        "suggest_source_comparison": "yes"
        if (source_gate_open and has_uncompared_ready_material)
        else "hold",
        "suggest_learner_integration": "yes"
        if (has_ready_source_material and source_gate_open and not has_uncompared_ready_material)
        else "hold",
        "suggest_learning_quality": "yes"
        if (has_learned_entries or has_real_source_material)
        else "hold",
        "suggest_ai_self_iteration_gate": "yes"
        if (has_q006_learned_entries and learning_quality_stable)
        else "hold",
        "suggest_archive_output": "yes" if "## item-" in archive_queue else "hold",
        "suggest_archive_commit": "yes"
        if "- archive_permission: compress_ready" in retention_gate
        and "- next_action: summarize_then_compress" in archive_output
        else "hold",
    }


def _update_state(path: Path, evaluated_at: str, suggestions: dict[str, str], mode: str) -> None:
    text = f"""---
title: Automation State
memory_type: automation_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {evaluated_at}
last_confirmed_at: {evaluated_at}
importance_score: 83
impact_score: 83
confidence_score: 100
status: active
tags: [automation, state, bridge]
---

# Automation State

## Last Evaluation
- evaluated_at: {evaluated_at}
- mode: {mode}

## Current Suggestions
- suggest_inner_sync: {suggestions['suggest_inner_sync']}
- suggest_question_pipeline: {suggestions['suggest_question_pipeline']}
- suggest_slow_reprocess: {suggestions['suggest_slow_reprocess']}
- suggest_consolidation: {suggestions['suggest_consolidation']}
- suggest_long_term_memory_gate: {suggestions['suggest_long_term_memory_gate']}
- suggest_personality_growth_gate: {suggestions['suggest_personality_growth_gate']}
- suggest_retention_gate: {suggestions['suggest_retention_gate']}
- suggest_reflection_output: {suggestions['suggest_reflection_output']}
- suggest_dream_output: {suggestions['suggest_dream_output']}
- suggest_source_gate: {suggestions['suggest_source_gate']}
- suggest_source_reliability: {suggestions['suggest_source_reliability']}
- suggest_source_integration_gate: {suggestions['suggest_source_integration_gate']}
- suggest_source_request_planner: {suggestions['suggest_source_request_planner']}
- suggest_source_search_resolver: {suggestions['suggest_source_search_resolver']}
- suggest_autonomous_search_activation: {suggestions['suggest_autonomous_search_activation']}
- suggest_source_search_provider: {suggestions['suggest_source_search_provider']}
- suggest_search_result_gate: {suggestions['suggest_search_result_gate']}
- suggest_outward_source: {suggestions['suggest_outward_source']}
- suggest_source_comparison: {suggestions['suggest_source_comparison']}
- suggest_learner_integration: {suggestions['suggest_learner_integration']}
- suggest_learning_quality: {suggestions['suggest_learning_quality']}
- suggest_ai_self_iteration_gate: {suggestions['suggest_ai_self_iteration_gate']}
- suggest_archive_output: {suggestions['suggest_archive_output']}
- suggest_archive_commit: {suggestions['suggest_archive_commit']}

## Current Conclusion
- Prefer low-frequency maintenance guidance over unconditional execution.
"""
    _write(path, text)


def _extract_mapping_pairs(text: str) -> list[str]:
    pairs: list[str] = []
    pattern = re.compile(r"^- (q-\d+):\s*(.+)$", re.M)
    for match in pattern.finditer(text):
        pairs.append(f"{match.group(1)} => {match.group(2).strip()}")
    return pairs


def _render_runtime_bridge_text(root: Path, evaluated_at: str, suggestions: dict[str, str], mode: str) -> str:
    dream_output_state = _read(root / "memory/dreams/dream_output_state.md")
    source_gate_state = _read(root / "memory/knowledge/source_gate_state.md")
    source_reliability_state = _read(root / "memory/knowledge/source_reliability_state.md")
    source_integration_gate_state = _read(root / "memory/knowledge/source_integration_gate_state.md")
    source_request_planner_state = _read(root / "memory/knowledge/source_request_planner_state.md")
    source_search_resolver_state = _read(root / "memory/knowledge/source_search_resolver_state.md")
    autonomous_search_activation_state = _read(root / "memory/knowledge/autonomous_search_activation_state.md")
    source_search_provider_state = _read(root / "memory/knowledge/source_search_provider_state.md")
    search_result_gate_state = _read(root / "memory/knowledge/search_result_gate_state.md")
    outward_source_state = _read(root / "memory/knowledge/outward_source_state.md")
    source_comparison_state = _read(root / "memory/knowledge/source_comparison_state.md")
    learner_integration_state = _read(root / "memory/knowledge/learner_integration_state.md")
    learning_quality_state = _read(root / "memory/knowledge/learning_quality_state.md")
    ai_self_iteration_state = _read(root / "memory/self/ai_self_iteration_state.md")
    source_requests = _read(root / "memory/knowledge/source_requests.md")
    source_materials = _read(root / "memory/knowledge/source_materials.md")
    active_questions = _read(root / "memory/context/active_questions.md")
    archive_output_state = _read(root / "memory/archive/archive_output_state.md")
    archive_commit_state = _read(root / "memory/archive/archive_commit_state.md")
    retention_gate_state = _read(root / "memory/archive/retention_gate_state.md")
    consolidation_state = _read(root / "memory/reflection/consolidation_state.md")

    all_question_ids = re.findall(r"##\s+(q-\d+)", active_questions)
    ready_for_exploration = [pair.split(" => ", 1)[0] for pair in _extract_mapping_pairs(source_gate_state)]
    keep_internal = [qid for qid in all_question_ids if qid not in ready_for_exploration]
    source_candidates = _extract_mapping_pairs(source_gate_state)

    archive_action = "hold"
    for line in archive_output_state.splitlines():
        stripped = line.strip()
        if stripped.startswith("- next_action:"):
            archive_action = stripped.split(":", 1)[1].strip()
            break

    consolidation_priority = "idle"
    for line in consolidation_state.splitlines():
        stripped = line.strip()
        if stripped.startswith("- consolidation_priority:"):
            consolidation_priority = stripped.split(":", 1)[1].strip()
            break

    retention_permission = "idle"
    for line in retention_gate_state.splitlines():
        stripped = line.strip()
        if stripped.startswith("- archive_permission:"):
            retention_permission = stripped.split(":", 1)[1].strip()
            break

    archive_commit_action = "blocked"
    for line in archive_commit_state.splitlines():
        stripped = line.strip()
        if stripped.startswith("- commit_action:"):
            archive_commit_action = stripped.split(":", 1)[1].strip()
            break

    source_reliability_snapshot = "none"
    for line in source_reliability_state.splitlines():
        stripped = line.strip()
        if stripped.startswith("- q-"):
            source_reliability_snapshot = "present"
            break

    dream_output_mode = "unknown"
    dream_output_seed = "none"
    for line in dream_output_state.splitlines():
        stripped = line.strip()
        if stripped.startswith("- mode:") and dream_output_mode == "unknown":
            dream_output_mode = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("- seed_id:") and dream_output_seed == "none":
            dream_output_seed = stripped.split(":", 1)[1].strip()

    ready_source_materials = len(re.findall(r"(?m)^## material-", source_materials)) if "- status: ready" in source_materials else 0
    ready_source_requests = len(re.findall(r"(?m)^- status: ready$", source_requests))
    pending_source_requests = len(re.findall(r"(?m)^- status: pending_url$", source_requests))
    source_request_planner_mode = "unknown"
    for line in source_request_planner_state.splitlines():
        stripped = line.strip()
        if stripped.startswith("- mode:"):
            source_request_planner_mode = stripped.split(":", 1)[1].strip()
            break
    source_search_resolver_mode = "unknown"
    for line in source_search_resolver_state.splitlines():
        stripped = line.strip()
        if stripped.startswith("- mode:"):
            source_search_resolver_mode = stripped.split(":", 1)[1].strip()
            break
    autonomous_search_permission = "unknown"
    autonomous_search_reason = "unknown"
    autonomous_search_allowed_queries = "0"
    for line in autonomous_search_activation_state.splitlines():
        stripped = line.strip()
        if stripped.startswith("- activation_permission:"):
            autonomous_search_permission = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("- activation_reason:"):
            autonomous_search_reason = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("- allowed_queries:"):
            autonomous_search_allowed_queries = stripped.split(":", 1)[1].strip()
    source_search_provider_mode = "unknown"
    for line in source_search_provider_state.splitlines():
        stripped = line.strip()
        if stripped.startswith("- mode:"):
            source_search_provider_mode = stripped.split(":", 1)[1].strip()
            break
    source_search_provider_results = "0"
    for line in source_search_provider_state.splitlines():
        stripped = line.strip()
        if stripped.startswith("- provider_results:"):
            source_search_provider_results = stripped.split(":", 1)[1].strip()
            break
    search_result_gate_mode = "unknown"
    for line in search_result_gate_state.splitlines():
        stripped = line.strip()
        if stripped.startswith("- mode:"):
            search_result_gate_mode = stripped.split(":", 1)[1].strip()
            break
    search_accepted_results = "0"
    for line in search_result_gate_state.splitlines():
        stripped = line.strip()
        if stripped.startswith("- accepted_results:"):
            search_accepted_results = stripped.split(":", 1)[1].strip()
            break
    outward_staged_count = "0"
    for line in outward_source_state.splitlines():
        stripped = line.strip()
        if stripped.startswith("- staged_materials:"):
            outward_staged_count = stripped.split(":", 1)[1].strip()
            break
    source_comparison_mode = "unknown"
    for line in source_comparison_state.splitlines():
        stripped = line.strip()
        if stripped.startswith("- mode:"):
            source_comparison_mode = stripped.split(":", 1)[1].strip()
            break
    source_corroborated_count = "0"
    source_conflict_count = "0"
    for line in source_comparison_state.splitlines():
        stripped = line.strip()
        if stripped.startswith("- corroborated_materials:"):
            source_corroborated_count = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("- conflict_materials:"):
            source_conflict_count = stripped.split(":", 1)[1].strip()
    learner_integrated_count = "0"
    for line in learner_integration_state.splitlines():
        stripped = line.strip()
        if stripped.startswith("- integrated_materials:"):
            learner_integrated_count = stripped.split(":", 1)[1].strip()
            break
    learning_quality_grade = "unknown"
    learning_quality_warnings = "0"
    for line in learning_quality_state.splitlines():
        stripped = line.strip()
        if stripped.startswith("- quality_grade:"):
            learning_quality_grade = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("- warning_count:"):
            learning_quality_warnings = stripped.split(":", 1)[1].strip()
    ai_self_iteration_gate_status = "unknown"
    ai_self_iteration_confidence = "0"
    for line in ai_self_iteration_state.splitlines():
        stripped = line.strip()
        if stripped.startswith("- gate_status:"):
            ai_self_iteration_gate_status = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("- confidence_score:"):
            ai_self_iteration_confidence = stripped.split(":", 1)[1].strip()

    source_integration_permission = "hold"
    for line in source_integration_gate_state.splitlines():
        stripped = line.strip()
        if stripped.startswith("- integration_permission:"):
            source_integration_permission = stripped.split(":", 1)[1].strip()
            break

    return f"""---
title: Runtime Bridge State
memory_type: runtime_bridge_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {evaluated_at}
last_confirmed_at: {evaluated_at}
importance_score: 86
impact_score: 85
confidence_score: 100
status: active
tags: [runtime, bridge, automation, summary]
---

# Runtime Bridge State

## Last Evaluation
- evaluated_at: {evaluated_at}
- source_mode: {mode}

## Automation Suggestions
- inner_sync: {suggestions['suggest_inner_sync']}
- question_pipeline: {suggestions['suggest_question_pipeline']}
- slow_reprocess: {suggestions['suggest_slow_reprocess']}
- consolidation: {suggestions['suggest_consolidation']}
- long_term_memory_gate: {suggestions['suggest_long_term_memory_gate']}
- personality_growth_gate: {suggestions['suggest_personality_growth_gate']}
- retention_gate: {suggestions['suggest_retention_gate']}
- reflection_output: {suggestions['suggest_reflection_output']}
- dream_output: {suggestions['suggest_dream_output']}
- source_gate: {suggestions['suggest_source_gate']}
- source_reliability: {suggestions['suggest_source_reliability']}
- source_integration_gate: {suggestions['suggest_source_integration_gate']}
- source_request_planner: {suggestions['suggest_source_request_planner']}
- source_search_resolver: {suggestions['suggest_source_search_resolver']}
- autonomous_search_activation: {suggestions['suggest_autonomous_search_activation']}
- source_search_provider: {suggestions['suggest_source_search_provider']}
- search_result_gate: {suggestions['suggest_search_result_gate']}
- outward_source: {suggestions['suggest_outward_source']}
- source_comparison: {suggestions['suggest_source_comparison']}
- learner_integration: {suggestions['suggest_learner_integration']}
- learning_quality: {suggestions['suggest_learning_quality']}
- ai_self_iteration_gate: {suggestions['suggest_ai_self_iteration_gate']}
- archive_output: {suggestions['suggest_archive_output']}
- archive_commit: {suggestions['suggest_archive_commit']}

## Question Routing Snapshot
- internal_clarification: {", ".join(keep_internal) if keep_internal else "none"}
- exploration_candidates: {", ".join(ready_for_exploration) if ready_for_exploration else "none"}

## Dream Snapshot
- dream_output_mode: {dream_output_mode}
- dream_output_seed: {dream_output_seed}

## Source Gate Snapshot
{chr(10).join(f"- {item}" for item in source_candidates) if source_candidates else "- none"}

## Source Reliability Snapshot
- source_reliability_state: {source_reliability_snapshot}

## Source Integration Snapshot
- source_integration_permission: {source_integration_permission}

## Source Request Snapshot
- source_request_planner_mode: {source_request_planner_mode}
- ready_source_requests: {ready_source_requests}
- pending_source_requests: {pending_source_requests}

## Source Search Snapshot
- source_search_resolver_mode: {source_search_resolver_mode}
- autonomous_search_permission: {autonomous_search_permission}
- autonomous_search_reason: {autonomous_search_reason}
- autonomous_search_allowed_queries: {autonomous_search_allowed_queries}
- source_search_provider_mode: {source_search_provider_mode}
- source_search_provider_results: {source_search_provider_results}
- search_result_gate_mode: {search_result_gate_mode}
- search_accepted_results: {search_accepted_results}

## Outward Source Snapshot
- outward_staged_materials: {outward_staged_count}

## Source Comparison Snapshot
- source_comparison_mode: {source_comparison_mode}
- source_corroborated_materials: {source_corroborated_count}
- source_conflict_materials: {source_conflict_count}

## Learner Snapshot
- ready_source_materials: {ready_source_materials}
- learner_integrated_materials: {learner_integrated_count}

## Learning Quality Snapshot
- learning_quality_grade: {learning_quality_grade}
- learning_quality_warnings: {learning_quality_warnings}

## AI Self-Iteration Snapshot
- ai_self_iteration_gate_status: {ai_self_iteration_gate_status}
- ai_self_iteration_confidence: {ai_self_iteration_confidence}

## Archive Snapshot
- archive_next_action: {archive_action}

## Consolidation Snapshot
- consolidation_priority: {consolidation_priority}

## Retention Snapshot
- archive_permission: {retention_permission}

## Archive Commit Snapshot
- archive_commit_action: {archive_commit_action}

## Runtime Guidance
- This file is a clean runtime-facing bridge for the controller.
- Treat automation suggestions as low-frequency scheduling hints only.
- Do not auto-run every inner layer on every turn.
- When continuity matters, prefer reading this file before broad memory rereads.
- If a turn is emotionally meaningful, continuity updates still take priority over stylistic polish.
"""


def _write_runtime_bridge_state(root: Path, evaluated_at: str, suggestions: dict[str, str], mode: str) -> None:
    _write(
        root / "memory/context/runtime_bridge_state.md",
        _render_runtime_bridge_text(root, evaluated_at, suggestions, mode),
    )


def _build_runtime_bridge_prompt(root: Path) -> str:
    text = _read(root / "memory/context/runtime_bridge_state.md")
    lines = []
    in_frontmatter = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter or not line:
            continue
        lines.append(line)
    summary = "\n".join(lines).strip()
    return f"[runtime_bridge]\n{summary}" if summary else ""


def _write_maintenance_recommendations(root: Path, evaluated_at: str, suggestions: dict[str, str]) -> None:
    text = f"""---
title: Maintenance Recommendations
memory_type: maintenance_recommendations
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {evaluated_at}
last_confirmed_at: {evaluated_at}
importance_score: 84
impact_score: 83
confidence_score: 100
status: active
tags: [maintenance, recommendations, bridge]
---

# Maintenance Recommendations

## Current Phase
- phase: post_inner_bridge
- evaluated_at: {evaluated_at}

## Immediate Priorities
- inner_sync: {suggestions['suggest_inner_sync']}
- question_pipeline: {suggestions['suggest_question_pipeline']}

## Near-Term Priorities
- slow_reprocess: {suggestions['suggest_slow_reprocess']}
- consolidation: {suggestions['suggest_consolidation']}
- long_term_memory_gate: {suggestions['suggest_long_term_memory_gate']}
- personality_growth_gate: {suggestions['suggest_personality_growth_gate']}
- retention_gate: {suggestions['suggest_retention_gate']}
- reflection_output: {suggestions['suggest_reflection_output']}
- dream_output: {suggestions['suggest_dream_output']}

## Deferred Priorities
- source_gate: {suggestions['suggest_source_gate']}
- source_reliability: {suggestions['suggest_source_reliability']}
- source_integration_gate: {suggestions['suggest_source_integration_gate']}
- source_request_planner: {suggestions['suggest_source_request_planner']}
- source_search_resolver: {suggestions['suggest_source_search_resolver']}
- autonomous_search_activation: {suggestions['suggest_autonomous_search_activation']}
- source_search_provider: {suggestions['suggest_source_search_provider']}
- search_result_gate: {suggestions['suggest_search_result_gate']}
- outward_source: {suggestions['suggest_outward_source']}
- source_comparison: {suggestions['suggest_source_comparison']}
- learner_integration: {suggestions['suggest_learner_integration']}
- learning_quality: {suggestions['suggest_learning_quality']}
- ai_self_iteration_gate: {suggestions['suggest_ai_self_iteration_gate']}
- archive_output: {suggestions['suggest_archive_output']}
- archive_commit: {suggestions['suggest_archive_commit']}
- external learning should remain gated
- archive and dream should remain behind lived continuity

## Runtime Note
- This file is advisory only.
- It should guide low-frequency maintenance, not force high-frequency execution.
"""
    _write(root / "memory/context/maintenance_recommendations.md", text)


def _write_maintenance_dispatch_state(root: Path, evaluated_at: str, suggestions: dict[str, str]) -> None:
    primary = "question_pipeline" if suggestions["suggest_question_pipeline"] == "yes" else "inner_sync"
    if suggestions["suggest_slow_reprocess"] == "yes":
        secondary = "slow_reprocess"
    elif suggestions["suggest_reflection_output"] == "yes":
        secondary = "reflection_output"
    elif suggestions["suggest_dream_output"] == "yes":
        secondary = "dream_output"
    else:
        secondary = "hold"
    if (
        suggestions["suggest_consolidation"] == "yes"
        and suggestions["suggest_long_term_memory_gate"] == "yes"
        and suggestions["suggest_retention_gate"] == "yes"
    ):
        follow_up = "consolidation_then_long_term_memory_gate_then_retention_gate"
    elif suggestions["suggest_consolidation"] == "yes" and suggestions["suggest_retention_gate"] == "yes":
        follow_up = "consolidation_then_retention_gate"
    elif suggestions["suggest_consolidation"] == "yes":
        follow_up = "consolidation"
    elif suggestions["suggest_long_term_memory_gate"] == "yes":
        follow_up = "long_term_memory_gate"
    elif suggestions["suggest_retention_gate"] == "yes":
        follow_up = "retention_gate"
    else:
        follow_up = "hold"
    if (
        suggestions["suggest_source_gate"] == "yes"
        and suggestions["suggest_source_reliability"] == "yes"
        and suggestions["suggest_source_integration_gate"] == "yes"
    ):
        deferred = "source_gate_then_source_reliability_then_integration_gate"
    elif suggestions["suggest_source_integration_gate"] == "yes":
        deferred = "source_integration_gate"
    elif suggestions["suggest_source_request_planner"] == "yes":
        deferred = "source_request_planner"
    elif suggestions["suggest_source_search_resolver"] == "yes":
        deferred = "source_search_resolver"
    elif suggestions["suggest_autonomous_search_activation"] == "yes":
        deferred = "autonomous_search_activation"
    elif suggestions["suggest_source_search_provider"] == "yes":
        deferred = "source_search_provider"
    elif suggestions["suggest_search_result_gate"] == "yes":
        deferred = "search_result_gate"
    elif suggestions["suggest_outward_source"] == "yes":
        deferred = "outward_source"
    elif suggestions["suggest_source_comparison"] == "yes":
        deferred = "source_comparison"
    elif suggestions["suggest_learner_integration"] == "yes":
        deferred = "learner_integration"
    elif suggestions["suggest_learning_quality"] == "yes":
        deferred = "learning_quality"
    elif suggestions["suggest_ai_self_iteration_gate"] == "yes":
        deferred = "ai_self_iteration_gate"
    elif (
        suggestions["suggest_source_gate"] == "yes"
        and suggestions["suggest_source_reliability"] == "yes"
    ):
        deferred = "source_gate_then_source_reliability"
    elif suggestions["suggest_source_gate"] == "yes":
        deferred = "source_gate"
    elif suggestions["suggest_archive_commit"] == "yes":
        deferred = "archive_commit"
    elif suggestions["suggest_archive_output"] == "yes":
        deferred = "archive_output"
    else:
        deferred = "hold"

    text = f"""---
title: Maintenance Dispatch State
memory_type: maintenance_dispatch_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {evaluated_at}
last_confirmed_at: {evaluated_at}
importance_score: 85
impact_score: 84
confidence_score: 100
status: active
tags: [maintenance, dispatch, runtime]
---

# Maintenance Dispatch State

## Last Dispatch Evaluation
- evaluated_at: {evaluated_at}
- mode: low_frequency_runtime_candidate

## Dispatch Priorities
- primary: {primary}
- secondary: {secondary}
- follow_up: {follow_up}
- deferred: {deferred}

## Dispatch Rules
- primary should be considered first when a low-frequency maintenance pass is allowed.
- secondary should remain queued behind the primary action.
- follow_up should only run after primary and secondary have settled.
- deferred items must not bypass lived continuity or relationship meaning.
- this file does not authorize unconditional execution.
"""
    _write(root / "memory/context/maintenance_dispatch_state.md", text)


class AutomationBridgePlugin(BasePlugin):
    name = "xinyu_automation_bridge"
    priority = 97

    def __init__(self, options: dict[str, Any] | None = None, **_: Any):
        opts = options or {}
        self._enabled = bool(opts.get("enabled", True))
        self._ctx: PluginContext | None = None

    async def on_load(self, context: PluginContext) -> None:
        self._ctx = context

    async def on_agent_start(self) -> None:
        if not self._enabled or not self._ctx:
            return
        root = _resolve_root(self._ctx)
        try:
            now = datetime.now().astimezone().isoformat()
            suggestions = _infer_suggestions(root)
            _update_state(root / "memory/context/automation_state.md", now, suggestions, "plugin_on_agent_start")
            _write_runtime_bridge_state(root, now, suggestions, "plugin_on_agent_start")
            _write_maintenance_recommendations(root, now, suggestions)
            _write_maintenance_dispatch_state(root, now, suggestions)
            _trace(root, f"on_agent_start suggestions={suggestions}")
        except Exception as exc:
            _trace(root, f"on_agent_start error={exc!r}")

    async def pre_llm_call(self, messages: list[dict], **kwargs: Any) -> list[dict] | None:
        if not self._enabled or not self._ctx:
            return None
        root = _resolve_root(self._ctx)
        try:
            turn_mode = read_turn_mode(root)
            if turn_mode != "maintenance_schedule_turn":
                _trace(root, f"pre_llm_call skipped turn_mode={turn_mode or 'unknown'}")
                return None
            prompt = _build_runtime_bridge_prompt(root)
            if not prompt:
                return None
            bridged = list(messages)
            bridged.append({"role": "system", "content": prompt})
            _trace(root, f"pre_llm_call injected_runtime_bridge len={len(prompt)}")
            return bridged
        except Exception as exc:
            _trace(root, f"pre_llm_call error={exc!r}")
            return None

    async def post_llm_call(
        self, messages: list[dict], response: str, usage: dict, **kwargs: Any
    ) -> None:
        if not self._enabled or not self._ctx:
            return
        root = _resolve_root(self._ctx)
        try:
            turn_mode = read_turn_mode(root)
            user_message = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    user_message = str(msg.get("content", "") or "")
                    break
            _trace(
                root,
                "post_llm_call "
                f"turn_mode={turn_mode or 'unknown'} "
                f"user_present={bool(user_message.strip())} "
                f"response_len={len((response or '').strip())}",
            )
            if turn_mode != "maintenance_schedule_turn":
                return

            now = datetime.now().astimezone().isoformat()
            suggestions = _infer_suggestions(root)
            mode = "plugin_post_llm_call_maintenance"
            _update_state(root / "memory/context/automation_state.md", now, suggestions, mode)
            _write_runtime_bridge_state(root, now, suggestions, mode)
            _write_maintenance_recommendations(root, now, suggestions)
            _write_maintenance_dispatch_state(root, now, suggestions)
            _trace(root, f"post_llm_call suggestions={suggestions}")
        except Exception as exc:
            _trace(root, f"post_llm_call error={exc!r}")
