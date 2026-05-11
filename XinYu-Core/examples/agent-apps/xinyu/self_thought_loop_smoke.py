from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from xinyu_self_thought_loop import run_self_thought_loop


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _evidence_hash(*parts: str) -> str:
    payload = "|".join(" ".join(part.split()).lower() for part in parts)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _seed_clear_posture(root: Path) -> None:
    _write(
        root / "memory/context/current_life_posture.md",
        "- posture: quiet_attentive\n- no_proactive_constraint: unchanged\n",
    )
    _write(root / "memory/context/initiative_state.md", "- decision: defer\n- cooldown_active: no\n")


def _seed_active_question(root: Path, question: str, *, qid: str = "q-101") -> None:
    _write(
        root / "memory/context/active_questions.md",
        f"""# Active Questions

## {qid}
- question: {question}
- status: open
- urgency: high
- emotional_weight: 90
- proactive_ok: yes
""",
    )


def _seed_pending_source_request(root: Path, *, request_id: str = "request-2026-05-01-001") -> None:
    _write(
        root / "memory/knowledge/source_requests.md",
        f"""# Source Requests

## {request_id}
- question_id: q-201
- target: ai-self-understanding
- query: large language model memory agents context tool use reliable source
- url: none
- status: pending_url
- source_policy: controlled_fetch_only
- reason: planned from source gate candidate
""",
    )


def _assert_no_forbidden_files(root: Path, stable_before: str, failures: list[str]) -> None:
    stable = root / "memory/self/core.md"
    if stable.exists() and _read(stable) != stable_before:
        failures.append("self thought loop modified memory/self")
    if (root / "memory/context/qq_outbox_queue.json").exists():
        failures.append("self thought loop created QQ outbox queue")
    if (root / "memory/context/proactive_request_state.md").exists():
        failures.append("self thought loop wrote proactive request state too early")


