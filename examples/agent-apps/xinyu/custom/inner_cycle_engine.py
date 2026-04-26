from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _extract_value(text: str, field: str) -> str:
    pattern = re.compile(rf"^- {re.escape(field)}:\s*(.+)$", re.M)
    match = pattern.search(text)
    return match.group(1).strip() if match else "unknown"


def _extract_frontmatter_value(text: str, field: str) -> str:
    pattern = re.compile(rf"^{re.escape(field)}:\s*(.+)$", re.M)
    match = pattern.search(text)
    return match.group(1).strip() if match else "unknown"


def _extract_snapshot_line(text: str, field: str) -> str:
    pattern = re.compile(rf"^- {re.escape(field)}:\s*(.+)$", re.M)
    match = pattern.search(text)
    return match.group(1).strip() if match else "none"


def _extract_top_topic(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- ") and (
            "topic:" in stripped or "theme:" in stripped or "target:" in stripped
        ):
            return stripped.split(":", 1)[1].strip()
    return "none"


def _extract_bullets_after_heading(text: str, heading: str) -> str:
    pattern = rf"({re.escape(heading)}\n)(.*?)(?=\n## |\n# |\Z)"
    match = re.search(pattern, text, flags=re.S)
    if not match:
        return "none"
    items = [
        line.removeprefix("- ").strip()
        for line in match.group(2).splitlines()
        if line.strip().startswith("- ")
    ]
    items = [item for item in items if item and item != "none"]
    return ", ".join(items) if items else "none"


def update_inner_cycle_state(
    path: Path, checked_at: str, mode: str, cycle_summary: dict[str, str]
) -> None:
    text = f"""---
title: Inner Cycle State
memory_type: inner_cycle_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {checked_at}
last_confirmed_at: {checked_at}
importance_score: 84
impact_score: 85
confidence_score: 100
status: active
tags: [inner, cycle, state]
---

# Inner Cycle State

## Latest Cycle
- checked_at: {checked_at}
- mode: {mode}

## Current Order
- sync
- question_pipeline
- initiative_loop
- slow_reprocess
- reflection_output
- dream_output
- source_gate
- source_reliability
- source_integration_gate
- source_request_planner
- source_search_resolver
- autonomous_search_activation
- source_search_provider
- search_result_gate
- outward_source
- source_comparison
- learner_integration
- learning_quality
- ai_self_iteration_gate
- consolidation
- long_term_memory_gate
- retention_gate
- archive_output
- archive_commit
- personality_growth_gate

## Layer Snapshot
- inner_sync_updated_at: {cycle_summary['inner_sync_updated_at']}
- question_pipeline_mode: {cycle_summary['question_pipeline_mode']}
- initiative_loop_mode: {cycle_summary['initiative_loop_mode']}
- slow_reprocess_mode: {cycle_summary['slow_reprocess_mode']}
- consolidation_mode: {cycle_summary['consolidation_mode']}
- long_term_memory_gate_mode: {cycle_summary['long_term_memory_gate_mode']}
- retention_gate_mode: {cycle_summary['retention_gate_mode']}
- reflection_output_mode: {cycle_summary['reflection_output_mode']}
- dream_output_mode: {cycle_summary['dream_output_mode']}
- dream_weight_mode: {cycle_summary['dream_weight_mode']}
- source_gate_mode: {cycle_summary['source_gate_mode']}
- source_reliability_mode: {cycle_summary['source_reliability_mode']}
- source_integration_gate_mode: {cycle_summary['source_integration_gate_mode']}
- source_request_planner_mode: {cycle_summary['source_request_planner_mode']}
- source_search_resolver_mode: {cycle_summary['source_search_resolver_mode']}
- autonomous_search_activation_mode: {cycle_summary['autonomous_search_activation_mode']}
- source_search_provider_mode: {cycle_summary['source_search_provider_mode']}
- search_result_gate_mode: {cycle_summary['search_result_gate_mode']}
- outward_source_mode: {cycle_summary['outward_source_mode']}
- source_comparison_mode: {cycle_summary['source_comparison_mode']}
- learner_integration_mode: {cycle_summary['learner_integration_mode']}
- learning_quality_mode: {cycle_summary['learning_quality_mode']}
- archive_output_mode: {cycle_summary['archive_output_mode']}
- archive_commit_mode: {cycle_summary['archive_commit_mode']}
- personality_growth_gate_mode: {cycle_summary['personality_growth_gate_mode']}

## Current Summary
- internal_clarification: {cycle_summary['internal_clarification']}
- exploration_candidates: {cycle_summary['exploration_candidates']}
- initiative_decision: {cycle_summary['initiative_decision']}
- initiative_question_budget: {cycle_summary['initiative_question_budget']}
- initiative_external_search_permission: {cycle_summary['initiative_external_search_permission']}
- source_reliability_ready: {cycle_summary['source_reliability_ready']}
- source_integration_permission: {cycle_summary['source_integration_permission']}
- source_ready_requests: {cycle_summary['source_ready_requests']}
- source_pending_url_requests: {cycle_summary['source_pending_url_requests']}
- source_search_resolved_results: {cycle_summary['source_search_resolved_results']}
- autonomous_search_permission: {cycle_summary['autonomous_search_permission']}
- autonomous_search_allowed_queries: {cycle_summary['autonomous_search_allowed_queries']}
- source_search_provider_results: {cycle_summary['source_search_provider_results']}
- search_accepted_results: {cycle_summary['search_accepted_results']}
- outward_staged_materials: {cycle_summary['outward_staged_materials']}
- source_corroborated_materials: {cycle_summary['source_corroborated_materials']}
- source_conflict_materials: {cycle_summary['source_conflict_materials']}
- learner_integrated_materials: {cycle_summary['learner_integrated_materials']}
- learner_total_integrated_materials: {cycle_summary['learner_total_integrated_materials']}
- learner_pending_ready_materials: {cycle_summary['learner_pending_ready_materials']}
- learning_quality_grade: {cycle_summary['learning_quality_grade']}
- learning_quality_warnings: {cycle_summary['learning_quality_warnings']}
- ai_self_iteration_gate_status: {cycle_summary['ai_self_iteration_gate_status']}
- ai_self_iteration_confidence: {cycle_summary['ai_self_iteration_confidence']}
- top_reflection_topic: {cycle_summary['top_reflection_topic']}
- dream_output_seed: {cycle_summary['dream_output_seed']}
- dream_weight_delta: {cycle_summary['dream_weight_delta']}
- dream_weight_effect: {cycle_summary['dream_weight_effect']}
- consolidation_priority: {cycle_summary['consolidation_priority']}
- long_term_memory_action: {cycle_summary['long_term_memory_action']}
- long_term_forget_permission: {cycle_summary['long_term_forget_permission']}
- archive_permission: {cycle_summary['archive_permission']}
- archive_next_action: {cycle_summary['archive_next_action']}
- archive_commit_action: {cycle_summary['archive_commit_action']}
- personality_gate_decision: {cycle_summary['personality_gate_decision']}
- personality_change_pressure: {cycle_summary['personality_change_pressure']}

## Notes
- This file summarizes the whole inner cycle and does not authorize high-frequency execution.
- Runtime should treat it as a structural snapshot, not as lived memory itself.
"""
    write_text(path, text)


