from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


QUICK_SMOKES = [
    [
        "-m",
        "py_compile",
        "xinyu_runtime_presence.py",
        "xinyu_core_bridge.py",
        "xinyu_runtime_context.py",
        "xinyu_memory_braid.py",
        "xinyu_turn_coherence.py",
        "xinyu_initiative_spine.py",
        "proactive_feedback_spine_smoke.py",
        "xinyu_housekeeping.py",
        "xinyu_self_thought_loop.py",
        "xinyu_research_handoff_loop.py",
        "xinyu_watched_sources.py",
        "xinyu_memory_self_review.py",
        "custom/research_handoff_engine.py",
        "custom/research_handoff_bridge_plugin.py",
        "custom/github_autonomous_learning_engine.py",
        "custom/github_autonomous_learning_bridge_plugin.py",
        "xinyu_proactive_request_loop.py",
        "xinyu_self_code_approval.py",
        "xinyu_self_code_watchdog.py",
        "xinyu_review_inbox.py",
        "xinyu_daily_digest.py",
        "xinyu_sticker_pack.py",
        "xinyu_environment_sensor.py",
        "xinyu_life_kernel.py",
        "xinyu_metabolism_contract.py",
        "xinyu_self_choice_store.py",
        "xinyu_dream_engine.py",
        "smoke_run.py",
    ],
    ["environment_sensor_smoke.py"],
    ["life_kernel_smoke.py"],
    ["life_kernel_entropy_smoke.py"],
    ["life_kernel_self_choice_bias_smoke.py"],
    ["xinyu_self_choice_store_smoke.py"],
    ["xinyu_dream_engine_smoke.py"],
    ["metabolism_contract_smoke.py"],
    ["metabolism_bridge_smoke.py"],
    ["metabolism_http_smoke.py"],
    ["xinyu_desktop_life_state_smoke.py"],
    ["xinyu_desktop_metabolism_ticket_smoke.py"],
    ["mojibake_guard_smoke.py"],
    ["runtime_presence_smoke.py"],
    ["memory_braid_smoke.py"],
    ["turn_coherence_smoke.py"],
    ["initiative_spine_smoke.py"],
    ["proactive_feedback_spine_smoke.py"],
    ["self_thought_loop_smoke.py"],
    ["research_handoff_smoke.py"],
    ["watched_sources_smoke.py"],
    ["github_autonomous_learning_smoke.py"],
    ["memory_self_review_smoke.py"],
    ["proactive_request_loop_smoke.py"],
    ["self_code_approval_smoke.py"],
    ["self_code_watchdog_smoke.py"],
    ["xinyu_review_inbox_smoke.py"],
    ["xinyu_daily_digest_smoke.py"],
    ["xinyu_sticker_pack_smoke.py"],
    ["xinyu_qq_gateway_smoke.py"],
]

CORE_SMOKES = [
    *QUICK_SMOKES,
    ["-m", "pytest", "tests", "-q"],
    ["smoke_run.py", "--group", "privacy"],
    ["smoke_run.py", "--group", "voice"],
]

FULL_SMOKES = [
    *CORE_SMOKES,
    ["smoke_run.py", "--group", "memory"],
    ["smoke_run.py", "--group", "learning"],
    ["runtime_readiness_smoke.py", "--offline"],
]

SMOKE_GROUPS = {
    "quick": QUICK_SMOKES,
    "core": CORE_SMOKES,
    "full": FULL_SMOKES,
    "deployment": [
        ["deployment_status_smoke.py"],
        ["xinyu_status.py", "--json"],
        ["bridge_probe_smoke.py"],
        ["bridge_session_cleanup_smoke.py"],
    ],
    "runtime": [
        ["runtime_readiness_smoke.py"],
    ],
    "memory": [
        ["memory_event_sourcing_smoke.py"],
        ["thought_seeds_smoke.py"],
        ["private_thought_events_smoke.py"],
        ["archive_queue_trace_smoke.py"],
        ["summary_coverage_smoke.py"],
    ],
    "voice": [
        ["persona_contract_absence_smoke.py"],
        ["personality_evolution_smoke.py"],
        ["live_voice_card_smoke.py"],
        ["pre_draft_turn_classifier_smoke.py"],
        ["voice_calibration_promotion_smoke.py"],
        ["dynamic_life_posture_smoke.py"],
        ["life_month_context_smoke.py"],
        ["persona_runtime_smoke.py"],
        ["xinyu_speech_controller_smoke.py"],
    ],
    "learning": [
        ["local_scope_smoke.py"],
        ["learning_library_smoke.py"],
        ["codex_delegate_smoke.py"],
        ["qq_outbox_smoke.py"],
        ["codex_dream_handoff_smoke.py"],
        ["bridge_learning_ingest_smoke.py"],
    ],
    "privacy": [
        ["runtime_security_smoke.py"],
        ["local_scope_smoke.py"],
        ["codex_delegation_reality_smoke.py"],
        ["mojibake_guard_smoke.py"],
    ],
}


