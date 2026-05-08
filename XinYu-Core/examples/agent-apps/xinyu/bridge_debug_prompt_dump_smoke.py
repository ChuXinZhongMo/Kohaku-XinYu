from __future__ import annotations

import os
from tempfile import TemporaryDirectory
from pathlib import Path

from xinyu_core_bridge import DEBUG_LIVE_SYSTEM_PROMPT_REL, DEBUG_PROMPT_DUMP_ENV, XinYuBridgeRuntime


class _Agent:
    def get_system_prompt(self) -> str:
        return "base prompt"


def main() -> int:
    failures: list[str] = []
    old_env = os.environ.get(DEBUG_PROMPT_DUMP_ENV)
    try:
        os.environ[DEBUG_PROMPT_DUMP_ENV] = "1"
        with TemporaryDirectory() as raw_root:
            runtime = object.__new__(XinYuBridgeRuntime)
            runtime.xinyu_dir = Path(raw_root)
            runtime._owner_private_payload_matches = lambda payload: True

            runtime._maybe_dump_live_system_prompt(
                _Agent(),
                payload={"metadata": {"is_owner_user": True}},
                session_key="owner-session",
                turn_id="turn-1",
                live_system_prompt="live prompt",
            )
            path = runtime.xinyu_dir / DEBUG_LIVE_SYSTEM_PROMPT_REL
            text = path.read_text(encoding="utf-8")
            if "base prompt" not in text or "live prompt" not in text:
                failures.append("debug prompt dump content changed")
            if list(path.parent.glob("*.tmp")):
                failures.append("debug prompt dump left temp files behind")
    finally:
        if old_env is None:
            os.environ.pop(DEBUG_PROMPT_DUMP_ENV, None)
        else:
            os.environ[DEBUG_PROMPT_DUMP_ENV] = old_env

    if failures:
        print("XinYu bridge debug prompt dump smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu bridge debug prompt dump smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
