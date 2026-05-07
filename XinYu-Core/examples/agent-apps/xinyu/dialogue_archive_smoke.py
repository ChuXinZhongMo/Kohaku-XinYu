from __future__ import annotations

import argparse
import sqlite3
import tempfile
from pathlib import Path

from xinyu_dialogue_archive import (
    OWNER_PRIVATE_SCOPE,
    archive_dialogue_turn,
    dialogue_archive_path,
    initialize_dialogue_archive,
    search_dialogue_archive,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate local XinYu dialogue archive.")
    parser.add_argument("--restore-after", action="store_true", help="Accepted for plan compatibility; smoke uses temp data.")
    return parser


def main() -> int:
    _parser().parse_args()
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-dialogue-archive-") as tmp:
        root = Path(tmp)
        initialize_dialogue_archive(root)
        payload = {
            "platform": "qq",
            "message_type": "private_text",
            "session_id": "qq:private:123456789",
            "user_id": "123456789",
            "message_id": "9001",
            "metadata": {"is_owner_user": True, "source": "smoke"},
        }
        result = archive_dialogue_turn(
            root,
            payload,
            user_text="We discussed why Codex search was blocked.",
            assistant_reply="I said the bridge needed an explicit owner-approved search task.",
            message_type="technical_work",
        )
        if not result["archived"] or len(result["message_ids"]) != 2:
            failures.append(f"turn was not archived: {result}")

        initialize_dialogue_archive(root)
        matches = search_dialogue_archive(
            root,
            "Codex search blocked",
            scopes=(OWNER_PRIVATE_SCOPE,),
            session_key="qq:private:123456789",
            limit=5,
        )
        if not matches or "Codex search" not in matches[0].text:
            failures.append("archive search did not find the previous owner-private topic")

        conn = sqlite3.connect(dialogue_archive_path(root))
        try:
            metadata_rows = [row[0] for row in conn.execute("SELECT metadata_json FROM dialogue_messages")]
        finally:
            conn.close()
        if any("123456789" in row for row in metadata_rows):
            failures.append("archive metadata exposed an unredacted QQ user id")

    if failures:
        print("dialogue_archive_smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("dialogue_archive_smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