@dataclass
class RunResult:
    name: str
    command: list[str]
    exit_code: int


def _python(root: Path, venv_path: str) -> Path:
    candidate = root / venv_path / "Scripts" / "python.exe"
    return candidate if candidate.exists() else Path(sys.executable)


def _command_name(script_args: list[str]) -> str:
    if len(script_args) >= 2 and script_args[0] == "-m":
        return "python -m " + script_args[1]
    if script_args and script_args[0] == "smoke_run.py" and "--group" in script_args:
        index = script_args.index("--group")
        if index + 1 < len(script_args):
            return f"smoke_run:{script_args[index + 1]}"
    return script_args[0] if script_args else "unknown"


def run_group(root: Path, group: str, *, venv_path: str, timeout_seconds: int, json_output: bool) -> int:
    py = _python(root, venv_path)
    results: list[RunResult] = []
    for script_args in SMOKE_GROUPS[group]:
        command = [str(py), *script_args]
        completed = subprocess.run(
            command,
            cwd=str(root),
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
        results.append(RunResult(name=_command_name(script_args), command=command, exit_code=completed.returncode))
        if completed.returncode != 0:
            break
    ok = all(item.exit_code == 0 for item in results)
    payload = {"group": group, "ok": ok, "results": [item.__dict__ for item in results]}
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"smoke_run group={group}:", "ok" if ok else "failed")
        for item in results:
            print(f"{'OK' if item.exit_code == 0 else 'FAIL'} {item.name}: exit={item.exit_code}")
            if item.exit_code != 0:
                print("command:", " ".join(item.command))
    return 0 if ok else 1


def run_plain_message(args: argparse.Namespace) -> int:
    root = Path(__file__).resolve().parent
    python_exe = _python(root, args.venv_path)
    launcher = root / "run_local_xinyu.py"
    message = args.message
    if args.message_file:
        message = Path(args.message_file).read_text(encoding="utf-8").strip()
        if not message:
            raise SystemExit(f"Message file is empty: {args.message_file}")

    proc = subprocess.Popen(
        [str(python_exe), str(launcher), "--mode", "plain", "--no-session"],
        cwd=str(root),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.stdin is not None
    time.sleep(args.warmup_seconds)
    proc.stdin.write(message + "\n")
    proc.stdin.flush()
    time.sleep(args.reply_wait_seconds)
    if proc.poll() is None:
        try:
            proc.stdin.write("/exit\n")
            proc.stdin.flush()
        except OSError:
            pass
    try:
        stdout, stderr = proc.communicate(timeout=120)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()

    print("=== RETURN CODE ===")
    print(proc.returncode)
    print("=== STDOUT ===")
    print(stdout)
    print("=== STDERR ===")
    print(stderr)
    log_dir = Path.home() / ".xinyu" / "logs"
    latest = max(log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, default=None)
    print("=== LATEST LOG ===")
    print(str(latest) if latest else "(none)")
    return proc.returncode


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Run XinYu smoke checks.")
    parser.add_argument("--group", choices=sorted(SMOKE_GROUPS), help="Run a grouped smoke manifest.")
    parser.add_argument("--json", action="store_true", help="Emit JSON for grouped smoke output.")
    parser.add_argument("--timeout-seconds", type=int, default=240)
    parser.add_argument("--message", default="hello xinyu")
    parser.add_argument("--message-file", default=None)
    parser.add_argument("--warmup-seconds", type=int, default=2)
    parser.add_argument("--reply-wait-seconds", type=int, default=20)
    parser.add_argument("--venv-path", default=".venv")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    if args.group:
        return run_group(
            root,
            args.group,
            venv_path=args.venv_path,
            timeout_seconds=args.timeout_seconds,
            json_output=args.json,
        )
    return run_plain_message(args)


if __name__ == "__main__":
    raise SystemExit(main())
