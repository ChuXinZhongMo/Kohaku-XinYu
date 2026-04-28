from __future__ import annotations

import tempfile
from pathlib import Path

from xinyu_core_bridge import XinYuBridgeRuntime
from xinyu_life_posture import build_life_posture, write_life_posture_state
from xinyu_turn_classifier import classify_visible_turn


class _DummyController:
    def __init__(self) -> None:
        self._pending_injections: list[dict[str, str]] = []


class _DummyAgent:
    def __init__(self) -> None:
        self.controller = _DummyController()


def _payload(owner: bool = True) -> dict:
    return {"metadata": {"is_owner_user": owner}, "message_type": "private"}


def main() -> int:
    root = Path(__file__).resolve().parent
    failures: list[str] = []

    with tempfile.TemporaryDirectory(prefix="xinyu-life-posture-") as tmp:
        temp_root = Path(tmp)

        no_change_turn = classify_visible_turn(temp_root, payload=_payload(), user_text="怎么感觉没什么变化")
        guarded = build_life_posture(
            temp_root,
            payload=_payload(),
            user_text="怎么感觉没什么变化",
            evaluated_at="2026-04-27T20:00:00+08:00",
            visible_turn=no_change_turn,
        )
        if guarded.posture != "guarded_after_correction":
            failures.append(f"style pressure posture mismatch: {guarded.posture}")
        if "block proactive" not in guarded.no_proactive_constraint:
            failures.append("style pressure posture did not block proactive")

        tech = build_life_posture(
            temp_root,
            payload=_payload(),
            user_text="继续实现代码和测试",
            evaluated_at="2026-04-27T20:00:00+08:00",
        )
        if tech.posture != "technical_work_mode" or "implementation" not in tech.speech_bias:
            failures.append(f"technical posture mismatch: {tech}")

        rest = build_life_posture(
            temp_root,
            payload=_payload(),
            user_text="我困了，别追问",
            evaluated_at="2026-04-27T01:00:00+08:00",
        )
        if rest.posture != "sleepy_quiet":
            failures.append(f"rest posture mismatch: {rest.posture}")

        hot = build_life_posture(
            temp_root,
            payload=_payload(),
            user_text="广州今天好热，想开空调",
            evaluated_at="2026-04-27T15:00:00+08:00",
        )
        if hot.posture != "hot_daily" or "Guangzhou heat" not in hot.allowed_daily_anchors:
            failures.append(f"hot daily posture mismatch: {hot}")

        write_life_posture_state(temp_root, evaluated_at="2026-04-27T15:00:00+08:00", state=hot)
        state = (temp_root / "memory/context/current_life_posture.md").read_text(encoding="utf-8")
        for marker in (
            "memory_type: current_life_posture",
            "posture: hot_daily",
            "no_write_constraint:",
            "must not fabricate body access",
        ):
            if marker not in state:
                failures.append(f"life posture state missing marker: {marker}")

    agent = _DummyAgent()
    runtime = XinYuBridgeRuntime(
        xinyu_dir=root,
        turn_timeout_seconds=1,
        max_text_chars=1000,
        settle_seconds=0,
        outward_renderer=False,
        render_timeout_seconds=1,
        session_idle_ttl_seconds=10,
        max_sessions=0,
    )
    runtime._inject_live_turn_context(agent, payload=_payload(), text="怎么感觉没什么变化")
    content = agent.controller._pending_injections[0]["content"]
    for marker in (
        "Current Life Posture",
        "posture: guarded_after_correction",
        "one_line_speech_bias:",
    ):
        if marker not in content:
            failures.append(f"bridge pre-draft life posture missing marker: {marker}")

    if failures:
        print("Dynamic life posture smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Dynamic life posture smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
