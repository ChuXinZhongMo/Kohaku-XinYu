from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path


CUSTOM_DIR = Path(__file__).resolve().parents[1] / "custom"
if str(CUSTOM_DIR) not in sys.path:
    sys.path.insert(0, str(CUSTOM_DIR))

from maintenance_bridge_utils import append_trace, maintenance_should_run, resolve_root, run_maintenance_bridge_once  # noqa: E402
from consolidation_bridge_plugin import ConsolidationBridgePlugin  # noqa: E402
from dream_output_bridge_plugin import DreamOutputBridgePlugin  # noqa: E402
from long_term_memory_gate_bridge_plugin import LongTermMemoryGateBridgePlugin  # noqa: E402
from question_pipeline_bridge_plugin import QuestionPipelineBridgePlugin  # noqa: E402
from reflection_output_bridge_plugin import ReflectionOutputBridgePlugin  # noqa: E402
from research_handoff_bridge_plugin import ResearchHandoffBridgePlugin  # noqa: E402
from slow_reprocess_bridge_plugin import SlowReprocessBridgePlugin  # noqa: E402
from source_gate_bridge_plugin import SourceGateBridgePlugin  # noqa: E402
from source_search_provider_bridge_plugin import SourceSearchProviderBridgePlugin  # noqa: E402


class _Ctx:
    def __init__(self, working_dir: Path):
        self.working_dir = str(working_dir)
        self._state: dict[str, str] = {}

    def get_state(self, key: str) -> str:
        return self._state.get(key, "")

    def set_state(self, key: str, value: str) -> None:
        self._state[key] = value


def test_maintenance_should_run_checks_turn_dispatch_recommendation_and_cooldown(tmp_path: Path) -> None:
    _write(tmp_path / "memory/context/turn_mode_state.md", "- mode: maintenance_schedule_turn\n")
    _write(tmp_path / "memory/context/maintenance_dispatch_state.md", "- deferred: source_gate\n")
    _write(tmp_path / "memory/context/maintenance_recommendations.md", "- source_gate: yes\n")
    ctx = _Ctx(tmp_path)

    assert resolve_root(ctx) == tmp_path
    assert maintenance_should_run(
        ctx,
        tmp_path,
        state_key="source_gate_last_run",
        min_interval_seconds=60,
        recommendation_markers=("- source_gate: yes",),
        dispatch_markers=("- deferred: source_gate",),
    ) == (True, "ready")

    ctx.set_state("source_gate_last_run", datetime.now().astimezone().isoformat())
    should_run, reason = maintenance_should_run(
        ctx,
        tmp_path,
        state_key="source_gate_last_run",
        min_interval_seconds=60,
        recommendation_markers=("- source_gate: yes",),
        dispatch_markers=("- deferred: source_gate",),
    )

    assert should_run is False
    assert reason.startswith("cooldown:")


def test_append_trace_writes_owner_trace_path(tmp_path: Path) -> None:
    append_trace(tmp_path, "memory/knowledge/source_gate_trace.log", "ok")

    text = (tmp_path / "memory/knowledge/source_gate_trace.log").read_text(encoding="utf-8")
    assert "ok" in text


def test_run_maintenance_bridge_once_runs_engine_sets_state_and_traces(tmp_path: Path) -> None:
    ctx = _Ctx(tmp_path)

    def engine(root: Path, *, checked_at: str, mode: str) -> dict[str, object]:
        assert root == tmp_path
        assert checked_at
        assert mode == "runtime_test"
        return {"candidate_count": 2}

    run_maintenance_bridge_once(
        ctx,  # type: ignore[arg-type]
        tmp_path,
        trace_rel="memory/knowledge/test_trace.log",
        should_run=lambda root: (root == tmp_path, "ready"),
        state_key="test_last_run",
        engine=engine,
        timestamp_arg="checked_at",
        mode="runtime_test",
        trace_label="runtime_test",
        result_summary=lambda result: f"candidate_count={result['candidate_count']}",
    )

    assert ctx.get_state("test_last_run")
    text = (tmp_path / "memory/knowledge/test_trace.log").read_text(encoding="utf-8")
    assert "post_llm_call should_run=True reason=ready" in text
    assert "runtime_test candidate_count=2" in text


