from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RuntimeContextFile:
    rel_path: str
    limit: int
    layer: str


@dataclass(frozen=True, slots=True)
class RuntimeContextSnapshot:
    life_month_context: str
    personality_evolution_state: str
    private_thought_state: str
    self_model_state: str
    memory_weight_state: str
    thought_seeds: str
    continuity_handoff_state: str = ""
    uncertainty_pause_state: str = ""
    async_exploration_state: str = ""
    self_code_approval_state: str = ""
    watched_source_state: str = ""
    memory_self_review_state: str = ""


RENDERER_CONTEXT_FILES: tuple[RuntimeContextFile, ...] = (
    RuntimeContextFile("prompts/live_voice_card.md", 1400, "concept_seed"),
    RuntimeContextFile("memory/self/core.md", 2200, "xinyu_concept"),
    RuntimeContextFile("memory/self/personality_profile.md", 2600, "xinyu_concept"),
    RuntimeContextFile("memory/self/voice_profile_zh.md", 2200, "voice"),
    RuntimeContextFile("memory/self/voice_calibration_log.md", 1800, "voice"),
    RuntimeContextFile("memory/self/narrative.md", 2600, "self_narrative"),
    RuntimeContextFile("memory/people/owner.md", 2800, "owner_relation"),
    RuntimeContextFile("memory/relationships/index.md", 1800, "relationship"),
    RuntimeContextFile("memory/emotions/current_state.md", 1600, "emotion"),
    RuntimeContextFile("memory/context/time_anchor.md", 1000, "time"),
    RuntimeContextFile("memory/context/current_life_month_context.md", 1600, "life_context"),
    RuntimeContextFile("memory/context/persona_surface_state.md", 1800, "recent_surface"),
    RuntimeContextFile("memory/context/runtime_self_presence.md", 1200, "runtime_presence"),
    RuntimeContextFile("memory/context/watched_source_state.md", 1600, "watched_source"),
    RuntimeContextFile("memory/context/memory_self_review_state.md", 1400, "memory_self_review"),
    RuntimeContextFile("memory/context/continuity_handoff_state.md", 1600, "continuity_handoff"),
    RuntimeContextFile("memory/context/uncertainty_pause_state.md", 1100, "uncertainty_pause"),
    RuntimeContextFile("memory/context/async_exploration_state.md", 1400, "async_exploration"),
    RuntimeContextFile("memory/context/self_code_approval_state.md", 1000, "self_code_approval"),
    RuntimeContextFile("memory/self/expression_self_learning_state.md", 1600, "expression_self_learning"),
    RuntimeContextFile("memory/self/learning_closed_loop_state.md", 1800, "learning_closed_loop"),
    RuntimeContextFile("memory/context/codex_delegation_policy.md", 1800, "codex_boundary"),
    RuntimeContextFile("memory/context/recent_context.md", 2600, "recent_context"),
    RuntimeContextFile("memory/context/initiative_state.md", 1400, "initiative"),
)

RECALLED_CONTEXT_PRIORITY_WORDING = "\n".join(
    [
        "## Recalled Context Priority",
        "Recalled Context is advisory only.",
        "It sits below the current owner message, live voice card, current life posture, privacy boundaries, and stable memory.",
        "Use recalled context only if it helps the current turn. Current owner message and current emotional posture outrank retrieved fragments.",
        "When uncertain, say uncertainty naturally instead of pretending.",
    ]
)


def read_limited(root: Path, rel_path: str, *, limit: int) -> str:
    path = root / rel_path
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""
    text = _unwrap_content_envelope(text)
    if len(text) <= limit:
        return text
    return text[-limit:]


def _unwrap_content_envelope(text: str) -> str:
    if text.startswith("content:---"):
        return text.removeprefix("content:")
    if text.startswith("content:\n"):
        return text.removeprefix("content:\n")
    return text


def refresh_runtime_context(
    root: Path,
    *,
    user_text: str = "",
    evaluated_at: str | None = None,
) -> RuntimeContextSnapshot:
    """Compatibility shim for callers that still expect a runtime snapshot.

    The old implementation refreshed many maintenance/growth files on every
    live turn. The concept-seed runtime keeps that work out of the speech path.
    """
    del user_text, evaluated_at
    return RuntimeContextSnapshot(
        life_month_context=read_limited(root, "memory/context/current_life_month_context.md", limit=1800),
        personality_evolution_state="",
        private_thought_state="",
        self_model_state="",
        memory_weight_state="",
        thought_seeds="",
        continuity_handoff_state=read_limited(root, "memory/context/continuity_handoff_state.md", limit=1600),
        uncertainty_pause_state=read_limited(root, "memory/context/uncertainty_pause_state.md", limit=1100),
        async_exploration_state=read_limited(root, "memory/context/async_exploration_state.md", limit=1400),
        self_code_approval_state=read_limited(root, "memory/context/self_code_approval_state.md", limit=1000),
        watched_source_state=read_limited(root, "memory/context/watched_source_state.md", limit=1600),
        memory_self_review_state=read_limited(root, "memory/context/memory_self_review_state.md", limit=1400),
    )


def build_renderer_memory_context(root: Path, *, user_text: str = "") -> str:
    del user_text
    parts: list[str] = []
    for spec in RENDERER_CONTEXT_FILES:
        text = read_limited(root, spec.rel_path, limit=spec.limit)
        if text:
            parts.append(f"[{spec.rel_path}]\n[layer: {spec.layer}]\n{text}")
    return "\n\n".join(parts) if parts else "(no memory context loaded)"


def wrap_recalled_context_block(block: str) -> str:
    clean = block.strip()
    if not clean:
        return ""
    return RECALLED_CONTEXT_PRIORITY_WORDING + "\n\n" + clean
