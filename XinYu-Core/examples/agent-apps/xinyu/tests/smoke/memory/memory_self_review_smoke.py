from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import tempfile
from pathlib import Path

from xinyu_dialogue_archive import list_memory_candidates, store_memory_candidate
from xinyu_memory_self_review import (
    BLOCKED_SCOPE_MISMATCH,
    BLOCKED_SENSITIVE,
    OBSERVE_MORE_OWNER_PREFERENCE,
    OBSERVE_MORE_RELATIONSHIP_SIGNAL,
    OWNER_REVIEW_REQUIRED,
    SELF_APPROVED_RECENT_CONTEXT,
    SELF_APPROVED_VOICE_REVIEW,
    run_memory_self_review,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def _candidate(
    root: Path,
    candidate_id: str,
    candidate_type: str,
    *,
    text: str,
    target_layer: str,
    reason: str,
    gate: str = "test_gate",
    score: int = 70,
) -> None:
    stored = store_memory_candidate(
        root,
        candidate_id=candidate_id,
        candidate_type=candidate_type,
        source_message_ids=[1],
        candidate_text=text,
        confidence_score=score,
        target_gate=gate,
        target_memory_layer=target_layer,
        reason=reason,
        review_notes="pending test review",
        created_at="2026-05-02T16:00:00+08:00",
    )
    if not stored:
        raise RuntimeError(f"failed to store candidate fixture: {candidate_id}")


def _ids_for_status(root: Path, status: str) -> set[str]:
    return {str(row.get("candidate_id")) for row in list_memory_candidates(root, status=status, limit=50)}


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-memory-self-review-") as tmp:
        root = Path(tmp)
        protected = [
            root / "memory/self/core.md",
            root / "memory/self/personality_profile.md",
            root / "memory/people/owner.md",
            root / "memory/relationships/index.md",
            root / "memory/context/recent_context.md",
        ]
        for path in protected:
            _write(path, f"stable {path.name}")
        before = {path: _read(path) for path in protected}

        _candidate(
            root,
            "project-1",
            "project_fact",
            text="runtime project fact candidate",
            target_layer="memory/context/recent_context.md",
            reason="project/runtime continuity signal",
        )
        _candidate(
            root,
            "voice-1",
            "voice_correction",
            text="voice correction candidate; stable voice rewrite blocked",
            target_layer="memory/self/voice_calibration_log.md",
            reason="owner-private voice/style correction markers",
        )
        _candidate(
            root,
            "pref-1",
            "owner_preference",
            text="owner preference candidate from one turn",
            target_layer="memory/people/owner.md",
            reason="possible owner preference; review for repetition",
        )
        _candidate(
            root,
            "rel-1",
            "relationship_signal",
            text="relationship signal candidate from one turn",
            target_layer="memory/relationships/index.md",
            reason="owner-private relationship or emotional residue markers",
        )
        _candidate(
            root,
            "group-rel-1",
            "relationship_signal",
            text="group_context says owner is disappointed",
            target_layer="memory/relationships/index.md",
            reason="group-scoped and not owner relationship memory",
        )
        _candidate(
            root,
            "core-1",
            "project_fact",
            text="rewrite core personality candidate",
            target_layer="memory/self/personality_profile.md",
            reason="stable identity change requested",
        )
        _candidate(
            root,
            "secret-1",
            "project_fact",
            text="temporary note with api_key=abc123456789012345",
            target_layer="memory/context/recent_context.md",
            reason="project continuity with credential-like material",
        )

        result = run_memory_self_review(root, checked_at="2026-05-02T16:10:00+08:00")
        state = _read(root / "memory/context/memory_self_review_state.md")
        trace = _read(root / "runtime/memory_self_review_trace.jsonl")

        if result["reviewed_candidates"] != 7:
            failures.append(f"expected 7 reviewed candidates, got {result}")
        if result["self_approved"] != 2:
            failures.append(f"expected 2 self-approved candidates, got {result}")
        if result["observe_more"] != 2:
            failures.append(f"expected 2 observe-more candidates, got {result}")
        if result["owner_review_required"] != 1:
            failures.append(f"expected 1 owner-review candidate, got {result}")
        if result["blocked"] != 2:
            failures.append(f"expected 2 blocked candidates, got {result}")
        if result["conflict_review_required"] != 0:
            failures.append(f"expected 0 conflict-review candidates, got {result}")

        expectations = {
            SELF_APPROVED_RECENT_CONTEXT: {"project-1"},
            SELF_APPROVED_VOICE_REVIEW: {"voice-1"},
            OBSERVE_MORE_OWNER_PREFERENCE: {"pref-1"},
            OBSERVE_MORE_RELATIONSHIP_SIGNAL: {"rel-1"},
            BLOCKED_SCOPE_MISMATCH: {"group-rel-1"},
            OWNER_REVIEW_REQUIRED: {"core-1"},
            BLOCKED_SENSITIVE: {"secret-1"},
        }
        for status, expected_ids in expectations.items():
            actual = _ids_for_status(root, status)
            missing = expected_ids - actual
            if missing:
                failures.append(f"{status} missing ids: {sorted(missing)}; actual={sorted(actual)}")
        if list_memory_candidates(root, status="pending"):
            failures.append("pending candidates remained after self-review")

        for marker in (
            "memory_type: memory_self_review_state",
            "status: reviewed",
            "reviewed_candidates: 7",
            "self_approved: 2",
            "observe_more: 2",
            "owner_review_required: 1",
            "blocked: 2",
            "conflict_review_required: 0",
            "stable_memory_write: blocked",
            "owner_bulk_review_required: false",
            "conflicting_candidate_evidence: owner_review_required_conflict_resolution",
            "group_owner_relationship_memory: blocked_scope_mismatch",
            "credential_or_secret_material: blocked_sensitive",
        ):
            if marker not in state:
                failures.append(f"self-review state missing marker: {marker}")
        if "api_key=abc123456789012345" in state or "api_key=abc123456789012345" in trace:
            failures.append("self-review leaked credential-like text")
        if "memory_self_review_completed" not in trace:
            failures.append("self-review trace missing completion note")
        for path, text in before.items():
            if _read(path) != text:
                failures.append(f"self-review changed protected memory file: {path}")
        if (root / "memory/context/qq_outbox_queue.json").exists():
            failures.append("self-review created QQ outbox")

    source_root = ROOT
    core_text = _read(source_root / "xinyu_core_bridge.py")
    sidecar_text = _read(source_root / "xinyu_bridge_turn_finish_sidecars.py")
    context_text = _read(source_root / "xinyu_runtime_context.py")
    presence_text = _read(source_root / "xinyu_runtime_presence.py")
    if "run_slow_turn_finish_sidecars" not in core_text:
        failures.append("xinyu_core_bridge.py does not run turn finish sidecars")
    if "run_memory_self_review(" not in sidecar_text:
        failures.append("xinyu_bridge_turn_finish_sidecars.py does not run memory self-review")
    if "memory/context/memory_self_review_state.md" not in context_text:
        failures.append("runtime context does not include memory_self_review_state")
    if "runtime/memory_self_review_trace.jsonl" not in presence_text:
        failures.append("runtime presence does not summarize memory self-review trace")

    if failures:
        print("memory_self_review_smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("memory_self_review_smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

