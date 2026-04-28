from __future__ import annotations

from pathlib import Path

from xinyu_core_bridge import XinYuBridgeRuntime


class FakeController:
    def __init__(self) -> None:
        self._pending_injections: list[dict[str, str]] = []


class FakeAgent:
    def __init__(self) -> None:
        self.controller = FakeController()


def test_bridge_injects_curiosity_soft_hint(tmp_path, monkeypatch) -> None:
    root = tmp_path / "xinyu"
    (root / "memory" / "context").mkdir(parents=True)
    (root / "memory" / "self").mkdir(parents=True)
    (root / "memory" / "relationships").mkdir(parents=True)
    (root / "memory" / "people").mkdir(parents=True)
    (root / "prompts").mkdir(parents=True)
    (root / "config.yaml").write_text("name: xinyu\n", encoding="utf-8")
    (root / "prompts" / "live_voice_card.md").write_text("# card\n", encoding="utf-8")
    (root / "memory" / "context" / "persona_surface_state.md").write_text("", encoding="utf-8")

    monkeypatch.setattr("xinyu_core_bridge.write_life_posture_state", lambda *args, **kwargs: None)
    monkeypatch.setattr("xinyu_core_bridge.refresh_current_life_month_context", lambda *args, **kwargs: "")
    monkeypatch.setattr("xinyu_core_bridge.refresh_memory_weight_state", lambda *args, **kwargs: "")

    runtime = XinYuBridgeRuntime(
        xinyu_dir=root,
        turn_timeout_seconds=3,
        max_text_chars=8000,
        settle_seconds=0,
        outward_renderer=False,
    )
    agent = FakeAgent()
    hint = "\n".join(
        [
            "## Dialogue Curiosity Soft Hint (This Turn Only)",
            "- previous_prediction_error: 0.82",
            "- stable_memory_write: blocked.",
        ]
    )

    runtime._inject_live_turn_context(
        agent,
        payload={"text": "还是很客服", "metadata": {"is_owner_user": True}},
        text="还是很客服",
        curiosity_context=hint,
    )

    content = agent.controller._pending_injections[0]["content"]
    assert "Dialogue Curiosity Soft Hint (This Turn Only)" in content
    assert "previous_prediction_error: 0.82" in content
    assert "stable_memory_write: blocked" in content

