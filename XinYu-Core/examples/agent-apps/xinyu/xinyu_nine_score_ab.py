"""E7 hard-outcome A/B sample: equal-weight vs outcome-reweight composites.

Compares overall under default DIMENSION_WEIGHTS vs reweight_dimensions_by_hard_outcomes
on the same soft scores + hard gates. Agent never consumes either live score.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_nine_score import (
    DIMENSION_WEIGHTS,
    agent_safe_scorecard_view,
    compute_nine_score,
    overall_capped_if_gates_fail,
    reweight_dimensions_by_hard_outcomes,
)

AB_REPORT_REL = Path("runtime") / "quality" / "nine_score_ab_latest.json"
AB_HISTORY_REL = Path("runtime") / "quality" / "nine_score_ab_history.jsonl"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def run_nine_score_ab_sample(
    root: Path,
    *,
    samples: dict[str, Any] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Run equal vs reweight A/B on current hard outcomes + soft scores."""
    root = Path(root)
    base = compute_nine_score(root, samples=samples)
    scores = {k: v for k, v in (base.get("scores") or {}).items() if k != "overall"}
    gates = dict(base.get("gates") or {})

    equal_weights = dict(DIMENSION_WEIGHTS)
    reweighted = reweight_dimensions_by_hard_outcomes(
        base_weights=DIMENSION_WEIGHTS,
        hard_outcomes=gates,
    )
    equal_overall = overall_capped_if_gates_fail(scores, gates, equal_weights)
    reweight_overall = overall_capped_if_gates_fail(scores, gates, reweighted)
    delta = float(reweight_overall) - float(equal_overall)

    # Weight deltas for explainability (ops only).
    weight_delta = {
        key: float(reweighted.get(key, 0.0)) - float(equal_weights.get(key, 0.0))
        for key in DIMENSION_WEIGHTS
    }

    report = {
        "version": 1,
        "sampled_at": _now_iso(),
        "gates": gates,
        "gates_pass": bool(base.get("gates_pass")),
        "equal": {
            "overall": equal_overall,
            "weights": equal_weights,
        },
        "reweight": {
            "overall": reweight_overall,
            "weights": reweighted,
        },
        "delta_overall": delta,
        "weight_delta": weight_delta,
        "agent_blind": True,
        "agent_safe_gates": agent_safe_scorecard_view(base).get("gates"),
        "notes": [
            "H4: soft scores not agent-readable",
            "E7: compare equal-weight vs hard-outcome reweight",
            f"auto_reweight_env={os.environ.get('XINYU_NINE_SCORE_AUTO_REWEIGHT', '0')}",
        ],
    }

    if persist:
        path = root / AB_REPORT_REL
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        hist = root / AB_HISTORY_REL
        try:
            with hist.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "sampled_at": report["sampled_at"],
                            "equal_overall": equal_overall,
                            "reweight_overall": reweight_overall,
                            "delta_overall": delta,
                            "gates_pass": report["gates_pass"],
                            "empty_idle_sends": gates.get("empty_idle_sends"),
                            "future_effect_consumption_rate": gates.get(
                                "future_effect_consumption_rate"
                            ),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        except OSError:
            pass
    return report


def load_nine_score_ab(root: Path) -> dict[str, Any]:
    path = Path(root) / AB_REPORT_REL
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def nine_score_status_fields(root: Path) -> dict[str, str]:
    """Operator status fields: gates + overall; never inject soft dims into prompts."""
    root = Path(root)
    try:
        from xinyu_nine_score import load_nine_score

        full = load_nine_score(root, agent_safe=False)
        safe = load_nine_score(root, agent_safe=True)
    except Exception:
        full, safe = {}, {}
    scores = full.get("scores") if isinstance(full.get("scores"), dict) else {}
    gates = safe.get("gates") if isinstance(safe.get("gates"), dict) else {}
    if not gates and isinstance(full.get("gates"), dict):
        gates = full["gates"]
    ab = load_nine_score_ab(root)
    auto_rw = os.environ.get("XINYU_NINE_SCORE_AUTO_REWEIGHT", "0").strip() or "0"
    return {
        "nine_score_computed_at": str(full.get("computed_at") or "missing"),
        "nine_score_overall": str(scores.get("overall", "missing")),
        "nine_score_gates_pass": str(bool(full.get("gates_pass"))).lower()
        if full
        else "missing",
        "nine_score_agent_blind": "true",
        "nine_score_empty_idle_sends": str(gates.get("empty_idle_sends", "missing")),
        "nine_score_silence_explain_rate": str(gates.get("silence_explain_rate", "missing")),
        "nine_score_future_effect_rate": str(
            gates.get("future_effect_consumption_rate", "missing")
        ),
        "nine_score_lean_prompt_p50": str(gates.get("lean_prompt_p50_chars", "missing")),
        "nine_score_fact_hit_rate_72h": str(gates.get("fact_hit_rate_72h", "missing")),
        "nine_score_auto_reweight": auto_rw,
        "nine_score_ab_delta": str(ab.get("delta_overall", "missing")),
        "nine_score_ab_equal_overall": str(
            (ab.get("equal") or {}).get("overall", "missing")
            if isinstance(ab.get("equal"), dict)
            else "missing"
        ),
        "nine_score_ab_reweight_overall": str(
            (ab.get("reweight") or {}).get("overall", "missing")
            if isinstance(ab.get("reweight"), dict)
            else "missing"
        ),
    }
