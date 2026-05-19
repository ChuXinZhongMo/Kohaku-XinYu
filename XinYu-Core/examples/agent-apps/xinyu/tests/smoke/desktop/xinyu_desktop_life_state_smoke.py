from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import asyncio
import json
import tempfile
from pathlib import Path

from xinyu_action_experience_digest import digest_action_experience_residue
from xinyu_core_bridge import XinYuBridgeRuntime


def _seed_action_digest(root: Path) -> None:
    path = root / "runtime/life_kernel/action_experience_residue.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "experience_id": "exp-life-state-action-digest",
        "created_at": "2026-01-01T00:00:10+00:00",
        "tool": "log_scan",
        "target_alias": "xinyu_logs",
        "result": "failure",
        "pressure": {"score": 0.66, "band": "medium", "reasons": ["life_state_smoke"]},
        "salience": 0.74,
        "memory_candidates": ["desktop life state should carry action residue"],
        "outcome_summary": ["xinyu_logs had a smoke warning"],
        "notes": ["desktop_life_state_action_digest_smoke"],
    }
    path.write_text(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    digest_action_experience_residue(root, produced_at="2026-01-01T00:00:20+00:00", salience_threshold=0.6)


async def _smoke() -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-desktop-life-state-") as tmp:
        root = Path(tmp)
        (root / "memory").mkdir(parents=True, exist_ok=True)
        _seed_action_digest(root)
        runtime = XinYuBridgeRuntime(
            xinyu_dir=root,
            turn_timeout_seconds=1,
            max_text_chars=2000,
            settle_seconds=0.0,
            outward_renderer=False,
            renderer_mode="off",
            render_timeout_seconds=1,
            session_idle_ttl_seconds=60,
            max_sessions=2,
            proactive_min_interval_seconds=60,
            autonomous_maintenance_enabled=False,
        )
        snapshot = await runtime.desktop_snapshot({})
        state = snapshot.get("xinyuState")
        environment = snapshot.get("environment")
        entropy = snapshot.get("entropyState")
        self_choice = snapshot.get("selfChoiceState")
        health = snapshot.get("health") if isinstance(snapshot.get("health"), dict) else {}
        if not isinstance(state, dict):
            failures.append("desktop snapshot missing xinyuState")
        else:
            for key in (
                "mood_tag",
                "current_attention",
                "recent_concerns",
                "is_waiting_for_reply",
                "physical_sensation",
                "entropy_level",
                "entropy_band",
                "scar_level",
                "memory_decay_risk",
                "metabolism_needed",
                "action_experience_count",
                "action_residue_label",
                "action_residue_route",
            ):
                if key not in state:
                    failures.append(f"xinyuState missing {key}")
            if not state.get("physical_sensation"):
                failures.append("xinyuState physical_sensation is empty")
            if int(state.get("action_experience_count") or 0) < 1:
                failures.append(f"xinyuState did not count action experience digest: {state}")
            if "xinyu_logs" not in str(state.get("current_attention")):
                failures.append(f"xinyuState current_attention did not carry action residue: {state}")
            if "我没做成" not in str(state.get("action_residue_label")) and "没有做成" not in str(state.get("action_residue_label")):
                failures.append(f"xinyuState action_residue_label did not summarize result: {state}")
            if "行动余温" not in str(state.get("physical_sensation")):
                failures.append(f"xinyuState physical_sensation did not carry action load residue: {state}")
        if not isinstance(environment, dict) or "physicalSensation" not in environment:
            failures.append("desktop snapshot missing environment physicalSensation")
        if not isinstance(entropy, dict):
            failures.append("desktop snapshot missing entropyState")
        elif "entropy_level" not in entropy or "visible_artifact" not in entropy:
            failures.append(f"desktop entropyState missing core fields: {entropy}")
        if not isinstance(self_choice, dict):
            failures.append("desktop snapshot missing selfChoiceState")
        else:
            band = self_choice.get("affect_band") if isinstance(self_choice.get("affect_band"), dict) else {}
            for key in ("urge", "closure", "fatigue"):
                if key not in band:
                    failures.append(f"selfChoiceState affect_band missing {key}: {self_choice}")
            serialized = str(self_choice)
            for forbidden in ("urge_to_express", "self_closure", "baseline_urge", "baseline_closure"):
                if forbidden in serialized:
                    failures.append(f"selfChoiceState leaked raw field {forbidden}: {self_choice}")
        if not isinstance(health.get("self_choice"), dict):
            failures.append(f"desktop snapshot health missing self_choice: {health}")
        if snapshot.get("notes") != ["desktop_snapshot_v1_life_state"]:
            failures.append(f"desktop snapshot notes should identify life state v1: {snapshot.get('notes')}")
        if "activeDesires" not in snapshot:
            failures.append("desktop snapshot missing activeDesires")
        await runtime.shutdown()
    return failures


def main() -> int:
    failures = asyncio.run(_smoke())
    if failures:
        print("XinYu desktop life state smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu desktop life state smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
