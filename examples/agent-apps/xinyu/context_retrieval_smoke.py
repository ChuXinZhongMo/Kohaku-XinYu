from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from xinyu_context_retrieval import retrieve_recalled_context
from xinyu_dialogue_archive import archive_dialogue_turn


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate XinYu recalled context retrieval.")
    parser.add_argument("--restore-after", action="store_true", help="Accepted for plan compatibility; smoke uses temp data.")
    return parser


def _payload() -> dict[str, object]:
    return {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "metadata": {"is_owner_user": True},
    }


def main() -> int:
    _parser().parse_args()
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-context-retrieval-") as tmp:
        root = Path(tmp)
        archive_dialogue_turn(
            root,
            _payload(),
            user_text="上次我们说 Codex 为什么不能搜索，是因为委托边界没接好。",
            assistant_reply="我会把搜索权限限制在 owner 明确任务里。",
            message_type="technical_work",
        )
        result = retrieve_recalled_context(
            root,
            _payload(),
            user_text="上次我们说 Codex 为什么不能搜来着？",
            dialogue_tail=[],
        )
        if "## Recalled Context" not in result.prompt_block:
            failures.append("recalled context block was not rendered")
        if "boundary: recalled dialogue context only" not in result.prompt_block:
            failures.append("recalled context boundary wording missing")
        if "Codex" not in result.prompt_block:
            failures.append("archive topic was not recalled")

        tail_result = retrieve_recalled_context(
            root,
            _payload(),
            user_text="刚才我说的饮料是什么？",
            dialogue_tail=[
                {"role": "user", "content": "我刚才说冰水适合配烤肉饭。"},
                {"role": "assistant", "content": "我记下这个搭配了。"},
            ],
        )
        if not tail_result.items or tail_result.items[0].source != "dialogue_tail":
            failures.append("just-now recall did not prefer the session tail")

    if failures:
        print("context_retrieval_smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("context_retrieval_smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
