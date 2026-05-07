from __future__ import annotations

import re
from pathlib import Path


BASE = Path(__file__).resolve().parent
CONFIG = BASE / "config.yaml"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_single_path(pattern: str, text: str) -> list[str]:
    return re.findall(pattern, text, flags=re.MULTILINE)


def _check_exists(paths: list[Path]) -> list[str]:
    missing: list[str] = []
    for path in paths:
        if not path.exists():
            missing.append(str(path))
    return missing


def main() -> int:
    problems: list[str] = []

    if not CONFIG.exists():
        print(f"Missing config: {CONFIG}")
        return 1

    config_text = _read_text(CONFIG)

    system_prompt_files = _extract_single_path(
        r"^system_prompt_file:\s+(.+)$", config_text
    )
    subagent_prompt_files = _extract_single_path(r"^\s*prompt_file:\s+(.+)$", config_text)
    plugin_modules = _extract_single_path(r"^\s*module:\s+(.+)$", config_text)
    memory_paths = _extract_single_path(r"^\s*path:\s+(.+)$", config_text)

    prompt_paths = [BASE / p.strip().strip('"').strip("'") for p in system_prompt_files]
    prompt_paths += [
        BASE / p.strip().strip('"').strip("'") for p in subagent_prompt_files
    ]

    plugin_paths = []
    for raw in plugin_modules:
        cleaned = raw.strip().strip('"').strip("'")
        if cleaned.startswith("./"):
            plugin_paths.append(BASE / cleaned[2:])

    local_memory_paths = []
    for raw in memory_paths:
        cleaned = raw.strip().strip('"').strip("'")
        if cleaned.startswith("./"):
            local_memory_paths.append(BASE / cleaned[2:])

    for missing in _check_exists(prompt_paths):
        problems.append(f"Missing prompt file: {missing}")
    for missing in _check_exists(plugin_paths):
        problems.append(f"Missing plugin module: {missing}")
    for missing in _check_exists(local_memory_paths):
        problems.append(f"Missing memory path: {missing}")

    required_files = [
        BASE / "memory" / "self" / "core.md",
        BASE / "memory" / "self" / "narrative.md",
        BASE / "memory" / "emotions" / "current_state.md",
        BASE / "memory" / "relationships" / "index.md",
        BASE / "memory" / "people" / "owner.md",
        BASE / "memory" / "context" / "active_questions.md",
        BASE / "memory" / "context" / "time_anchor.md",
        BASE / "memory" / "context" / "runtime_rhythm.md",
        BASE / "memory" / "context" / "maintenance_plan.md",
    ]

    for missing in _check_exists(required_files):
        problems.append(f"Missing required scaffold file: {missing}")

    if problems:
        print("Xinyu scaffold validation failed:")
        for item in problems:
            print(f"- {item}")
        return 1

    print("Xinyu scaffold validation passed.")
    print(f"Prompts checked: {len(prompt_paths)}")
    print(f"Plugins checked: {len(plugin_paths)}")
    print(f"Memory roots checked: {len(local_memory_paths)}")
    print(f"Required files checked: {len(required_files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
