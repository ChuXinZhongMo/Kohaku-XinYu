from __future__ import annotations

import argparse
import os
import sqlite3
import tempfile
from pathlib import Path

from xinyu_dialogue_archive import (
    OWNER_PRIVATE_SCOPE,
    archive_dialogue_turn,
    dialogue_archive_path,
    search_dialogue_archive,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate local-only semantic dialogue retrieval.")
    parser.add_argument("--restore-after", action="store_true", help="Accepted for plan compatibility; smoke uses temp data.")
    return parser


def main() -> int:
    _parser().parse_args()
    old_enabled = os.environ.get("XINYU_DIALOGUE_SEMANTIC_RETRIEVAL_ENABLED")
    os.environ["XINYU_DIALOGUE_SEMANTIC_RETRIEVAL_ENABLED"] = "1"
    failures: list[str] = []
    try:
        with tempfile.TemporaryDirectory(prefix="xinyu-semantic-retrieval-") as tmp:
            root = Path(tmp)
            payload = {
                "platform": "qq",
                "message_type": "private_text",
                "session_id": "qq:private:owner-semantic",
                "user_id": "424242",
                "message_id": "semantic-1",
                "metadata": {"is_owner_user": True},
            }
            archive_dialogue_turn(
                root,
                payload,
                user_text="Codex 搜索权限被拦住，因为需要 owner 明确任务。",
                assistant_reply="我会把搜索限定在明确委托里。",
                message_type="technical_work",
            )
            matches = search_dialogue_archive(
                root,
                "辅助脑查找为什么不行",
                scopes=(OWNER_PRIVATE_SCOPE,),
                session_key="qq:private:owner-semantic",
                limit=5,
            )
            if not matches:
                failures.append("semantic retrieval returned no matches")
            if not any(match.retrieval_source == "semantic" for match in matches):
                failures.append(f"semantic retrieval source missing: {[match.retrieval_source for match in matches]}")

            conn = sqlite3.connect(dialogue_archive_path(root))
            try:
                rows = conn.execute("SELECT embedding_json FROM dialogue_semantic_index").fetchall()
                metadata_rows = [row[0] for row in conn.execute("SELECT metadata_json FROM dialogue_messages")]
            finally:
                conn.close()
            if not rows:
                failures.append("semantic index was not written")
            if any("424242" in row for row in metadata_rows):
                failures.append("semantic retrieval archive exposed raw owner id")
            if rows and any("Codex 搜索权限" in row[0] for row in rows):
                failures.append("semantic embedding row stored raw dialogue text")
    finally:
        if old_enabled is None:
            os.environ.pop("XINYU_DIALOGUE_SEMANTIC_RETRIEVAL_ENABLED", None)
        else:
            os.environ["XINYU_DIALOGUE_SEMANTIC_RETRIEVAL_ENABLED"] = old_enabled

    if failures:
        print("dialogue_semantic_retrieval_smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("dialogue_semantic_retrieval_smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
