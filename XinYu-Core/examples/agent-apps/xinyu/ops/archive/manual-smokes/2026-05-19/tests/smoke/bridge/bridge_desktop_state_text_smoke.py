from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from datetime import datetime

from xinyu_bridge_desktop_state_text import desktop_replace_frontmatter_field, desktop_replace_list_field
from xinyu_core_bridge import XinYuBridgeRuntime


def _field_value(text: str, field: str) -> str:
    for line in text.splitlines():
        if line.startswith(f"{field}: "):
            return line.split(": ", 1)[1]
        if line.startswith(f"- {field}: "):
            return line.split(": ", 1)[1]
    return ""


def main() -> int:
    failures: list[str] = []

    frontmatter = "updated_at: old\nname: x\n"
    if desktop_replace_frontmatter_field(frontmatter, "updated_at", "new") != "updated_at: new\nname: x\n":
        failures.append("desktop frontmatter field replacement changed")
    appended_frontmatter = desktop_replace_frontmatter_field("name: x\n", "updated_at", "")
    try:
        datetime.fromisoformat(_field_value(appended_frontmatter, "updated_at"))
    except ValueError:
        failures.append("desktop frontmatter timestamp default is not parseable ISO")

    list_text = "- status: requested\n- owner: x\n"
    if desktop_replace_list_field(list_text, "status", "sent") != "- status: sent\n- owner: x\n":
        failures.append("desktop list field replacement changed")
    if desktop_replace_list_field("- owner: x\n", "status", "") != "- owner: x\n- status: none\n":
        failures.append("desktop list field append/default changed")
    appended_list = desktop_replace_list_field("- owner: x\n", "updated_at", "")
    try:
        datetime.fromisoformat(_field_value(appended_list, "updated_at"))
    except ValueError:
        failures.append("desktop list timestamp default is not parseable ISO")

    if (
        XinYuBridgeRuntime._desktop_replace_frontmatter_field is not desktop_replace_frontmatter_field
        or XinYuBridgeRuntime._desktop_replace_list_field is not desktop_replace_list_field
    ):
        failures.append("core desktop state text aliases no longer delegate")

    if failures:
        print("XinYu bridge desktop state text smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu bridge desktop state text smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