def test_source_gate_bridge_delegates_maintenance_gate(tmp_path: Path) -> None:
    _write(tmp_path / "memory/context/turn_mode_state.md", "- mode: maintenance_schedule_turn\n")
    _write(tmp_path / "memory/context/maintenance_dispatch_state.md", "- deferred: source_gate\n")
    _write(tmp_path / "memory/context/maintenance_recommendations.md", "- source_gate: yes\n")
    ctx = _Ctx(tmp_path)
    plugin = SourceGateBridgePlugin({"min_interval_seconds": 60})

    asyncio.run(plugin.on_load(ctx))  # type: ignore[arg-type]

    assert plugin._should_run(tmp_path) == (True, "ready")
    ctx.set_state("source_gate_last_run", datetime.now().astimezone().isoformat())
    should_run, reason = plugin._should_run(tmp_path)
    assert should_run is False
    assert reason.startswith("cooldown:")


def test_source_search_provider_bridge_preserves_activation_gate(tmp_path: Path) -> None:
    _write(tmp_path / "memory/context/turn_mode_state.md", "- mode: maintenance_schedule_turn\n")
    _write(tmp_path / "memory/context/maintenance_recommendations.md", "- source_search_provider: yes\n")
    _write(
        tmp_path / "memory/knowledge/autonomous_search_activation_state.md",
        "- activation_permission: hold\n",
    )
    ctx = _Ctx(tmp_path)
    plugin = SourceSearchProviderBridgePlugin({"min_interval_seconds": 60})
    asyncio.run(plugin.on_load(ctx))  # type: ignore[arg-type]

    assert plugin._should_run(tmp_path) == (False, "activation_not_allowed")

    _write(
        tmp_path / "memory/knowledge/autonomous_search_activation_state.md",
        "- activation_permission: provider_allowed\n",
    )
    assert plugin._should_run(tmp_path) == (True, "ready")


def test_consolidation_bridge_needs_only_maintenance_turn_then_cooldown(tmp_path: Path) -> None:
    _write(tmp_path / "memory/context/turn_mode_state.md", "- mode: maintenance_schedule_turn\n")
    ctx = _Ctx(tmp_path)
    plugin = ConsolidationBridgePlugin({"min_interval_seconds": 60})
    asyncio.run(plugin.on_load(ctx))  # type: ignore[arg-type]

    assert plugin._should_run(tmp_path) == (True, "ready")

    ctx.set_state("consolidation_last_run", datetime.now().astimezone().isoformat())
    should_run, reason = plugin._should_run(tmp_path)
    assert should_run is False
    assert reason.startswith("cooldown:")


def test_long_term_memory_gate_keeps_recommendation_guard(tmp_path: Path) -> None:
    _write(tmp_path / "memory/context/turn_mode_state.md", "- mode: maintenance_schedule_turn\n")
    _write(tmp_path / "memory/context/maintenance_recommendations.md", "- retention_gate: yes\n")
    ctx = _Ctx(tmp_path)
    plugin = LongTermMemoryGateBridgePlugin({"min_interval_seconds": 60})
    asyncio.run(plugin.on_load(ctx))  # type: ignore[arg-type]

    assert plugin._should_run(tmp_path) == (False, "recommendation_not_yes")

    _write(tmp_path / "memory/context/maintenance_recommendations.md", "- long_term_memory_gate: yes\n")
    assert plugin._should_run(tmp_path) == (True, "ready")


