from __future__ import annotations

import argparse

from _manual_paths import APP_ROOT, bootstrap_paths


def _load_engine():
    bootstrap_paths()
    from question_pipeline_engine import run_question_pipeline

    return run_question_pipeline


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Advance Xinyu question pipeline without full runtime.")
    parser.add_argument("--show-state", action="store_true", help="Print key question-pipeline files after update.")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    xinyu_dir = APP_ROOT
    run_question_pipeline = _load_engine()
    result = run_question_pipeline(xinyu_dir, mode="manual_question_pipeline")

    print("Xinyu manual question pipeline complete.")
    print(f"Internal clarification: {len(result['internal_ids'])}")
    print(f"Future exploration: {len(result['external_ids'])}")
    print(f"Blocked by self/relationship meaning: {len(result['blocked_ids'])}")

    if args.show_state:
        for rel in [
            "memory/context/question_pipeline_state.md",
            "memory/context/question_states.md",
            "memory/context/exploration_queue.md",
            "memory/knowledge/source_notes.md",
        ]:
            path = xinyu_dir / rel
            print(f"\n--- {rel} ---")
            print(path.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
