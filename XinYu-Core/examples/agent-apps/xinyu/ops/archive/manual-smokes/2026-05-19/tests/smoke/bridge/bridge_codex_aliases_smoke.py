from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from xinyu_codex_service import (
    codex_owner_task_text,
    codex_reply_variant,
    codex_started_reply,
    codex_task_subject,
    looks_like_codex_image_generation_task,
)
from xinyu_core_bridge import XinYuBridgeRuntime


def main() -> int:
    failures: list[str] = []

    if XinYuBridgeRuntime._codex_reply_variant is not codex_reply_variant:
        failures.append("Codex reply variant alias no longer delegates")
    if XinYuBridgeRuntime._codex_owner_task_text is not codex_owner_task_text:
        failures.append("Codex owner task text alias no longer delegates")
    if XinYuBridgeRuntime._codex_task_subject is not codex_task_subject:
        failures.append("Codex task subject alias no longer delegates")
    if XinYuBridgeRuntime._codex_started_reply is not codex_started_reply:
        failures.append("Codex started reply alias no longer delegates")
    if XinYuBridgeRuntime._looks_like_codex_image_generation_task is not looks_like_codex_image_generation_task:
        failures.append("Codex image generation task alias no longer delegates")

    if not XinYuBridgeRuntime._looks_like_codex_image_generation_task("帮我生成一张图片"):
        failures.append("Codex image generation detector behavior changed")
    if not XinYuBridgeRuntime._codex_task_subject("请分析这个仓库"):
        failures.append("Codex task subject behavior changed")

    if failures:
        print("XinYu bridge Codex aliases smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu bridge Codex aliases smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
