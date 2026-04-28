from __future__ import annotations

import sys
from pathlib import Path

from xinyu_bridge_renderer import BridgeRenderer
from xinyu_memory_weights import calculate_memory_weights
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
        "stable memory architecture",
        "Stable Prompt Layers",
        "Floating Prompt Layers",
        "real_world_anchor_policy",
        "Life Simulation Boundary",
        "not allowed to claim",
        "does not reset to generic helper wording every turn",
    ):
        if marker not in text:
            failures.append(f"missing marker: {marker}")

    config = (root / "config.yaml").read_text(encoding="utf-8-sig")
    system = (root / "prompts/system.md").read_text(encoding="utf-8-sig")
    if "system_prompt_memory: memory/self/system_prompt_memory.md" not in config:
        failures.append("config does not inject system_prompt_memory")
    if "{{ system_prompt_memory }}" not in system or "[self/system_prompt_memory.md]" not in system:
        failures.append("system prompt template does not include system_prompt_memory")
    if "Treat `system_prompt_memory.md` as stable memory" not in system:
        failures.append("system prompt does not describe system_prompt_memory priority")

    renderer = BridgeRenderer(
        xinyu_dir=root,
        speech_controller=XinyuSpeechController(root),
        renderer_mode="quality",
        render_timeout_seconds=1,
    )
    renderer_context = renderer.renderer_memory_context()
    if "[memory/self/system_prompt_memory.md]" not in renderer_context:
        failures.append("renderer context does not include system_prompt_memory")
    if "# System Prompt Memory" not in renderer_context:
        failures.append("renderer context did not load system_prompt_memory body")

    weights = calculate_memory_weights(root)
    prompt_rows = [row for row in weights if row["path"] == "memory/self/system_prompt_memory.md"]
    if not prompt_rows:
        failures.append("memory weight calculation does not include system_prompt_memory")
    elif prompt_rows[0]["active_weight"] < 90:
        failures.append(f"system_prompt_memory active weight too low: {prompt_rows[0]['active_weight']}")

    if failures:
        print("System prompt memory smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("System prompt memory smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
