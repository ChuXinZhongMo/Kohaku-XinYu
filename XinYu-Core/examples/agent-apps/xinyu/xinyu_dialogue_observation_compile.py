from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


RULE_FIELDS = [
    "scene_summary",
    "relationship_state",
    "trigger",
    "observed_response_strategy",
    "relationship_effect",
    "xinyu_rule",
    "xinyu_do_not_learn",
]

METADATA_FIELDS = [
    "source_file",
    "line_index",
    "speaker",
    "signals",
    "xinyu_fit_score",
    "reject_risks",
]

BOUNDARY = (
    "owner_observation_only; stable_profile_write blocked; "
    "runtime_integration blocked; model_training blocked"
)

_CANDIDATE_RE = re.compile(r"^## Candidate\s+(?P<number>\d+):\s+(?P<candidate_id>\S+)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class ReviewCandidate:
    source_review: str
    source_key: str
    source_family: str
    number: int
    candidate_id: str
    keep: str
    metadata: dict[str, str]
    rule_fields: dict[str, str]


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


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8-sig", newline="\n")
    tmp.replace(path)


def _source_key(review_path: Path) -> str:
    name = review_path.name
    marker = "_review_batch_"
    if marker in name:
        return name.split(marker, 1)[0]
    return review_path.stem


def _source_family(source_key: str) -> str:
    lowered = source_key.lower()
    if "va11" in lowered:
        return "game_va11halla"
    if "chinesedating" in lowered:
        return "game_chinesedating"
    if lowered.startswith("audio"):
        return source_key
    return source_key


def _display_name(source_key: str) -> str:
    names = {
        "va11halla": "VA-11 Hall-A",
        "chinesedating": "ChineseDating",
        "audio_2087_cocktail": "Audio 2087 Cocktail",
    }
    return names.get(source_key, source_key.replace("_", " ").title())


def _parse_keep(line: str) -> str:
    lowered = line.lower()
    yes_checked = re.search(r"\[[xX]\]\s*yes", line) is not None
    no_checked = re.search(r"\[[xX]\]\s*no", line) is not None
    if yes_checked and not no_checked:
        return "yes"
    if no_checked and not yes_checked:
        return "no"
    if re.search(r"\bkeep:\s*yes\b", lowered):
        return "yes"
    if re.search(r"\bkeep:\s*no\b", lowered):
        return "no"
    if yes_checked and no_checked:
        return "ambiguous"
    return "unset"


def _parse_metadata(block: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    in_code = False
    for raw in block.splitlines():
        stripped = raw.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not stripped.startswith("- "):
            continue
        key, sep, value = stripped[2:].partition(":")
        if sep and key.strip() in METADATA_FIELDS:
            metadata[key.strip()] = value.strip()
    return metadata


def _parse_rule_fields(block: str) -> dict[str, str]:
    fields = {field: "" for field in RULE_FIELDS}
    current: str | None = None
    in_code = False
    field_re = re.compile(rf"^({'|'.join(RULE_FIELDS)}):\s*(.*)$")
    for raw in block.splitlines():
        stripped = raw.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        match = field_re.match(stripped)
        if match:
            current = match.group(1)
            fields[current] = match.group(2).strip()
            continue
        if current and stripped and not stripped.startswith(("-", "keep:", "##")):
            previous = fields[current]
            fields[current] = f"{previous}\n{stripped}" if previous else stripped
    return fields


def parse_review_batch(path: Path) -> list[ReviewCandidate]:
    text = _read_text(path)
    matches = list(_CANDIDATE_RE.finditer(text))
    source_key = _source_key(path)
    source_family = _source_family(source_key)
    rows: list[ReviewCandidate] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.end() : end]
        keep = "unset"
        for line in block.splitlines():
            if line.strip().lower().startswith("keep:"):
                keep = _parse_keep(line)
                break
        rows.append(
            ReviewCandidate(
                source_review=path.name,
                source_key=source_key,
                source_family=source_family,
                number=int(match.group("number")),
                candidate_id=match.group("candidate_id"),
                keep=keep,
                metadata=_parse_metadata(block),
                rule_fields=_parse_rule_fields(block),
            )
        )
    return rows


def _accepted_index_text(source_key: str, review_name: str, rows: list[ReviewCandidate]) -> str:
    lines = [
        f"# {_display_name(source_key)} Accepted Candidate Index",
        "",
        "status: owner_accepted_for_rule_card_drafting",
        f"source_review: {review_name}",
        f"boundary: {BOUNDARY}",
        "",
    ]
    for idx, row in enumerate(rows, start=1):
        rule_field_status = "owner_notes_present" if any(row.rule_fields.values()) else "blank_rule_card_fields"
        lines.extend(
            [
                f"## Accepted {idx}",
                "",
                f"- candidate_id: {row.candidate_id}",
                f"- source_file: {row.metadata.get('source_file', '')}",
                f"- line_index: {row.metadata.get('line_index', '')}",
                f"- signals: {row.metadata.get('signals', '')}",
                f"- reject_risks: {row.metadata.get('reject_risks', '')}",
                f"- xinyu_fit_score: {row.metadata.get('xinyu_fit_score', '')}",
                f"- rule_field_status: {rule_field_status}",
                "- next_step: draft_rule_card_without_copying_source_text",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _drafts_text(rows: list[ReviewCandidate]) -> str:
    by_source = Counter(row.source_key for row in rows)
    lines = [
        "# Dialogue Observation Accepted Rule Card Drafts",
        "",
        "status: accepted_candidates_waiting_for_owner_rule_rewrite",
        f"boundary: {BOUNDARY}",
        "source_text_policy: raw dialogue excerpts intentionally omitted",
        "",
        "## Summary",
        "",
        f"- accepted_total: {len(rows)}",
    ]
    for source_key, count in sorted(by_source.items()):
        lines.append(f"- {source_key}: {count}")
    lines.append("")

    for idx, row in enumerate(rows, start=1):
        lines.extend(
            [
                f"## Draft {idx}: {row.candidate_id}",
                "",
                f"source_ref: {row.source_family} / {row.candidate_id}",
                f"source_review: {row.source_review}",
                f"source_file: {row.metadata.get('source_file', '')}",
                f"line_index: {row.metadata.get('line_index', '')}",
                f"speaker: {row.metadata.get('speaker', '')}",
                f"signals: {row.metadata.get('signals', '')}",
                f"reject_risks: {row.metadata.get('reject_risks', '')}",
                f"xinyu_fit_score: {row.metadata.get('xinyu_fit_score', '')}",
                "",
            ]
        )
        for field in RULE_FIELDS:
            lines.append(f"{field}: {row.rule_fields.get(field, '')}")
            lines.append("")
        lines.extend(
            [
                "review_status: owner_observation_only",
                "stable_profile_write: blocked",
                "runtime_integration: blocked",
                "model_training: blocked",
                "notes: Rewrite as a XinYu behavior rule before any later review; do not copy source lines.",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _summary_text(candidates: list[ReviewCandidate], accepted: list[ReviewCandidate], index_paths: dict[str, Path]) -> str:
    by_review: dict[str, list[ReviewCandidate]] = defaultdict(list)
    for row in candidates:
        by_review[row.source_review].append(row)
    signal_counts: Counter[str] = Counter()
    risk_counts: Counter[str] = Counter()
    for row in accepted:
        for signal in _split_labels(row.metadata.get("signals", "")):
            signal_counts[signal] += 1
        for risk in _split_labels(row.metadata.get("reject_risks", "")):
            risk_counts[risk] += 1

    lines = [
        "# Dialogue Observation Flow Summary",
        "",
        "status: review_batches_compiled",
        f"boundary: {BOUNDARY}",
        "",
        "## Batch Counts",
        "",
        "| source_review | total | yes | no | unset | ambiguous | accepted_index |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for review_name, rows in sorted(by_review.items()):
        counts = Counter(row.keep for row in rows)
        source_key = rows[0].source_key if rows else ""
        index_path = index_paths.get(source_key)
        index_name = index_path.name if index_path else ""
        lines.append(
            f"| {review_name} | {len(rows)} | {counts['yes']} | {counts['no']} | "
            f"{counts['unset']} | {counts['ambiguous']} | {index_name} |"
        )

    lines.extend(["", "## Accepted Signal Counts", ""])
    if signal_counts:
        for signal, count in sorted(signal_counts.items()):
            lines.append(f"- {signal}: {count}")
    else:
        lines.append("- none")

    lines.extend(["", "## Accepted Risk Labels", ""])
    if risk_counts:
        for risk, count in sorted(risk_counts.items()):
            lines.append(f"- {risk}: {count}")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Next Manual Step",
            "",
            "- Open accepted_rule_card_drafts.md.",
            "- Fill only owner-written behavior rules.",
            "- Keep source text, character imitation, plot lore, runtime hooks, and stable memory writes out of this pass.",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _split_labels(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def compile_reviews(curated_dir: Path, review_glob: str = "*_review_batch_*.md") -> dict[str, object]:
    review_paths = sorted(curated_dir.glob(review_glob))
    candidates: list[ReviewCandidate] = []
    for path in review_paths:
        candidates.extend(parse_review_batch(path))
    accepted = [row for row in candidates if row.keep == "yes"]

    index_paths: dict[str, Path] = {}
    accepted_by_source: dict[str, list[ReviewCandidate]] = defaultdict(list)
    for row in accepted:
        accepted_by_source[row.source_key].append(row)
    for source_key, rows in sorted(accepted_by_source.items()):
        review_names = sorted({row.source_review for row in rows})
        review_name = ", ".join(review_names)
        path = curated_dir / f"{source_key}_accepted_index.md"
        _write_text(path, _accepted_index_text(source_key, review_name, rows))
        index_paths[source_key] = path

    drafts_path = curated_dir / "accepted_rule_card_drafts.md"
    summary_path = curated_dir / "dialogue_observation_flow_summary.md"
    _write_text(drafts_path, _drafts_text(accepted))
    _write_text(summary_path, _summary_text(candidates, accepted, index_paths))

    keep_counts = Counter(row.keep for row in candidates)
    return {
        "review_batch_count": len(review_paths),
        "candidate_count": len(candidates),
        "accepted_count": len(accepted),
        "keep_counts": dict(sorted(keep_counts.items())),
        "accepted_indexes": [str(path) for path in sorted(index_paths.values())],
        "drafts": str(drafts_path),
        "summary": str(summary_path),
        "boundary": BOUNDARY,
    }


def main(argv: list[str] | None = None) -> int:
    app_root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Compile owner-reviewed dialogue observation batches.")
    parser.add_argument("--curated-dir", type=Path, default=default_curated_dir(app_root))
    parser.add_argument("--review-glob", default="*_review_batch_*.md")
    args = parser.parse_args(argv)

    result = compile_reviews(args.curated_dir, args.review_glob)
    for key, value in result.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
