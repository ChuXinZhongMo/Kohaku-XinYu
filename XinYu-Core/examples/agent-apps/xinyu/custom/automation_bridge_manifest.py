"""Automation bridge manifest for Xinyu inner framework."""

from __future__ import annotations

AUTOMATION_BRIDGE_INPUTS: list[str] = [
    "memory/context/runtime_rhythm.md",
    "memory/context/maintenance_plan.md",
    "memory/context/maintenance_targets.md",
    "memory/context/inner_cycle_state.md",
    "memory/context/inner_sync_state.md",
    "memory/context/question_pipeline_state.md",
    "memory/reflection/reprocessing_state.md",
    "memory/reflection/reflection_output_state.md",
    "memory/knowledge/source_gate_state.md",
]

AUTOMATION_BRIDGE_OUTPUTS: list[str] = [
    "memory/context/automation_policy.md",
    "memory/context/automation_state.md",
]
