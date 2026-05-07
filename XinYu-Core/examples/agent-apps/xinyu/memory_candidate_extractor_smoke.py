from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from xinyu_dialogue_archive import list_memory_candidates
from xinyu_memory_candidate_extractor import extract_memory_candidates


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate XinYu memory candidate extraction.")
    parser.add_argument("--restore-after", action="store_true", help="Accepted for plan compatibility; smoke uses temp data.")
    return parser


def main() -> int:
    _parser().parse_args()
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-memory-candidates-") as tmp:
        root = Path(tmp)
        owner_payload = {
            "platform": "qq",
            "message_type": "private_text",
            "session_id": "qq:private:owner",
            "user_id": "42",
            "metadata": {"is_owner_user": True},
        }
        result = extract_memory_candidates(
            root,
            owner_payload,
            user_text="不像你，太接待腔了，没什么变化。Codex 这个 runtime 修完后也要记得复查。",
            assistant_reply="知道了，我先把这次修复结果放进候选，不改稳定记忆。",
            source_message_ids=[1, 2],
        )
        rows = list_memory_candidates(root)
        types = {row["candidate_type"] for row in rows}
        if result["candidate_count"] < 2:
            failures.append(f"expected multiple candidates, got {result}")
        if "voice_correction" not in types:
            failures.append("voice correction candidate missing")
        if "project_fact" not in types:
            failures.append("project fact candidate missing")
        if (root / "memory" / "people" / "owner.md").exists():
            failures.append("candidate extraction wrote stable owner memory")

        group_payload = {
            "platform": "qq",
            "message_type": "group_text",
            "session_id": "qq:group:7:99",
            "user_id": "99",
            "group_id": "7",
            "metadata": {"is_owner_user": False},
        }
        before = len(list_memory_candidates(root))
        extract_memory_candidates(
            root,
            group_payload,
            user_text="群里有人说 owner 很失望。",
            assistant_reply="这只能当群上下文，不能写 owner 关系记忆。",
            source_message_ids=[3, 4],
        )
        after_rows = list_memory_candidates(root)
        new_types = [row["candidate_type"] for row in after_rows[: max(0, len(after_rows) - before)]]
        if "relationship_signal" in new_types:
            failures.append("group chat created an owner relationship candidate")

    if failures:
        print("memory_candidate_extractor_smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("memory_candidate_extractor_smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
