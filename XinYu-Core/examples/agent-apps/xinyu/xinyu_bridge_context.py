from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from xinyu_bridge_prompt_context_signature_store import prompt_context_file_signature
from xinyu_storage_paths import knowledge_ref


PROMPT_CONTEXT_SIGNATURE_FILES: tuple[str, ...] = (
    "config.yaml",
    "prompts/system.md",
    "prompts/output.md",
    "prompts/live_voice_card.md",
    "memory/self/system_prompt_memory.md",
    "memory/self/core.md",
    "memory/self/personality_profile.md",
    "memory/context/life_month_slots.md",
    "memory/context/current_life_month_context.md",
    "memory/self/mind_loop_policy.md",
    "memory/self/mind_loop_state.md",
    "memory/self/voice_profile_zh.md",
    "memory/self/narrative.md",
    "memory/emotions/taxonomy.md",
    "memory/emotions/current_state.md",
    "memory/relationships/vector_model.md",
    "memory/relationships/index.md",
    "memory/people/index.md",
    "memory/people/owner.md",
    "memory/context/time_anchor.md",
    "memory/context/real_world_anchor_policy.md",
    "memory/context/real_life_input_adapter_policy.md",
    "memory/context/watch_sources.md",
    "memory/context/watched_source_state.md",
    "memory/creative/planning/novel_profile.md",
    "memory/creative/planning/novel_state.md",
    "memory/context/memory_self_review_state.md",
    "memory/context/continuity_handoff_state.md",
    "memory/context/uncertainty_pause_state.md",
    "memory/context/self_code_approval_state.md",
    "memory/context/initiative_policy.md",
    "memory/context/initiative_state.md",
    "memory/context/owner_permission_grants.md",
    "memory/context/codex_delegation_policy.md",
    "memory/context/runtime_bridge_state.md",
    "memory/context/maintenance_recommendations.md",
    "memory/context/maintenance_dispatch_state.md",
    "memory/context/inner_cycle_state.md",
    "memory/context/maintenance_schedule_state.md",
    "memory/dreams/dream_weight_state.md",
    "memory/archive/long_term_memory_gate_state.md",
    "memory/self/personality_change_state.md",
    "memory/self/personality_self_review_state.md",
    "memory/self/ai_self_iteration_state.md",
    "memory/self/ai_self_iteration_review_state.md",
    "memory/self/expression_self_learning_state.md",
    "memory/self/learning_closed_loop_state.md",
    "memory/self/learning_closed_loop_cases.md",
    knowledge_ref("ai_domain.md"),
    knowledge_ref("social_inquiry_policy.md"),
)


def prompt_context_signature(xinyu_dir: Path, rel_paths: Iterable[str]) -> str:
    parts: list[str] = []
    for rel in rel_paths:
        signature = prompt_context_file_signature(xinyu_dir / rel)
        if signature is None:
            parts.append(f"{rel}:missing")
            continue
        parts.append(f"{rel}:{signature.mtime_ns}:{signature.size}")
    return "|".join(parts)


def runtime_session_prompt_signature(runtime: Any) -> str:
    return prompt_context_signature(runtime.xinyu_dir, PROMPT_CONTEXT_SIGNATURE_FILES)