def test_question_and_slow_reprocess_keep_dispatch_roles(tmp_path: Path) -> None:
    _write(tmp_path / "memory/context/turn_mode_state.md", "- mode: maintenance_schedule_turn\n")
    _write(tmp_path / "memory/context/maintenance_dispatch_state.md", "- primary: question_pipeline\n")
    ctx = _Ctx(tmp_path)
    question = QuestionPipelineBridgePlugin({"min_interval_seconds": 60})
    slow = SlowReprocessBridgePlugin({"min_interval_seconds": 60})
    asyncio.run(question.on_load(ctx))  # type: ignore[arg-type]
    asyncio.run(slow.on_load(ctx))  # type: ignore[arg-type]

    assert question._should_run(tmp_path) == (True, "ready")
    assert slow._should_run(tmp_path) == (False, "dispatch_not_secondary")

    _write(tmp_path / "memory/context/maintenance_dispatch_state.md", "- secondary: slow_reprocess\n")
    assert question._should_run(tmp_path) == (False, "dispatch_not_primary")
    assert slow._should_run(tmp_path) == (True, "ready")

    ctx.set_state("slow_reprocess_last_run", datetime.now().astimezone().isoformat())
    should_run, reason = slow._should_run(tmp_path)
    assert should_run is False
    assert reason.startswith("cooldown:")


def test_reflection_and_dream_output_keep_recommendation_seed_and_cooldown_gates(tmp_path: Path) -> None:
    _write(tmp_path / "memory/context/turn_mode_state.md", "- mode: maintenance_schedule_turn\n")
    _write(tmp_path / "memory/context/maintenance_recommendations.md", "- reflection_output: yes\n")
    ctx = _Ctx(tmp_path)
    reflection = ReflectionOutputBridgePlugin({"min_interval_seconds": 60})
    dream = DreamOutputBridgePlugin({"min_interval_seconds": 60, "export_enabled": False})
    asyncio.run(reflection.on_load(ctx))  # type: ignore[arg-type]
    asyncio.run(dream.on_load(ctx))  # type: ignore[arg-type]

    assert reflection._should_run(tmp_path) == (True, "ready")
    assert dream._should_run(tmp_path) == (False, "recommendation_not_yes")

    _write(tmp_path / "memory/context/maintenance_recommendations.md", "- dream_output: yes\n")
    assert dream._should_run(tmp_path) == (False, "no_unconsumed_dream_seed")

    _write(
        tmp_path / "memory/dreams/dream_seeds.md",
        """# Dream Seeds

## seed-test-001
- theme: runtime residue
- residue: still unsettled
- emotional_weight: 80
- factual_status: confirmed interaction
- dream_permission: can_recombine_but_not_rewrite_fact
- consumed_at: none
- dream_count: 0
- last_dreamed_at: none
- decay_after_dream: soft_decay_after_reflection
""",
    )
    assert dream._should_run(tmp_path) == (True, "ready")

    ctx.set_state("dream_output_last_run", datetime.now().astimezone().isoformat())
    should_run, reason = dream._should_run(tmp_path)
    assert should_run is False
    assert reason.startswith("cooldown:")


def test_research_handoff_keeps_research_needed_gate(tmp_path: Path) -> None:
    _write(tmp_path / "memory/context/turn_mode_state.md", "- mode: maintenance_schedule_turn\n")
    ctx = _Ctx(tmp_path)
    plugin = ResearchHandoffBridgePlugin({"min_interval_seconds": 60})
    asyncio.run(plugin.on_load(ctx))  # type: ignore[arg-type]

    assert plugin._should_run(tmp_path) == (False, "research_not_needed")

    _write(tmp_path / "memory/context/self_thought_state.md", "- research_needed: true\n")
    assert plugin._should_run(tmp_path) == (True, "ready")

    ctx.set_state("research_handoff_last_run", datetime.now().astimezone().isoformat())
    should_run, reason = plugin._should_run(tmp_path)
    assert should_run is False
    assert reason.startswith("cooldown:")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
