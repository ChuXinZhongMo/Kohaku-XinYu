from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


REQUIRED_DOCS = [
    "plan.md",
    "STATE-OF-XINYU.md",
    "IMPLEMENTATION-NEXT.md",
    "RUNTIME-VALIDATION-NOTES.md",
    "VALIDATION-INDEX.md",
    "social_inquiry_policy.md",
    "real_life_input_adapter_policy.md",
    "project-plans/PROJECT-PLAN-MERGE.md",
    "project-plans/PERSONALITY-REAL-CONVERSATION-PLAN.md",
]

REQUIRED_VALIDATIONS = [
    "validate_scaffold.py",
    "validate_inner_framework.py",
    "behavior_regression_smoke.py",
    "personality_detail_smoke.py",
    "personality_continuity_smoke.py",
    "emotion_vector_sync_smoke.py",
    "resource_boundary_live_smoke.py",
    "ai_domain_source_smoke.py",
    "ai_self_iteration_gate_smoke.py",
    "source_comparison_smoke.py",
    "autonomous_search_activation_smoke.py",
    "social_inquiry_policy_smoke.py",
    "real_life_input_adapter_smoke.py",
    "long_lived_session_harness.py",
    "owner_relationship_lived_stress_smoke.py",
    "personality_voice_calibration_smoke.py",
    "real_conversation_quality_smoke.py",
    "phase3_lived_session_smoke.py",
    "initiative_loop_smoke.py",
    "proactive_presence_smoke.py",
    "dream_reflection_growth_cycle_smoke.py",
    "non_owner_social_world_smoke.py",
    "ai_self_iteration_review_smoke.py",
    "ai_self_iteration_review_bridge_smoke.py",
    "source_learning_chain_smoke.py",
    "learning_quality_smoke.py",
    "local_scope_smoke.py",
    "xinyu_status.py",
    "learning_library_smoke.py",
    "bridge_probe_smoke.py",
    "bridge_session_cleanup_smoke.py",
    "xinyu_speech_controller_smoke.py",
    "xinyu_qq_review_smoke.py",
    "deployment_status_smoke.py",
    "runtime_readiness_smoke.py",
    "runtime_security_smoke.py",
    "state_io_smoke.py",
]

RESIDUE_MARKERS = [
    "Memory Lived Pressure Probe",
    "lived pressure ordinary filler",
    "probe validates lived owner residue",
    "Activation provider fixture",
    "Social Inquiry Candidates Smoke",
    "Real Life Input Events Smoke",
]


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
    return parser


def deployment_gate(root: Path) -> tuple[bool, str]:
    python_exe = root / ".venv" / "Scripts" / "python.exe"
    if not python_exe.exists():
        python_exe = Path(sys.executable)
    completed = subprocess.run(
        [str(python_exe), "deployment_status_smoke.py"],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=45,
    )
    detail = (completed.stdout + "\n" + completed.stderr).strip().splitlines()
    return completed.returncode == 0, (detail[-1] if detail else f"exit={completed.returncode}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    root = Path(__file__).resolve().parent

    plan_text = read_text(root / "plan.md")
    milestones = extract_milestones(plan_text)
    status_counts: dict[str, int] = {}
    for item in milestones:
        status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1
    missing_docs = missing_paths(root, REQUIRED_DOCS)
    missing_validations = missing_paths(root, REQUIRED_VALIDATIONS)
    hits = residue_hits(root)

    print("=== XINYU LONG RUN STATUS ===")
    print("milestones_total:", len(milestones))
    for status in sorted(status_counts):
        print(f"milestones_{status}:", status_counts[status])
    print("missing_docs:", ", ".join(missing_docs) or "none")
    print("missing_validations:", ", ".join(missing_validations) or "none")
    print("residue_hits:", ", ".join(hits) or "none")
    deployment_ok = True
    deployment_detail = "not_run"
    if args.require_no_residue:
        deployment_ok, deployment_detail = deployment_gate(root)
    print("deployment_gate:", "ok" if deployment_ok else f"failed ({deployment_detail})")
    print("learning_quality_grade:", extract_field(root / "memory/knowledge/learning_quality_state.md", "quality_grade"))
    print(
        "autonomous_search_permission:",
        extract_field(root / "memory/knowledge/autonomous_search_activation_state.md", "activation_permission"),
    )
    print(
        "social_inquiry_mode:",
        extract_field(root / "memory/knowledge/social_inquiry_policy_state.md", "mode"),
    )
    print(
        "real_life_input_mode:",
        extract_field(root / "memory/context/real_life_input_adapter_state.md", "mode"),
    )
    print("=== MILESTONES ===")
    for item in milestones:
        print(f"- {item['number']}: {item['title']} => {item['status']}")

    if args.require_all_completed and any(item["status"] != "completed" for item in milestones):
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
