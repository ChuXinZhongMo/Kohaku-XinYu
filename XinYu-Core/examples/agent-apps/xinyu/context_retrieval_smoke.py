from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from xinyu_context_retrieval import RecalledContextItem, render_recalled_context, retrieve_recalled_context
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

        redacted_block = render_recalled_context(
            [
                RecalledContextItem(
                    recall_id="smoke-repair-meta",
                    source="dialogue_archive",
                    scope="owner_private",
                    time="smoke",
                    speaker="XinYu",
                    summary="懂，问题在话本身，我继续修。",
                    relevance="smoke",
                    confidence="high",
                    score=10,
                )
            ]
        )
        if "我继续修" in redacted_block or "问题在话本身" in redacted_block:
            failures.append("recalled context should redact repair-meta fallback phrases")
        if "[repair-meta-redacted]" not in redacted_block:
            failures.append("recalled context should leave a redaction marker for bad repair-meta phrases")

        plan_dir = root / "project-plans"
        plan_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / "XINYU-LOCAL-TINY-SELF-CORE-BACKUP.md").write_text(
            (
                "# XinYu 本地小型自我核心备忘\n\n"
                "本地小型自我核心不是用小模型直接替换 API。"
                "重点是让身份连续性、记忆连贯性、工具调用习惯和 Codex 调度习惯慢慢沉淀。"
                "0.1B 或 7B 都不能绕过现有边界；第一步只做数据闭环，不训练模型。\n"
            ),
            encoding="utf-8",
        )
        (plan_dir / "XINYU-ALIFE-OPEN-ENDED-DIRECTION-PLAN.md").write_text(
            "# ALife\n行动结果是经验，不是直接人格改写。\n",
            encoding="utf-8",
        )
        (root / "OPEN-ENDED-BOUNDED-LOOP.md").write_text(
            "# Open-Ended Bounded Loop\naudit 只审查，不生成 next safe challenge。\n",
            encoding="utf-8",
        )
        self_core_result = retrieve_recalled_context(
            root,
            _payload(),
            user_text="我们之前说 API 基底、小模型 0.1B、本地小型自我核心和记忆连贯性，是怎么规划的？",
            dialogue_tail=[],
        )
        if not any(item.source == "self_core_architecture_context" for item in self_core_result.items):
            failures.append("self-learning architecture topic did not retrieve project-plan context")
        if "本地小型自我核心不是用小模型直接替换 API" not in self_core_result.prompt_block:
            failures.append("self-core prompt block should include the local tiny self core context")
        if "not stable personality memory" not in self_core_result.prompt_block:
            failures.append("self-core retrieval should mark context as advisory, not stable personality")

    if failures:
        print("context_retrieval_smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("context_retrieval_smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
