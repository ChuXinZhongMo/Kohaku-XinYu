from __future__ import annotations

import re

from xinyu_bridge_values import safe_str


def desktop_replace_frontmatter_field(text: str, field: str, value: str) -> str:
    replacement = f"{field}: {safe_str(value).strip() or 'none'}"
    updated, count = re.subn(
        rf"(?m)^{re.escape(field)}:\s*.*$",
        replacement,
        text,
        count=1,
    )
    if count:
        return updated
    return text.rstrip() + "\n" + replacement + "\n"


def desktop_replace_list_field(text: str, field: str, value: str) -> str:
    replacement = f"- {field}: {safe_str(value).strip() or 'none'}"
    updated, count = re.subn(
        rf"(?m)^-\s+{re.escape(field)}:\s*.*$",
        replacement,
        text,
        count=1,
    )
    if count:
        return updated
    return text.rstrip() + "\n" + replacement + "\n"
