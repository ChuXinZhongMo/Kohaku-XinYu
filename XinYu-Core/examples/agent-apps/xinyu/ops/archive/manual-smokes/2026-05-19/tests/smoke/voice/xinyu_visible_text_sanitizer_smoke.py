from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

from xinyu_visible_text_sanitizer import (
    sanitize_visible_text,
    visible_action_theme_label,
    visible_text_has_internal_prompt_leak,
    visible_text_has_tool_artifact,
)


def main() -> int:
    failures: list[str] = []
    raw = (
        "reflection queue strong topic: action residue after "
        "local action pressure after log_scan:minecraft_server; "
        "codex_delegate:none ended as failure pressure=medium; "
        "codex_delegate:n"
    )
    visible = sanitize_visible_text(raw)
    forbidden = (
        "reflection queue strong topic",
        "action residue after",
        "local action pressure",
        "log_scan:",
        "codex_delegate",
        "codex_delegate:n",
        "ended as failure",
        "pressure=medium",
    )
    for marker in forbidden:
        if marker in visible:
            failures.append(f"visible text sanitizer leaked marker: {marker}")
    for marker in ("我后面想反复想的是", "minecraft_server 的日志扫过", "我让 Codex 帮忙那次", "没有做成", "有点压着"):
        if marker not in visible:
            failures.append(f"visible text sanitizer missing visible marker: {marker}")

    if visible_action_theme_label("local action pressure after log_scan:xinyu_logs") != "我看过 xinyu_logs 日志那次":
        failures.append("visible action theme did not preserve log target label")
    if visible_action_theme_label("local action pressure after codex_delegate:none") != "我让 Codex 帮忙那次":
        failures.append("visible action theme did not humanize codex delegation")

    tool_artifact = "owner 留下了一次有轻微留痕意义的互动：[Tool batch completed] ## read_9601cfa6 - OK 1→-"
    if not visible_text_has_tool_artifact(tool_artifact):
        failures.append("tool artifact detector missed Codex tool batch output")
    cleaned_artifact = sanitize_visible_text(tool_artifact)
    for marker in ("[Tool batch completed]", "## read", "OK 1→", "owner 留下了一次有轻微留痕意义的互动"):
        if marker in cleaned_artifact:
            failures.append(f"tool artifact sanitizer leaked marker: {marker}")

    prompt_leak = (
        "It is not a safety ban on any protected class. "
        "If `resource_posture` is `normal`, treat it as ordinary chat. "
        "/think? </think>\u54e5\uff0c\u665a\u4e0a\u597d\u3002"
        "\u521a\u9192\u8fd8\u662f\u8fd8\u6ca1\u7761\u3002"
    )
    if not visible_text_has_internal_prompt_leak(prompt_leak):
        failures.append("internal prompt leak detector missed resource posture leak")
    cleaned_leak = sanitize_visible_text(prompt_leak)
    for marker in ("safety ban", "protected class", "resource_posture", "/think", "<think", "</think"):
        if marker in cleaned_leak.lower():
            failures.append(f"internal prompt sanitizer leaked marker: {marker}")
    if "\u54e5\uff0c\u665a\u4e0a\u597d\u3002" not in cleaned_leak:
        failures.append("internal prompt sanitizer removed the visible Chinese reply")

    if failures:
        print("XinYu visible text sanitizer smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu visible text sanitizer smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
