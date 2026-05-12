from __future__ import annotations

from xinyu_bridge_renderer import BridgeRenderer, critical_final_guard_flags, replace_last_assistant_message
from xinyu_core_bridge import XinYuBridgeRuntime


class _Message:
    def __init__(self) -> None:
        self.content = "old"
        self.tool_calls = [{"name": "old_tool"}]


class _Conversation:
    def __init__(self, message: _Message | None = None, *, fail: bool = False) -> None:
        self.message = message
        self.fail = fail

    def get_last_assistant_message(self):
        if self.fail:
            raise RuntimeError("boom")
        return self.message


class _Controller:
    def __init__(self, conversation: _Conversation | None = None) -> None:
        self.conversation = conversation


class _Agent:
    def __init__(self, conversation: _Conversation | None = None) -> None:
        self.controller = _Controller(conversation)


def main() -> int:
    failures: list[str] = []

    flags = [
        "reply_quality_template_pressure",
        "machine_introspection_naturalized",
        "emotion_council_mechanics_blocked",
        "final_guard_repair_rendered",
        "false_codex_unavailable_claim_blocked",
        "layered_voice_self_analysis_blocked",
        "owner_address_label_blocked",
        "owner_address_query_blocked",
    ]
    expected = [
        "machine_introspection_naturalized",
        "emotion_council_mechanics_blocked",
        "false_codex_unavailable_claim_blocked",
        "layered_voice_self_analysis_blocked",
        "owner_address_label_blocked",
        "owner_address_query_blocked",
    ]

    if critical_final_guard_flags(flags) != expected:
        failures.append("critical final guard filtering changed")
    if critical_final_guard_flags(tuple(flags)) != expected:
        failures.append("critical final guard tuple filtering changed")
    if XinYuBridgeRuntime._critical_final_guard_flags(flags) != expected:
        failures.append("core bridge critical final guard alias no longer delegates")
    if XinYuBridgeRuntime._normalize_renderer_mode("quality") != BridgeRenderer.normalize_renderer_mode("quality"):
        failures.append("core bridge renderer mode alias no longer delegates")
    if XinYuBridgeRuntime._normalize_renderer_mode("unknown") != "off":
        failures.append("renderer mode fallback changed")

    message = _Message()
    agent = _Agent(_Conversation(message))
    replace_last_assistant_message(agent, "new reply")
    if message.content != "new reply" or message.tool_calls is not None:
        failures.append("replace_last_assistant_message did not replace content/tool calls")

    alias_message = _Message()
    XinYuBridgeRuntime._replace_last_assistant_message(_Agent(_Conversation(alias_message)), "alias reply")
    if alias_message.content != "alias reply" or alias_message.tool_calls is not None:
        failures.append("core bridge replace assistant alias no longer delegates")

    replace_last_assistant_message(_Agent(_Conversation(None)), "ignored")
    replace_last_assistant_message(_Agent(_Conversation(_Message(), fail=True)), "ignored")

    if failures:
        print("XinYu bridge renderer guard flags smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu bridge renderer guard flags smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
