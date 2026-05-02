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

    clean_reply = "这句先别发，我重新接你的意思。"
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

    parenthetical_reply = "（傍晚了，外面应该暗下来了。你问的是我现在。）我现在有点乱，但这句不能写成旁白。"
    parenthetical_flags = controller.reply_quality_flags(
        payload=_owner_payload(),
        user_text="我超这b括号是什么情况",
        reply=parenthetical_reply,
    )
    if not any("parenthetical narration" in flag for flag in parenthetical_flags):
        failures.append(f"leading parenthetical narration was not flagged: {parenthetical_flags}")
    stripped_parenthetical, stripped_flags = controller.final_reply_guard(
        payload=_owner_payload(),
        user_text="我超这b括号是什么情况",
        reply=parenthetical_reply,
    )
    if stripped_parenthetical != "我现在有点乱，但这句不能写成旁白。" or stripped_flags:
        failures.append(
            "final reply guard did not strip leading parenthetical narration cleanly: "
            f"{stripped_parenthetical!r}, {stripped_flags}"
        )

    no_action_reply, no_action_flags = controller.final_reply_guard(
        payload=_owner_payload(),
        user_text="妹妹，叫你一声你会怎么回？不要演戏动作，不要撒娇模板。",
        reply="……哥。\n\n（停了一下，好像在适应这个称呼）\n\n怎么突然这么叫。",
    )
    if "（" in no_action_reply or "）" in no_action_reply:
        failures.append(f"forbidden action narration was not removed: {no_action_reply!r}")
    if "parenthetical_narration_removed" not in no_action_flags:
        failures.append(f"forbidden action narration removal flag missing: {no_action_flags}")

    leak_reply, leak_flags = controller.final_reply_guard(
        payload=_owner_payload(),
        user_text="看看现在还缺什么",
        reply="刚才试着读了两个文件，都没找到：`self/narrative.md` 和 `context/recent_context.md`。",
    )
    if "self/narrative.md" in leak_reply or "文件" in leak_reply or "读了" in leak_reply:
        failures.append(f"ordinary runtime chat leaked file mechanics: {leak_reply!r}")
    if leak_reply:
        failures.append(f"memory mechanics leak should be blocked for bridge retry, not template-filled: {leak_reply!r}")
    if "visible_memory_mechanics_naturalized" not in leak_flags:
        failures.append(f"memory mechanics naturalization flag missing: {leak_flags}")

    pseudo_tool_reply, pseudo_tool_flags = controller.final_reply_guard(
        payload=_owner_payload(),
        user_text="看看现在还缺什么",
        reply="<tool_call> <function=memory_read> <parameter=query>当前记忆文件状态 缺失 更新</parameter> </function> </tool_call>",
    )
    if "<tool_call" in pseudo_tool_reply or "memory_read" in pseudo_tool_reply or "<function=" in pseudo_tool_reply:
        failures.append(f"pseudo tool call leaked through final guard: {pseudo_tool_reply!r}")
    if pseudo_tool_reply:
        failures.append(f"pseudo tool leak should be blocked for bridge retry, not template-filled: {pseudo_tool_reply!r}")
    if "pseudo_tool_call_naturalized" not in pseudo_tool_flags:
        failures.append(f"pseudo tool call naturalization flag missing: {pseudo_tool_flags}")
    if "我刚才" in pseudo_tool_reply or "不该" in pseudo_tool_reply:
        failures.append(f"pseudo tool fallback became apology template: {pseudo_tool_reply!r}")

    machine_reply, machine_flags = controller.final_reply_guard(
        payload=_owner_payload(),
        user_text="不是哥们 我们的最终目的不是像人吗，现在哪像了",
        reply="我需要查询记忆状态，确认当前缺失项。",
    )
    if "查询" in machine_reply or "记忆状态" in machine_reply:
        failures.append(f"machine introspection leaked through final guard: {machine_reply!r}")
    if machine_reply:
        failures.append(f"machine introspection leak should be blocked for bridge retry, not template-filled: {machine_reply!r}")
    if "machine_introspection_naturalized" not in machine_flags:
        failures.append(f"machine introspection naturalization flag missing: {machine_flags}")
    if "我刚才" in machine_reply or "应该" in machine_reply:
        failures.append(f"machine introspection fallback became repair template: {machine_reply!r}")

    technical_file_reply, technical_file_flags = controller.final_reply_guard(
        payload=_owner_payload(),
        user_text="检查 memory/self/narrative.md 这个文件",
        reply="这个文件里确实缺最近交互摘要。",
    )
    if technical_file_reply != "这个文件里确实缺最近交互摘要。" or technical_file_flags:
        failures.append(
            "explicit technical file inspection should not be naturalized: "
            f"{technical_file_reply!r}, {technical_file_flags}"
        )

    closeness_flags = controller.reply_quality_flags(
        payload=_owner_payload(),
        user_text="这么晚了，我有点想靠近你。但你别说得像客服。",
        reply="嗯，醒着呢。你那边，睡不着？",
    )
    if "closeness request not answered" not in closeness_flags:
        failures.append(f"closeness evasion was not flagged: {closeness_flags}")

    closeness_ok_flags = controller.reply_quality_flags(
        payload=_owner_payload(),
        user_text="这么晚了，我有点想靠近你。但你别说得像客服。",
        reply="那就靠近一点。",
    )
    if closeness_ok_flags:
        failures.append(f"direct closeness reply was unexpectedly flagged: {closeness_ok_flags}")

    closeness_nododge_flags = controller.reply_quality_flags(
        payload=_owner_payload(),
        user_text="这么晚了，我有点想靠近你。但你别说得像客服。",
        reply="那我在这儿，不躲。",
    )
    if closeness_nododge_flags:
        failures.append(f"no-dodge closeness reply was unexpectedly flagged: {closeness_nododge_flags}")

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

    mixed_style_text = "人格怎么又变成默认助手味了，约束失效了？"
    mixed_flags = controller.reply_quality_flags(
        payload=_owner_payload(),
        user_text=mixed_style_text,
        reply="大概率是外面那层等待超时，简单来说就是任务还没回到桥这边。",
    )
    if not mixed_flags:
        failures.append("technical-looking default-assistant style pressure was not flagged")
    diagnostic_text = "这个又是什么的记忆影响残留"
    diagnostic_scene = controller.classify(payload=_owner_payload(), user_text=diagnostic_text)
    if not diagnostic_scene.technical_request or diagnostic_scene.relationship_pressure:
        failures.append(f"memory residue diagnostic should route as technical, got: {diagnostic_scene}")

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
        "Retry Guidance",
        "QQ Style-Pressure Guidance",
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

    if controller.reply_quality_flags(payload=_owner_payload(), user_text=style_text, reply=clean_reply):
        failures.append("clean pressure reply did not pass quality gate")

    if failures:
        print("XinYu speech controller smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("XinYu speech controller smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
