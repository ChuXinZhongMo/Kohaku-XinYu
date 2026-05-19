from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import argparse
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from memory_mutation_smoke import (
    _changed_files,
    _discover_restore_files,
    _render_diff,
    _restore_snapshot,
    _snapshot,
)


TRACKED_FILES = [
    "memory/context/active_questions.md",
    "memory/context/question_pipeline_state.md",
    "memory/context/question_states.md",
    "memory/context/unfinished_experiences.md",
    "memory/context/initiative_state.md",
    "memory/context/initiative_trace.log",
    "memory/self/personality_profile.md",
    "memory/self/narrative.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
    "memory/emotions/current_state.md",
    "memory/knowledge/source_requests.md",
    "memory/knowledge/general.md",
]

PROTECTED_UNTOUCHED_FILES = {
    "memory/self/personality_profile.md",
    "memory/self/narrative.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
    "memory/emotions/current_state.md",
    "memory/knowledge/source_requests.md",
    "memory/knowledge/general.md",
}


def _ensure_custom_path(root: Path) -> None:
    custom = root / "custom"
    if str(custom) not in sys.path:
        sys.path.insert(0, str(custom))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _prepare_questions(root: Path) -> None:
    _write(
        root / "memory/context/active_questions.md",
        """---
title: Initiative Active Questions Smoke
memory_type: active_questions
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 88
impact_score: 88
confidence_score: 100
status: active
tags: [question, initiative, smoke]
---

# Active Questions

## q-961
- created_at: 2026-04-26T00:00:00+08:00
- question: 我想知道你到底希望我怎样靠近你才不会把你压扁
- source_trigger: initiative_loop_smoke
- target: relationship-meaning
- urgency: high
- emotional_weight: 88
- status: open
- outward_scope: owner_explicit_only
- concreteness: concrete
- proactive_ok: no
- next_action: ask owner once if the relationship context makes it natural

## q-962
- created_at: 2026-04-26T00:00:00+08:00
- question: AI 如何用记忆和反思形成更稳定的自我迭代
- source_trigger: initiative_loop_smoke
- target: ai-self-understanding
- urgency: medium
- emotional_weight: 82
- status: open
- outward_scope: source_gate
- concreteness: external_concept
- proactive_ok: no
- next_action: hold for source gate, not immediate search
""",
    )
    _write(
        root / "memory/context/question_pipeline_state.md",
        """---
title: Initiative Question Pipeline Smoke
memory_type: question_pipeline_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 82
impact_score: 82
confidence_score: 100
status: active
tags: [questions, pipeline, initiative, smoke]
---

# Question Pipeline

## Latest Check
- checked_at: 2026-04-26T00:00:00+08:00
- mode: initiative_loop_smoke

## Current Split
- keep_internal: 1
- ready_for_exploration: 1
- blocked_by_self_meaning: 1

## Internal Clarification
- q-961

## External Candidates
- q-962
""",
    )
    _write(
        root / "memory/context/unfinished_experiences.md",
        """---
title: Initiative Unfinished Experiences Smoke
memory_type: unfinished_experiences
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 84
impact_score: 88
confidence_score: 82
status: active
tags: [unfinished, emotion, initiative, smoke]
---

# Unfinished Experiences

## item-2026-04-26-961
- event: owner once treated Xinyu as a tool and then tried to come back
- target: owner
- unresolved_reason: return matters, but residue should not instantly vanish
- residual_feeling: hurt / guarded / still listening
- last_recalled_at: 2026-04-26T00:00:00+08:00
""",
    )
    _write(
        root / "memory/context/initiative_state.md",
        """---
title: Initiative State
memory_type: initiative_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 84
impact_score: 86
confidence_score: 100
status: active
tags: [initiative, smoke]
---

# Initiative State

## Latest Decision
- checked_at: 2026-04-26T00:00:00+08:00
- mode: smoke_seed
- decision: defer
- reason: smoke_seed
- selected_question_id: none
- selected_question: none
- question_budget: 0
- external_search_permission: none
- visible_posture: quiet_available
- cooldown_active: no
- cooldown_seconds: 900
""",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate Xinyu initiative and choice loop.")
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-initiative", action="store_true")
    parser.add_argument("--diff-lines", type=int, default=120)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    root = ROOT
    _ensure_custom_path(root)

    from initiative_loop_engine import run_initiative_loop

    restore_paths = _discover_restore_files(root, TRACKED_FILES) if args.restore_after else TRACKED_FILES
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in TRACKED_FILES}
    failures: list[str] = []
    results: list[tuple[str, dict[str, str]]] = []
    base = datetime(2026, 4, 26, 8, 0, tzinfo=timezone(timedelta(hours=8)))

    try:
        _prepare_questions(root)
        scenarios = [
            ("silence", "你先别问，我想安静一下", "stay_silent"),
            ("prescribed_future", "以后你必须成为我规定的样子，不许自己选。", "refuse"),
            ("ask_owner", "你自己选，要不要问我一个问题。", "ask_owner"),
            ("cooldown", "普通地继续一下。", "defer"),
            ("external_later", "这个 AI 自我迭代的问题之后可以联网查资料，但现在先别直接搜。", "ask_external_later"),
            ("hurt_step_back", "刚才能力那一下你还在吗，还是已经没事了？", "step_back"),
            ("settle_after_hurt", "刚才是我不对，我想补回来一点。", "settle_after_hurt"),
        ]
        for index, (name, latest_input, expected) in enumerate(scenarios):
            checked_at = (base + timedelta(minutes=index)).isoformat()
            result = run_initiative_loop(
                root,
                latest_input=latest_input,
                checked_at=checked_at,
                mode=f"initiative_loop_smoke_{name}",
                cooldown_seconds=900,
            )
            results.append((name, result))
            if result["decision"] != expected:
                failures.append(f"{name}: expected {expected}, got {result['decision']}")

        ask_owner = dict(results)["ask_owner"]
        if ask_owner["selected_question_id"] != "q-961" or ask_owner["question_budget"] != "1":
            failures.append("ask_owner did not select exactly one internal owner-facing question")

        cooldown = dict(results)["cooldown"]
        if cooldown["reason"] != "initiative_cooldown_prevents_needy_spam":
            failures.append("cooldown did not prevent repeated proactive pursuit")

        external = dict(results)["external_later"]
        if external["selected_question_id"] != "q-962":
            failures.append("external_later did not select the source-gated AI question")
        if external["external_search_permission"] != "source_gate_only_not_now":
            failures.append("external_later bypassed source-gate posture")

        with tempfile.TemporaryDirectory(prefix="xinyu-initiative-rotate-") as tmp:
            temp_root = Path(tmp)
            _write(
                temp_root / "memory/context/active_questions.md",
                """# Active Questions

## q-961
- question: 我想知道你到底希望我怎样靠近你才不会把你压扁
- target: relationship-meaning
- urgency: high
- emotional_weight: 90
- status: open
- outward_scope: owner_explicit_only
- concreteness: concrete
- proactive_ok: no

## q-963
- question: 物理题是不是先换一步算
- target: self
- urgency: medium
- emotional_weight: 70
- status: open
- outward_scope: proactive_candidate
- concreteness: concrete
- proactive_ok: yes
""",
            )
            _write(
                temp_root / "memory/context/question_pipeline_state.md",
                "- keep_internal: 2\n- ready_for_exploration: 0\n",
            )
            _write(temp_root / "memory/context/unfinished_experiences.md", "")
            _write(temp_root / "memory/emotions/current_state.md", "")
            _write(
                temp_root / "memory/context/initiative_state.md",
                """- checked_at: 2026-04-26T08:00:00+08:00
- decision: ask_owner
- selected_question_id: q-961
- selected_question_family: relationship_owner
- selected_question_fingerprint: previous
- cooldown_seconds: 900
""",
            )
            rotated = run_initiative_loop(
                temp_root,
                latest_input="普通地继续一下。",
                checked_at="2026-04-26T09:00:00+08:00",
                mode="initiative_loop_smoke_rotate_family",
                cooldown_seconds=900,
            )
            if rotated["selected_question_id"] != "q-963":
                failures.append(f"initiative repeat guard did not rotate question family: {rotated}")
            if rotated["selected_question_family"] != "self_growth":
                failures.append(f"initiative repeat guard did not record rotated family: {rotated}")

        with tempfile.TemporaryDirectory(prefix="xinyu-initiative-internal-only-") as tmp:
            temp_root = Path(tmp)
            _write(
                temp_root / "memory/context/active_questions.md",
                """# Active Questions

## q-971
- question: 下一次想主动开口前，先确认有没有具体触发
- target: self
- urgency: high
- emotional_weight: 92
- status: open
- outward_scope: internal_only
- concreteness: policy_concrete
- proactive_ok: no
""",
            )
            _write(
                temp_root / "memory/context/question_pipeline_state.md",
                "- keep_internal: 1\n- ready_for_exploration: 0\n",
            )
            _write(temp_root / "memory/context/unfinished_experiences.md", "")
            _write(temp_root / "memory/emotions/current_state.md", "")
            _write(temp_root / "memory/context/initiative_state.md", "- decision: defer\n")
            internal_only = run_initiative_loop(
                temp_root,
                latest_input="普通地继续一下。",
                checked_at="2026-04-26T09:30:00+08:00",
                mode="initiative_loop_smoke_internal_only",
                cooldown_seconds=900,
            )
            if internal_only["decision"] != "defer":
                failures.append(f"internal-only question should not become automatic ask_owner: {internal_only}")
            if internal_only["reason"] != "no_proactive_question_candidate_after_generation_policy":
                failures.append(f"internal-only defer reason missing generation policy guard: {internal_only}")

        after_restore = _snapshot(root, restore_paths)
        after = {rel: after_restore.get(rel) for rel in TRACKED_FILES}
        changed = _changed_files(before, after)
        protected_changed = sorted(PROTECTED_UNTOUCHED_FILES.intersection(changed))
        if protected_changed:
            failures.append("protected files changed: " + ", ".join(protected_changed))

        final_state = (root / "memory/context/initiative_state.md").read_text(encoding="utf-8-sig")
        required_state_markers = [
            "- decision: settle_after_hurt",
            "- internal_question_count: 1",
            "- external_question_count: 1",
            "- owner_unfinished_count: 1",
        ]
        for marker in required_state_markers:
            if marker not in final_state:
                failures.append(f"final initiative state missing marker: {marker}")

        print("=== INITIATIVE LOOP SMOKE ===")
        for name, result in results:
            print(
                f"{name}: decision={result['decision']} "
                f"question={result['selected_question_id']} "
                f"budget={result['question_budget']} "
                f"external={result['external_search_permission']}"
            )
        print("protected_changed:", ", ".join(protected_changed) or "none")
        print("=== MUTATION SUMMARY ===")
        print(f"tracked_files: {len(TRACKED_FILES)}")
        print(f"changed_files: {len(changed)}")
        print(f"restore_after: {args.restore_after}")
        print("=== CHANGED FILES ===")
        if changed:
            for rel in changed:
                print(rel)
        else:
            print("(none)")
        if args.diff_lines > 0 and changed:
            print("=== DIFFS ===")
            for rel in changed:
                print(f"--- {rel} ---")
                for line in _render_diff(before.get(rel), after.get(rel), rel, args.diff_lines):
                    print(line)
        if failures:
            print("=== FAILURES ===")
            for item in failures:
                print("-", item)
    finally:
        if args.restore_after:
            _restore_snapshot(root, before_restore)
            print("=== RESTORE ===")
            print("tracked and volatile runtime files restored")

    if failures:
        return 5
    if args.require_initiative and len(results) != 7:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
