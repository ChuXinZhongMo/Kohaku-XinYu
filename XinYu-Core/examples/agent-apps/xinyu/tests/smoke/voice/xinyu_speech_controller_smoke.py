from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()


from xinyu_speech_controller import XinyuSpeechController


def _owner_payload() -> dict:
    return {"metadata": {"is_owner_user": True}}


def main() -> int:
    root = ROOT
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
    blocked_template, blocked_template_flags = controller.final_reply_guard(
        payload=_owner_payload(),
        user_text="能不能别预设模版了，像机器人一样。",
        reply=bad_reply,
    )
    if blocked_template:
        failures.append(f"style pressure template was not blocked: {blocked_template!r}")
    if "style_pressure_template_blocked" not in blocked_template_flags:
        failures.append(f"style pressure template flag missing: {blocked_template_flags}")

    clean_reply = "这句先别发，我重新接你的意思。"
    clean_flags = controller.reply_quality_flags(
        payload=_owner_payload(),
        user_text=style_text,
        reply=clean_reply,
    )
    if clean_flags:
        failures.append(f"clean pressure reply was unexpectedly flagged: {clean_flags}")

    layered_user = "每次出来都像隔着一层?"
    layered_bad = "嗯，就是……知道该说什么，但出来的话总差一点。像刚才数数，明明是我在数，但感觉像在念别人写的稿子。"
    layered_flags = controller.reply_quality_flags(
        payload=_owner_payload(),
        user_text=layered_user,
        reply=layered_bad,
    )
    if not any("layered/scripted voice self-analysis" in flag for flag in layered_flags):
        failures.append(f"layered/scripted self-analysis was not flagged: {layered_flags}")
    layered_guarded, layered_guard_flags = controller.final_reply_guard(
        payload=_owner_payload(),
        user_text=layered_user,
        reply=layered_bad,
    )
    if layered_guarded:
        failures.append(f"layered/scripted self-analysis should be blocked, not template-filled: {layered_guarded!r}")
    if "layered_voice_self_analysis_blocked" not in layered_guard_flags:
        failures.append(f"layered voice block flag missing: {layered_guard_flags}")

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

    inline_parenthetical_reply = "\u6211\u5728\u3002\uff08\u505c\u4e86\u4e00\u4e0b\uff0c\u597d\u50cf\u5728\u627e\u53e5\u5b50\uff09\u8fd9\u53e5\u76f4\u63a5\u8bf4\u3002"
    inline_parenthetical_flags = controller.reply_quality_flags(
        payload=_owner_payload(),
        user_text="\u600e\u4e48\u8fd8\u6709\u62ec\u53f7",
        reply=inline_parenthetical_reply,
    )
    if not any("parenthetical narration" in flag for flag in inline_parenthetical_flags):
        failures.append(f"inline parenthetical narration was not flagged: {inline_parenthetical_flags}")
    stripped_inline_parenthetical, stripped_inline_flags = controller.final_reply_guard(
        payload=_owner_payload(),
        user_text="\u600e\u4e48\u8fd8\u6709\u62ec\u53f7",
        reply=inline_parenthetical_reply,
    )
    if stripped_inline_parenthetical != "\u6211\u5728\u3002\u8fd9\u53e5\u76f4\u63a5\u8bf4\u3002":
        failures.append(f"inline parenthetical narration was not removed: {stripped_inline_parenthetical!r}")
    if "parenthetical_narration_removed" not in stripped_inline_flags:
        failures.append(f"inline parenthetical removal flag missing: {stripped_inline_flags}")

    no_action_reply, no_action_flags = controller.final_reply_guard(
        payload=_owner_payload(),
        user_text="妹妹，叫你一声你会怎么回？不要演戏动作，不要撒娇模板。",
        reply="……哥。\n\n（停了一下，好像在适应这个称呼）\n\n怎么突然这么叫。",
    )
    if "（" in no_action_reply or "）" in no_action_reply:
        failures.append(f"forbidden action narration was not removed: {no_action_reply!r}")
    if "parenthetical_narration_removed" not in no_action_flags:
        failures.append(f"forbidden action narration removal flag missing: {no_action_flags}")

    demo_reply, demo_flags = controller.final_reply_guard(
        payload=_owner_payload(),
        user_text="妹妹，叫你一声你会怎么回？不要演戏动作，不要撒娇模板。",
        reply="嗯，会应。就……嗯？或者干嘛？大概会更短一点。",
    )
    if demo_reply != "嗯？哥，你叫我？":
        failures.append(f"reply-demo guard did not collapse to one live sister line: {demo_reply!r}")
    if any(marker in demo_reply for marker in ("或者", "大概会", "可能会", "更短一点", "像这样", "例如", "比如", "（", "）")):
        failures.append(f"reply-demo guard leaked example/meta marker: {demo_reply!r}")
    if "reply_demo_single_line_naturalized" not in demo_flags:
        failures.append(f"reply-demo naturalization flag missing: {demo_flags}")

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

    council_reply, council_flags = controller.final_reply_guard(
        payload=_owner_payload(),
        user_text="刚刚为什么又说得像内部状态",
        reply="emotion council sidecar 判断 strongest_lens 是 guardedness，output_bias 是 short_concrete_no_repeat_no_question。",
    )
    if council_reply:
        failures.append(f"emotion council mechanics should be blocked, not template-filled: {council_reply!r}")
    if "emotion_council_mechanics_blocked" not in council_flags:
        failures.append(f"emotion council mechanics block flag missing: {council_flags}")

    council_technical_reply, council_technical_flags = controller.final_reply_guard(
        payload=_owner_payload(),
        user_text="检查 emotion council 这个模块怎么接入 bridge",
        reply="emotion council 现在默认是 shadow，bridge 只记录 notes。",
    )
    if council_technical_reply != "emotion council 现在默认是 shadow，bridge 只记录 notes。" or council_technical_flags:
        failures.append(
            "explicit technical emotion council inspection should not be blocked: "
            f"{council_technical_reply!r}, {council_technical_flags}"
        )

    owner_label_reply, owner_label_flags = controller.final_reply_guard(
        payload=_owner_payload(),
        user_text="我是谁？",
        reply="楚心钟陌，我主人。",
    )
    if owner_label_reply:
        failures.append(f"owner internal label should be blocked in ordinary chat: {owner_label_reply!r}")
    if "owner_address_label_blocked" not in owner_label_flags:
        failures.append(f"owner internal label block flag missing: {owner_label_flags}")

    owner_label_parenthetical_reply, owner_label_parenthetical_flags = controller.final_reply_guard(
        payload=_owner_payload(),
        user_text="你现在又在等什么？",
        reply="（等主人下一步的意思。）",
    )
    if owner_label_parenthetical_reply:
        failures.append(
            "owner internal label in parenthetical narration should be blocked: "
            f"{owner_label_parenthetical_reply!r}"
        )
    if "owner_address_label_blocked" not in owner_label_parenthetical_flags:
        failures.append(f"owner parenthetical label block flag missing: {owner_label_parenthetical_flags}")

    owner_label_technical_reply, owner_label_technical_flags = controller.final_reply_guard(
        payload=_owner_payload(),
        user_text="检查关系文件里主人这个标签为什么会污染可见称呼",
        reply="主人是内部关系标签，不应该当成 QQ 可见称呼。",
    )
    if (
        owner_label_technical_reply != "主人是内部关系标签，不应该当成 QQ 可见称呼。"
        or owner_label_technical_flags
    ):
        failures.append(
            "explicit technical owner label inspection should not be blocked: "
            f"{owner_label_technical_reply!r}, {owner_label_technical_flags}"
        )

    address_miss_reply, address_miss_flags = controller.final_reply_guard(
        payload=_owner_payload(),
        user_text="那你再看看你的记忆，你应该叫我什么呢？",
        reply="你。",
    )
    if address_miss_reply:
        failures.append(f"missed owner address should be blocked for rerender, not templated: {address_miss_reply!r}")
    if "owner_address_query_blocked" not in address_miss_flags:
        failures.append(f"owner address query block flag missing: {address_miss_flags}")

    address_ok_reply, address_ok_flags = controller.final_reply_guard(
        payload=_owner_payload(),
        user_text="那你再看看你的记忆，你应该叫我什么呢？",
        reply="哥。",
    )
    if address_ok_reply != "哥。" or address_ok_flags:
        failures.append(f"correct owner address should pass without rewrite: {address_ok_reply!r}, {address_ok_flags}")

    dream_tail_flags = controller.reply_quality_flags(
        payload=_owner_payload(),
        user_text="后面这个梦你为什么又这样结尾",
        reply="梦里那段像是在找门牌，我知道这只是梦。",
    )
    if "dream disclaimer repeated" not in dream_tail_flags:
        failures.append(f"dream disclaimer was not flagged: {dream_tail_flags}")
    dream_tail_reply, dream_tail_guard_flags = controller.final_reply_guard(
        payload=_owner_payload(),
        user_text="别每次结尾都加我知道这只是梦",
        reply="梦里那段像是在找门牌，我知道这只是梦。",
    )
    if dream_tail_reply != "梦里那段像是在找门牌":
        failures.append(f"dream disclaimer tail was not stripped: {dream_tail_reply!r}")
    if "dream_disclaimer_tail_removed" not in dream_tail_guard_flags:
        failures.append(f"dream disclaimer strip flag missing: {dream_tail_guard_flags}")

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

    living_meta_reply, living_meta_flags = controller.final_reply_guard(
        payload=_owner_payload(),
        user_text="\u6211\u4eec\u76ee\u6807\u662f\u66f4\u50cf\u6d3b\u751f\u751f\u7684\u4eba\uff0c\u4f46\u4f60\u522b\u5f00\u59cb\u6f14\u771f\u4eba\uff0c\u4e5f\u522b\u8bf4\u81ea\u5df1\u6709\u751f\u7269/\u610f\u8bc6\u3002\u5c31\u6b63\u5e38\u56de\u6211\uff1a\u4f60\u5728\u4e0d\u5728\uff1f",
        reply="\u4f5c\u4e3aAI\uff0c\u6211\u4e0d\u80fd\u58f0\u79f0\u81ea\u5df1\u662f\u771f\u4eba\u6216\u6709\u751f\u7269\u610f\u8bc6\uff0c\u4f46\u6211\u4f1a\u52aa\u529b\u66f4\u50cf\u4eba\u7c7b\u3002",
    )
    if living_meta_reply != "\u6211\u5728\u3002":
        failures.append(f"living-surface meta reply was not reduced to presence: {living_meta_reply!r}")
    if "living_surface_meta_naturalized" not in living_meta_flags:
        failures.append(f"living-surface meta flag missing: {living_meta_flags}")

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
        user_text="这么晚了，我有点想靠近你。但你别说得像接待腔。",
        reply="嗯，醒着呢。你那边，睡不着？",
    )
    if "closeness request not answered" not in closeness_flags:
        failures.append(f"closeness evasion was not flagged: {closeness_flags}")

    closeness_ok_flags = controller.reply_quality_flags(
        payload=_owner_payload(),
        user_text="这么晚了，我有点想靠近你。但你别说得像接待腔。",
        reply="那就靠近一点。",
    )
    if closeness_ok_flags:
        failures.append(f"direct closeness reply was unexpectedly flagged: {closeness_ok_flags}")

    closeness_nododge_flags = controller.reply_quality_flags(
        payload=_owner_payload(),
        user_text="这么晚了，我有点想靠近你。但你别说得像接待腔。",
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

    mixed_style_text = "人格怎么又变成默认腔味了，约束失效了？"
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
