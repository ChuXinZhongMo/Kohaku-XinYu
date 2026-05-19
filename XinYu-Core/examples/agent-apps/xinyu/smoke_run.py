from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


QUICK_SMOKES = [
    [
        "-m",
        "py_compile",
        "state_service.py",
        "stores/state_service.py",
        "xinyu_chat_service.py",
        "services/chat_service.py",
        "xinyu_runtime_presence.py",
        "xinyu_core_bridge.py",
        "xinyu_runtime_context.py",
        "xinyu_persona_realism_eval.py",
        "xinyu_memory_braid.py",
        "xinyu_turn_coherence.py",
        "xinyu_initiative_spine.py",
        "tests/smoke/initiative/proactive_feedback_spine_smoke.py",
        "xinyu_housekeeping.py",
        "xinyu_self_thought_loop.py",
        "xinyu_emotion_council.py",
        "xinyu_research_handoff_loop.py",
        "xinyu_watched_sources.py",
        "xinyu_memory_self_review.py",
        "custom/turn_mode_bridge_plugin.py",
        "custom/automation_bridge_plugin.py",
        "custom/maintenance_schedule_bridge_plugin.py",
        "custom/initiative_loop_bridge_plugin.py",
        "custom/inner_cycle_bridge_plugin.py",
        "custom/desktop_thoughts_bridge_plugin.py",
        "custom/research_handoff_engine.py",
        "custom/research_handoff_bridge_plugin.py",
        "custom/github_autonomous_learning_engine.py",
        "custom/github_autonomous_learning_bridge_plugin.py",
        "custom/maintenance_bridge_utils.py",
        "custom/question_pipeline_bridge_plugin.py",
        "custom/slow_reprocess_bridge_plugin.py",
        "custom/reflection_output_bridge_plugin.py",
        "custom/dream_output_bridge_plugin.py",
        "custom/consolidation_bridge_plugin.py",
        "custom/long_term_memory_gate_bridge_plugin.py",
        "custom/retention_gate_bridge_plugin.py",
        "custom/archive_output_bridge_plugin.py",
        "custom/archive_commit_bridge_plugin.py",
        "custom/ai_self_iteration_gate_bridge_plugin.py",
        "custom/ai_self_iteration_review_bridge_plugin.py",
        "custom/personality_growth_gate_bridge_plugin.py",
        "custom/source_gate_bridge_plugin.py",
        "custom/source_reliability_bridge_plugin.py",
        "custom/source_integration_gate_bridge_plugin.py",
        "custom/source_request_planner_bridge_plugin.py",
        "custom/source_search_resolver_bridge_plugin.py",
        "custom/autonomous_search_activation_bridge_plugin.py",
        "custom/source_search_provider_bridge_plugin.py",
        "custom/search_result_gate_bridge_plugin.py",
        "custom/outward_source_bridge_plugin.py",
        "custom/source_comparison_bridge_plugin.py",
        "custom/learner_integration_bridge_plugin.py",
        "custom/learning_quality_bridge_plugin.py",
        "xinyu_proactive_request_loop.py",
        "xinyu_self_code_approval.py",
        "xinyu_self_code_watchdog.py",
        "xinyu_review_inbox.py",
        "xinyu_daily_digest.py",
        "services/daily_digest.py",
        "xinyu_external_plugins.py",
        "xinyu_bridge_external_plugin_routes.py",
        "xinyu_bridge_desktop_proactive_routes.py",
        "xinyu_bridge_desktop_self_action_routes.py",
        "xinyu_bridge_metabolism_routes.py",
        "xinyu_bridge_proactive_delivery_routes.py",
        "xinyu_bridge_utility_routes.py",
        "xinyu_qq_gateway_context_enrichment.py",
        "xinyu_qq_visible_dispatch.py",
        "xinyu_sticker_pack.py",
        "xinyu_environment_sensor.py",
        "xinyu_life_kernel.py",
        "xinyu_metabolism_contract.py",
        "xinyu_self_choice_store.py",
        "xinyu_self_chosen_goal_ecology.py",
        "xinyu_goal_outcome_observer.py",
        "xinyu_self_action_gateway.py",
        "xinyu_self_action_patch_executor.py",
        "xinyu_dream_engine.py",
        "xinyu_speech_controller.py",
        "xinyu_bridge_renderer.py",
        "smoke_run.py",
    ],
    ["tests/smoke/life/environment_sensor_smoke.py"],
    ["tests/smoke/life/life_kernel_smoke.py"],
    ["tests/smoke/life/life_kernel_entropy_smoke.py"],
    ["tests/smoke/life/life_kernel_self_choice_bias_smoke.py"],
    ["tests/smoke/life/xinyu_self_choice_store_smoke.py"],
    ["tests/smoke/life/xinyu_dream_engine_smoke.py"],
    ["tests/smoke/life/metabolism_contract_smoke.py"],
    ["tests/smoke/life/metabolism_bridge_smoke.py"],
    ["tests/smoke/life/metabolism_http_smoke.py"],
    ["tests/smoke/desktop/xinyu_desktop_life_state_smoke.py"],
    ["tests/smoke/desktop/xinyu_desktop_metabolism_ticket_smoke.py"],
    ["tests/smoke/runtime/mojibake_guard_smoke.py"],
    ["tests/smoke/runtime/runtime_presence_smoke.py"],
    ["tests/smoke/memory/memory_braid_smoke.py"],
    ["tests/smoke/initiative/turn_coherence_smoke.py"],
    ["tests/smoke/initiative/initiative_spine_smoke.py"],
    ["tests/smoke/initiative/proactive_feedback_spine_smoke.py"],
    ["tests/smoke/initiative/self_thought_loop_smoke.py"],
    ["tests/smoke/initiative/self_chosen_goal_ecology_smoke.py"],
    ["tests/smoke/initiative/goal_outcome_observer_smoke.py"],
    ["tests/smoke/initiative/self_action_gateway_smoke.py"],
    ["tests/smoke/initiative/self_action_patch_executor_smoke.py"],
    ["tests/smoke/initiative/emotion_council_smoke.py"],
    ["tests/smoke/voice/xinyu_speech_controller_smoke.py"],
    ["tests/smoke/voice/persona_realism_eval_smoke.py"],
    ["tests/smoke/bridge/bridge_renderer_guard_flags_smoke.py"],
    ["tests/smoke/learning/integration/research_handoff_smoke.py"],
    ["tests/smoke/learning/watched_sources_smoke.py"],
    ["tests/smoke/learning/github_autonomous_learning_smoke.py"],
    ["tests/smoke/memory/memory_self_review_smoke.py"],
    ["tests/smoke/initiative/proactive_request_loop_smoke.py"],
    ["tests/smoke/codex/self_code_approval_smoke.py"],
    ["tests/smoke/codex/self_code_watchdog_smoke.py"],
    ["tests/smoke/tools/xinyu_review_inbox_smoke.py"],
    ["tests/smoke/tools/xinyu_daily_digest_smoke.py"],
    ["tests/smoke/tools/xinyu_external_plugins_smoke.py"],
    ["tests/smoke/tools/xinyu_sticker_pack_smoke.py"],
    ["tests/smoke/qq/integration/xinyu_qq_gateway_smoke.py"],
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
    ["tests/smoke/runtime/integration/runtime_readiness_smoke.py", "--offline"],
]

