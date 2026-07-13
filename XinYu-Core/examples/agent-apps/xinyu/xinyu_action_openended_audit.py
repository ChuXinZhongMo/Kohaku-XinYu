from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from xinyu_action_openended_audit_store import read_action_openended_audit_jsonl
from xinyu_action_openended_audit_store import read_action_openended_audit_text
from xinyu_action_openended_audit_store import ACTION_RESIDUE_REL, DREAM_SEEDS_REL, RECENT_ACTION_REL, REFLECTION_QUEUE_REL


LOW_SALIENCE_THRESHOLD = 0.6


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _bounded_float(value: Any, *, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(0.0, min(1.0, number))


def _markdown_blocks(text: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    pattern = re.compile(r"(?ms)^## (?P<id>[^\n]+)\n(?P<body>.*?)(?=^## |\Z)")
    for match in pattern.finditer(text):
        body = match.group("body")
        blocks.append(
            {
                "id": match.group("id").strip(),
                "body": body,
                "fields": _fields_from_block(body),
            }
        )
    return blocks


def _fields_from_block(block: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        key, value = stripped[2:].split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def _source_experience_id(text: str) -> str:
    match = re.search(r"\baction_experience(?:_residue)?\s*/\s*(exp-[A-Za-z0-9_-]+)", text)
    return match.group(1) if match else ""


def _row_experience_id(row: dict[str, Any]) -> str:
    return _safe_str(row.get("experience_id")).strip()


def _row_salience(row: dict[str, Any]) -> float:
    return _bounded_float(row.get("salience"), default=0.0)


def _salience_index(*row_sets: list[dict[str, Any]]) -> dict[str, float]:
    indexed: dict[str, float] = {}
    for rows in row_sets:
        for row in rows:
            exp_id = _row_experience_id(row)
            if not exp_id:
                continue
            salience = _row_salience(row)
            if exp_id not in indexed:
                indexed[exp_id] = salience
            else:
                indexed[exp_id] = min(indexed[exp_id], salience)
    return indexed


def _action_source_blocks(blocks: list[dict[str, Any]], source_field: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for block in blocks:
        fields = block.get("fields") if isinstance(block.get("fields"), dict) else {}
        source = _safe_str(fields.get(source_field))
        if "action_experience" not in source:
            continue
        exp_id = _source_experience_id(source)
        enriched = dict(block)
        enriched["source"] = source
        enriched["experience_id"] = exp_id
        result.append(enriched)
    return result


def _normalize_theme(row: dict[str, Any]) -> str:
    tool = _safe_str(row.get("tool"), "unknown") or "unknown"
    target = _safe_str(row.get("target_alias"), "none") or "none"
    result = _safe_str(row.get("result"), "unknown") or "unknown"
    diagnosis = row.get("diagnosis") if isinstance(row.get("diagnosis"), dict) else {}
    diagnosis_kind = _safe_str(diagnosis.get("kind")).strip()
    if not diagnosis_kind:
        load = row.get("load") if isinstance(row.get("load"), dict) else {}
        load_diagnosis = load.get("diagnosis") if isinstance(load.get("diagnosis"), dict) else {}
        diagnosis_kind = _safe_str(load_diagnosis.get("kind")).strip()
    parts = [tool, target, result]
    if diagnosis_kind:
        parts.append(diagnosis_kind)
    return " / ".join(parts)


def _top_repeated_action_themes(rows: list[dict[str, Any]], *, limit: int = 8) -> list[dict[str, Any]]:
    counts = Counter(_normalize_theme(row) for row in rows if _safe_str(row.get("tool")).strip())
    return [
        {"theme": theme, "count": count}
        for theme, count in counts.most_common(limit)
        if count >= 2
    ]


def _visible_values_from_row(row: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("summary", "memory_candidates", "outcome_summary"):
        raw = row.get(key)
        if isinstance(raw, list):
            values.extend(_safe_str(item) for item in raw)
        elif raw:
            values.append(_safe_str(raw))
    diagnosis = row.get("diagnosis") if isinstance(row.get("diagnosis"), dict) else {}
    if diagnosis:
        values.append(_safe_str(diagnosis.get("summary")))
    return [value for value in values if value.strip()]


def _visible_values_from_block(block: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    fields = block.get("fields") if isinstance(block.get("fields"), dict) else {}
    return [_safe_str(fields.get(key)) for key in keys if _safe_str(fields.get(key)).strip()]


def _normalize_phrase(text: str) -> str:
    text = _safe_str(text)
    text = text.replace("\\", "/")
    text = re.sub(r"[A-Za-z]:/[^，。；;\s]+", "<path>", text)
    text = re.sub(r"\b(?:codex|action)-[A-Za-z0-9_-]{8,}\b", "<id>", text)
    text = re.sub(r"\bexp-[A-Za-z0-9_-]+\b", "<exp>", text)
    text = re.sub(r"\bseed-[A-Za-z0-9_-]+\b", "<seed>", text)
    text = re.sub(r"\bitem-\d{4}-\d{2}-\d{2}-\d{3}\b", "<item>", text)
    text = re.sub(r"\d{4}-\d{2}-\d{2}(?:[T ][0-9:+-]+)?", "<date>", text)
    text = re.sub(r"\b\d+\b", "<n>", text)
    text = re.sub(r"\s+", " ", text).strip(" -:;；,，。")
    return text


def _phrase_fragments(text: str) -> list[str]:
    normalized = _normalize_phrase(text)
    if not normalized:
        return []
    pieces = re.split(r"[。；;|｜\n]+", normalized)
    fragments: list[str] = []
    for piece in pieces:
        cleaned = piece.strip(" -:;；,，。")
        if not cleaned:
            continue
        if len(cleaned) < 8 and not re.search(r"[A-Za-z]{4,}", cleaned):
            continue
        if len(cleaned) > 140:
            cleaned = cleaned[:137].rstrip() + "..."
        fragments.append(cleaned)
    return fragments


def _top_repeated_visible_phrases(
    recent_rows: list[dict[str, Any]],
    residue_rows: list[dict[str, Any]],
    dream_action_blocks: list[dict[str, Any]],
    reflection_action_blocks: list[dict[str, Any]],
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    phrases: list[str] = []
    for row in [*recent_rows, *residue_rows]:
        for value in _visible_values_from_row(row):
            phrases.extend(_phrase_fragments(value))
    for block in dream_action_blocks:
        for value in _visible_values_from_block(block, ("theme", "residue", "factual_status")):
            phrases.extend(_phrase_fragments(value))
    for block in reflection_action_blocks:
        for value in _visible_values_from_block(block, ("topic", "waking_residue", "boundary")):
            phrases.extend(_phrase_fragments(value))
    counts = Counter(phrases)
    return [
        {"phrase": phrase, "count": count}
        for phrase, count in counts.most_common(limit)
        if count >= 2
    ]


def _low_salience_leaks(
    residue_rows: list[dict[str, Any]],
    dream_action_blocks: list[dict[str, Any]],
    reflection_action_blocks: list[dict[str, Any]],
    salience_by_id: dict[str, float],
    *,
    threshold: float,
) -> list[dict[str, str]]:
    leaks: list[dict[str, str]] = []
    for row in residue_rows:
        exp_id = _row_experience_id(row)
        if exp_id and _row_salience(row) < threshold:
            leaks.append({"where": "action_residue", "experience_id": exp_id})
    for where, blocks in (("dream_seed", dream_action_blocks), ("reflection_queue", reflection_action_blocks)):
        for block in blocks:
            exp_id = _safe_str(block.get("experience_id"))
            if not exp_id:
                continue
            salience = salience_by_id.get(exp_id)
            if salience is not None and salience < threshold:
                leaks.append({"where": where, "experience_id": exp_id})
    return leaks


def _build_warnings(
    *,
    base_warnings: list[str],
    recent_rows: list[dict[str, Any]],
    residue_rows: list[dict[str, Any]],
    dream_action_blocks: list[dict[str, Any]],
    reflection_action_blocks: list[dict[str, Any]],
    low_leaks: list[dict[str, str]],
    repeated_themes: list[dict[str, Any]],
    repeated_phrases: list[dict[str, Any]],
    salience_by_id: dict[str, float],
) -> list[str]:
    warnings = list(base_warnings)
    recent_count = len(recent_rows)
    residue_count = len(residue_rows)
    dream_count = len(dream_action_blocks)
    reflection_count = len(reflection_action_blocks)

    if recent_count == 0:
        warnings.append("no_recent_action_experience")
    if residue_count > recent_count and recent_count:
        warnings.append(f"residue_count_exceeds_recent_actions:residue={residue_count}:recent={recent_count}")
    if recent_count >= 4 and residue_count / max(1, recent_count) > 0.5:
        warnings.append(f"residue_ratio_high:residue={residue_count}:recent={recent_count}")
    if low_leaks:
        warnings.append(f"low_salience_leak:count={len(low_leaks)}:threshold={LOW_SALIENCE_THRESHOLD}")
    if residue_count and dream_count > residue_count:
        warnings.append(f"over_dreamized_action_residue:dream={dream_count}:residue={residue_count}")
    if residue_count and reflection_count > residue_count:
        warnings.append(f"over_reflectionized_action_residue:reflection={reflection_count}:residue={residue_count}")
    if recent_count and (dream_count + reflection_count) / max(1, recent_count) > 0.8:
        warnings.append(
            f"action_metabolism_ratio_high:dream_plus_reflection={dream_count + reflection_count}:recent={recent_count}"
        )

    unmatched = 0
    for block in [*dream_action_blocks, *reflection_action_blocks]:
        exp_id = _safe_str(block.get("experience_id"))
        if exp_id and exp_id not in salience_by_id:
            unmatched += 1
    if unmatched:
        warnings.append(f"unmatched_action_experience_refs:{unmatched}")

    for item in repeated_themes[:3]:
        count = int(item.get("count") or 0)
        if count >= 4:
            warnings.append(f"repeated_action_theme:{item.get('theme')}:count={count}")
    for item in repeated_phrases[:3]:
        count = int(item.get("count") or 0)
        if count >= 3:
            warnings.append(f"repeated_visible_phrase:{item.get('phrase')}:count={count}")
    return warnings


def _health_status(warnings: list[str]) -> str:
    if any(
        warning.startswith(prefix)
        for warning in warnings
        for prefix in (
            "low_salience_leak:",
            "over_dreamized_action_residue:",
            "over_reflectionized_action_residue:",
            "residue_ratio_high:",
            "residue_count_exceeds_recent_actions:",
        )
    ):
        return "unhealthy"
    if any(warning.startswith("missing_input:") or warning.startswith("read_error:") for warning in warnings):
        return "unknown"
    if warnings:
        return "watch"
    return "healthy"


def run_audit(root: Path, *, low_salience_threshold: float = LOW_SALIENCE_THRESHOLD) -> dict[str, Any]:
    root = root.resolve()
    recent_rows, recent_warnings = read_action_openended_audit_jsonl(root / RECENT_ACTION_REL)
    residue_rows, residue_warnings = read_action_openended_audit_jsonl(root / ACTION_RESIDUE_REL)
    dream_text, dream_warnings = read_action_openended_audit_text(root / DREAM_SEEDS_REL)
    reflection_text, reflection_warnings = read_action_openended_audit_text(root / REFLECTION_QUEUE_REL)

    dream_blocks = _markdown_blocks(dream_text)
    reflection_blocks = _markdown_blocks(reflection_text)
    dream_action_blocks = _action_source_blocks(dream_blocks, "source_event")
    reflection_action_blocks = _action_source_blocks(reflection_blocks, "source")
    salience_by_id = _salience_index(recent_rows, residue_rows)
    low_leaks = _low_salience_leaks(
        residue_rows,
        dream_action_blocks,
        reflection_action_blocks,
        salience_by_id,
        threshold=low_salience_threshold,
    )
    action_rows = [*recent_rows, *residue_rows]
    repeated_themes = _top_repeated_action_themes(action_rows)
    repeated_phrases = _top_repeated_visible_phrases(
        recent_rows,
        residue_rows,
        dream_action_blocks,
        reflection_action_blocks,
    )
    warnings = _build_warnings(
        base_warnings=[*recent_warnings, *residue_warnings, *dream_warnings, *reflection_warnings],
        recent_rows=recent_rows,
        residue_rows=residue_rows,
        dream_action_blocks=dream_action_blocks,
        reflection_action_blocks=reflection_action_blocks,
        low_leaks=low_leaks,
        repeated_themes=repeated_themes,
        repeated_phrases=repeated_phrases,
        salience_by_id=salience_by_id,
    )
    health = _health_status(warnings)
    result = {
        "health_status": health,
        "recent_action_count": len(recent_rows),
        "residue_count": len(residue_rows),
        "dream_seed_from_action_count": len(dream_action_blocks),
        "reflection_from_action_count": len(reflection_action_blocks),
        "low_salience_leaked_count": len(low_leaks),
        "top_repeated_action_themes": repeated_themes,
        "top_repeated_visible_phrases": repeated_phrases,
        "warnings": warnings,
    }
    try:
        from xinyu_replicator_pressure_audit import assess_replicator_pressure

        result["replicator_pressure"] = assess_replicator_pressure(root, audit_result=result)
    except Exception:
        pass
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only audit for XinYu action experience sedimentation health."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="XinYu app root. Defaults to the directory containing this script.",
    )
    parser.add_argument(
        "--low-salience-threshold",
        type=float,
        default=LOW_SALIENCE_THRESHOLD,
        help="Salience below this value is treated as too low for residue/dream/reflection.",
    )
    args = parser.parse_args(argv)
    result = run_audit(args.root, low_salience_threshold=args.low_salience_threshold)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
