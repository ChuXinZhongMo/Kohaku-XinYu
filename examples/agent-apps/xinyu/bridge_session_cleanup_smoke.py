from __future__ import annotations

import asyncio
import time
from pathlib import Path

from xinyu_core_bridge import AgentSession, XinYuBridgeRuntime


class DummyAgent:
    def __init__(self) -> None:
        self.stopped = False

    async def stop(self) -> None:
        self.stopped = True


async def run_smoke() -> list[str]:
    root = Path(__file__).resolve().parent
    failures: list[str] = []

    runtime = XinYuBridgeRuntime(
        xinyu_dir=root,
        turn_timeout_seconds=1,
        max_text_chars=100,
        settle_seconds=0,
        outward_renderer=False,
        render_timeout_seconds=1,
        session_idle_ttl_seconds=10,
        max_sessions=0,
    )
    now = time.time()
    old_agent = DummyAgent()
    fresh_agent = DummyAgent()
    runtime._sessions = {
        "old": AgentSession("old", old_agent, last_used_at=now - 30),
        "fresh": AgentSession("fresh", fresh_agent, last_used_at=now),
    }
    result = await runtime._cleanup_idle_sessions()
    if result["cleaned_sessions"] != 1 or "old" in runtime._sessions or "fresh" not in runtime._sessions:
        failures.append("idle ttl cleanup did not remove only the old session")
    if not old_agent.stopped or fresh_agent.stopped:
        failures.append("idle ttl cleanup stopped the wrong dummy agent")

    runtime = XinYuBridgeRuntime(
        xinyu_dir=root,
        turn_timeout_seconds=1,
        max_text_chars=100,
        settle_seconds=0,
        outward_renderer=False,
        render_timeout_seconds=1,
        session_idle_ttl_seconds=0,
        max_sessions=2,
    )
    agents = {key: DummyAgent() for key in ("a", "b", "c")}
    runtime._sessions = {
        "a": AgentSession("a", agents["a"], last_used_at=now - 30),
        "b": AgentSession("b", agents["b"], last_used_at=now - 20),
        "c": AgentSession("c", agents["c"], last_used_at=now - 10),
    }
    result = await runtime._cleanup_idle_sessions(preserve_keys={"c"})
    if result["cleaned_sessions"] != 1 or set(runtime._sessions) != {"b", "c"}:
        failures.append("max-session cleanup did not remove the oldest non-preserved session")
    if not agents["a"].stopped or agents["b"].stopped or agents["c"].stopped:
        failures.append("max-session cleanup stopped the wrong dummy agent")

    return failures


def main() -> int:
    failures = asyncio.run(run_smoke())
    if failures:
        print("Bridge session cleanup smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Bridge session cleanup smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
