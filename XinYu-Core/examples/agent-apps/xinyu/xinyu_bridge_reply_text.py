from __future__ import annotations

import re


def normalize_bridge_reply(text: str) -> str:
    lines = [line.strip() for line in text.replace("\r\n", "\n").split("\n")]
    compact_lines: list[str] = []

    for line in lines:
        if not line.strip():
            continue
        line = re.sub(r"^\s*(?:[-*•>]+|\d+[.)])\s*", "", line).strip()
        line = re.sub(r"^\*{1,2}(.+?)\*{1,2}$", r"\1", line).strip()
        compact_lines.append(line)

    if not compact_lines:
        return ""

    reply = compact_lines[0]
    for line in compact_lines[1:]:
        if reply and reply[-1].isascii() and line and line[0].isascii():
            reply += " " + line
        else:
            reply += line
    return reply.strip()
