"""Surface voice gate for QQ replies."""

from __future__ import annotations


SERVICE_TICS = (
    "作为一个AI",
    "作为AI",
    "希望这能帮助",
    "如果你需要",
    "总之",
    "综上",
    "首先",
    "其次",
    "最后",
)


def clean_voice(text: str) -> tuple[str, tuple[str, ...]]:
    notes: list[str] = []
    reply = " ".join(line.strip() for line in text.replace("\r\n", "\n").split("\n") if line.strip())
    for tic in SERVICE_TICS:
        if tic in reply:
            reply = reply.replace(tic, "")
            notes.append(f"removed:{tic}")
    reply = reply.strip(" ，,。")
    if len(reply) > 420:
        reply = reply[:420].rstrip(" ，,。") + "。"
        notes.append("truncated_for_qq")
    return reply, tuple(notes)

