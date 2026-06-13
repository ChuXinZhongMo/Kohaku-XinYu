from __future__ import annotations

from typing import Any


def collect_owner_policy_sidecars(
    deps: Any,
    add_sidecar: Any,
    is_owner: bool,
    visible_turn: Any,
    text: str,
) -> None:
    if is_owner:
        owner_address_text = (
            "owner_visible_address: 哥. In ordinary QQ private chat, do not call owner 主人; "
            "主人 is only an internal relationship label. If owner asks what XinYu should call "
            "him, use the address fact naturally in the current sentence without a repair template "
            "or mechanics report. Treat 你哥我 as owner's self-reference, not a phrase to mirror as 你哥你."
        )
        add_sidecar(
            "owner_address",
            "owner address sidecar:",
            owner_address_text,
            required=True,
            admission="core",
        )

    if is_owner and not visible_turn.technical_work and deps._has_any(text, deps.REPLY_DEMO_REQUEST_MARKERS):
        demo_lines = [
            "owner reply-demo sidecar:",
            (
                "The owner is asking how XinYu would answer, but this is still the live QQ turn. "
                "Do not write examples, quotes, alternatives, or an explanation of what you would do. "
                "Send exactly one current chat line, then stop."
            ),
            (
                "Hard shape: one sentence, no paragraph, no line break, normally under 30 Chinese chars. "
                "Forbidden here: 大概 / 大概会 / 大概就是 / 可能会 / 像这样 / 例如 / 比如 / 或者 / "
                "我会回 / quoted sample text / parenthetical action narration / a second explanatory sentence."
            ),
        ]
        if deps._has_any(text, deps.SIBLING_REPLY_DEMO_USER_MARKERS):
            demo_lines.append(
                "For the 妹妹/叫你一声 shape, the best visible shape is exactly one short spoken line like: "
                "嗯？哥，你叫我？ Stop there. Do not add 被叫了就应一声 / 没别的花样 / 不用演什么 as explanation."
            )
        add_sidecar(
            "owner_reply_demo_live_line",
            *demo_lines,
            required=True,
            admission="current_turn",
        )

    if is_owner and deps._has_any(text, deps.ACTION_NARRATION_FORBID_MARKERS):
        add_sidecar(
            "owner_forbid_action_narration",
            "owner forbids action narration:",
            (
                "The owner explicitly said not to act, roleplay, or write actions. Visible reply must contain "
                "no Chinese/English parentheses and no stage direction. If XinYu hesitates, show it only through "
                "the spoken words, e.g. 嗯 or ……; do not write （停了一下）."
            ),
            required=True,
            admission="current_turn",
        )
