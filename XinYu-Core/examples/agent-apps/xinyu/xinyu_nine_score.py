"""Nine-score quality scorecard for XinYu Continuity Runtime.

Writes a machine-readable report under runtime/quality/nine_score_latest.json.
Does not invent a 9.0 — missing live signals stay conservative defaults.
Hard gates cap overall at 8.4 when failed (see OVERALL_CAP_ON_GATE_FAIL).

H4 (2026-07-17 deep-research): live composite scores are **agent-blind**.
Reply/proactive paths must not read overall/scores to steer generation.
Offline reweight uses only dimensions linked to hard owner outcomes.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

SCORECARD_REL = Path("runtime") / "quality" / "nine_score_latest.json"
WEIGHTS_REL = Path("runtime") / "quality" / "nine_score_weights.json"
OVERALL_CAP_ON_GATE_FAIL = 8.4
# Soft dims agent must never consume at reply time (H4).
AGENT_BLIND_SCORE_KEYS = frozenset(
    {
        "overall",
        "D1_oral",
        "D2_memory",
        "D3_proactive_restraint",
        "D4_autonomy_loop",
        "D5_live_stability",
        "D6_modularity",
        "D7_skills",
        "D8_body_feedback",
        "D9_ops_security",
    }
)
# Hard outcomes that may reweight soft dims offline (agent still cannot read scores).
HARD_OUTCOME_KEYS = (
    "empty_idle_sends",
    "silence_explain_rate",
    "future_effect_consumption_rate",
    "fact_hit_rate_72h",
    "lean_prompt_p50_chars",
    "private_chat_smoke_ok",
)
DIMENSION_WEIGHTS = {
    "D1_oral": 0.18,
    "D2_memory": 0.18,
    "D3_proactive_restraint": 0.12,
    "D4_autonomy_loop": 0.15,
    "D5_live_stability": 0.12,
    "D6_modularity": 0.10,
    "D7_skills": 0.05,
    "D8_body_feedback": 0.05,
    "D9_ops_security": 0.05,
}

_PROACTIVE_STATE_REL = Path("memory") / "context" / "proactive_request_state.md"
_ENV_ALLOW_AGENT_SCORE_READ = "XINYU_ALLOW_AGENT_NINE_SCORE_READ"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _clamp(value: float, lo: float = 0.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, float(value)))


def measure_lean_prompt_chars(sample_prompt: str) -> int:
    return len(str(sample_prompt or ""))


def _field_value(text: str, key: str) -> str:
    match = re.search(rf"^-\s*{re.escape(key)}:\s*(.*)$", text, flags=re.MULTILINE)
    if not match:
        return ""
    return match.group(1).strip()


def count_empty_idle_sends(root: Path) -> int:
    """Count owner_long_idle paths that would count as empty-concrete *sends*.

    Empty concrete_question with status blocked/none is correct silence (0).
    Only status in {sent, claimed} with empty concrete counts as a bad send.
    """
    path = Path(root) / _PROACTIVE_STATE_REL
    if not path.is_file():
        return 0
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return 0
    source = _field_value(text, "source")
    focus = _field_value(text, "focus_kind")
    status = _field_value(text, "status").lower()
    concrete = _field_value(text, "concrete_question")
    if source != "owner_long_idle" and focus != "owner_long_idle":
        return 0
    if concrete.strip():
        return 0
    if status in {"sent", "claimed"}:
        return 1
    return 0


def _default_scores(samples: dict[str, Any]) -> dict[str, float]:
    # Conservative engineering baseline; live owner ratings override via samples.
    base = {
        "D1_oral": float(samples.get("D1_oral", 7.5)),
        "D2_memory": float(samples.get("D2_memory", 7.0)),
        "D3_proactive_restraint": float(samples.get("D3_proactive_restraint", 8.0)),
        "D4_autonomy_loop": float(samples.get("D4_autonomy_loop", 7.0)),
        "D5_live_stability": float(samples.get("D5_live_stability", 7.5)),
        "D6_modularity": float(samples.get("D6_modularity", 4.0)),
        "D7_skills": float(samples.get("D7_skills", 4.0)),
        "D8_body_feedback": float(samples.get("D8_body_feedback", 5.5)),
        "D9_ops_security": float(samples.get("D9_ops_security", 6.0)),
    }
    return {key: _clamp(value) for key, value in base.items()}


def agent_may_read_live_scores() -> bool:
    """Live composite scores are agent-blind unless explicitly opened for ops tools."""
    raw = os.environ.get(_ENV_ALLOW_AGENT_SCORE_READ, "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def load_dimension_weights(root: Path | None = None) -> dict[str, float]:
    """Equal default weights, optionally overridden by offline reweight artifact."""
    weights = dict(DIMENSION_WEIGHTS)
    if root is None:
        return weights
    path = Path(root) / WEIGHTS_REL
    if not path.is_file():
        return weights
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return weights
    raw = data.get("weights") if isinstance(data, dict) else None
    if not isinstance(raw, dict):
        return weights
    merged: dict[str, float] = {}
    for key in DIMENSION_WEIGHTS:
        try:
            merged[key] = max(0.0, float(raw.get(key, DIMENSION_WEIGHTS[key])))
        except (TypeError, ValueError):
            merged[key] = DIMENSION_WEIGHTS[key]
    total = sum(merged.values())
    if total <= 0:
        return weights
    return {key: value / total for key, value in merged.items()}


def reweight_dimensions_by_hard_outcomes(
    *,
    base_weights: dict[str, float] | None = None,
    hard_outcomes: dict[str, Any] | None = None,
) -> dict[str, float]:
    """Offline reweight: boost dims linked to healthy hard outcomes; dilute null links.

    Does not invent causal proof — applies conservative, testable heuristics so
    equal-weight dilution (H4 research) is not the only mode.
    """
    weights = dict(base_weights or DIMENSION_WEIGHTS)
    outcomes = dict(hard_outcomes or {})
    # Start from base; scale selected dims by hard-outcome health.
    scale = {key: 1.0 for key in weights}

    empty_idle = int(outcomes.get("empty_idle_sends") or 0)
    silence = float(outcomes.get("silence_explain_rate") or 0.0)
    future_fx = float(outcomes.get("future_effect_consumption_rate") or 0.0)
    fact_hit = float(outcomes.get("fact_hit_rate_72h") or 0.0)
    lean = int(outcomes.get("lean_prompt_p50_chars") or 0)
    smoke = bool(outcomes.get("private_chat_smoke_ok"))

    # D3 linked to empty idle + silence explainability.
    if empty_idle == 0 and silence >= 0.95:
        scale["D3_proactive_restraint"] = 1.25
    elif empty_idle > 0 or silence < 0.5:
        scale["D3_proactive_restraint"] = 0.7

    # D2 linked to fact hit; null/low hit dilutes memory weight in composite.
    if fact_hit >= 0.90:
        scale["D2_memory"] = 1.2
    elif fact_hit < 0.5:
        scale["D2_memory"] = 0.65

    # D4/D8 linked to future_effect consumption.
    if future_fx >= 0.8:
        scale["D4_autonomy_loop"] = 1.15
        scale["D8_body_feedback"] = 1.2
    elif future_fx < 0.3:
        scale["D4_autonomy_loop"] = 0.75
        scale["D8_body_feedback"] = 0.7

    # D1 oral only gains weight when lean prompt is measured and healthy (proxy for not bloating).
    if 0 < lean < 12000:
        scale["D1_oral"] = 1.1
    elif lean >= 12000:
        scale["D1_oral"] = 0.75

    # D5 stability needs smoke ok; otherwise dilute.
    scale["D5_live_stability"] = 1.1 if smoke else 0.7

    # Dims without demonstrated hard-outcome link stay ≤1.0 (anti dilution by noise dims).
    for key in ("D6_modularity", "D7_skills", "D9_ops_security"):
        scale[key] = min(scale.get(key, 1.0), 1.0)

    scaled = {key: max(0.0, float(weights.get(key, 0.0)) * scale.get(key, 1.0)) for key in weights}
    total = sum(scaled.values())
    if total <= 0:
        return dict(DIMENSION_WEIGHTS)
    return {key: value / total for key, value in scaled.items()}


def write_dimension_weights(root: Path, weights: dict[str, float], *, note: str = "") -> Path:
    root = Path(root)
    path = root / WEIGHTS_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "updated_at": _now_iso(),
        "weights": {key: float(weights.get(key, 0.0)) for key in DIMENSION_WEIGHTS},
        "note": str(note or ""),
        "agent_blind": True,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def apply_offline_reweight(root: Path, hard_outcomes: dict[str, Any] | None = None) -> dict[str, float]:
    """Compute outcome-linked weights, persist, return normalized weights."""
    weights = reweight_dimensions_by_hard_outcomes(
        base_weights=DIMENSION_WEIGHTS,
        hard_outcomes=hard_outcomes,
    )
    write_dimension_weights(root, weights, note="offline_hard_outcome_reweight")
    return weights


def _weighted_overall(scores: dict[str, float], weights: dict[str, float] | None = None) -> float:
    use = weights or DIMENSION_WEIGHTS
    total = 0.0
    for key, weight in use.items():
        total += float(scores.get(key, 0.0)) * float(weight)
    return _clamp(total)


def operator_scorecard_view(report: dict[str, Any]) -> dict[str, Any]:
    """Full scorecard for ops/CLI only — not for prompt injection."""
    return dict(report or {})


def agent_safe_scorecard_view(report: dict[str, Any]) -> dict[str, Any]:
    """Strip soft scores; expose only hard gate facts the agent may need for silence policy.

    Soft dimension scores and overall remain operator-only (H4 agent-blind).
    """
    if agent_may_read_live_scores():
        return operator_scorecard_view(report)
    gates = dict((report or {}).get("gates") or {})
    return {
        "version": (report or {}).get("version"),
        "computed_at": (report or {}).get("computed_at"),
        "gates": {key: gates.get(key) for key in HARD_OUTCOME_KEYS if key in gates},
        "gates_pass": bool((report or {}).get("gates_pass")),
        "agent_blind": True,
        "scores": None,
    }


def gates_pass(gates: dict[str, Any]) -> bool:
    fact_hit = float(gates.get("fact_hit_rate_72h") or 0.0)
    empty_idle = int(gates.get("empty_idle_sends") or 0)
    lean_p50 = int(gates.get("lean_prompt_p50_chars") or 0)
    silence = float(gates.get("silence_explain_rate") or 0.0)
    future_fx = float(gates.get("future_effect_consumption_rate") or 0.0)
    smoke_ok = bool(gates.get("private_chat_smoke_ok"))
    if fact_hit < 0.90:
        return False
    if empty_idle != 0:
        return False
    if lean_p50 <= 0 or lean_p50 >= 12000:
        # 0 means unmeasured → fail hard gate until sampled
        if lean_p50 == 0:
            return False
        if lean_p50 >= 12000:
            return False
    if silence < 0.95:
        return False
    if future_fx < 0.50:
        return False
    if not smoke_ok:
        return False
    return True


def overall_capped_if_gates_fail(
    scores: dict[str, float],
    gates: dict[str, Any],
    weights: dict[str, float] | None = None,
) -> float:
    overall = _weighted_overall(scores, weights)
    if not gates_pass(gates):
        return min(overall, OVERALL_CAP_ON_GATE_FAIL)
    return overall


def compute_nine_score(root: Path, *, samples: dict[str, Any] | None = None) -> dict[str, Any]:
    samples = dict(samples or {})
    root = Path(root)
    scores = _default_scores(samples)

    empty_idle = samples.get("empty_idle_sends")
    if empty_idle is None:
        empty_idle = count_empty_idle_sends(root)
    empty_idle = int(empty_idle)

    lean_p50 = int(samples.get("lean_prompt_p50_chars") or 0)
    if lean_p50 <= 0:
        try:
            from xinyu_lean_prompt_samples import lean_prompt_p50_chars

            lean_p50 = int(lean_prompt_p50_chars(root) or 0)
        except Exception:
            lean_p50 = 0
    if lean_p50 <= 0 and samples.get("sample_prompt"):
        lean_p50 = measure_lean_prompt_chars(str(samples.get("sample_prompt")))

    fact_hit = float(samples.get("fact_hit_rate_72h") or 0.0)
    # Optional live probe hook (N1): xinyu_fact_hit_probe.run_fact_hit_probe
    if "fact_hit_rate_72h" not in samples:
        try:
            from xinyu_fact_hit_probe import run_fact_hit_probe

            probe = run_fact_hit_probe(root)
            fact_hit = float(probe.get("hit_rate") or 0.0)
        except Exception:
            fact_hit = 0.0

    if "future_effect_consumption_rate" not in samples:
        try:
            from xinyu_future_effect_instrumentation import future_effect_consumption_rate

            samples["future_effect_consumption_rate"] = float(
                future_effect_consumption_rate(root) or 0.0
            )
        except Exception:
            samples.setdefault("future_effect_consumption_rate", 0.0)

    if empty_idle == 0:
        scores["D3_proactive_restraint"] = max(scores["D3_proactive_restraint"], 8.5)
    else:
        scores["D3_proactive_restraint"] = min(scores["D3_proactive_restraint"], 5.0)

    if fact_hit >= 0.90:
        scores["D2_memory"] = max(scores["D2_memory"], 9.0)
    elif fact_hit >= 0.70:
        scores["D2_memory"] = max(scores["D2_memory"], 8.0)

    gates = {
        "fact_hit_rate_72h": fact_hit,
        "empty_idle_sends": empty_idle,
        "lean_prompt_p50_chars": lean_p50,
        "silence_explain_rate": float(samples.get("silence_explain_rate") or 0.0),
        "future_effect_consumption_rate": float(
            samples.get("future_effect_consumption_rate") or 0.0
        ),
        "private_chat_smoke_ok": bool(samples.get("private_chat_smoke_ok", False)),
    }
    # Prefer offline reweighted weights when present (H4).
    weights = load_dimension_weights(root)
    if samples.get("use_outcome_reweight"):
        weights = reweight_dimensions_by_hard_outcomes(
            base_weights=DIMENSION_WEIGHTS,
            hard_outcomes=gates,
        )
    overall = overall_capped_if_gates_fail(scores, gates, weights)
    scores["overall"] = overall
    return {
        "version": 1,
        "computed_at": _now_iso(),
        "scores": scores,
        "gates": gates,
        "gates_pass": gates_pass(gates),
        "weights": dict(weights),
        "agent_blind": True,
        "notes": list(samples.get("notes") or []),
    }


def write_nine_score(root: Path, report: dict[str, Any] | None = None) -> Path:
    root = Path(root)
    payload = report if report is not None else compute_nine_score(root)
    path = root / SCORECARD_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_nine_score(root: Path, *, agent_safe: bool = False) -> dict[str, Any]:
    """Load scorecard. agent_safe=True strips soft scores (H4) for any agent/prompt path."""
    path = Path(root) / SCORECARD_REL
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    if agent_safe:
        return agent_safe_scorecard_view(data)
    return data


def refresh_nine_scorecard(
    root: Path,
    *,
    samples: dict[str, Any] | None = None,
    persist_reweight: bool | None = None,
) -> dict[str, Any]:
    """Recompute scorecard; optionally persist outcome-linked weights from hard gates.

    persist_reweight:
      None → follow env XINYU_NINE_SCORE_AUTO_REWEIGHT (default off)
      True/False → force
    """
    root = Path(root)
    samples = dict(samples or {})
    if persist_reweight is None:
        raw = os.environ.get("XINYU_NINE_SCORE_AUTO_REWEIGHT", "").strip().lower()
        persist_reweight = raw in {"1", "true", "yes", "on"}
    report = compute_nine_score(root, samples=samples)
    if persist_reweight:
        apply_offline_reweight(root, report.get("gates") or {})
        samples = dict(samples)
        samples["use_outcome_reweight"] = True
        report = compute_nine_score(root, samples=samples)
        report.setdefault("notes", [])
        if isinstance(report["notes"], list):
            report["notes"] = list(report["notes"]) + ["offline_reweight_applied"]
    write_nine_score(root, report)
    # Always write agent-safe mirror for accidental agent reads.
    safe_path = root / "runtime" / "quality" / "nine_score_agent_safe.json"
    try:
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        safe_path.write_text(
            json.dumps(agent_safe_scorecard_view(report), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass
    return report
