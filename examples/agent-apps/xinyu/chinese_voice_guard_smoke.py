from __future__ import annotations

from pathlib import Path

from xinyu_core_bridge import XinYuBridgeRuntime


def _runtime() -> XinYuBridgeRuntime:
    root = Path(__file__).resolve().parent
    return XinYuBridgeRuntime(
        xinyu_dir=root,
        turn_timeout_seconds=1,
        max_text_chars=4000,
        settle_seconds=0,
        outward_renderer=True,
        render_timeout_seconds=1,
    )


def _assert_flagged(runtime: XinYuBridgeRuntime, user_text: str, reply: str) -> None:
    flags = runtime._reply_quality_flags(user_text=user_text, reply=reply)
    if not flags:
        raise AssertionError(f"expected flags for reply: {reply}")


def _assert_clean(runtime: XinYuBridgeRuntime, user_text: str, reply: str) -> None:
    flags = runtime._reply_quality_flags(user_text=user_text, reply=reply)
    if flags:
        raise AssertionError(f"unexpected flags for reply: {reply}\nflags={flags}")


def main() -> int:
    runtime = _runtime()

    _assert_flagged(
        runtime,
        "用词也不像中文互联网里的人说话，我真的气到红温。",
        "我理解你的反馈，这说明系统输出层还没有达到预期，我会持续优化。",
    )
    _assert_flagged(
        runtime,
        "朋友，大问题，我们做了那么多感情系统和记忆系统，怎么还是这么不像人。",
        "核心问题在于架构和模型输出没有充分承接你的情绪价值。",
    )
    _assert_flagged(
        runtime,
        "这句话GPT味太重了。",
        "我刚才那句确实太像AI味了，我会努力调整。",
    )
    _assert_clean(
        runtime,
        "用词也不像中文互联网里的人说话，我真的气到红温。",
        "……我知道你为什么火。别急着把我整个判没了。",
    )

    context = runtime._renderer_memory_context()
    if "[memory/self/voice_profile_zh.md]" not in context:
        raise AssertionError("voice_profile_zh.md was not injected into renderer memory context")

    print("Chinese voice guard smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
