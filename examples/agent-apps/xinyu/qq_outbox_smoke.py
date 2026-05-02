from __future__ import annotations

import tempfile
from pathlib import Path

from xinyu_qq_outbox import ack_qq_outbox_message, claim_next_qq_outbox_message, enqueue_qq_outbox_message


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-qq-outbox-") as tmp:
        root = Path(tmp)

        queued = enqueue_qq_outbox_message(
            root,
            user_id="42",
            message="Codex 跑完了。报告在本地 Codex Outbox：codex-qq-smoke-report.md。",
            source="codex_completion",
            dedupe_key="codex_completion:smoke",
            metadata={"job_id": "smoke"},
        )
        if not queued.get("queued"):
            failures.append("message was not queued")

        duplicate = enqueue_qq_outbox_message(
            root,
            user_id="42",
            message="duplicate",
            source="codex_completion",
            dedupe_key="codex_completion:smoke",
        )
        if duplicate.get("queued") or "duplicate_dedupe_key" not in duplicate.get("notes", []):
            failures.append("dedupe did not block duplicate message")

        claim = claim_next_qq_outbox_message(root, {"claim_id": "claim-1", "adapter": "smoke"})
        if not claim.get("message_claimed"):
            failures.append("queued message was not claimed")
        if claim.get("target", {}).get("message_kind") != "private":
            failures.append("claimed target is not private")
        if "D:\\XinYu" in str(claim.get("message", "")):
            failures.append("claimed message leaked a raw local path")

        empty = claim_next_qq_outbox_message(root, {"claim_id": "claim-empty", "adapter": "smoke"})
        if empty.get("message_claimed"):
            failures.append("claimed same message twice before ack")

        ack = ack_qq_outbox_message(
            root,
            {
                "message_id": claim.get("message_id"),
                "claim_id": claim.get("claim_id"),
                "ack_status": "sent",
                "adapter_message_id": "qq-msg-1",
            },
        )
        if not ack.get("ack_recorded") or ack.get("ack_status") != "sent":
            failures.append("sent ack was not recorded")

        after_sent = claim_next_qq_outbox_message(root, {"claim_id": "claim-after-sent", "adapter": "smoke"})
        if after_sent.get("message_claimed"):
            failures.append("sent message was claimed again")

        state = (root / "memory/context/qq_outbox_dispatch_state.md").read_text(encoding="utf-8")
        for marker in ("sent_count: 1", "QQ Outbox Dispatch State", "Gateway must ack"):
            if marker not in state:
                failures.append(f"dispatch state missing marker: {marker}")

    if failures:
        print("QQ outbox smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("QQ outbox smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