def run_inner_cycle_summary(
    root: Path,
    checked_at: str | None = None,
    mode: str = "runtime_inner_cycle_summary",
) -> dict[str, str]:
    checked_at = checked_at or datetime.now().astimezone().isoformat()

    inner_sync = read_text(root / "memory/context/inner_sync_state.md")
    question_pipeline = read_text(root / "memory/context/question_pipeline_state.md")
    initiative = read_text(root / "memory/context/initiative_state.md")
    reflection_queue = read_text(root / "memory/reflection/reflection_queue.md")
    reprocessing = read_text(root / "memory/reflection/reprocessing_state.md")
    reflection_output = read_text(root / "memory/reflection/reflection_output_state.md")
    dream_output = read_text(root / "memory/dreams/dream_output_state.md")
    dream_weight = read_text(root / "memory/dreams/dream_weight_state.md")
    consolidation = read_text(root / "memory/reflection/consolidation_state.md")
    long_term_memory_gate = read_text(root / "memory/archive/long_term_memory_gate_state.md")
    personality_change = read_text(root / "memory/self/personality_change_state.md")
    source_gate = read_text(root / "memory/knowledge/source_gate_state.md")
    source_reliability = read_text(root / "memory/knowledge/source_reliability_state.md")
    source_integration_gate = read_text(root / "memory/knowledge/source_integration_gate_state.md")
    source_request_planner = read_text(root / "memory/knowledge/source_request_planner_state.md")
    source_search_resolver = read_text(root / "memory/knowledge/source_search_resolver_state.md")
    autonomous_search_activation = read_text(root / "memory/knowledge/autonomous_search_activation_state.md")
    source_search_provider = read_text(root / "memory/knowledge/source_search_provider_state.md")
    search_result_gate = read_text(root / "memory/knowledge/search_result_gate_state.md")
    outward_source = read_text(root / "memory/knowledge/outward_source_state.md")
    source_comparison = read_text(root / "memory/knowledge/source_comparison_state.md")
    learner_integration = read_text(root / "memory/knowledge/learner_integration_state.md")
    learning_quality = read_text(root / "memory/knowledge/learning_quality_state.md")
    ai_self_iteration = read_text(root / "memory/self/ai_self_iteration_state.md")
    retention_gate = read_text(root / "memory/archive/retention_gate_state.md")
    archive_output = read_text(root / "memory/archive/archive_output_state.md")
    archive_commit = read_text(root / "memory/archive/archive_commit_state.md")
    runtime_bridge = read_text(root / "memory/context/runtime_bridge_state.md")

    cycle_summary = {
        "inner_sync_updated_at": _extract_frontmatter_value(inner_sync, "updated_at"),
        "question_pipeline_mode": _extract_value(question_pipeline, "mode"),
        "initiative_loop_mode": _extract_value(initiative, "mode"),
        "slow_reprocess_mode": _extract_value(reprocessing, "mode"),
        "consolidation_mode": _extract_value(consolidation, "mode"),
        "long_term_memory_gate_mode": _extract_value(long_term_memory_gate, "mode"),
        "retention_gate_mode": _extract_value(retention_gate, "mode"),
        "reflection_output_mode": _extract_value(reflection_output, "mode"),
        "dream_output_mode": _extract_value(dream_output, "mode"),
        "dream_weight_mode": _extract_value(dream_weight, "mode"),
        "source_gate_mode": _extract_value(source_gate, "mode"),
        "source_reliability_mode": _extract_value(source_reliability, "mode"),
        "source_integration_gate_mode": _extract_value(source_integration_gate, "mode"),
        "source_request_planner_mode": _extract_value(source_request_planner, "mode"),
        "source_search_resolver_mode": _extract_value(source_search_resolver, "mode"),
        "autonomous_search_activation_mode": _extract_value(autonomous_search_activation, "mode"),
        "source_search_provider_mode": _extract_value(source_search_provider, "mode"),
        "search_result_gate_mode": _extract_value(search_result_gate, "mode"),
        "outward_source_mode": _extract_value(outward_source, "mode"),
        "source_comparison_mode": _extract_value(source_comparison, "mode"),
        "learner_integration_mode": _extract_value(learner_integration, "mode"),
        "learning_quality_mode": _extract_value(learning_quality, "mode"),
        "ai_self_iteration_gate_status": _extract_value(ai_self_iteration, "gate_status"),
        "ai_self_iteration_confidence": _extract_value(ai_self_iteration, "confidence_score"),
        "archive_output_mode": _extract_value(archive_output, "mode"),
        "archive_commit_mode": _extract_value(archive_commit, "mode"),
        "personality_growth_gate_mode": _extract_value(personality_change, "mode"),
        "internal_clarification": _extract_bullets_after_heading(
            question_pipeline, "## 当前内部澄清优先问题"
        ),
        "exploration_candidates": _extract_bullets_after_heading(
            question_pipeline, "## 当前外探候选问题"
        ),
        "initiative_decision": _extract_value(initiative, "decision"),
        "initiative_question_budget": _extract_value(initiative, "question_budget"),
        "initiative_external_search_permission": _extract_value(
            initiative, "external_search_permission"
        ),
        "source_reliability_ready": _extract_value(source_integration_gate, "reliability_ready"),
        "source_integration_permission": _extract_value(source_integration_gate, "integration_permission"),
        "source_ready_requests": _extract_value(source_request_planner, "ready_requests"),
        "source_pending_url_requests": _extract_value(source_request_planner, "pending_url_requests"),
        "source_search_resolved_results": _extract_value(source_search_resolver, "resolved_results"),
        "autonomous_search_permission": _extract_value(autonomous_search_activation, "activation_permission"),
        "autonomous_search_allowed_queries": _extract_value(autonomous_search_activation, "allowed_queries"),
        "source_search_provider_results": _extract_value(source_search_provider, "provider_results"),
        "search_accepted_results": _extract_value(search_result_gate, "accepted_results"),
        "outward_staged_materials": _extract_value(outward_source, "staged_materials"),
        "source_corroborated_materials": _extract_value(source_comparison, "corroborated_materials"),
        "source_conflict_materials": _extract_value(source_comparison, "conflict_materials"),
        "learner_integrated_materials": _extract_value(learner_integration, "integrated_materials"),
        "learner_total_integrated_materials": _extract_value(learner_integration, "total_integrated_materials"),
        "learner_pending_ready_materials": _extract_value(learner_integration, "pending_ready_materials"),
        "learning_quality_grade": _extract_value(learning_quality, "quality_grade"),
        "learning_quality_warnings": _extract_value(learning_quality, "warning_count"),
        "top_reflection_topic": _extract_top_topic(reflection_queue),
        "dream_output_seed": _extract_value(dream_output, "seed_id"),
        "dream_weight_delta": _extract_value(dream_weight, "weight_delta"),
        "dream_weight_effect": _extract_value(dream_weight, "weight_effect"),
        "archive_next_action": _extract_value(archive_output, "next_action"),
        "consolidation_priority": _extract_value(
            consolidation, "consolidation_priority"
        ),
        "long_term_memory_action": _extract_value(long_term_memory_gate, "memory_action"),
        "long_term_forget_permission": _extract_value(long_term_memory_gate, "forget_permission"),
        "archive_permission": _extract_value(retention_gate, "archive_permission"),
        "personality_gate_decision": _extract_value(personality_change, "gate_decision"),
        "personality_change_pressure": _extract_value(personality_change, "change_pressure"),
        }
    cycle_summary["archive_commit_action"] = _extract_value(
        archive_commit, "commit_action"
    )

    update_inner_cycle_state(
        root / "memory/context/inner_cycle_state.md",
        checked_at,
        mode,
        cycle_summary,
    )
    cycle_summary["checked_at"] = checked_at
    return cycle_summary
