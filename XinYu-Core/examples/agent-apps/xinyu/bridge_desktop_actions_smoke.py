from __future__ import annotations

from xinyu_bridge_desktop_actions import (
    desktop_action_pressure_label,
    desktop_action_result_label,
    desktop_action_theme_label,
    desktop_scrub_action_markers,
)
from xinyu_core_bridge import (
    _desktop_action_pressure_label,
    _desktop_action_result_label,
    _desktop_action_theme_label,
    _desktop_scrub_action_markers,
)


def main() -> int:
    failures: list[str] = []

    if desktop_action_result_label("success") != "已完成":
        failures.append("desktop result success label changed")
    if desktop_action_result_label("error") != "执行失败":
        failures.append("desktop result error label changed")
    if desktop_action_result_label("blocked_by_boundary") != "边界拦住":
        failures.append("desktop result boundary label changed")
    if desktop_action_result_label("custom action result with a long tail") != "custom action r...":
        failures.append("desktop result fallback compaction changed")

    if desktop_action_pressure_label("high") != "高负载":
        failures.append("desktop high pressure label changed")
    if desktop_action_pressure_label("medium") != "中负载":
        failures.append("desktop medium pressure label changed")
    if desktop_action_pressure_label("low") != "低负载":
        failures.append("desktop low pressure label changed")
    if desktop_action_pressure_label("") != "负载未知":
        failures.append("desktop empty pressure label changed")

    if desktop_action_theme_label("local action pressure after log_scan:xinyu_logs") != "xinyu_logs 日志扫描":
        failures.append("desktop action theme label changed")

    cleaned = desktop_scrub_action_markers(
        "reflection queue strong topic: action residue after local action pressure after codex_delegate:none"
    )
    for marker in ("reflection queue strong topic", "action residue after", "local action pressure"):
        if marker in cleaned:
            failures.append(f"desktop marker scrub leaked marker: {marker}")

    if _desktop_action_result_label("timeout") != desktop_action_result_label("timeout"):
        failures.append("core desktop result alias no longer delegates")
    if _desktop_action_pressure_label("unknown") != desktop_action_pressure_label("unknown"):
        failures.append("core desktop pressure alias no longer delegates")
    if _desktop_action_theme_label("local action pressure after codex_delegate:none") != desktop_action_theme_label(
        "local action pressure after codex_delegate:none"
    ):
        failures.append("core desktop theme alias no longer delegates")
    if _desktop_scrub_action_markers("codex_delegate:none") != desktop_scrub_action_markers("codex_delegate:none"):
        failures.append("core desktop scrub alias no longer delegates")

    if failures:
        print("XinYu bridge desktop actions smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu bridge desktop actions smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
