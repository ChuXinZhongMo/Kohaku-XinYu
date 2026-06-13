from __future__ import annotations

from pathlib import Path


REPORT_REL = Path("worklog") / "xinyu-memory-health-latest.md"
STAGE8_STATE_REL = Path("memory/context/stage8_memory_governance_state.md")
STAGE8_DUPLICATE_CONSOLIDATION_STATE_REL = Path("memory/context/stage8_duplicate_consolidation_state.md")
STAGE8_LEARNING_TRIAL_VALIDATION_STATE_REL = Path("memory/context/stage8_learning_trial_validation_state.md")

MEMORY_HEALTH_SOURCE_RELS = {
    "personality_evolution": Path("memory/self/personality_evolution_state.md"),
    "personality_self_review": Path("memory/self/personality_self_review_state.md"),
    "personality_change": Path("memory/self/personality_change_state.md"),
    "learning_closed_loop": Path("memory/self/learning_closed_loop_state.md"),
    "growth_log": Path("memory/reflection/growth_log.md"),
    "stage8_duplicate_consolidation_state": STAGE8_DUPLICATE_CONSOLIDATION_STATE_REL,
    "stage8_learning_trial_validation_state": STAGE8_LEARNING_TRIAL_VALIDATION_STATE_REL,
}


def memory_health_report_path(root: Path | str, output: Path | None = None) -> Path:
    root = Path(root)
    path = output if output is not None else root / REPORT_REL
    if not path.is_absolute():
        path = root / path
    return path


def stage8_memory_governance_state_path(root: Path | str) -> Path:
    return Path(root).resolve() / STAGE8_STATE_REL


def stage8_duplicate_consolidation_state_path(root: Path | str) -> Path:
    return Path(root).resolve() / STAGE8_DUPLICATE_CONSOLIDATION_STATE_REL


def stage8_learning_trial_validation_state_path(root: Path | str) -> Path:
    return Path(root).resolve() / STAGE8_LEARNING_TRIAL_VALIDATION_STATE_REL


def memory_health_source_path(root: Path | str, source_id: str) -> Path:
    rel = MEMORY_HEALTH_SOURCE_RELS[source_id]
    return Path(root).resolve() / rel


def read_memory_health_text(path: Path, *, limit: int = 20000) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    return text[:limit]


def read_memory_health_source_text(root: Path | str, source_id: str, *, limit: int = 20000) -> str:
    return read_memory_health_text(memory_health_source_path(root, source_id), limit=limit)


def write_memory_health_report_text(root: Path | str, text: str, *, output: Path | None = None) -> Path:
    path = memory_health_report_path(Path(root), output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_stage8_memory_governance_state_text(root: Path | str, text: str) -> Path:
    path = stage8_memory_governance_state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
