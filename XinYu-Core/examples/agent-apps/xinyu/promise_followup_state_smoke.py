from __future__ import annotations

import tempfile
from pathlib import Path

from xinyu_core_bridge import PROMISE_FOLLOWUP_STATE_REL, XinYuBridgeRuntime


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-promise-followup-state-") as tmp:
        root = Path(tmp)
        runtime = object.__new__(XinYuBridgeRuntime)
        runtime.xinyu_dir = root
        runtime._write_promised_followup_state(
            {
                "session_key": "owner:private:smoke",
                "user_id": "42",
                "dedupe_key": "promise_followup:smoke",
                "user_text": "owner asked for a followup",
                "reply": "XinYu promised to check",
            },
            status="queued",
            message_id="qq-outbox-smoke",
            notes=["scheduled", "queued", "queued"],
        )

        state_path = root / PROMISE_FOLLOWUP_STATE_REL
        if not state_path.is_file():
            failures.append("promise followup state file was not written")
        else:
            text = state_path.read_text(encoding="utf-8-sig")
            required = (
                "memory_type: promise_followup_state",
                "- status: queued",
                "- session_key: owner:private:smoke",
                "- dedupe_key: promise_followup:smoke",
                "- queued_message_id: qq-outbox-smoke",
                "- scheduled",
                "- queued",
            )
            for marker in required:
                if marker not in text:
                    failures.append(f"state missing marker: {marker}")
            if sum(1 for line in text.splitlines() if line == "- queued") != 1:
                failures.append("state notes were not deduped")
            if not text.endswith("\n"):
                failures.append("state file missing final newline")

        leftovers = list(state_path.parent.glob(f".{state_path.name}.*.tmp")) if state_path.parent.exists() else []
        if leftovers:
            failures.append("atomic write left temporary files behind")

    if failures:
        print("promise_followup_state_smoke failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("promise_followup_state_smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
