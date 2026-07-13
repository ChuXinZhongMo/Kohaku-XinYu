"""Skill artifacts: named, reusable behavioural routines distilled from experience.

Where the candidate/dream/learning loops record *facts* and *reflections*, a skill
records a *method* — "in situation X, the routine that worked is Y". Skills are
plain frontmatter'd markdown under ``memory/skills/`` so they are inspectable and
owner-editable, and they are recalled by situation match into the live prompt
through the same boundary mechanism candidates already use.

Skills are ``review_only`` by contract: they are recalled as hints, never as a
stable identity rewrite. The current turn and any owner correction always win.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

SKILLS_REL = Path("memory") / "skills"
INDEX_NAME = "index.md"
SKILL_MEMORY_TYPE = "skill_artifact"
SKILL_PERMISSION = "review_only"

_SCALAR_FIELDS = (
    "title",
    "memory_type",
    "skill_id",
    "status",
    "created_at",
    "updated_at",
    "evidence_count",
    "confidence",
    "permission",
)
_LIST_FIELDS = ("trigger_keys", "evidence_candidate_ids", "tags")


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def skills_dir(root: Path) -> Path:
    return Path(root) / SKILLS_REL


def skill_path(root: Path, skill_id: str) -> Path:
    return skills_dir(root) / f"{slugify(skill_id)}.md"


def index_path(root: Path) -> Path:
    return skills_dir(root) / INDEX_NAME


def slugify(text: str) -> str:
    clean = re.sub(r"[^a-z0-9一-鿿]+", "-", _safe_str(text).strip().lower())
    clean = clean.strip("-")
    return clean or "skill"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def tokenize(text: str) -> list[str]:
    """Latin words plus CJK bigrams. Bigrams (not single chars) keep situational
    matching precise — single-char CJK overlap matches almost everything (e.g. the
    shared 气 in 天气/语气)."""

    tokens: list[str] = []
    for run in re.findall(r"[a-z0-9_+#./-]{2,}|[一-鿿]+", _safe_str(text).lower()):
        if re.fullmatch(r"[一-鿿]+", run):
            if len(run) == 1:
                tokens.append(run)
            else:
                tokens.extend(run[i : i + 2] for i in range(len(run) - 1))
        else:
            tokens.append(run)
    return tokens


# --- minimal frontmatter (scalars + simple [a, b] lists) -------------------------


def _render_list(values: Any) -> str:
    items = [str(v).strip() for v in (values or []) if str(v).strip()]
    return "[" + ", ".join(items) + "]"


def _parse_list(raw: str) -> list[str]:
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    return [item.strip() for item in raw.split(",") if item.strip()]


def parse_skill_frontmatter(text: str) -> dict[str, Any]:
    text = _safe_str(text)
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end].strip("\n")
    fields: dict[str, Any] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if key in _LIST_FIELDS:
            fields[key] = _parse_list(value)
        elif key:
            fields[key] = value
    return fields


def render_skill_markdown(skill: dict[str, Any]) -> str:
    lines = ["---"]
    for field in _SCALAR_FIELDS:
        lines.append(f"{field}: {_safe_str(skill.get(field))}")
    for field in _LIST_FIELDS:
        lines.append(f"{field}: {_render_list(skill.get(field))}")
    lines.append("---")
    lines.append("")
    lines.append("## Situation")
    lines.append(_safe_str(skill.get("situation")).strip() or "(unspecified)")
    lines.append("")
    lines.append("## Routine")
    lines.append(_safe_str(skill.get("routine")).strip() or "(unspecified)")
    lines.append("")
    lines.append("## Evidence")
    lines.append(_safe_str(skill.get("evidence")).strip() or "(none)")
    lines.append("")
    lines.append("## Boundary")
    lines.append(
        "review_only: recall as a hint, not a stable identity rewrite; "
        "the current turn and any owner correction always win."
    )
    lines.append("")
    return "\n".join(lines)


def _body_section(text: str, header: str) -> str:
    match = re.search(rf"^##\s+{re.escape(header)}\s*$(.*?)(?=^##\s+|\Z)", text, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def write_skill(root: Path, skill: dict[str, Any]) -> Path:
    skill_id = slugify(skill.get("skill_id") or skill.get("title") or "skill")
    now = _now_iso()
    existing = read_skill(root, skill_id)
    record = dict(skill)
    record["skill_id"] = skill_id
    record["memory_type"] = SKILL_MEMORY_TYPE
    record["permission"] = SKILL_PERMISSION
    record.setdefault("status", SKILL_PERMISSION)
    record["created_at"] = existing.get("created_at") if existing else now
    record["updated_at"] = now
    path = skill_path(root, skill_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_skill_markdown(record), encoding="utf-8")
    rebuild_index(root)
    return path


def read_skill(root: Path, skill_id: str) -> dict[str, Any]:
    path = skill_path(root, skill_id)
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    fields = parse_skill_frontmatter(text)
    fields["situation"] = _body_section(text, "Situation")
    fields["routine"] = _body_section(text, "Routine")
    fields["evidence"] = _body_section(text, "Evidence")
    return fields


def list_skills(root: Path) -> list[dict[str, Any]]:
    directory = skills_dir(root)
    if not directory.exists():
        return []
    skills: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.md")):
        if path.name == INDEX_NAME:
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        if _safe_str(parse_skill_frontmatter(text).get("memory_type")) != SKILL_MEMORY_TYPE:
            continue
        fields = parse_skill_frontmatter(text)
        fields["situation"] = _body_section(text, "Situation")
        fields["routine"] = _body_section(text, "Routine")
        skills.append(fields)
    return skills


def rebuild_index(root: Path) -> Path:
    skills = list_skills(root)
    lines = ["# Skill Library Index", "", f"updated_at: {_now_iso()}", f"skill_count: {len(skills)}", ""]
    for skill in skills:
        title = _safe_str(skill.get("title"), skill.get("skill_id", "skill"))
        triggers = ", ".join(skill.get("trigger_keys") or [])
        lines.append(f"- [{skill.get('skill_id', '')}] {title} — triggers: {triggers}")
    path = index_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _skill_haystack(skill: dict[str, Any]) -> set[str]:
    haystack: set[str] = set()
    for key in ("title", "situation"):
        haystack.update(tokenize(skill.get(key, "")))
    for trig in skill.get("trigger_keys") or []:
        haystack.update(tokenize(trig))
    return haystack


def _skill_overlap(skill: dict[str, Any], query_tokens: set[str]) -> int:
    if not query_tokens:
        return 0
    return len(query_tokens & _skill_haystack(skill))


def _skill_rank(skill: dict[str, Any], query_tokens: set[str]) -> int:
    # overlap qualifies a match; confidence is only a tiebreaker and must not, on its
    # own, surface a skill that does not match the situation.
    try:
        confidence = int(_safe_str(skill.get("confidence"), "0") or 0)
    except ValueError:
        confidence = 0
    return _skill_overlap(skill, query_tokens) * 4 + min(confidence, 5)


def _clip(text: str, limit: int) -> str:
    clean = re.sub(r"\s+", " ", _safe_str(text)).strip()
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 1)].rstrip() + "…"


def build_skill_recall_block(root: Any, *, query_text: str = "", limit: int = 3) -> str:
    """Situation-keyed skill recall, rendered with the same review-only boundary
    framing the candidate boundaries use, so the model treats skills as hints."""

    skills = list_skills(Path(root))
    if not skills:
        return ""
    query_tokens = set(tokenize(query_text))
    ranked = sorted(skills, key=lambda s: _skill_rank(s, query_tokens), reverse=True)
    # With a query, only surface skills that actually match the situation (token
    # overlap); with no query, fall back to the most recent handful.
    if query_tokens:
        ranked = [s for s in ranked if _skill_overlap(s, query_tokens) > 0]
    if not ranked:
        return ""
    ranked = ranked[: max(1, int(limit))]
    lines = [
        "## Learned Skills",
        "purpose: reusable routines distilled from past experience; recall as hints only.",
        "- review_only: true",
        "- current_turn_wins: true",
    ]
    for skill in ranked:
        lines.extend(
            [
                f"- skill_id: {_safe_str(skill.get('skill_id'), 'unknown')}",
                f"  title: {_clip(skill.get('title'), 80)}",
                f"  when: {_clip(skill.get('situation'), 160)}",
                f"  routine: {_clip(skill.get('routine'), 220)}",
                "  use_policy: situational_hint_not_stable_identity",
            ]
        )
    return "\n".join(lines).strip()
