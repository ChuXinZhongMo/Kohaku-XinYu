from __future__ import annotations

from pathlib import Path


REPORT_REL = Path("worklog") / "xinyu-persona-health-latest.md"
DIMENSIONS_REL = Path("memory/self/personality_dimensions.md")
EVAL_CASES_REL = Path("memory/self/persona_eval_cases.md")
PROFILE_REL = Path("memory/self/personality_profile.md")
EVOLUTION_REL = Path("memory/self/personality_evolution_state.md")
SELF_REVIEW_REL = Path("memory/self/personality_self_review_state.md")
TRIAL_FEEDBACK_REL = Path("memory/self/personality_trial_feedback.md")
GROWTH_LOG_REL = Path("memory/reflection/growth_log.md")
REFLECTION_LOG_REL = Path("memory/reflection/reflection_log.md")

PERSONA_HEALTH_SOURCE_RELS = {
    "dimensions": DIMENSIONS_REL,
    "eval_cases": EVAL_CASES_REL,
    "profile": PROFILE_REL,
    "evolution": EVOLUTION_REL,
    "self_review": SELF_REVIEW_REL,
    "trial_feedback": TRIAL_FEEDBACK_REL,
    "growth_log": GROWTH_LOG_REL,
    "reflection_log": REFLECTION_LOG_REL,
}


def persona_health_report_path(root: Path | str) -> Path:
    return Path(root) / REPORT_REL


def persona_health_source_path(root: Path | str, source_id: str) -> Path:
    return Path(root).resolve() / PERSONA_HEALTH_SOURCE_RELS[source_id]


def read_persona_health_text(path: Path, *, limit: int = 80000) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    return text[:limit]


def read_persona_health_source_text(root: Path | str, source_id: str, *, limit: int = 80000) -> str:
    return read_persona_health_text(persona_health_source_path(root, source_id), limit=limit)


def write_persona_health_report_text(root: Path | str, text: str) -> Path:
    path = persona_health_report_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
