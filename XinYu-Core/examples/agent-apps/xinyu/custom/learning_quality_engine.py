from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from xinyu_text_variants import looks_like_legacy_mojibake
from xinyu_storage_paths import knowledge_file_path
from xinyu_state_io import read_text, write_text


def append_lines_to_section(text: str, heading: str, lines: list[str]) -> str:
    if heading not in text:
        return text.rstrip() + f"\n\n{heading}\n" + "\n".join(lines)
    pattern = rf"(?ms)^({re.escape(heading)}\n)(.*?)(?=^## |\Z)"
    match = re.search(pattern, text)
    if not match:
        return text.rstrip() + f"\n\n{heading}\n" + "\n".join(lines)
    body = match.group(2).rstrip()
    addition = ("\n" if body else "") + "\n".join(lines)
    replacement = match.group(1) + body + addition + "\n\n"
    return text[: match.start()] + replacement + text[match.end():]


def _knowledge(root: Path, filename: str) -> Path:
    return knowledge_file_path(root, filename)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _timestamp_or_now_iso(value: object) -> str:
    parsed = _parse_iso(value)
    if parsed is None:
        return _now_iso()
    return parsed.astimezone().isoformat()


def _parse_iso(value: object) -> datetime | None:
    text = "" if value is None else str(value).strip()
    if not text or text == "none":
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def host_of(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host or "unknown"


def split_blocks(text: str, prefix: str) -> list[dict[str, str]]:
    parts = re.split(rf"(?m)^## ({re.escape(prefix)}-[\w-]+)\n", text)
    items: list[dict[str, str]] = []
    if len(parts) < 3:
        return items
    for i in range(1, len(parts), 2):
        item_id = parts[i].strip()
        body = parts[i + 1]
        if item_id.endswith("-none"):
            continue
        item = {"id": item_id}
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith("- ") and ": " in stripped:
                key, value = stripped[2:].split(": ", 1)
                item[key.strip()] = value.strip()
        items.append(item)
    return items


def normalize_claim(claim: str) -> str:
    value = re.sub(r"\s+", " ", claim.lower()).strip()
    value = re.sub(r"[^a-z0-9 ]+", "", value)
    return value[:160]


def enriched_learned_entries(learned: list[dict[str, str]], materials: list[dict[str, str]]) -> list[dict[str, str]]:
    by_material = {item["id"]: item for item in materials}
    enriched: list[dict[str, str]] = []
    for entry in learned:
        material_id = entry.get("source_material", "none")
        material = by_material.get(material_id, {})
        url = material.get("url", entry.get("url", "none"))
        enriched.append(
            {
                **entry,
                "material_id": material_id,
                "url": url,
                "host": host_of(url),
                "material_status": material.get("status", "unknown"),
                "material_comparison_status": material.get("comparison_status", entry.get("comparison_status", "unknown")),
                "material_reliability": material.get("reliability", entry.get("reliability", "unknown")),
            }
        )
    return enriched


def build_warnings(enriched: list[dict[str, str]], materials: list[dict[str, str]]) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    integrated_count = len(enriched)
    host_counts = Counter(item["host"] for item in enriched if item["host"] != "unknown")
    for host, count in host_counts.most_common():
        if integrated_count >= 3 and count >= 3 and count / integrated_count >= 0.67:
            warnings.append(
                {
                    "kind": "dominant_host",
                    "severity": "caution",
                    "target": host,
                    "detail": f"{count}/{integrated_count} learned entries come from the same host",
                }
            )

    by_question_hosts: dict[str, Counter[str]] = defaultdict(Counter)
    for item in enriched:
        qid = item.get("question_id", "none")
        host = item.get("host", "unknown")
        if qid != "none" and host != "unknown":
            by_question_hosts[qid][host] += 1
    for qid, counts in sorted(by_question_hosts.items()):
        host, count = counts.most_common(1)[0]
        total = sum(counts.values())
        if count >= 2 and total > 0 and count * 3 >= total * 2:
            warnings.append(
                {
                    "kind": "repeated_question_host",
                    "severity": "review",
                    "target": f"{qid}@{host}",
                    "detail": f"{count}/{total} learned entries for {qid} come from the same host",
                }
            )

    normalized_counts = Counter(normalize_claim(item.get("claim", "")) for item in enriched if item.get("claim", "none") != "none")
    duplicate_claims = sum(1 for claim, count in normalized_counts.items() if claim and count > 1)
    if duplicate_claims:
        warnings.append(
            {
                "kind": "duplicate_claim",
                "severity": "review",
                "target": "knowledge/general",
                "detail": f"{duplicate_claims} repeated learned claim pattern(s) detected",
            }
        )

    material_ids = {item["id"] for item in materials}
    orphaned = [item for item in enriched if item.get("material_id", "none") not in material_ids]
    if orphaned:
        warnings.append(
            {
                "kind": "orphaned_learned_material",
                "severity": "review",
                "target": "knowledge/general",
                "detail": f"{len(orphaned)} learned entries reference missing source material",
            }
        )

    garbled_learned = [
        item for item in enriched
        if looks_like_legacy_mojibake(item.get("claim", ""))
    ]
    if garbled_learned:
        warnings.append(
            {
                "kind": "garbled_learned_claim",
                "severity": "review",
                "target": "knowledge/general",
                "detail": f"{len(garbled_learned)} learned entries look like Chinese mojibake",
            }
        )

    unmarked_ready = [
        item for item in materials
        if item.get("status") == "ready"
        and item.get("comparison_status", "not_compared") in {"not_compared", "unknown", "none"}
    ]
    if unmarked_ready:
        warnings.append(
            {
                "kind": "uncompared_ready_material",
                "severity": "review",
                "target": "source_materials",
                "detail": f"{len(unmarked_ready)} ready material(s) lack source comparison status",
            }
        )

    return warnings


def quality_grade(
    warnings: list[dict[str, str]],
    conflict_materials: int,
    semantic_mismatch_materials: int,
    single_source_learned: int,
    integrated_count: int,
) -> str:
    if conflict_materials > 0 or semantic_mismatch_materials > 0 or any(item["severity"] == "review" for item in warnings):
        return "review_needed"
    if warnings or (integrated_count >= 3 and single_source_learned > integrated_count // 2):
        return "caution"
    return "stable"


def render_state(
    evaluated_at: str,
    mode: str,
    metrics: dict[str, int | str],
    warnings: list[dict[str, str]],
) -> str:
    warning_block = "\n".join(
        f"- {item['kind']}: severity={item['severity']}; target={item['target']}; detail={item['detail']}"
        for item in warnings
    ) or "- none"
    return f"""---
title: Learning Quality State
memory_type: learning_quality_state
time_scope: mid_term
subject_ids: [xinyu]
protected: true
source: system
created_at: {_timestamp_or_now_iso('2026-04-24T00:00:00+08:00')}
updated_at: {_timestamp_or_now_iso(evaluated_at)}
last_confirmed_at: {_timestamp_or_now_iso(evaluated_at)}
importance_score: 83
impact_score: 82
confidence_score: 100
status: active
tags: [knowledge, learning, quality]
---

# Learning Quality State

## Last Evaluation
- evaluated_at: {evaluated_at}
- mode: {mode}
- quality_grade: {metrics['quality_grade']}
- learned_entries: {metrics['learned_entries']}
- source_materials: {metrics['source_materials']}
- unique_learned_hosts: {metrics['unique_learned_hosts']}
- dominant_host: {metrics['dominant_host']}
- dominant_host_entries: {metrics['dominant_host_entries']}
- single_source_learned: {metrics['single_source_learned']}
- corroborated_learned: {metrics['corroborated_learned']}
- limited_independence_learned: {metrics['limited_independence_learned']}
- conflict_hold_materials: {metrics['conflict_hold_materials']}
- semantic_mismatch_hold_materials: {metrics['semantic_mismatch_hold_materials']}
- garbled_learned_entries: {metrics['garbled_learned_entries']}
- uncompared_ready_materials: {metrics['uncompared_ready_materials']}
- warning_count: {len(warnings)}

## Warnings
{warning_block}

## Boundaries
- This layer evaluates learning quality after learner integration.
- It may write quality notes, but it does not rewrite learned knowledge by itself.
- It does not rewrite self, owner, relationship, emotion, dream, or archive memory.
"""


def append_quality_notes(root: Path, evaluated_at: str, warnings: list[dict[str, str]]) -> None:
    if not warnings:
        return
    path = _knowledge(root, "source_notes.md")
    text = read_text(path).rstrip()
    text = re.sub(r"(?m)^updated_at:\s*.+$", f"updated_at: {_timestamp_or_now_iso(evaluated_at)}", text)
    text = re.sub(
        r"(?m)^last_confirmed_at:\s*.+$",
        f"last_confirmed_at: {_timestamp_or_now_iso(evaluated_at)}",
        text,
    )
    lines: list[str] = []
    for item in warnings:
        marker = f"- {item['kind']}::{item['target']}:"
        if marker in text:
            continue
        lines.append(
            f"{marker} {item['severity']} at {evaluated_at}; {item['detail']}"
        )
    if not lines:
        return
    text = append_lines_to_section(text, "## Learning Quality Warnings", lines)
    write_text(path, text.rstrip() + "\n")


def update_current_quality_notes(root: Path, evaluated_at: str, quality: str, warnings: list[dict[str, str]]) -> None:
    path = _knowledge(root, "source_notes.md")
    text = read_text(path).rstrip()
    warning_lines = [
        f"- {item['kind']}: severity={item['severity']}; target={item['target']}; detail={item['detail']}"
        for item in warnings
    ] or ["- none"]
    heading = "## Current Learning Quality Status"
    section = "\n".join(
        [
            heading,
            f"- evaluated_at: {evaluated_at}",
            f"- quality_grade: {quality}",
            f"- current_warning_count: {len(warnings)}",
            *warning_lines,
        ]
    )
    if heading in text:
        text = re.sub(
            rf"(?ms)^{re.escape(heading)}\n.*?(?=^## |\Z)",
            section + "\n\n",
            text,
        ).rstrip()
    else:
        text = text.rstrip() + "\n\n" + section
    write_text(path, text.rstrip() + "\n")


def run_learning_quality(
    root: Path,
    evaluated_at: str | None = None,
    mode: str = "runtime_learning_quality",
) -> dict[str, object]:
    evaluated_at = _timestamp_or_now_iso(evaluated_at)
    materials = split_blocks(read_text(_knowledge(root, "source_materials.md")), "material")
    learned = split_blocks(read_text(_knowledge(root, "general.md")), "learned")
    enriched = enriched_learned_entries(learned, materials)
    warnings = build_warnings(enriched, materials)

    host_counts = Counter(item["host"] for item in enriched if item["host"] != "unknown")
    dominant_host = "none"
    dominant_count = 0
    if host_counts:
        dominant_host, dominant_count = host_counts.most_common(1)[0]
    conflict_hold_materials = sum(1 for item in materials if item.get("status") == "hold" and item.get("comparison_status") == "conflict_hold")
    semantic_mismatch_hold_materials = sum(
        1 for item in materials
        if item.get("status") == "hold" and item.get("comparison_status") == "semantic_mismatch_hold"
    )
    garbled_learned_entries = sum(1 for item in enriched if looks_like_legacy_mojibake(item.get("claim", "")))
    uncompared_ready = sum(
        1 for item in materials
        if item.get("status") == "ready"
        and item.get("comparison_status", "not_compared") in {"not_compared", "unknown", "none"}
    )
    single_source_learned = sum(1 for item in enriched if item.get("comparison_status") == "single_source")
    corroborated_learned = sum(1 for item in enriched if item.get("comparison_status") in {"corroborated", "verified"})
    limited_independence = sum(1 for item in enriched if item.get("comparison_status") == "limited_independence")

    grade = quality_grade(warnings, conflict_hold_materials, semantic_mismatch_hold_materials, single_source_learned, len(enriched))
    metrics: dict[str, int | str] = {
        "quality_grade": grade,
        "learned_entries": len(enriched),
        "source_materials": len(materials),
        "unique_learned_hosts": len(host_counts),
        "dominant_host": dominant_host,
        "dominant_host_entries": dominant_count,
        "single_source_learned": single_source_learned,
        "corroborated_learned": corroborated_learned,
        "limited_independence_learned": limited_independence,
        "conflict_hold_materials": conflict_hold_materials,
        "semantic_mismatch_hold_materials": semantic_mismatch_hold_materials,
        "garbled_learned_entries": garbled_learned_entries,
        "uncompared_ready_materials": uncompared_ready,
    }
    write_text(
        _knowledge(root, "learning_quality_state.md"),
        render_state(evaluated_at, mode, metrics, warnings),
    )
    update_current_quality_notes(root, evaluated_at, str(metrics["quality_grade"]), warnings)
    append_quality_notes(root, evaluated_at, warnings)
    return {
        "evaluated_at": evaluated_at,
        **metrics,
        "warning_count": len(warnings),
        "warnings": warnings,
    }
