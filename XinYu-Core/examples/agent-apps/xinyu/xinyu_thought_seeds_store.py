from __future__ import annotations

from pathlib import Path

from state_service import atomic_write_text
from state_service import read_text_safe


STATE_REL = "memory/context/thought_seeds.md"
DREAM_WEIGHT_REL = "memory/dreams/dream_weight_state.md"
DREAM_LOG_REL = "memory/dreams/dream_log.md"
PERSONA_SURFACE_REL = "memory/context/persona_surface_state.md"
RECENT_CONTEXT_REL = "memory/context/recent_context.md"
INITIATIVE_STATE_REL = "memory/context/initiative_state.md"
INNER_CYCLE_STATE_REL = "memory/context/inner_cycle_state.md"
MIND_LOOP_STATE_REL = "memory/self/mind_loop_state.md"
ACTIVE_QUESTIONS_REL = "memory/context/active_questions.md"
PERSONALITY_EVOLUTION_REL = "memory/self/personality_evolution_state.md"
MEMORY_WEIGHT_REL = "memory/context/memory_weight_state.md"
UNFINISHED_EXPERIENCES_REL = "memory/context/unfinished_experiences.md"


def thought_seeds_state_path(root: Path) -> Path:
    return Path(root) / STATE_REL


def thought_seeds_source_path(root: Path, rel: str) -> Path:
    return Path(root) / rel


def read_thought_seed_text(path: Path) -> str:
    return read_text_safe(Path(path), default="")


def read_thought_seeds_state(root: Path) -> str:
    return read_thought_seed_text(thought_seeds_state_path(root))


def write_thought_seeds_state(root: Path, text: str) -> None:
    atomic_write_text(thought_seeds_state_path(root), text, final_newline=False)
