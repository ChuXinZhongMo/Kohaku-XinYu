from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_RUNTIME_REL = Path("runtime") / "dialogue_curiosity"


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _trim(text: str, limit: int = 180) -> str:
    clean = " ".join(_safe_str(text).split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1] + "..."


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8-sig", errors="replace").splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            rows.append({"_load_error": f"{path.name}:{line_number}: invalid_json", "raw": line[:180]})
            continue
        if isinstance(data, dict):
            rows.append(data)
    return rows


def _float_value(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _runtime_dir(root: Path) -> Path:
    return root / DEFAULT_RUNTIME_REL


def _counter_value(counter: Counter[str], key: str) -> int:
    return int(counter.get(key, 0))


def _marker_summary(rows: list[dict[str, Any]]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        reaction = row.get("reaction_features")
        if not isinstance(reaction, dict):
            continue
        markers = reaction.get("markers")
        if not isinstance(markers, dict):
            continue
        for category, values in markers.items():
            if not isinstance(values, list):
                continue
            for value in values:
                marker = _safe_str(value).strip()
                if marker:
                    counter[f"{category}:{marker}"] += 1
    return counter


def _actual_counter(rows: list[dict[str, Any]]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        actual = row.get("actual_next")
        if not isinstance(actual, dict):
            continue
        for key, value in actual.items():
            if _float_value(value) >= 0.5:
                counter[_safe_str(key)] += 1
    return counter


def _source_counter(rows: list[dict[str, Any]]) -> Counter[str]:
    return Counter(_safe_str(row.get("source_scope"), "unknown") or "unknown" for row in rows)


def _prediction_by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        prediction_id = _safe_str(row.get("prediction_id")).strip()
        if prediction_id:
            result[prediction_id] = row
    return result


def _format_counter(counter: Counter[str], *, limit: int = 8) -> list[str]:
    if not counter:
        return ["- none"]
    return [f"- {key}: {value}" for key, value in counter.most_common(limit)]


def _format_prediction_values(values: Any) -> str:
    if not isinstance(values, dict):
        return "unknown"
    parts: list[str] = []
    for key in ("style_complaint", "relationship_pressure_up", "technical_continue", "softening"):
        if key in values:
            parts.append(f"{key}={_float_value(values.get(key)):.2f}")
    return ", ".join(parts) if parts else "unknown"


def build_review(root: Path, *, limit: int = 10) -> str:
    runtime_dir = _runtime_dir(root)
    predictions = _load_jsonl(runtime_dir / "predictions.jsonl")
    evaluations = _load_jsonl(runtime_dir / "evaluations.jsonl")
    error_cases = _load_jsonl(runtime_dir / "error_cases.jsonl")
    predictions_by_id = _prediction_by_id(predictions)
    high_errors = sorted(error_cases, key=lambda row: _float_value(row.get("prediction_error")), reverse=True)
    evaluated_errors = [_float_value(row.get("prediction_error")) for row in evaluations]
    avg_error = sum(evaluated_errors) / len(evaluated_errors) if evaluated_errors else 0.0
    max_error = max(evaluated_errors) if evaluated_errors else 0.0
    actuals = _actual_counter(evaluations)
    sources = _source_counter(evaluations)
    markers = _marker_summary(error_cases)

    generated_at = datetime.now().astimezone().isoformat()
    lines: list[str] = [
        "# Dialogue Curiosity Review",
        "",
        f"- generated_at: {generated_at}",
        f"- root: {root}",
        f"- runtime_dir: {runtime_dir}",
        f"- predictions: {len(predictions)}",
        f"- evaluations: {len(evaluations)}",
        f"- high_error_cases: {len(error_cases)}",
        f"- average_prediction_error: {avg_error:.3f}",
        f"- max_prediction_error: {max_error:.3f}",
        "",
        "## Source Scopes",
        *_format_counter(sources),
        "",
        "## Actual Reaction Patterns",
        *_format_counter(actuals),
        "",
        "## High-Error Markers",
        *_format_counter(markers),
        "",
        "## Highest Error Cases",
    ]

    if not high_errors:
        lines.append("- none")
    for index, row in enumerate(high_errors[:limit], 1):
        prediction = predictions_by_id.get(_safe_str(row.get("prediction_id")), {})
        lines.extend(
            [
                "",
                f"### Case {index}",
                f"- prediction_id: {_safe_str(row.get('prediction_id'), 'unknown')}",
                f"- prediction_error: {_float_value(row.get('prediction_error')):.3f}",
                f"- evaluated_at: {_safe_str(row.get('evaluated_at'), 'unknown')}",
                f"- source_scope: {_safe_str(row.get('source_scope'), 'unknown')}",
                f"- predicted_next: {_format_prediction_values(prediction.get('predicted_next'))}",
                f"- actual_next: {_format_prediction_values(row.get('actual_next'))}",
                f"- previous_user: {_trim(_safe_str(prediction.get('user_preview')))}",
                f"- previous_reply: {_trim(_safe_str(prediction.get('reply_preview')))}",
                f"- next_user: {_trim(_safe_str(row.get('current_user_preview')))}",
            ]
        )
        reaction = row.get("reaction_features")
        if isinstance(reaction, dict):
            markers_obj = reaction.get("markers")
            if isinstance(markers_obj, dict):
                flat_markers: list[str] = []
                for category, values in markers_obj.items():
                    if isinstance(values, list):
                        flat_markers.extend(f"{category}:{_safe_str(value)}" for value in values[:4] if _safe_str(value))
                if flat_markers:
                    lines.append("- markers: " + ", ".join(flat_markers[:10]))

    lines.extend(
        [
            "",
            "## Readout",
            "- Use this report to judge whether high-error cases match real conversational failures.",
            "- Keep this loop as current-turn strategy influence until repeated patterns are reviewed.",
            "- Do not promote single cases directly into stable personality or voice profile.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only review for XinYu dialogue curiosity logs.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--output", type=Path, default=None, help="Optional Markdown output path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    report = build_review(root, limit=max(1, args.limit))
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"Wrote dialogue curiosity review: {args.output}")
        return 0
    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
