from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


BOUNDARY = (
    "owner_approved_local_rule_cards; stable_profile_write blocked; "
    "runtime_integration blocked; model_training blocked"
)

RULE_FIELDS = [
    "scene_summary",
    "relationship_state",
    "trigger",
    "observed_response_strategy",
    "relationship_effect",
    "xinyu_rule",
    "xinyu_do_not_learn",
]


@dataclass(frozen=True)
class SynthesizedRule:
    number: int
    title: str
    fields: dict[str, str]
    support_refs: tuple[str, ...]


def _workspace_root(app_root: Path) -> Path:
    candidates = [app_root, *app_root.parents]
    for candidate in candidates:
        if (candidate / "XinYu-Core").exists() and (candidate / "XinYu-Local-Scope").exists():
            return candidate
    for candidate in candidates:
        if candidate.name == "XinYu-Core" and (candidate.parent / "XinYu-Local-Scope").exists():
            return candidate.parent
    for candidate in reversed(candidates):
        if (candidate / "XinYu-Local-Scope").exists():
            return candidate
    return app_root


def default_curated_dir(app_root: Path) -> Path:
    root = _workspace_root(app_root)
    return root / "XinYu-Local-Scope" / "SourceMaterials" / "dialogue_observation" / "curated"


def default_input_path(app_root: Path) -> Path:
    return default_curated_dir(app_root) / "auto_rule_synthesis_drafts.md"


def default_output_path(app_root: Path) -> Path:
    return default_curated_dir(app_root) / "owner_rule_cards.md"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8-sig", newline="\n")
    tmp.replace(path)


def _parse_block_fields(block: str) -> tuple[dict[str, str], tuple[str, ...]]:
    fields: dict[str, str] = {}
    support_refs: list[str] = []
    current: str | None = None
    field_re = re.compile(r"^([A-Za-z_]+):\s*(.*)$")
    for raw in block.splitlines():
        stripped = raw.strip()
        if not stripped:
            current = None if current == "support_refs" else current
            continue
        match = field_re.match(stripped)
        if match:
            current = match.group(1)
            value = match.group(2).strip()
            if current == "support_refs":
                continue
            fields[current] = value
            continue
        if current == "support_refs" and stripped.startswith("- "):
            support_refs.append(stripped)
    return fields, tuple(support_refs)


def parse_synthesized_rules(path: Path) -> list[SynthesizedRule]:
    text = _read_text(path)
    matches = list(
        re.finditer(
            r"^## Rule Candidate\s+(?P<number>\d+):\s+(?P<title>.+?)\s*$",
            text,
            re.MULTILINE,
        )
    )
    rules: list[SynthesizedRule] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.end() : end]
        fields, support_refs = _parse_block_fields(block)
        rules.append(
            SynthesizedRule(
                number=int(match.group("number")),
                title=match.group("title").strip(),
                fields=fields,
                support_refs=support_refs,
            )
        )
    return rules


def render_owner_rule_cards(
    rules: list[SynthesizedRule],
    *,
    source_path: Path,
    approved_at: str,
    approval_note: str,
) -> str:
    lines = [
        "# Owner Approved Dialogue Observation Rule Cards",
        "",
        "status: owner_direction_approved",
        f"approved_at: {approved_at}",
        f"source_synthesis: {source_path.name}",
        f"boundary: {BOUNDARY}",
        "source_text_policy: raw dialogue excerpts intentionally omitted",
        f"approval_note: {approval_note}",
        "",
        "## Gate",
        "",
        "- These are behavior rule cards for later review, not direct runtime instructions.",
        "- Promotion into live prompt, trial overlay, stable voice, or model training remains blocked until a separate implementation gate.",
        "- Owner can edit, split, or reject any card later.",
        "",
    ]
    for rule in sorted(rules, key=lambda item: item.number):
        rule_key = rule.fields.get("rule_key", f"rule_{rule.number}")
        lines.extend(
            [
                f"## Card {rule.number}: {rule.title}",
                "",
                f"source_ref: dialogue_observation_auto_synthesis / {rule_key}",
                f"confidence: {rule.fields.get('confidence', '')}",
                f"support_count: {rule.fields.get('support_count', '')}",
                "support_refs:",
            ]
        )
        lines.extend(rule.support_refs or ["- none"])
        lines.append("")
        for field in RULE_FIELDS:
            lines.append(f"{field}: {rule.fields.get(field, '')}")
            lines.append("")
        lines.extend(
            [
                "review_status: owner_direction_approved",
                "promotion_stage: voice_lesson_candidate",
                "stable_profile_write: blocked",
                "runtime_integration: blocked",
                "model_training: blocked",
                "promotion_gate: separate owner-reviewed implementation required",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def approve_rules(
    input_path: Path,
    output_path: Path,
    *,
    approved_at: str | None = None,
    approval_note: str = "owner approved current direction in chat",
) -> dict[str, object]:
    approved_at = approved_at or datetime.now().astimezone().isoformat()
    rules = parse_synthesized_rules(input_path)
    _write_text(
        output_path,
        render_owner_rule_cards(
            rules,
            source_path=input_path,
            approved_at=approved_at,
            approval_note=approval_note,
        ),
    )
    return {
        "approved_rule_count": len(rules),
        "output": str(output_path),
        "boundary": BOUNDARY,
    }


def main(argv: list[str] | None = None) -> int:
    app_root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Mark synthesized dialogue observation rules as owner-approved local rule cards.")
    parser.add_argument("--input", type=Path, default=default_input_path(app_root))
    parser.add_argument("--output", type=Path, default=default_output_path(app_root))
    parser.add_argument("--approved-at", default=None)
    parser.add_argument("--approval-note", default="owner approved current direction in chat")
    args = parser.parse_args(argv)

    result = approve_rules(
        args.input,
        args.output,
        approved_at=args.approved_at,
        approval_note=args.approval_note,
    )
    for key, value in result.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
