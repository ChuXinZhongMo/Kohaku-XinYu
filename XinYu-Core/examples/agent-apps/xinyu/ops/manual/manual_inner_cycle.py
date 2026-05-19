from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from _manual_paths import APP_ROOT, bootstrap_paths


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the full inner-framework cycle without full runtime."
    )
    parser.add_argument("--user", required=True, help="User text to feed into manual inner sync.")
    parser.add_argument("--assistant", default="", help="Optional assistant text for the same turn.")
    parser.add_argument("--show-state", action="store_true", help="Print resulting state files.")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    manual_dir = Path(__file__).resolve().parent
    xinyu_dir = APP_ROOT
    python_exe = Path(sys.executable)

    subprocess.run(
        [str(python_exe), str(manual_dir / "manual_inner_sync.py"), "--user", args.user, "--assistant", args.assistant],
        check=True,
    )
    subprocess.run([str(python_exe), str(manual_dir / "manual_question_pipeline.py")], check=True)
    subprocess.run([str(python_exe), str(manual_dir / "manual_slow_reprocess.py")], check=True)
    subprocess.run([str(python_exe), str(manual_dir / "manual_reflection_output.py")], check=True)
    subprocess.run([str(python_exe), str(manual_dir / "manual_source_gate.py")], check=True)

    bootstrap_paths()
    from long_term_memory_gate_engine import run_long_term_memory_gate
    from personality_growth_gate_engine import run_personality_growth_gate
    from source_integration_gate_engine import run_source_integration_gate
    from source_reliability_engine import run_source_reliability

    checked_at = datetime.now().astimezone().isoformat()
    run_source_reliability(
        xinyu_dir,
        checked_at=checked_at,
        mode="manual_inner_cycle_source_reliability",
    )
    run_source_integration_gate(
        xinyu_dir,
        checked_at=checked_at,
        mode="manual_inner_cycle_source_integration_gate",
    )
    run_long_term_memory_gate(
        xinyu_dir,
        checked_at=checked_at,
        mode="manual_inner_cycle_long_term_memory_gate",
    )
    run_personality_growth_gate(
        xinyu_dir,
        checked_at=checked_at,
        mode="manual_inner_cycle_personality_growth_gate",
    )
    from inner_cycle_engine import run_inner_cycle_summary

    run_inner_cycle_summary(
        xinyu_dir,
        checked_at=checked_at,
        mode="manual_inner_cycle",
    )

    print("Xinyu manual inner cycle complete.")
    print("Order: sync -> question_pipeline -> slow_reprocess -> reflection_output -> source_gate -> source_reliability -> source_integration_gate -> long_term_memory_gate -> personality_growth_gate -> inner_cycle")

    if args.show_state:
        for rel in [
            "memory/context/inner_cycle_state.md",
            "memory/context/inner_sync_state.md",
            "memory/context/question_pipeline_state.md",
            "memory/reflection/reprocessing_state.md",
            "memory/reflection/reflection_output_state.md",
            "memory/archive/long_term_memory_gate_state.md",
            "memory/self/personality_change_state.md",
            "memory/knowledge/source_gate_state.md",
            "memory/knowledge/source_reliability_state.md",
            "memory/knowledge/source_integration_gate_state.md",
        ]:
            path = xinyu_dir / rel
            print(f"\n--- {rel} ---")
            print(path.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