SMOKE_GROUPS = {
    "quick": QUICK_SMOKES,
    "core": CORE_SMOKES,
    "full": FULL_SMOKES,
    "deployment": [
        ["tests/smoke/runtime/integration/deployment_status_smoke.py"],
        ["xinyu_status.py", "--json"],
        ["tests/smoke/bridge/integration/bridge_probe_smoke.py"],
        ["tests/smoke/bridge/bridge_session_cleanup_smoke.py"],
    ],
    "runtime": [
        ["tests/smoke/runtime/integration/runtime_readiness_smoke.py"],
    ],
    "memory": [
        ["tests/smoke/memory/memory_event_sourcing_smoke.py"],
        ["tests/smoke/memory/thought_seeds_smoke.py"],
        ["tests/smoke/memory/private_thought_events_smoke.py"],
        ["tests/smoke/memory/archive_queue_trace_smoke.py"],
        ["tests/smoke/memory/summary_coverage_smoke.py"],
    ],
    "voice": [
        ["tests/smoke/voice/integration/persona_contract_absence_smoke.py"],
        ["tests/smoke/voice/personality_evolution_smoke.py"],
        ["tests/smoke/voice/integration/live_voice_card_smoke.py"],
        ["tests/smoke/voice/pre_draft_turn_classifier_smoke.py"],
        ["tests/smoke/voice/voice_calibration_promotion_smoke.py"],
        ["tests/smoke/voice/dynamic_life_posture_smoke.py"],
        ["tests/smoke/life/life_month_context_smoke.py"],
        ["tests/smoke/voice/persona_runtime_smoke.py"],
        ["tests/smoke/voice/persona_realism_eval_smoke.py"],
        ["tests/smoke/voice/xinyu_speech_controller_smoke.py"],
    ],
    "learning": [
        ["tests/smoke/learning/local_scope_smoke.py"],
        ["tests/smoke/learning/learning_library_smoke.py"],
        ["tests/smoke/codex/codex_delegate_smoke.py"],
        ["tests/smoke/qq/qq_outbox_smoke.py"],
        ["tests/smoke/codex/codex_dream_handoff_smoke.py"],
        ["tests/smoke/bridge/integration/bridge_learning_ingest_smoke.py"],
    ],
    "privacy": [
        ["tests/smoke/runtime/runtime_security_smoke.py"],
        ["tests/smoke/learning/local_scope_smoke.py"],
        ["tests/smoke/codex/codex_delegation_reality_smoke.py"],
        ["tests/smoke/runtime/mojibake_guard_smoke.py"],
    ],
    "replay": [
        [
            "-m",
            "pytest",
            "tests/test_retrieval_replay_cases.py",
            "tests/test_conversation_experience_replay_cases.py",
            "tests/test_chat_replay_fixture_exporter.py",
            "-q",
        ],
    ],
}


