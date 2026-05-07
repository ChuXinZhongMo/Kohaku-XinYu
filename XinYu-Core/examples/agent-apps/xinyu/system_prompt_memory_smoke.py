from __future__ import annotations

import sys
from pathlib import Path

from xinyu_bridge_renderer import BridgeRenderer
from xinyu_speech_controller import XinyuSpeechController


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    root = Path(__file__).resolve().parent
    memory_path = root / "memory/self/system_prompt_memory.md"
    failures: list[str] = []

    try:
        text = memory_path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        print(f"System prompt memory smoke failed: {exc}")
        return 1

    for marker in (
        "# System Prompt Memory",
        "should no longer act as a hard personality constitution",
        "keep only the XinYu concept",
        "Prompt material is a seed, not law",
        "less machinery at the surface",
    ):
        if marker not in text:
            failures.append(f"missing marker: {marker}")

    config = (root / "config.yaml").read_text(encoding="utf-8-sig")
    system = (root / "prompts/system.md").read_text(encoding="utf-8-sig")
    if "system_prompt_memory: memory/self/system_prompt_memory.md" in config:
        failures.append("config should not inject system_prompt_memory into base prompt")
    if "{{ system_prompt_memory }}" in system or "[self/system_prompt_memory.md]" in system:
        failures.append("system prompt should not include system_prompt_memory")
    if "stable memory" in system:
        failures.append("system prompt still describes stable prompt memory")

    renderer = BridgeRenderer(
        xinyu_dir=root,
        speech_controller=XinyuSpeechController(root),
        renderer_mode="quality",
        render_timeout_seconds=1,
    )
    renderer_context = renderer.renderer_memory_context()
    if "[memory/self/system_prompt_memory.md]" in renderer_context:
        failures.append("renderer context should not include full system_prompt_memory")
    if "# System Prompt Memory" in renderer_context:
        failures.append("renderer context should keep stable prompt architecture out of final speech context")

    if failures:
        print("System prompt memory smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("System prompt memory smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
