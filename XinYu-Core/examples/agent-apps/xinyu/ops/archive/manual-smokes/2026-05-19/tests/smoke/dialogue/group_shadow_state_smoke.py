from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import json
import tempfile
from pathlib import Path

from xinyu_group_shadow_observer import HISTORY_REL, STATE_REL, TRACE_REL, record_group_shadow_observation


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
        followup = record_group_shadow_observation(
            root,
            event={"group_id": "7", "user_id": "43", "message_id": "shadow-smoke-2"},
            text="second shadow line with previous context",
            normalized_text="second shadow line with previous context",
            triggered=False,
            trigger_reason="not_triggered",
            allowed_group=True,
            prepare_reason="sender_not_whitelisted",
        )
        if result.get("recorded") is not True:
            failures.append("group shadow observation was not recorded")
        if followup.get("row", {}).get("recent_group_context_count") != 1:
            failures.append("group shadow followup did not include previous message history")

        trace_path = root / TRACE_REL
        rows = [
            json.loads(line)
            for line in trace_path.read_text(encoding="utf-8-sig").splitlines()
            if line.strip()
        ]
        if not rows or rows[-1].get("message_id_hash") != followup["row"].get("message_id_hash"):
            failures.append("group shadow trace row was not appended")
        if rows and rows[-1].get("stable_memory_write") != "blocked":
            failures.append("group shadow trace boundary changed")
        history_path = root / HISTORY_REL
        history_rows = [
            json.loads(line)
            for line in history_path.read_text(encoding="utf-8-sig").splitlines()
            if line.strip()
        ]
        if len(history_rows) != 2:
            failures.append("group shadow recent history did not persist both messages")

        state_text = (root / STATE_REL).read_text(encoding="utf-8")
        for marker in (
            "memory_type: group_shadow_state",
            "## Recent Group Context",
            "XinYu group shadow smoke question?",
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
