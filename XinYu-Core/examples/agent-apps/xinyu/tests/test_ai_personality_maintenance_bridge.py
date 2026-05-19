from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = Path(__file__).resolve().parents[4] / "src"
CUSTOM_DIR = ROOT / "custom"
for path in (CORE_SRC, CUSTOM_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from ai_self_iteration_gate_bridge_plugin import AiSelfIterationGateBridgePlugin  # noqa: E402
from ai_self_iteration_review_bridge_plugin import AiSelfIterationReviewBridgePlugin  # noqa: E402
from personality_growth_gate_bridge_plugin import PersonalityGrowthGateBridgePlugin  # noqa: E402


class _Ctx:
    def __init__(self, working_dir: Path):
        self.working_dir = str(working_dir)
        self._state: dict[str, str] = {}

    def get_state(self, key: str) -> str:
        return self._state.get(key, "")

    def set_state(self, key: str, value: str) -> None:
        self._state[key] = value


def test_ai_self_iteration_gate_keeps_domain_checks_before_cooldown(tmp_path: Path) -> None:
    _write(tmp_path / "memory/context/turn_mode_state.md", "- mode: maintenance_schedule_turn\n")
    _write(tmp_path / "memory/context/maintenance_recommendations.md", "- ai_self_iteration_gate: yes\n")
    _write(tmp_path / "memory/knowledge/general.md", "- question_id: other\n")
    _write(tmp_path / "memory/knowledge/learning_quality_state.md", "- quality_grade: stable\n")
    ctx = _Ctx(tmp_path)
    plugin = AiSelfIterationGateBridgePlugin({"min_interval_seconds": 60})
    asyncio.run(plugin.on_load(ctx))  # type: ignore[arg-type]
    ctx.set_state("ai_self_iteration_gate_last_run", datetime.now().astimezone().isoformat())

    assert plugin._should_run(tmp_path) == (False, "no_q006_knowledge")

    _write(tmp_path / "memory/knowledge/general.md", "- question_id: q-006\n")
    should_run, reason = plugin._should_run(tmp_path)
    assert should_run is False
    assert reason.startswith("cooldown:")


def test_ai_self_iteration_review_keeps_owner_stale_and_cooldown_semantics(tmp_path: Path) -> None:
    _write(tmp_path / "memory/context/turn_mode_state.md", "- mode: maintenance_schedule_turn\n")
    _write(tmp_path / "memory/context/capability_zones_state.md", "")
    _write(tmp_path / "memory/self/ai_self_iteration_state.md", "- gate_status: growth_review_candidate\n")
    _write(
        tmp_path / "memory/self/ai_self_iteration_review_state.md",
        "- review_permission: owner_visible_review_required\n- input_gate_status: growth_review_candidate\n",
    )
    ctx = _Ctx(tmp_path)
    plugin = AiSelfIterationReviewBridgePlugin({"min_interval_seconds": 60})
    asyncio.run(plugin.on_load(ctx))  # type: ignore[arg-type]
    ctx.set_state("ai_self_iteration_review_last_run", datetime.now().astimezone().isoformat())

    _write(
        tmp_path / "memory/context/owner_permission_grants.md",
        "- grant_ai_self_iteration_review: approved_for_non_stable_planning\n",
    )
    assert plugin._should_run(tmp_path) == (True, "owner_grant_refresh")

    _write(tmp_path / "memory/context/owner_permission_grants.md", "")
    _write(
        tmp_path / "memory/self/ai_self_iteration_review_state.md",
        "- review_permission: owner_approved_for_non_stable_planning\n- input_gate_status: stale\n",
    )
    assert plugin._should_run(tmp_path) == (True, "review_missing_or_stale")

    _write(
        tmp_path / "memory/self/ai_self_iteration_review_state.md",
        "- review_permission: owner_approved_for_non_stable_planning\n- input_gate_status: growth_review_candidate\n",
    )
    should_run, reason = plugin._should_run(tmp_path)
    assert should_run is False
    assert reason.startswith("cooldown:")

    ctx.set_state("ai_self_iteration_review_last_run", "not-a-datetime")
    assert plugin._should_run(tmp_path) == (True, "bad_last_run")

    ctx.set_state(
        "ai_self_iteration_review_last_run",
        (datetime.now().astimezone() - timedelta(seconds=120)).isoformat(),
    )
    assert plugin._should_run(tmp_path) == (True, "cooldown_ready")


def test_personality_growth_gate_delegates_to_maintenance_helper(tmp_path: Path) -> None:
    _write(tmp_path / "memory/context/turn_mode_state.md", "- mode: maintenance_schedule_turn\n")
    _write(tmp_path / "memory/context/maintenance_recommendations.md", "- personality_growth_gate: yes\n")
    ctx = _Ctx(tmp_path)
    plugin = PersonalityGrowthGateBridgePlugin({"min_interval_seconds": 60})
    asyncio.run(plugin.on_load(ctx))  # type: ignore[arg-type]

    assert plugin._should_run(tmp_path) == (True, "ready")
    ctx.set_state("personality_growth_gate_last_run", datetime.now().astimezone().isoformat())
    should_run, reason = plugin._should_run(tmp_path)
    assert should_run is False
    assert reason.startswith("cooldown:")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
