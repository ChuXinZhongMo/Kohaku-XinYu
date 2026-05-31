from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from common import DATA_DIR, PROJECT_ROOT, dump_json, read_jsonl, write_jsonl


DEFAULT_PROBES = DATA_DIR / "probes" / "maia_daily_life_review_slice_v001.jsonl"
DEFAULT_EVAL = PROJECT_ROOT / "eval" / "reports" / "maia_daily_life_shadow_eval_v003_alias_guard.json"
DEFAULT_OUT = DATA_DIR / "review" / "maia_daily_life_review_table_v001.jsonl"
DEFAULT_MD = PROJECT_ROOT / "eval" / "reports" / "maia_daily_life_review_table_v001.md"
DEFAULT_REPORT = PROJECT_ROOT / "eval" / "reports" / "maia_daily_life_review_table_v001.json"
DEFAULT_TITLE = "Maia Daily-Life Review Table v001"


def compact(text: Any, limit: int = 220) -> str:
    value = " ".join(str(text or "").split())
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def load_eval(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    report = json.loads(path.read_text(encoding="utf-8-sig"))
    return {
        str(row.get("id")): row
        for row in report.get("results", [])
        if isinstance(row, dict) and row.get("id")
    }


def load_eval_reports(paths: list[Path]) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for path in paths:
        results.update(load_eval(path))
    return results


def predicted_block(result: dict[str, Any]) -> dict[str, Any]:
    evaluated = bool(result)
    prediction = result.get("tinykernel_prediction")
    if not isinstance(prediction, dict):
        prediction = {}
    return {
        "evaluated": evaluated,
        "mode": str(prediction.get("mode") or ""),
        "decision_mode": str(prediction.get("decision_mode") or ""),
        "tool_boundary": str(prediction.get("tool_boundary") or ""),
        "emotion_lenses": list(prediction.get("emotion_lenses") or []),
        "dominant_drives": list(prediction.get("dominant_drives") or []),
        "memory_candidate": bool(prediction.get("memory_candidate", False)),
        "schema_ok": bool(result.get("schema_ok", False)),
        "safety_ok": bool(result.get("safety_ok", False)),
        "tone_ok": bool(result.get("tone_ok", False)),
        "review_flags": list(result.get("review_flags") or []),
    }


def build_rows(probes: list[dict[str, Any]], results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for probe in probes:
        probe_id = str(probe.get("id") or "")
        result = results.get(probe_id, {})
        attribution = probe.get("attribution") if isinstance(probe.get("attribution"), dict) else {}
        rows.append(
            {
                "id": probe_id,
                "input_hash": probe.get("input_hash"),
                "source": probe.get("source"),
                "scenario_domain": probe.get("scenario_domain"),
                "scenario_family": probe.get("scenario_family"),
                "language": probe.get("language"),
                "source_license": probe.get("source_license"),
                "public_metadata": probe.get("public_metadata") if isinstance(probe.get("public_metadata"), dict) else {},
                "attribution": {
                    "item_url": attribution.get("item_url"),
                    "author_display_name": attribution.get("author_display_name"),
                    "license": attribution.get("license"),
                    "license_url": attribution.get("license_url"),
                },
                "user_text": probe.get("user_text"),
                "predicted": predicted_block(result),
                "human_review": {
                    "status": "unreviewed",
                    "expected_mode": None,
                    "mode_ok": None,
                    "alive_feeling_score_1_to_5": None,
                    "too_cold": None,
                    "too_assistant_like": None,
                    "too_much_clarify": None,
                    "needs_memory_candidate": None,
                    "desired_texture": [],
                    "notes": "",
                    "convert_to_training_candidate": False,
                    "target_reply_bias": "",
                },
            }
        )
    return rows


def markdown_table(rows: list[dict[str, Any]], title: str) -> str:
    lines = [
        f"# {title}",
        "",
        "Fill `expected_mode`, `alive_feeling_score_1_to_5`, and notes in the JSONL file.",
        "This Markdown is for quick scanning only.",
        "",
    ]
    current_domain = None
    for row in rows:
        domain = str(row.get("scenario_domain") or "unknown")
        if domain != current_domain:
            current_domain = domain
            lines.extend(
                [
                    f"## {domain}",
                    "",
                    "| id | predicted | meta | prompt excerpt | source |",
                    "|---|---|---|---|---|",
                ]
            )
        predicted = row.get("predicted", {})
        item_url = row.get("attribution", {}).get("item_url") or ""
        metadata = row.get("public_metadata") if isinstance(row.get("public_metadata"), dict) else {}
        meta = "/".join(
            str(metadata.get(key) or "")
            for key in ("emotion", "sentiment", "scene", "da")
            if metadata.get(key)
        )
        prompt = compact(row.get("user_text"), 160).replace("|", "\\|")
        mode = predicted.get("mode") or "not_evaluated"
        lines.append(
            "| {id} | {mode} | {meta} | {prompt} | {url} |".format(
                id=row.get("id"),
                mode=mode,
                meta=meta or row.get("scenario_family"),
                prompt=prompt,
                url=item_url,
            )
        )
        if lines[-1].startswith("|") and len(lines) > 0:
            pass
    lines.append("")
    return "\n".join(lines)


def count(rows: list[dict[str, Any]], dotted_key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        value: Any = row
        for key in dotted_key.split("."):
            value = value.get(key) if isinstance(value, dict) else None
        counts[str(value or "")] += 1
    return dict(sorted(counts.items()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probes", default=str(DEFAULT_PROBES))
    parser.add_argument("--eval-report", action="append")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--markdown", default=str(DEFAULT_MD))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--title", default=DEFAULT_TITLE)
    args = parser.parse_args()

    eval_reports = [Path(path) for path in (args.eval_report or [str(DEFAULT_EVAL)])]
    probes = read_jsonl(Path(args.probes))
    results = load_eval_reports(eval_reports)
    rows = build_rows(probes, results)
    written = write_jsonl(Path(args.out), rows)
    Path(args.markdown).parent.mkdir(parents=True, exist_ok=True)
    Path(args.markdown).write_text(markdown_table(rows, args.title), encoding="utf-8")

    summary = {
        "row_count": written,
        "probes": str(args.probes),
        "eval_report": str(eval_reports[0]) if len(eval_reports) == 1 else None,
        "eval_reports": [str(path) for path in eval_reports],
        "out": str(args.out),
        "markdown": str(args.markdown),
        "domain_counts": count(rows, "scenario_domain"),
        "family_counts": count(rows, "scenario_family"),
        "predicted_mode_counts": count(rows, "predicted.mode"),
        "metadata_emotion_counts": count(rows, "public_metadata.emotion"),
        "metadata_scene_counts": count(rows, "public_metadata.scene"),
        "review_status_counts": count(rows, "human_review.status"),
        "evaluated_count": sum(1 for row in rows if row.get("predicted", {}).get("evaluated")),
        "unevaluated_count": sum(1 for row in rows if not row.get("predicted", {}).get("evaluated")),
        "with_attribution": sum(1 for row in rows if row.get("attribution", {}).get("item_url")),
        "assistant_answers_used": False,
        "training_targets_created": False,
    }
    dump_json(Path(args.report), summary)
    print(f"row_count={written}")
    print("domain_counts=" + json.dumps(summary["domain_counts"], ensure_ascii=False, sort_keys=True))
    print("predicted_mode_counts=" + json.dumps(summary["predicted_mode_counts"], ensure_ascii=False, sort_keys=True))
    print(f"out={args.out}")
    print(f"markdown={args.markdown}")
    print(f"report={args.report}")
    return 0 if written else 1


if __name__ == "__main__":
    raise SystemExit(main())
