from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import argparse
import tempfile
from pathlib import Path

from xinyu_dialogue_archive import list_temporal_traces, search_temporal_traces
from xinyu_living_memory_recall import retrieve_living_memory as retrieve_recalled_context
from xinyu_memory_candidate_extractor import extract_memory_candidates


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate candidate-backed temporal traces.")
    parser.add_argument("--restore-after", action="store_true", help="Accepted for plan compatibility; smoke uses temp data.")
    return parser


def _owner_payload() -> dict[str, object]:
    return {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": "qq:private:trace-owner",
        "user_id": "42",
        "metadata": {"is_owner_user": True},
    }


def main() -> int:
    _parser().parse_args()
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-temporal-trace-") as tmp:
        root = Path(tmp)
        result = extract_memory_candidates(
            root,
            _owner_payload(),
            user_text="你这句太接待腔了，之前修 Codex 搜索权限也别忘了复查。",
            assistant_reply="我先把它放进候选，不直接改稳定记忆。",
            source_message_ids=[101, 102],
        )
        traces = list_temporal_traces(root)
        trace_types = {row["trace_type"] for row in traces}
        if result.get("temporal_trace_count", 0) <= 0:
            failures.append(f"candidate extraction did not report temporal traces: {result}")
        if "procedural_voice_trace" not in trace_types:
            failures.append(f"voice trace missing: {trace_types}")
        if "project_continuity_trace" not in trace_types:
            failures.append(f"project trace missing: {trace_types}")
        if (root / "memory" / "relationships" / "index.md").exists():
            failures.append("temporal trace wrote stable relationship memory")

        matches = search_temporal_traces(root, "之前太接待腔 Codex 复查", limit=5)
        if not matches:
            failures.append("temporal trace search returned no matches")
        recalled = retrieve_recalled_context(
            root,
            _owner_payload(),
            user_text="之前我说你太接待腔，还有 Codex 复查那个，记得吗？",
        )
        if "temporal_trace" not in recalled.prompt_block:
            failures.append(f"recalled context did not include temporal trace: {recalled.prompt_block!r}")
        if "not stable memory" not in recalled.prompt_block:
            failures.append("temporal trace recalled context missed stability boundary")

        group_payload = {
            "platform": "qq",
            "message_type": "group_text",
            "session_id": "qq:group:trace:99",
            "user_id": "99",
            "group_id": "trace",
            "metadata": {"is_owner_user": False},
        }
        extract_memory_candidates(
            root,
            group_payload,
            user_text="群里有人说 owner 很失望。",
            assistant_reply="这只能当群上下文。",
            source_message_ids=[201, 202],
        )
        group_relationship_traces = [
            row
            for row in list_temporal_traces(root)
            if row["scope"] == "qq_group" and row["trace_type"] == "relationship_emotion_trace"
        ]
        if group_relationship_traces:
            failures.append("group chat created owner relationship temporal traces")

    if failures:
        print("temporal_trace_smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("temporal_trace_smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
