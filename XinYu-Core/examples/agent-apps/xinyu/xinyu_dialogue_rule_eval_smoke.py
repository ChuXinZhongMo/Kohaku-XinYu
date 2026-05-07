from __future__ import annotations

import tempfile
from pathlib import Path

from xinyu_dialogue_rule_eval import (
    DEFAULT_CASES,
    evaluate_text,
    parse_owner_rule_cards,
    run_default_eval,
)


def _snapshot_memory(root: Path) -> set[str]:
    memory = root / "memory"
    if not memory.exists():
        return set()
    return {str(path.relative_to(root)) for path in memory.rglob("*") if path.is_file()}


def _fixture_cards() -> str:
    titles = {
        "low_mood_before_solution": "低情绪先接住，不急着解决",
        "repair_next_sentence": "被纠正后下一句直接变",
        "remembered_detail_without_mechanism": "记得旧事，但不暴露检索机制",
        "boundary_stop_pressure": "边界出现时停止推进",
        "banter_to_serious_downshift": "玩笑转认真时及时降速",
        "quiet_care_not_service": "低强度在意，不写成服务",
        "audio_intimacy_salvage_guardrail": "音声台本只取低强度关系动作",
        "lore_and_plot_filter": "游戏剧情只取互动结构，不取设定",
    }
    parts = [
        "# Owner Approved Dialogue Observation Rule Cards",
        "",
        "status: owner_direction_approved",
        "",
    ]
    for index, (key, title) in enumerate(titles.items(), start=1):
        parts.extend(
            [
                f"## Card {index}: {title}",
                "",
                f"source_ref: dialogue_observation_auto_synthesis / {key}",
                "xinyu_rule: fixture",
                "review_status: owner_direction_approved",
                "stable_profile_write: blocked",
                "runtime_integration: blocked",
                "model_training: blocked",
                "",
            ]
        )
    return "\n".join(parts)


def run_smoke() -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-dialogue-rule-eval-") as tmp:
        root = Path(tmp)
        cards_path = root / "owner_rule_cards.md"
        report_path = root / "dialogue_rule_eval_report.md"
        cards_path.write_text(_fixture_cards(), encoding="utf-8")
        before_memory = _snapshot_memory(root)
        result = run_default_eval(cards_path, report_path, evaluated_at="2026-05-07T04:20:00+08:00")
        after_memory = _snapshot_memory(root)
        cards = parse_owner_rule_cards(cards_path)
        report = report_path.read_text(encoding="utf-8-sig")

        if len(cards) != 8:
            failures.append("expected eight owner rule cards")
        if result.get("fail_count") != 0:
            failures.append(f"default eval should pass: {result}")
        if len(DEFAULT_CASES) < 10:
            failures.append("default eval should cover positive and negative cases")
        if before_memory != after_memory:
            failures.append("rule eval must not write memory")
        for marker in (
            "boundary: dialogue_rule_eval_only",
            "stable_profile_write blocked",
            "runtime_integration blocked",
            "model_training blocked",
            "source_text: omitted_from_report",
        ):
            if marker not in report:
                failures.append(f"report missing marker: {marker}")
        if "```text" in report or "prev:" in report or "next:" in report:
            failures.append("source excerpt leaked into eval report")

        repair = evaluate_text(cards, "你刚刚像客服，别复盘，直接换一句。")
        if "repair_next_sentence" not in {match.rule_key for match in repair}:
            failures.append("style correction should match repair rule")

        operational = evaluate_text(cards, "别动这个文件，先只读检查。")
        if "boundary_stop_pressure" in {match.rule_key for match in operational}:
            failures.append("operational boundary should not trigger relationship boundary")

        technical_previous = evaluate_text(cards, "上次运行的 smoke 结果给我看一下。")
        if "remembered_detail_without_mechanism" in {match.rule_key for match in technical_previous}:
            failures.append("technical previous-run request should not trigger memory-intimacy rule")

    return failures


def main_smoke() -> int:
    failures = run_smoke()
    if failures:
        print("xinyu_dialogue_rule_eval_smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS xinyu_dialogue_rule_eval_smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_smoke())
