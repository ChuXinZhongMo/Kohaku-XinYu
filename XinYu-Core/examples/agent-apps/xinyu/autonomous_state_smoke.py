from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from xinyu_core_bridge import XinYuBridgeRuntime


async def _run() -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-autonomous-state-") as tmp:
        runtime = XinYuBridgeRuntime(
            xinyu_dir=Path(tmp),
            turn_timeout_seconds=1,
            max_text_chars=100,
            settle_seconds=0.0,
            outward_renderer=False,
            renderer_mode="off",
            render_timeout_seconds=1,
            session_idle_ttl_seconds=60,
            max_sessions=1,
            autonomous_maintenance_enabled=False,
        )
        try:
            runtime._autonomous_run_count = 2
            runtime._autonomous_failure_count = 1
            runtime._autonomous_last_error = "smoke_error"
            runtime._write_autonomous_state("smoke", memory_changed=True, notes=["state_service_smoke"])

            state_path = Path(tmp) / "memory/context/autonomous_mind_loop_state.md"
            text = state_path.read_text(encoding="utf-8")
            required = [
                "memory_type: autonomous_mind_loop_state",
                "- status: smoke",
                "- enabled: false",
                "- run_count: 2",
                "- failure_count: 1",
                "- memory_changed: true",
                "- last_error: smoke_error",
                "- state_service_smoke",
            ]
            for marker in required:
                if marker not in text:
                    failures.append(f"missing autonomous state marker: {marker}")
            if not text.endswith("\n"):
                failures.append("autonomous state should end with a newline")
        finally:
            await runtime.shutdown()
    return failures


def main() -> int:
    failures = asyncio.run(_run())
    if failures:
        print("Autonomous state smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Autonomous state smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
