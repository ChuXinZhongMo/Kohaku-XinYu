"""Kernel self-story from World Model + Reorg/Cycle history (Higher Goal 1 / K-011).

Generates an auditable engineering narrative — not LLM prose, not owner-facing
memory/self/narrative.md. Output: memory/kernel/self_story.md
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SELF_STORY_REL = Path("memory") / "kernel" / "self_story.md"
SELF_STORY_STATE_REL = Path("memory") / "kernel" / "self_story_state.json"


def _read_jsonl_tail(path: Path, limit: int = 8) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").strip().splitlines()
    except Exception:
        return []
    events: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def build_self_story(kernel_self: Any, root: Path | None = None) -> dict[str, Any]:
    """Compose self-story sections from kernel state + recent event history."""
    model = kernel_self.get_self_model()
    goals = kernel_self.get_active_goals(3)
    beliefs = kernel_self.get_stable_beliefs(0.65)
    wm_ctx = kernel_self.world_model_to_context()
    cycle_state = kernel_self.cognitive_cycle_state

    reorg_events: list[dict[str, Any]] = []
    cycle_events: list[dict[str, Any]] = []
    if root is not None:
        event_dir = root / "memory" / "events"
        reorg_events = _read_jsonl_tail(event_dir / "reorg_events.jsonl", 6)
        cycle_events = _read_jsonl_tail(event_dir / "cognitive_cycle_events.jsonl", 6)

    structural_moments = []
    for ev in cycle_events:
        if ev.get("structural_impact"):
            structural_moments.append(
                f"cycle {ev.get('source_event_id', '?')}: mode={ev.get('reorg_mode')} "
                f"importance={ev.get('importance')} error={ev.get('error_magnitude')}"
            )
    for ev in reorg_events:
        if ev.get("structural_impact") or ev.get("applied_count", 0) > 0:
            actions = ", ".join(ev.get("applied_actions") or []) or "none"
            structural_moments.append(
                f"reorg {ev.get('source_event_id', '?')}: applied=[{actions}] "
                f"pending={ev.get('pending_review_count', 0)}"
            )

    orientation = model.get("core_summary") or "No stable core statements yet."
    goal_text = "; ".join(g.description[:60] for g in goals) if goals else "No active goals."
    belief_text = "; ".join(b["content"][:60] for b in beliefs[:3]) if beliefs else "No stable beliefs yet."

    paragraphs = [
        "## Current Orientation",
        orientation,
        "",
        "## Active Motivations",
        goal_text,
        "",
        "## Stable Beliefs",
        belief_text,
        "",
        "## World Model Anchor",
        wm_ctx or "World model not yet populated.",
        "",
        "## Continuity Markers",
        (
            f"self_id={kernel_self.self_id}; cycles={cycle_state.cycle_count}; "
            f"slow_signals={cycle_state.slow_signal_count}; "
            f"last_fast_reorg={cycle_state.last_fast_reorg_event_id or 'none'}"
        ),
        "",
        "## Recent Structural Changes",
    ]
    if structural_moments:
        paragraphs.extend(f"- {m}" for m in structural_moments[-5:])
    else:
        paragraphs.append("- No recorded structural changes yet.")

    body = "\n".join(paragraphs)
    return {
        "self_id": kernel_self.self_id,
        "cycle_count": cycle_state.cycle_count,
        "structural_moment_count": len(structural_moments),
        "body": body,
        "summary": body.split("\n\n")[0].replace("## Current Orientation\n", "")[:300],
    }


def write_self_story(root: Path, story: dict[str, Any]) -> dict[str, Any]:
    """Persist self-story markdown + state json."""
    out_dir = root / "memory" / "kernel"
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "self_story.md"
    state_path = out_dir / "self_story_state.json"

    header = (
        f"<!-- kernel self-story | self_id={story.get('self_id')} "
        f"| cycles={story.get('cycle_count')} | auto-generated -->\n\n"
    )
    md_path.write_text(header + story.get("body", ""), encoding="utf-8")

    state = {
        "self_id": story.get("self_id"),
        "cycle_count": story.get("cycle_count"),
        "structural_moment_count": story.get("structural_moment_count", 0),
        "summary": story.get("summary", ""),
        "path": str(SELF_STORY_REL).replace("\\", "/"),
    }
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"written": True, "md_path": str(md_path), "state": state}


def maybe_update_self_story(
    kernel_self: Any,
    root: Path | None,
    *,
    force: bool = False,
    structural_impact: bool = False,
) -> dict[str, Any]:
    """Update self-story when structural impact occurs or every 5 cycles."""
    if root is None:
        return {"updated": False, "reason": "no_root"}

    cycle_count = kernel_self.cognitive_cycle_state.cycle_count
    should = force or structural_impact or (cycle_count > 0 and cycle_count % 5 == 0)
    if not should:
        return {"updated": False, "reason": "rate_limited", "cycle_count": cycle_count}

    story = build_self_story(kernel_self, root)
    write_result = write_self_story(root, story)
    return {"updated": True, "cycle_count": cycle_count, **write_result}