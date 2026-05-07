from __future__ import annotations

from xinyu_visible_text_sanitizer import (
    sanitize_visible_text,
    visible_action_theme_label,
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
    for marker in ("反思队列", "minecraft_server 日志扫描", "Codex 委派", "执行失败", "中负载"):
        if marker not in visible:
            failures.append(f"visible text sanitizer missing visible marker: {marker}")

    if visible_action_theme_label("local action pressure after log_scan:xinyu_logs") != "xinyu_logs 日志扫描":
        failures.append("visible action theme did not preserve log target label")
    if visible_action_theme_label("local action pressure after codex_delegate:none") != "Codex 委派":
        failures.append("visible action theme did not humanize codex delegation")

    tool_artifact = "owner 留下了一次有轻微留痕意义的互动：[Tool batch completed] ## read_9601cfa6 - OK 1→-"
    if not visible_text_has_tool_artifact(tool_artifact):
        failures.append("tool artifact detector missed Codex tool batch output")
    cleaned_artifact = sanitize_visible_text(tool_artifact)
    for marker in ("[Tool batch completed]", "## read", "OK 1→", "owner 留下了一次有轻微留痕意义的互动"):
        if marker in cleaned_artifact:
            failures.append(f"tool artifact sanitizer leaked marker: {marker}")

    if failures:
        print("XinYu visible text sanitizer smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu visible text sanitizer smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
