from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from xinyu_codex_dream_handoff import handoff_codex_to_dream


ROOT = Path(__file__).resolve().parent


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-codex-dream-") as tmp:
        temp_root = Path(tmp)
        shutil.copytree(ROOT / "memory", temp_root / "memory")
        shutil.copytree(ROOT / "custom", temp_root / "custom")
        result = handoff_codex_to_dream(
            temp_root,
            task_text="用 codex 学习这个链接 https://github.com/Comfy-Org/ComfyUI/pull/13588",
            report_path=r"D:\XinYu\XinYu-Local-Scope\Outbox\codex-qq-smoke-report.md",
            request_path=r"D:\XinYu\XinYu-Local-Scope\Requests\codex-qq-smoke.md",
            workspace_path=r"D:\XinYu\XinYu-Local-Scope\Workspace\codex-qq-smoke",
            timed_out=True,
            produced_at="2026-04-28T09:10:00+08:00",
        )

        checks = {
            "memory/dreams/dream_seeds.md": (
                result.seed_id,
                "Codex 未完成的学习任务不能被关掉",
                "codex-qq-smoke-report.md",
            ),
            "memory/reflection/reflection_queue.md": (
                result.reflection_item_id,
                "Codex 学习任务超时后不能关闭",
                "suggested_writer: reflection_writer",
            ),
            "memory/dreams/dream_log.md": (
                result.seed_id,
                "Codex 未完成的学习任务不能被关掉",
                "不能证明现实里发生过新的对话、接触、感官经验或关系事实",
            ),
            "memory/dreams/dream_weight_state.md": (
                "mode: codex_timeout_dream_handoff",
                f"source_seed: {result.seed_id}",
                "weight_effect: existing_emotional_residue_strengthened",
            ),
            "memory/reflection/reflection_output_state.md": (
                "mode: codex_timeout_dream_handoff",
                "dream_context_used: yes",
            ),
            "memory/context/inner_cycle_state.md": (
                "mode: codex_timeout_dream_handoff",
                "dream_output_seed:",
            ),
        }
        for rel_path, markers in checks.items():
            text = _read(temp_root / rel_path)
            for marker in markers:
                if marker not in text:
                    failures.append(f"{rel_path} missing marker: {marker}")

        if not result.accepted:
            failures.append("handoff result was not accepted")
        if "codex_dream_handoff" not in result.notes:
            failures.append("handoff result missing note")
        if not Path(result.trace_path).exists():
            failures.append("handoff trace was not written")

    if failures:
        print("Codex dream handoff smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Codex dream handoff smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
