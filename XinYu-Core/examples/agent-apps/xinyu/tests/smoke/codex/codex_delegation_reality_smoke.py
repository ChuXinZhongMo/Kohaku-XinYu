from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

from pathlib import Path


def main() -> int:
    root = ROOT
    failures: list[str] = []

    config = (root / "config.yaml").read_text(encoding="utf-8-sig")
    system = (root / "prompts/system.md").read_text(encoding="utf-8-sig")
    policy_path = root / "memory/context/codex_delegation_policy.md"
    if not policy_path.exists():
        policy_path = root / "memory-seeds/context/codex_delegation_policy.md"
    policy = policy_path.read_text(encoding="utf-8-sig")
    core = (root / "xinyu_core_bridge.py").read_text(encoding="utf-8-sig")
    renderer = (root / "xinyu_bridge_renderer.py").read_text(encoding="utf-8-sig")
    runtime_context = (root / "xinyu_runtime_context.py").read_text(encoding="utf-8-sig")

    required_markers = {
        "config.yaml": (
            "codex_delegation_policy: memory/context/codex_delegation_policy.md",
        ),
        "prompts/system.md": (
            "{{ codex_delegation_policy }}",
            "The native QQ gateway does not infer or auto-launch Codex from ordinary chat",
            "Owner-private `/codex <task>` may route to core `/codex/execute`",
            "hidden model handoff below is also an explicit bridge delegation path",
            "Do not tell the owner they must manually send `/codex`",
            "Codex completion callbacks may return through QQ Outbox",
            "explicit local/API delegation to `/codex/execute`",
        ),
        "memory/context/codex_delegation_policy.md": (
            "direct_qq_to_codex_execution: blocked_no_raw_cli_from_gateway",
            "explicit_qq_codex_command: owner_private_only_via_gateway_to_core_bridge",
            "automatic_codex_process_launch: disabled_for_ordinary_chat",
            "model_hidden_codex_delegate: owner_private_only_via_core_bridge_marker",
            "completion_return_path: core_qq_outbox_claim_ack_via_gateway",
            "queue_watcher: not_implemented",
            "owner private `/codex <task>` or explicit local/API request or hidden model handoff -> core `/codex/execute` -> background `codex exec`",
            "must not claim Codex requires manual `/codex`",
            "gateway_direct_subprocess: blocked",
            "completion_summary_visibility: owner_private_summary_no_raw_stdout_stderr_no_full_local_path",
            "timeout_policy: Codex execution is bounded",
            "Timeout is not treated as closing the task",
        ),
        "xinyu_core_bridge.py": (
            "memory/context/codex_delegation_policy.md",
        ),
        "xinyu_bridge_renderer.py": (
            "build_renderer_memory_context",
        ),
        "xinyu_runtime_context.py": (
            "memory/context/codex_delegation_policy.md",
        ),
    }
    texts = {
        "config.yaml": config,
        "prompts/system.md": system,
        "memory/context/codex_delegation_policy.md": policy,
        "xinyu_core_bridge.py": core,
        "xinyu_bridge_renderer.py": renderer,
        "xinyu_runtime_context.py": runtime_context,
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
