"""Reorg meta-learning: track what reorganization modes actually change the system."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

META_STATE_REL = Path("memory") / "kernel" / "reorg_meta_state.json"

_DEFAULT_SLOW_ESCALATION_THRESHOLD = 3
_MIN_SLOW_ESCALATION_THRESHOLD = 2
_MAX_SLOW_ESCALATION_THRESHOLD = 5


def _meta_path(root: Path) -> Path:
    return root / META_STATE_REL


def compute_slow_escalation_threshold(meta: dict[str, Any]) -> int:
    """Derive slow→fast escalation count from rolling reorg effectiveness."""
    rec = str(meta.get("recommendation", "insufficient_data"))
    if rec == "consider_lower_slow_escalation_threshold":
        return _MIN_SLOW_ESCALATION_THRESHOLD
    if rec == "fast_reorg_often_ineffective_review_gates":
        return _MAX_SLOW_ESCALATION_THRESHOLD
    return _DEFAULT_SLOW_ESCALATION_THRESHOLD


def get_slow_escalation_threshold(root: Path | None) -> int:
    if root is None:
        return _DEFAULT_SLOW_ESCALATION_THRESHOLD
    meta = load_reorg_meta(root)
    threshold = meta.get("slow_escalation_threshold")
    if isinstance(threshold, int) and _MIN_SLOW_ESCALATION_THRESHOLD <= threshold <= _MAX_SLOW_ESCALATION_THRESHOLD:
        return threshold
    return compute_slow_escalation_threshold(meta)


def load_reorg_meta(root: Path) -> dict[str, Any]:
    path = _meta_path(root)
    if not path.exists():
        return {
            "fast_cycles": 0,
            "slow_cycles": 0,
            "fast_with_impact": 0,
            "slow_with_impact": 0,
            "skip_cycles": 0,
            "recommendation": "insufficient_data",
            "slow_escalation_threshold": _DEFAULT_SLOW_ESCALATION_THRESHOLD,
        }
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"recommendation": "load_error"}


def record_cycle_meta(root: Path, *, reorg_mode: str, structural_impact: bool) -> dict[str, Any]:
    """Update rolling reorg effectiveness stats after each cognitive cycle."""
    meta = load_reorg_meta(root)
    key = f"{reorg_mode}_cycles"
    if reorg_mode in ("fast", "slow", "skip"):
        meta[key] = int(meta.get(key, 0)) + 1
    if structural_impact and reorg_mode in ("fast", "slow"):
        meta[f"{reorg_mode}_with_impact"] = int(meta.get(f"{reorg_mode}_with_impact", 0)) + 1

    fast = int(meta.get("fast_cycles", 0))
    slow = int(meta.get("slow_cycles", 0))
    fast_hit = int(meta.get("fast_with_impact", 0))
    slow_hit = int(meta.get("slow_with_impact", 0))

    if fast + slow < 3:
        meta["recommendation"] = "insufficient_data"
    elif slow >= 5 and slow_hit == 0 and fast_hit > 0:
        meta["recommendation"] = "consider_lower_slow_escalation_threshold"
    elif fast > 0 and fast_hit / fast < 0.3:
        meta["recommendation"] = "fast_reorg_often_ineffective_review_gates"
    else:
        meta["recommendation"] = "balanced"

    meta["fast_impact_rate"] = round(fast_hit / fast, 3) if fast else 0.0
    meta["slow_impact_rate"] = round(slow_hit / slow, 3) if slow else 0.0
    meta["slow_escalation_threshold"] = compute_slow_escalation_threshold(meta)

    path = _meta_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta