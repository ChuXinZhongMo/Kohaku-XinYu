from __future__ import annotations

import json
import tempfile
from pathlib import Path

from xinyu_group_shadow_observer import STATE_REL, TRACE_REL, record_group_shadow_observation


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-group-shadow-") as tmp:
        root = Path(tmp)
        result = record_group_shadow_observation(
            root,
            event={"group_id": "7", "user_id": "42", "message_id": "shadow-smoke"},
            text="XinYu group shadow smoke question?",
            normalized_text="XinYu group shadow smoke question?",
            triggered=True,
            trigger_reason="smoke",
            allowed_group=True,
            prepare_reason="group_mention_or_prefix",
        )
        if result.get("recorded") is not True:
            failures.append("group shadow observation was not recorded")

        trace_path = root / TRACE_REL
        rows = [
            json.loads(line)
            for line in trace_path.read_text(encoding="utf-8-sig").splitlines()
            if line.strip()
        ]
        if not rows or rows[-1].get("message_id_hash") != result["row"].get("message_id_hash"):
            failures.append("group shadow trace row was not appended")
        if rows and rows[-1].get("stable_memory_write") != "blocked":
            failures.append("group shadow trace boundary changed")

        state_text = (root / STATE_REL).read_text(encoding="utf-8")
        for marker in (
            "memory_type: group_shadow_state",
            "- reply_policy: no_reply_shadow_only",
            "- stable_memory_write: blocked",
            "- owner_relationship_write: blocked",
        ):
            if marker not in state_text:
                failures.append(f"missing group shadow state marker: {marker}")
        if not state_text.endswith("\n"):
            failures.append("group shadow state should end with newline")

    if failures:
        print("Group shadow state smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Group shadow state smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
