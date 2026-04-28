from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


SMOKE_GROUPS = {
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
        ["archive_queue_trace_smoke.py"],
        ["summary_coverage_smoke.py"],
    ],
    "voice": [
        ["persona_contract_absence_smoke.py"],
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
        results.append(RunResult(name=script_args[0], command=command, exit_code=completed.returncode))
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
    log_dir = Path.home() / ".kohakuterrarium" / "logs"
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
