from __future__ import annotations

from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    failures: list[str] = []

    config = (root / "config.yaml").read_text(encoding="utf-8-sig")
    system = (root / "prompts/system.md").read_text(encoding="utf-8-sig")
    policy = (root / "memory/context/codex_delegation_policy.md").read_text(encoding="utf-8-sig")
    core = (root / "xinyu_core_bridge.py").read_text(encoding="utf-8-sig")
    renderer = (root / "xinyu_bridge_renderer.py").read_text(encoding="utf-8-sig")

    required_markers = {
        "config.yaml": (
            "codex_delegation_policy: memory/context/codex_delegation_policy.md",
        ),
        "prompts/system.md": (
            "{{ codex_delegation_policy }}",
            "The native QQ gateway does not auto-launch Codex from chat",
            "explicit local/API delegation to `/codex/execute`",
        ),
        "memory/context/codex_delegation_policy.md": (
            "direct_qq_to_codex_execution: disabled_after_native_qq_gateway_migration",
            "automatic_codex_process_launch: core_endpoint_available_not_auto_routed_from_qq",
            "queue_watcher: not_implemented",
            "explicit local/API request -> core `/codex/execute` -> background `codex exec`",
            "timeout_policy: Codex execution is bounded",
            "Timeout is not treated as closing the task",
        ),
        "xinyu_core_bridge.py": (
            "memory/context/codex_delegation_policy.md",
        ),
        "xinyu_bridge_renderer.py": (
            "memory/context/codex_delegation_policy.md",
        ),
    }
    texts = {
        "config.yaml": config,
        "prompts/system.md": system,
        "memory/context/codex_delegation_policy.md": policy,
        "xinyu_core_bridge.py": core,
        "xinyu_bridge_renderer.py": renderer,
    }
    for label, markers in required_markers.items():
        text = texts[label]
        for marker in markers:
            if marker not in text:
                failures.append(f"{label} missing marker: {marker}")

    if failures:
        print("Codex delegation reality smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Codex delegation reality smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
