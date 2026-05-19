"""Archived manifest for XinYu memory event sourcing sidecars."""

MEMORY_EVENT_SOURCING_SOURCES: list[str] = [
    "memory/events/raw_events.jsonl",
    "memory/events/structured_events.jsonl",
    "memory/events/atomic_claims.jsonl",
    "memory/events/summary_views.jsonl",
]

MEMORY_EVENT_SOURCING_TARGETS: list[str] = [
    "memory/events/consistency_gate_state.md",
    "memory/events/summary_coverage_state.md",
]

MEMORY_EVENT_SOURCING_POLICY_FILES: list[str] = [
    "memory/context/memory_event_sourcing_policy.md",
    "project-plans/MEMORY-EVENT-SOURCING-CONSISTENCY-PLAN.md",
]
