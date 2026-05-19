from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

try:
    from ._validation_paths import ensure_validation_paths
except ImportError:  # Direct script execution from ops/validation.
    from _validation_paths import ensure_validation_paths


APP_ROOT = ensure_validation_paths()

from xinyu_storage_paths import knowledge_file_path


REQUIRED_DOCS = [
    "STATE-OF-XINYU.md",
    "IMPLEMENTATION-NEXT.md",
    "RUNTIME-VALIDATION-NOTES.md",
    "VALIDATION-INDEX.md",
    "social_inquiry_policy.md",
    "real_life_input_adapter_policy.md",
]

REQUIRED_VALIDATIONS = [
    "ops/validation/validate_scaffold.py",
    "ops/validation/validate_inner_framework.py",
    "tests/smoke/dialogue/integration/behavior_regression_smoke.py",
    "tests/smoke/voice/integration/personality_detail_smoke.py",
    "tests/smoke/voice/integration/personality_continuity_smoke.py",
    "tests/smoke/initiative/integration/emotion_vector_sync_smoke.py",
    "tests/smoke/dialogue/integration/resource_boundary_live_smoke.py",
    "tests/smoke/learning/integration/ai_domain_source_smoke.py",
    "tests/smoke/initiative/integration/ai_self_iteration_gate_smoke.py",
    "tests/smoke/learning/integration/source_comparison_smoke.py",
    "tests/smoke/learning/integration/autonomous_search_activation_smoke.py",
    "tests/smoke/dialogue/integration/social_inquiry_policy_smoke.py",
    "tests/smoke/dialogue/integration/real_life_input_adapter_smoke.py",
    "ops/probes/long_lived_session_harness.py",
    "tests/smoke/dialogue/integration/owner_relationship_lived_stress_smoke.py",
    "tests/smoke/voice/integration/personality_voice_calibration_smoke.py",
    "tests/smoke/voice/integration/real_conversation_quality_smoke.py",
    "tests/smoke/dialogue/integration/phase3_lived_session_smoke.py",
    "tests/smoke/initiative/integration/initiative_loop_smoke.py",
    "tests/smoke/initiative/proactive_presence_smoke.py",
    "tests/smoke/life/integration/dream_reflection_growth_cycle_smoke.py",
    "tests/smoke/dialogue/integration/non_owner_social_world_smoke.py",
    "tests/smoke/initiative/integration/ai_self_iteration_review_smoke.py",
    "tests/smoke/initiative/integration/ai_self_iteration_review_bridge_smoke.py",
    "tests/smoke/learning/integration/source_learning_chain_smoke.py",
    "tests/smoke/learning/integration/learning_quality_smoke.py",
    "tests/smoke/learning/local_scope_smoke.py",
    "xinyu_status.py",
    "tests/smoke/learning/learning_library_smoke.py",
    "tests/smoke/bridge/integration/bridge_probe_smoke.py",
    "tests/smoke/bridge/bridge_session_cleanup_smoke.py",
    "tests/smoke/voice/xinyu_speech_controller_smoke.py",
    "tests/smoke/qq/xinyu_qq_review_smoke.py",
    "tests/smoke/runtime/integration/deployment_status_smoke.py",
    "tests/smoke/runtime/integration/runtime_readiness_smoke.py",
    "tests/smoke/runtime/runtime_security_smoke.py",
    "tests/smoke/runtime/state_io_smoke.py",
]

RESIDUE_MARKERS = [
    "Memory Lived Pressure Probe",
    "lived pressure ordinary filler",
    "probe validates lived owner residue",
    "Activation provider fixture",
    "Social Inquiry Candidates Smoke",
    "Real Life Input Events Smoke",
]


def _knowledge(root: Path, filename: str) -> Path:
    return knowledge_file_path(root, filename)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def extract_milestones(plan_text: str) -> list[dict[str, str]]:
    pattern = re.compile(
        r"(?m)^#{2,3} Milestone (?P<number>\d+): (?P<title>.+?)\n\nstatus: (?P<status>[a-z_]+)"
    )
    return [match.groupdict() for match in pattern.finditer(plan_text)]


def missing_paths(root: Path, rels: list[str]) -> list[str]:
    return [rel for rel in rels if not (root / rel).exists()]