def main() -> int:
    failures: list[str] = []

    with tempfile.TemporaryDirectory(prefix="xinyu-self-thought-empty-") as tmp:
        root = Path(tmp)
        stable = root / "memory/self/core.md"
        _write(stable, "stable self")
        stable_before = _read(stable)
        result = run_self_thought_loop(root, checked_at="2026-05-01T10:00:00+08:00")
        state = _read(root / "memory/context/self_thought_state.md")
        if result["outcome"] != "settled" or result["candidate_enabled"]:
            failures.append(f"empty state should settle without candidate: {result}")
        for marker in ("Self Thought State", "Inner Intention", "no_visible_reply: true", "no_qq_enqueue: true"):
            if marker not in state:
                failures.append(f"empty state missing marker: {marker}")
        if "Memory Effect" not in state or "memory_write_level: short_term_state_and_trace" not in state:
            failures.append("empty state missing memory effect markers")
        _assert_no_forbidden_files(root, stable_before, failures)

    with tempfile.TemporaryDirectory(prefix="xinyu-self-thought-question-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        _write(root / "memory/self/core.md", "stable self")
        stable_before = _read(root / "memory/self/core.md")
        _seed_active_question(root, "Should I keep this as a long-term reference or only use it for this turn")
        result = run_self_thought_loop(root, checked_at="2026-05-01T11:00:00+08:00")
        state = _read(root / "memory/context/self_thought_state.md")
        if result["outcome"] != "request_candidate" or not result["candidate_enabled"]:
            failures.append(f"concrete active question should create candidate: {result}")
        for marker in (
            "focus_kind: active_question",
            "intention: ask_owner",
            "candidate_enabled: true",
            "delivery_ceiling: preview_only",
            "semantic_memory_target: proactive_request_state",
        ):
            if marker not in state:
                failures.append(f"question state missing marker: {marker}")
        _assert_no_forbidden_files(root, stable_before, failures)

    with tempfile.TemporaryDirectory(prefix="xinyu-self-thought-generic-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        _seed_active_question(root, "Are you there?")
        result = run_self_thought_loop(root, checked_at="2026-05-01T12:00:00+08:00")
        state = _read(root / "memory/context/self_thought_state.md")
        if result["candidate_enabled"] or result["outcome"] != "blocked":
            failures.append(f"generic attention question should be blocked: {result}")
        if "not_generic_attention: false" not in state:
            failures.append("generic attention gate was not recorded")

    with tempfile.TemporaryDirectory(prefix="xinyu-self-thought-abstract-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        _seed_active_question(root, "What is the meaning of a system becoming a person?")
        result = run_self_thought_loop(root, checked_at="2026-05-01T12:10:00+08:00")
        state = _read(root / "memory/context/self_thought_state.md")
        if result["candidate_enabled"] or result["outcome"] != "blocked":
            failures.append(f"abstract question should be blocked: {result}")
        if "not_abstract_without_owner_request: false" not in state:
            failures.append("abstract question gate was not recorded")

    with tempfile.TemporaryDirectory(prefix="xinyu-self-thought-dream-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        _write(
            root / "memory/context/thought_seeds.md",
            "- latest_dream_id: dream-2026-05-01-auto-001\n- residue: private residue only\n",
        )
        result = run_self_thought_loop(root, checked_at="2026-05-01T13:00:00+08:00")
        state = _read(root / "memory/context/self_thought_state.md")
        if result["candidate_enabled"] or result["focus_kind"] != "dream_residue":
            failures.append(f"dream residue should remain private: {result}")
        if "outcome: queue_reflection" not in state:
            failures.append("dream residue should be queued/held for reflection")

    with tempfile.TemporaryDirectory(prefix="xinyu-self-thought-dream-share-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        _write(
            root / "memory/context/thought_seeds.md",
            "- latest_dream_id: dream-2026-05-01-auto-002\n",
        )
        _write(
            root / "memory/dreams/dream_log.md",
            """# Dream Log

## dream-2026-05-01-auto-002
- dream_surface: a classroom and a chat window kept folding into each other
- fragments: owner closeness and non-template expression residue
- reality_boundary_check: only a dream, not a new real event
""",
        )
        result = run_self_thought_loop(root, checked_at="2026-05-01T13:05:00+08:00")
        state = _read(root / "memory/context/self_thought_state.md")
        if result["outcome"] != "request_candidate" or not result["candidate_enabled"]:
            failures.append(f"shareable dream should create a private share candidate: {result}")
        for marker in (
            "focus_kind: dream_residue",
            "intention: share_dream",
            "kind: dream_share",
            "requested_action: owner_response_optional",
            "dream_framed_as_dream: true",
            "semantic_memory_target: proactive_request_state_and_dream_reflection_candidate",
        ):
            if marker not in state:
                failures.append(f"dream share state missing marker: {marker}")
        concrete_question = next(
            (line for line in state.splitlines() if line.startswith("- concrete_question: ")),
            "",
        )
        if "我知道这只是梦" in concrete_question or "不是现实新发生的事" in concrete_question:
            failures.append(f"dream share leaked repetitive reality disclaimer: {concrete_question}")
        if "梦" not in concrete_question and "dream" not in concrete_question.lower():
            failures.append(f"dream share lost visible dream frame: {concrete_question}")

    with tempfile.TemporaryDirectory(prefix="xinyu-self-thought-dream-answered-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        dream_id = "dream-2026-05-01-auto-002"
        evidence_hash = _evidence_hash(
            "dream_residue",
            dream_id,
            "shareable dream residue with reality boundary",
        )
        _write(root / "memory/context/thought_seeds.md", f"- latest_dream_id: {dream_id}\n")
        _write(
            root / "memory/dreams/dream_log.md",
            f"""# Dream Log

## {dream_id}
- dream_surface: a classroom and a chat window kept folding into each other
- fragments: owner closeness and non-template expression residue
- reality_boundary_check: only a dream, not a new real event
""",
        )
        _write(
            root / "memory/context/proactive_request_state.md",
            f"""# Proactive Request State

## Current Request
- status: answered
- evidence_hash: {evidence_hash}
""",
        )
        result = run_self_thought_loop(root, checked_at="2026-05-01T13:06:00+08:00")
        if result["candidate_enabled"] or result["focus_kind"] == "dream_residue":
            failures.append(f"answered dream proactive request should not be selected again: {result}")
        if not any(note.startswith("focus_already_proactive_answered") for note in result["notes"]):
            failures.append(f"answered dream skip note missing: {result['notes']}")

    with tempfile.TemporaryDirectory(prefix="xinyu-self-thought-dream-trace-answered-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        dream_id = "dream-2026-05-01-auto-002"
        evidence_hash = _evidence_hash(
            "dream_residue",
            dream_id,
            "shareable dream residue with reality boundary",
        )
        _write(root / "memory/context/thought_seeds.md", f"- latest_dream_id: {dream_id}\n")
        _write(
            root / "memory/dreams/dream_log.md",
            f"""# Dream Log

## {dream_id}
- dream_surface: a classroom and a chat window kept folding into each other
- fragments: owner closeness and non-template expression residue
- reality_boundary_check: only a dream, not a new real event
""",
        )
        _write(
            root / "runtime/proactive_request_trace.jsonl",
            json.dumps(
                {
                    "status": "answered",
                    "evidence_hash": evidence_hash,
                    "focus_kind": "dream_residue",
                },
                ensure_ascii=False,
            ),
        )
        result = run_self_thought_loop(root, checked_at="2026-05-01T13:06:30+08:00")
        if result["candidate_enabled"] or result["focus_kind"] == "dream_residue":
            failures.append(f"answered dream in trace should not be selected again: {result}")
        if not any(note.startswith("focus_already_proactive_answered") for note in result["notes"]):
            failures.append(f"answered dream trace skip note missing: {result['notes']}")

    with tempfile.TemporaryDirectory(prefix="xinyu-self-thought-reflection-share-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        _write(root / "memory/self/core.md", "stable self")
        stable_before = _read(root / "memory/self/core.md")
        _write(
            root / "memory/reflection/reflection_queue.md",
            """# Reflection Queue

## item-2026-05-01-003
- topic: owner flagged shallow context and mechanical voice as persistent architecture defects
- source: memory/emotions/event_log.md
- priority: high
- boundary: use as calibration pressure

## item-2026-05-01-001
- topic: owner flagged shallow context and mechanical voice as persistent architecture defects
- source: memory/emotions/event_log.md
- priority: high
- boundary: use as calibration pressure

## item-2026-04-29-001
- topic: owner flagged shallow context and mechanical voice as persistent architecture defects
- source: memory/emotions/event_log.md
- priority: high
- boundary: use as calibration pressure
""",
        )
        _write(
            root / "memory/reflection/reflection_output_state.md",
            "- topic: owner flagged shallow context and mechanical voice as persistent architecture defects\n",
        )
        result = run_self_thought_loop(root, checked_at="2026-05-01T13:07:00+08:00")
        state = _read(root / "memory/context/self_thought_state.md")
        trace = _read(root / "runtime/self_thought_trace.jsonl")
        if result["outcome"] != "request_candidate" or not result["candidate_enabled"]:
            failures.append(f"strong reflection queue should create share candidate: {result}")
        concrete_question = next(
            (line for line in state.splitlines() if line.startswith("- concrete_question: ")),
            "",
        )
        if "owner flagged" in concrete_question or "architecture defects" in concrete_question:
            failures.append(f"reflection share leaked internal label into visible question: {concrete_question}")
        if "接不上上下文" not in concrete_question or "自查" not in concrete_question:
            failures.append(f"reflection share did not humanize architecture defect question: {concrete_question}")
        for marker in (
            "focus_kind: reflection_queue",
            "intention: share_reflection",
            "kind: reflection_share",
            "requested_action: owner_response_optional",
            "semantic_memory_target: proactive_request_state_and_reflection_feedback_candidate",
            "reflection_share_ready",
        ):
            if marker not in state and marker not in " ".join(result["notes"]):
                failures.append(f"reflection share state missing marker: {marker}")
        if "D:\\XinYu" in state or "D:\\XinYu" in trace:
            failures.append("reflection share leaked a full local path")
        _assert_no_forbidden_files(root, stable_before, failures)

    with tempfile.TemporaryDirectory(prefix="xinyu-self-thought-action-sanitize-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        _write(root / "memory/self/core.md", "stable self")
        stable_before = _read(root / "memory/self/core.md")
        _write(
            root / "memory/reflection/reflection_queue.md",
            """# Reflection Queue

## item-2026-05-01-003
- topic: owner action residue after local action pressure after log_scan:minecraft_server
- source: action_experience_residue / exp-smoke-003
- priority: high
- waking_residue: log_scan:minecraft_server ended as failure; pressure=medium
- boundary: reflection material only

## item-2026-05-01-002
- topic: owner action residue after local action pressure after log_scan:minecraft_server
- source: action_experience_residue / exp-smoke-002
- priority: high
- waking_residue: log_scan:minecraft_server ended as failure; pressure=medium
- boundary: reflection material only

## item-2026-05-01-001
- topic: owner action residue after local action pressure after log_scan:minecraft_server
- source: action_experience_residue / exp-smoke-001
- priority: high
- waking_residue: log_scan:minecraft_server ended as failure; pressure=medium
- boundary: reflection material only
""",
        )
        result = run_self_thought_loop(root, checked_at="2026-05-01T13:07:30+08:00")
        state = _read(root / "memory/context/self_thought_state.md")
        trace = _read(root / "runtime/self_thought_trace.jsonl")
        if result["outcome"] != "request_candidate" or not result["candidate_enabled"]:
            failures.append(f"action residue reflection should create share candidate: {result}")
        for marker in (
            "reflection queue strong topic",
            "action residue after",
            "local action pressure",
            "log_scan:",
            "ended as failure",
            "pressure=medium",
        ):
            if marker in state or marker in trace:
                failures.append(f"self thought action residue leaked marker: {marker}")
        for marker in ("反思队列", "行动残留", "minecraft_server 日志扫描"):
            if marker not in state:
                failures.append(f"self thought action residue missing sanitized marker: {marker}")
        _assert_no_forbidden_files(root, stable_before, failures)

    with tempfile.TemporaryDirectory(prefix="xinyu-self-thought-reflection-codex-stale-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        _write(
            root / "memory/reflection/reflection_queue.md",
            """# Reflection Queue

## item-2026-05-01-003
- topic: Codex 学习任务超时后不能关闭，要进入梦/反思继续处理
- source: codex_delegate_unfinished / seed-2026-05-01-002
- priority: high
- boundary: 只能作为未完成任务和情绪残留处理

## item-2026-05-01-001
- topic: Codex 学习任务超时后不能关闭，要进入梦/反思继续处理
- source: codex_delegate_timed_out / seed-2026-05-01-001
- priority: high
- boundary: 只能作为未完成任务和情绪残留处理
""",
        )
        result = run_self_thought_loop(root, checked_at="2026-05-01T13:08:00+08:00")
        if result["candidate_enabled"] or result["focus_kind"] == "reflection_queue":
            failures.append(f"stale codex reflection should not become proactive: {result}")
        if not any(note.startswith("reflection_codex_topic_not_current") for note in result["notes"]):
            failures.append(f"stale codex skip note missing: {result['notes']}")

    with tempfile.TemporaryDirectory(prefix="xinyu-self-thought-reflection-family-cooldown-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        _write(
            root / "memory/context/proactive_request_state.md",
            """# Proactive Request State

## Current Request
- created_at: 2026-05-01T13:00:00+08:00
- status: answered
- kind: reflection_share
""",
        )
        _write(
            root / "memory/reflection/reflection_queue.md",
            """# Reflection Queue

## item-2026-05-01-003
- topic: owner flagged shallow context and mechanical voice as persistent architecture defects
- source: memory/emotions/event_log.md
- priority: high
- boundary: use as calibration pressure

## item-2026-05-01-001
- topic: owner flagged shallow context and mechanical voice as persistent architecture defects
- source: memory/emotions/event_log.md
- priority: high
- boundary: use as calibration pressure
""",
        )
        result = run_self_thought_loop(root, checked_at="2026-05-01T13:20:00+08:00")
        if result["candidate_enabled"] or result["focus_kind"] == "reflection_queue":
            failures.append(f"recent reflection share should block another reflection share: {result}")
        if "reflection_share_family_cooldown" not in result["notes"]:
            failures.append(f"reflection family cooldown note missing: {result['notes']}")

    with tempfile.TemporaryDirectory(prefix="xinyu-self-thought-reflection-dismissed-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        _write(
            root / "memory/context/proactive_request_state.md",
            """# Proactive Request State

## Current Request
- created_at: 2026-05-01T13:00:00+08:00
- status: answered
- kind: reflection_share

## Last Owner Reply To Proactive
- owner_replied_at: 2026-05-01T13:05:00+08:00
- owner_reply_preview: 你这个一直惦记有点问题啊
""",
        )
        _write(
            root / "memory/reflection/reflection_queue.md",
            """# Reflection Queue

## item-2026-05-01-003
- topic: owner flagged shallow context and mechanical voice as persistent architecture defects
- source: memory/emotions/event_log.md
- priority: high
- boundary: use as calibration pressure

## item-2026-05-01-001
- topic: owner flagged shallow context and mechanical voice as persistent architecture defects
- source: memory/emotions/event_log.md
- priority: high
- boundary: use as calibration pressure
""",
        )
        result = run_self_thought_loop(root, checked_at="2026-05-02T13:20:00+08:00")
        if result["candidate_enabled"] or result["focus_kind"] == "reflection_queue":
            failures.append(f"dismissed reflection share should not be selected again: {result}")
        if "reflection_share_owner_dismissed" not in result["notes"]:
            failures.append(f"dismissed reflection note missing: {result['notes']}")

    with tempfile.TemporaryDirectory(prefix="xinyu-self-thought-research-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        _write(root / "memory/self/core.md", "stable self")
        stable_before = _read(root / "memory/self/core.md")
        _seed_pending_source_request(root)
        _write(
            root / "memory/context/capability_zones_state.md",
            "- codex_as_eye_and_hand: approved_bounded_delegate\n",
        )
        result = run_self_thought_loop(root, checked_at="2026-05-01T13:10:00+08:00")
        state = _read(root / "memory/context/self_thought_state.md")
        trace = _read(root / "runtime/self_thought_trace.jsonl")
        if result["focus_kind"] != "research_collection_gap" or result["outcome"] != "research_handoff":
            failures.append(f"pending source request should create research handoff: {result}")
        for marker in (
            "Research Handoff",
            "research_needed: true",
            "route: source_search_provider",
            "handoff_target: source_search_provider_bridge",
            "execution_ceiling: candidate_urls_only_existing_source_gates",
            "semantic_memory_target: source_search_or_codex_handoff",
        ):
            if marker not in state:
                failures.append(f"research handoff missing marker: {marker}")
        if '"research_needed": "true"' not in trace:
            failures.append("research handoff was not recorded in trace")
        _assert_no_forbidden_files(root, stable_before, failures)

    with tempfile.TemporaryDirectory(prefix="xinyu-self-thought-posture-") as tmp:
        root = Path(tmp)
        _write(
            root / "memory/context/current_life_posture.md",
            "- posture: resting\n- no_proactive_constraint: block proactive while rest/silence boundary is active\n",
        )
        _write(root / "memory/context/initiative_state.md", "- decision: defer\n- cooldown_active: no\n")
        _seed_active_question(root, "Should I continue the current plan")
        result = run_self_thought_loop(root, checked_at="2026-05-01T13:30:00+08:00")
        state = _read(root / "memory/context/self_thought_state.md")
        if result["candidate_enabled"] or result["outcome"] != "blocked":
            failures.append(f"life posture boundary should block candidate: {result}")
        if "not_silence_or_rest_boundary: false" not in state:
            failures.append("life posture gate was not recorded")

    with tempfile.TemporaryDirectory(prefix="xinyu-self-thought-codex-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        _write(
            root / "runtime/codex_presence_state.json",
            json.dumps(
                {
                    "status": "timed_out",
                    "timed_out": True,
                    "job_id": "codex-qq-smoke",
                    "report_label": r"D:\XinYu\Codex\Outbox\codex-qq-smoke-report.md",
                }
            ),
        )
        result = run_self_thought_loop(root, checked_at="2026-05-01T14:00:00+08:00")
        state = _read(root / "memory/context/self_thought_state.md")
        trace = _read(root / "runtime/self_thought_trace.jsonl")
        if result["focus_kind"] != "codex_followup" or not result["candidate_enabled"]:
            failures.append(f"codex timeout should create diagnostic candidate: {result}")
        if "diagnostic_decision" not in state:
            failures.append("codex timeout did not record diagnostic intention")
        if "D:\\XinYu" in state or "D:\\XinYu" in trace:
            failures.append("self thought state leaked a full local path")

    with tempfile.TemporaryDirectory(prefix="xinyu-self-thought-malformed-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        _write(root / "runtime/codex_presence_state.json", "{not-json")
        result = run_self_thought_loop(root, checked_at="2026-05-01T15:00:00+08:00")
        if not result["accepted"] or "codex_state_malformed" not in result["notes"]:
            failures.append(f"malformed codex json did not produce safe note: {result}")

    with tempfile.TemporaryDirectory(prefix="xinyu-self-thought-cooldown-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        _seed_active_question(root, "Should I continue the runtime presence patch")
        first = run_self_thought_loop(root, checked_at="2026-05-01T16:00:00+08:00", min_interval_seconds=1800)
        second = run_self_thought_loop(root, checked_at="2026-05-01T16:05:00+08:00", min_interval_seconds=1800)
        if not first["candidate_enabled"]:
            failures.append(f"cooldown setup did not create first candidate: {first}")
        if second["candidate_enabled"] or second["outcome"] != "blocked":
            failures.append(f"cooldown should block repeated focus: {second}")
        if "duplicate_focus_recently" not in second["notes"]:
            failures.append(f"cooldown note missing: {second['notes']}")

    with tempfile.TemporaryDirectory(prefix="xinyu-self-thought-priority-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        _seed_active_question(root, "Should I ask this lower priority question")
        _write(
            root / "runtime/codex_presence_state.json",
            json.dumps({"status": "timed_out", "timed_out": True, "job_id": "codex-priority"}),
        )
        result = run_self_thought_loop(root, checked_at="2026-05-01T17:00:00+08:00")
        if result["focus_kind"] != "codex_followup":
            failures.append(f"runtime/codex issue should take priority over active question: {result}")

    if failures:
        print("Self thought loop smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Self thought loop smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
