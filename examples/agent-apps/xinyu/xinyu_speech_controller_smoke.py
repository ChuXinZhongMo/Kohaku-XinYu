from __future__ import annotations

from pathlib import Path

from xinyu_speech_controller import XinyuSpeechController


def _owner_payload() -> dict:
    return {"metadata": {"is_owner_user": True}}


def main() -> int:
    root = Path(__file__).resolve().parent
    controller = XinyuSpeechController(root)
    failures: list[str] = []

    style_text = "用词不像中文互联网的人说话，GPT味很重，我真的红温。"
    bad_reply = "我理解你的反馈，这说明系统输出层还没有达到预期，我会持续优化。"
    flags = controller.reply_quality_flags(
        payload=_owner_payload(),
        user_text=style_text,
        reply=bad_reply,
    )
    if not flags:
        failures.append("bad style-pressure reply was not flagged")
    if not any("template" in flag or "assistant" in flag for flag in flags):
        failures.append(f"bad reply missing assistant/template flag: {flags}")

    clean_reply = "别急着把我整个判没了，我知道这次刺到你了。"
    clean_flags = controller.reply_quality_flags(
        payload=_owner_payload(),
        user_text=style_text,
        reply=clean_reply,
    )
    if clean_flags:
        failures.append(f"clean pressure reply was unexpectedly flagged: {clean_flags}")

    newline_flags = controller.reply_quality_flags(
        payload=_owner_payload(),
        user_text=style_text,
        reply="我知道你为什么火。\n这次我不再写成说明书。",
    )
    if not any("line breaks" in flag for flag in newline_flags):
        failures.append("voluntary line break was not flagged")

    cliche_flags = controller.reply_quality_flags(
        payload=_owner_payload(),
        user_text=style_text,
        reply="简单来说，核心在于这不仅是语气问题，更是系统输出没有达到预期。",
    )
    if not cliche_flags:
        failures.append("GPT essay cliches were not flagged")
    if not any("not-but" in flag or "paired essay" in flag or "template" in flag for flag in cliche_flags):
        failures.append(f"GPT cliche reply missing expected flag: {cliche_flags}")

    technical_flags = controller.reply_quality_flags(
        payload=_owner_payload(),
        user_text="现在怎么设计这个最终说话控制器的代码？",
        reply="先抽成 xinyu_speech_controller.py，再接入 bridge 的最终出口。",
    )
    if technical_flags:
        failures.append(f"technical reply should not be pressure-gated: {technical_flags}")

    messages = controller.build_messages(
        payload=_owner_payload(),
        user_text=style_text,
        draft_reply=bad_reply,
        output_prompt="# Xinyu Output Layer\nPlain text only.",
        memory_context="[memory/self/voice_profile_zh.md]\n用词要像中文私聊。",
        conversation_tail="user: 你这句太像AI了",
        failed_reply=bad_reply,
        quality_flags=flags,
    )
    system = messages[0]["content"]
    user = messages[1]["content"]
    for marker in (
        "Final Speaking Controller Contract",
        "controller draft is semantic material only",
        "Retry Because Previous Visible Reply Failed",
        "QQ Style-Pressure Hard Mode",
    ):
        if marker not in system:
            failures.append(f"renderer system missing marker: {marker}")
    for marker in (
        "Controller Semantic Draft",
        "Persona Runtime State",
        "Memory Context",
        "Failure Flags",
    ):
        if marker not in user:
            failures.append(f"renderer user message missing marker: {marker}")

    fallback = controller.fallback_reply(payload=_owner_payload(), user_text=style_text)
    if not fallback:
        failures.append("style-pressure fallback was empty")
    elif controller.reply_quality_flags(payload=_owner_payload(), user_text=style_text, reply=fallback):
        failures.append(f"fallback did not pass quality gate: {fallback}")

    if failures:
        print("XinYu speech controller smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("XinYu speech controller smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