def residue_hits(root: Path) -> list[str]:
    hits: list[str] = []
    memory_root = root / "memory"
    if not memory_root.exists():
        return ["memory directory missing"]
    for path in memory_root.rglob("*.md"):
        text = read_text(path)
        for marker in RESIDUE_MARKERS:
            if marker in text:
                hits.append(f"{path.relative_to(root).as_posix()}: {marker}")
    return hits


def extract_field(path: Path, field: str, default: str = "unknown") -> str:
    if not path.exists():
        return "missing"
    text = read_text(path)
    match = re.search(rf"(?m)^- {re.escape(field)}:\s*(.+)$", text)
    return match.group(1).strip() if match else default


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize Xinyu long-run engineering status.")
    parser.add_argument("--require-all-completed", action="store_true")
    parser.add_argument("--require-no-residue", action="store_true")
    parser.add_argument(
        "--skip-deployment-gate",
        action="store_true",
        help="Skip live deployment status checks when the caller is explicitly offline.",
    )
    return parser


def deployment_gate(root: Path) -> tuple[bool, str]:
    python_exe = root / ".venv" / "Scripts" / "python.exe"
    if not python_exe.exists():
        python_exe = Path(sys.executable)
    completed = subprocess.run(
        [str(python_exe), "tests/smoke/runtime/integration/deployment_status_smoke.py", "--json"],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=45,
    )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError:
        detail = (completed.stdout + "\n" + completed.stderr).strip().splitlines()
        return completed.returncode == 0, (detail[-1] if detail else f"exit={completed.returncode}")
    failures = result.get("failures", [])
    if completed.returncode == 0 and result.get("ok") is True:
        return True, "ok"
    if isinstance(failures, list) and failures:
        detail = "; ".join(str(item) for item in failures[:3])
        if len(failures) > 3:
            detail += f"; +{len(failures) - 3} more"
        return False, detail
    return False, f"exit={completed.returncode}"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    root = APP_ROOT

    plan_path = root / "plan.md"
    plan_text = read_text(plan_path) if plan_path.exists() else ""
    milestones = extract_milestones(plan_text) if plan_text else []
    status_counts: dict[str, int] = {}
    for item in milestones:
        status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1
    missing_docs = missing_paths(root, REQUIRED_DOCS)
    missing_validations = missing_paths(root, REQUIRED_VALIDATIONS)
    hits = residue_hits(root)

    print("=== XINYU LONG RUN STATUS ===")
    print("milestones_source:", "plan.md" if plan_text else "deleted_plan_docs_skipped")
    print("milestones_total:", len(milestones))
    for status in sorted(status_counts):
        print(f"milestones_{status}:", status_counts[status])
    print("missing_docs:", ", ".join(missing_docs) or "none")
    print("missing_validations:", ", ".join(missing_validations) or "none")
    print("residue_hits:", ", ".join(hits) or "none")
    deployment_ok = True
    deployment_detail = "not_run"
    if args.require_no_residue and not args.skip_deployment_gate:
        deployment_ok, deployment_detail = deployment_gate(root)
    elif args.skip_deployment_gate:
        deployment_detail = "skipped_offline"
    if args.skip_deployment_gate:
        print("deployment_gate:", deployment_detail)
    else:
        print("deployment_gate:", "ok" if deployment_ok else f"failed ({deployment_detail})")
    print("learning_quality_grade:", extract_field(_knowledge(root, "learning_quality_state.md"), "quality_grade"))
    print(
        "autonomous_search_permission:",
        extract_field(_knowledge(root, "autonomous_search_activation_state.md"), "activation_permission"),
    )
    print(
        "social_inquiry_mode:",
        extract_field(_knowledge(root, "social_inquiry_policy_state.md"), "mode"),
    )
    print(
        "real_life_input_mode:",
        extract_field(root / "memory/context/real_life_input_adapter_state.md", "mode"),
    )
    print("=== MILESTONES ===")
    for item in milestones:
        print(f"- {item['number']}: {item['title']} => {item['status']}")

    if args.require_all_completed and milestones and any(item["status"] != "completed" for item in milestones):
        return 4
    if args.require_no_residue and hits:
        return 5
    if args.require_no_residue and not deployment_ok:
        return 7
    if missing_docs or missing_validations:
        return 6
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
