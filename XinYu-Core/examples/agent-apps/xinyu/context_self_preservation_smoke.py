from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from xinyu_context_retrieval import retrieve_recalled_context
from xinyu_dialogue_archive import archive_dialogue_turn


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate recalled-context self-preservation wording.")
    parser.add_argument("--restore-after", action="store_true", help="Accepted for plan compatibility; smoke uses temp data.")
    return parser


def main() -> int:
    _parser().parse_args()
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-context-self-") as tmp:
        root = Path(tmp)
        payload = {
            "platform": "qq",
            "message_type": "private_text",
            "session_id": "qq:private:owner",
            "user_id": "42",
            "metadata": {"is_owner_user": True},
        }
        archive_dialogue_turn(
            root,
            payload,
            user_text="之前我说你太接待腔，别写成规则。",
            assistant_reply="知道了，我会先把话落下来。",
            message_type="owner_style_pressure",
        )
        result = retrieve_recalled_context(
            root,
            payload,
            user_text="回到之前你太接待腔那个问题，但现在按我这句来。",
            dialogue_tail=[],
        )
        block = result.prompt_block
        for marker in (
            "advisory only",
            "Current owner message and current emotional posture outrank retrieved fragments.",
            "When uncertain, say uncertainty naturally instead of pretending.",
            "boundary: recalled dialogue context only; not stable memory unless already marked stable",
        ):
            if marker not in block:
                failures.append(f"self-preservation marker missing: {marker}")
        if "Required Context" in block:
            failures.append("block used Required Context wording")

    if failures:
        print("context_self_preservation_smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("context_self_preservation_smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
