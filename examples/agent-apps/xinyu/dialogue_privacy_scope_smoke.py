from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from xinyu_context_retrieval import retrieve_recalled_context
from xinyu_dialogue_archive import archive_dialogue_turn


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate dialogue archive privacy scope boundaries.")
    parser.add_argument("--restore-after", action="store_true", help="Accepted for plan compatibility; smoke uses temp data.")
    return parser


def main() -> int:
    _parser().parse_args()
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-privacy-scope-") as tmp:
        root = Path(tmp)
        owner_payload = {
            "platform": "qq",
            "message_type": "private_text",
            "session_id": "qq:private:owner",
            "user_id": "42",
            "metadata": {"is_owner_user": True},
        }
        group_payload = {
            "platform": "qq",
            "message_type": "group_text",
            "session_id": "qq:group:7:42",
            "user_id": "42",
            "group_id": "7",
            "metadata": {"is_owner_user": True},
        }
        archive_dialogue_turn(
            root,
            owner_payload,
            user_text="shared keyword owner private detail",
            assistant_reply="owner-private answer",
            message_type="ordinary_owner_chat",
        )
        archive_dialogue_turn(
            root,
            group_payload,
            user_text="shared keyword group detail",
            assistant_reply="group answer",
            message_type="group_chat",
        )

        owner_result = retrieve_recalled_context(
            root,
            owner_payload,
            user_text="之前 shared keyword detail 是什么？",
            dialogue_tail=[],
        )
        if "owner private detail" not in owner_result.prompt_block:
            failures.append("owner-private recall did not include owner-private detail")
        if "group detail" in owner_result.prompt_block:
            failures.append("owner-private recall leaked group context")

        group_result = retrieve_recalled_context(
            root,
            group_payload,
            user_text="之前 shared keyword detail 是什么？",
            dialogue_tail=[],
        )
        if "group detail" not in group_result.prompt_block:
            failures.append("group-scoped recall did not find group context")

    if failures:
        print("dialogue_privacy_scope_smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("dialogue_privacy_scope_smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
