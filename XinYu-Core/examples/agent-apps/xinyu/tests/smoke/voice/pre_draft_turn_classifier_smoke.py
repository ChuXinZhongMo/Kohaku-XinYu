from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

from pathlib import Path

from xinyu_core_bridge import XinYuBridgeRuntime
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
    root = ROOT
    failures: list[str] = []

    no_change = classify_visible_turn(root, payload=_payload(), user_text="怎么感觉没什么变化")
    if no_change.turn_kind != "owner_no_change_pressure":
        failures.append(f"no-change turn kind mismatch: {no_change.turn_kind}")
    if not no_change.owner_style_pressure or not no_change.owner_no_change_pressure:
        failures.append("no-change turn did not set style/no-change pressure flags")
    if no_change.technical_work:
        failures.append("no-change pressure should not be technical work")

    tech = classify_visible_turn(root, payload=_payload(), user_text="按照 plan 继续实现代码和测试")
    if tech.turn_kind != "technical_work" or not tech.technical_work:
        failures.append(f"technical turn not preserved: {tech}")
    if tech.max_visible_chars < 300:
        failures.append("technical turn was forced into tiny QQ length")

    daily = classify_visible_turn(root, payload=_payload(), user_text="广州今天好热，想开空调")
    if daily.turn_kind != "daily_life" or not daily.daily_life:
        failures.append(f"daily life turn mismatch: {daily.turn_kind}")

    rest = classify_visible_turn(root, payload=_payload(), user_text="我困了，别追问，先安静一会")
    if rest.turn_kind != "rest_silence" or rest.proactive_constraint != "block proactive during rest/silence boundary":
        failures.append(f"rest/silence turn mismatch: {rest}")

    external = classify_visible_turn(root, payload=_payload(owner=False), user_text="怎么感觉没什么变化")
    if external.turn_kind == "owner_no_change_pressure":
        failures.append("external contact should not become owner no-change pressure")

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
    agent = _DummyAgent()
    runtime._inject_live_turn_context(agent, payload=_payload(), text="怎么感觉没什么变化")
    injections = agent.controller._pending_injections
    if len(injections) != 1:
        failures.append(f"expected one pre-draft injection, got {len(injections)}")
    else:
        content = injections[0]["content"]
        for marker in (
            "Visible Turn Context",
            "turn_kind: owner_no_change_pressure",
            "owner_no_change_pressure: true",
            "answer with the changed short surface line itself",
        ):
            if marker not in content:
                failures.append(f"pre-draft injection missing marker: {marker}")

    if failures:
        print("Pre-draft turn classifier smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Pre-draft turn classifier smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