RESTORE_PATHS = ("memory", "runtime/research_handoff_bridge_trace.log")


@dataclass
class RunResult:
    name: str
    command: list[str]
    exit_code: int


class RuntimeSnapshot:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self._tmp = Path(tempfile.mkdtemp(prefix="xinyu-smoke-restore-"))
        self._entries: list[tuple[str, bool, bool]] = []
        for rel in RESTORE_PATHS:
            src = self.root / rel
            dst = self._tmp / rel
            existed = src.exists()
            was_dir = src.is_dir()
            self._entries.append((rel, existed, was_dir))
            if not existed:
                continue
            if was_dir:
                shutil.copytree(src, dst)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

    def _remove_target(self, target: Path) -> None:
        resolved = target.resolve()
        if resolved != self.root and self.root not in resolved.parents:
            raise RuntimeError(f"Refusing to restore outside root: {target}")
        if not target.exists():
            return
        if target.is_dir():
            last_error: OSError | None = None
            for attempt in range(30):
                try:
                    shutil.rmtree(target)
                    return
                except OSError as exc:
                    last_error = exc
                    if not target.exists():
                        return
                    self._remove_directory_children(target)
                    if not target.exists():
                        return
                    time.sleep(min(0.1 * (attempt + 1), 1.0))
            if target.is_dir():
                self._remove_directory_children(target)
                return
            if last_error is not None:
                raise last_error
            return
        for attempt in range(5):
            try:
                target.unlink()
                return
            except OSError:
                if attempt == 4:
                    raise
                time.sleep(0.2)

    def _remove_directory_children(self, target: Path) -> None:
        try:
            children = list(target.iterdir())
        except OSError:
            return
        for child in children:
            try:
                if child.is_dir() and not child.is_symlink():
                    shutil.rmtree(child)
                else:
                    child.unlink()
            except OSError:
                continue

    def restore(self) -> None:
        for rel, existed, was_dir in self._entries:
            target = self.root / rel
            source = self._tmp / rel
            self._remove_target(target)
            if not existed:
                continue
            if was_dir:
                shutil.copytree(source, target, dirs_exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)

    def close(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)


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


def _supports_restore_after(root: Path, script_args: list[str]) -> bool:
    if not script_args or "--restore-after" in script_args:
        return False
    script = script_args[0]
    if script == "-m":
        return False
    path = root / script
    if path.suffix != ".py" or not path.exists():
        return False
    try:
        return "--restore-after" in path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def _script_args(root: Path, script_args: list[str], *, restore_after: bool) -> list[str]:
    args = list(script_args)
    if restore_after and _supports_restore_after(root, args):
        args.append("--restore-after")
    return args


def run_group(
    root: Path,
    group: str,
    *,
    venv_path: str,
    timeout_seconds: int,
    json_output: bool,
    restore_after: bool,
) -> int:
    py = _python(root, venv_path)
    results: list[RunResult] = []
    snapshot = RuntimeSnapshot(root) if restore_after else None
    try:
        for script_args in SMOKE_GROUPS[group]:
            script_args = _script_args(root, script_args, restore_after=restore_after)
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
            if snapshot:
                snapshot.restore()
            results.append(RunResult(name=_command_name(script_args), command=command, exit_code=completed.returncode))
            if completed.returncode != 0:
                break
    finally:
        if snapshot:
            snapshot.restore()
            snapshot.close()
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
    parser.add_argument(
        "--restore-after",
        action="store_true",
        help="Restore project runtime state around grouped child smokes and pass --restore-after to children that support it.",
    )
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
            restore_after=args.restore_after,
        )
    return run_plain_message(args)


if __name__ == "__main__":
    raise SystemExit(main())
