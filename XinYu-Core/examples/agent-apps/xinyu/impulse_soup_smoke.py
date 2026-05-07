from __future__ import annotations

import json
import tempfile
from pathlib import Path

from xinyu_impulse_soup import STATE_JSON_REL, STATE_MD_REL, TRACE_REL, run_impulse_soup


CHECKED_AT = "2026-05-07T10:00:00+08:00"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _state(root: Path) -> dict[str, object]:
    return json.loads(_read(root / STATE_JSON_REL))


def _append_trace(root: Path, row: dict[str, object]) -> None:
    path = root / "memory/context/proactive_decision_trace.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _assert_no_dispatch(root: Path, failures: list[str]) -> None:
    for rel in (
        "memory/context/qq_outbox_queue.json",
        "memory/context/proactive_qq_dispatch_state.md",
    ):
        if (root / rel).exists():
            failures.append(f"impulse soup created dispatch file: {rel}")


def _seed_dream_trace(root: Path, *, score: int = 75, recommendation: str = "inbox") -> None:
    _append_trace(
        root,
        {
            "event_kind": "proactive_decision",
            "observed_at": "2026-05-07T09:55:00+08:00",
            "source_type": "dream_residue",
            "candidate_signature": "prosig:dream-smoke",
            "candidate_id": "proshadow-dream",
            "total_score": score,
            "recommendation": recommendation,
            "hard_blocks": ["qq_send_disabled_for_dream_v0"],
            "score": {"total_score": score, "repetition_penalty": 0},
            "candidate": {
                "owner_visible_text": "A dream residue is available for review.",
                "source_ref": "dream_output:dream-smoke",
            },
        },
    )


def _seed_runtime_trace(root: Path) -> None:
    _append_trace(
        root,
        {
            "event_kind": "proactive_decision",
            "observed_at": "2026-05-07T09:56:00+08:00",
            "source_type": "runtime_error",
            "candidate_signature": "prosig:runtime-smoke",
            "candidate_id": "proshadow-runtime",
            "total_score": 92,
            "recommendation": "send_now",
            "hard_blocks": [],
            "score": {"total_score": 92, "repetition_penalty": 0},
            "candidate": {
                "owner_visible_text": "A runtime subsystem reported an error.",
                "source_ref": "runtime_program_awareness:watched_source",
            },
        },
    )


def _seed_style_trace(root: Path, suffix: int) -> None:
    _append_trace(
        root,
        {
            "event_kind": "proactive_decision",
            "observed_at": f"2026-05-07T09:5{suffix}:00+08:00",
            "source_type": "style_repair",
            "candidate_signature": f"prosig:style-smoke-{suffix}",
            "candidate_id": f"proshadow-style-{suffix}",
            "total_score": 99,
            "recommendation": "send_now",
            "hard_blocks": [],
            "score": {"total_score": 99, "repetition_penalty": 0},
            "candidate": {
                "owner_visible_text": f"A reply-style repair signal is waiting. {suffix}",
                "source_ref": f"style_repair:smoke-{suffix}",
            },
        },
    )


def _seed_leaky_trace(root: Path) -> None:
    _append_trace(
        root,
        {
            "event_kind": "proactive_decision",
            "observed_at": "2026-05-07T09:57:00+08:00",
            "source_type": "reflection_question",
            "candidate_signature": "prosig:leaky-smoke",
            "candidate_id": "proshadow-leaky",
            "total_score": 70,
            "recommendation": "inbox",
            "hard_blocks": [],
            "score": {"total_score": 70, "repetition_penalty": 0},
            "candidate": {
                "owner_visible_text": "Codex source_seed dream_weight should be visible?",
                "source_ref": "reflection_queue:leaky",
            },
        },
    )


def main() -> int:
    failures: list[str] = []

    with tempfile.TemporaryDirectory(prefix="xinyu-impulse-basic-") as tmp:
        root = Path(tmp)
        _seed_dream_trace(root)
        _seed_runtime_trace(root)
        result = run_impulse_soup(root, checked_at=CHECKED_AT)
        state = _state(root)
        md = _read(root / STATE_MD_REL)
        trace = _read(root / TRACE_REL)
        if result["created_count"] < 2 or result["active_count"] < 1:
            failures.append(f"basic seeds should create active thoughtlets: {result}")
        if "no_qq_enqueue: true" not in md or "no_tool_execution: true" not in md:
            failures.append("safety boundaries missing from md state")
        if "impulse_soup_cycle" not in trace:
            failures.append("impulse soup trace was not written")
        if not state.get("boundaries", {}).get("no_process_replication"):
            failures.append("json state did not record no_process_replication")
        _assert_no_dispatch(root, failures)

    with tempfile.TemporaryDirectory(prefix="xinyu-impulse-repeat-") as tmp:
        root = Path(tmp)
        _seed_dream_trace(root, score=75, recommendation="inbox")
        first = run_impulse_soup(root, checked_at=CHECKED_AT)
        _seed_dream_trace(root, score=30, recommendation="drop")
        second = run_impulse_soup(root, checked_at="2026-05-07T10:05:00+08:00")
        state = _state(root)
        thoughtlets = state.get("thoughtlets", [])
        if first["thoughtlet_count"] != 1 or second["thoughtlet_count"] != 1:
            failures.append(f"same source signature should refresh, not duplicate: first={first} second={second}")
        if thoughtlets and thoughtlets[0].get("activation_count", 0) < 2:
            failures.append("repeated seed did not increment activation_count")
        if thoughtlets and thoughtlets[0].get("energy", 100) >= 75:
            failures.append("repeated low-value seed did not cool energy")
        _assert_no_dispatch(root, failures)

    with tempfile.TemporaryDirectory(prefix="xinyu-impulse-spawn-") as tmp:
        root = Path(tmp)
        _write(
            root / STATE_JSON_REL,
            json.dumps(
                {
                    "schema_version": "impulse_soup_v0",
                    "thoughtlets": [
                        {
                            "thoughtlet_id": "impulse-parent",
                            "lineage_id": "impline-parent",
                            "parent_id": "none",
                            "generation": 0,
                            "source_kind": "runtime_error",
                            "source_ref": "runtime_awareness:smoke",
                            "source_signature": "impseed:parent",
                            "desire_shape": "runtime_diagnostic_reflex",
                            "proposed_next_action": "diagnose_locally_first",
                            "inhibition_rule": "no_owner_interrupt_until_diagnosis",
                            "energy": 88,
                            "usefulness_score": 80,
                            "mutation_count": 0,
                            "activation_count": 3,
                            "risk_flags": [],
                            "evidence_preview": "runtime smoke",
                            "status": "active",
                            "created_at": "2026-05-07T00:00:00+08:00",
                            "updated_at": "2026-05-07T00:00:00+08:00",
                            "last_triggered_at": "2026-05-07T00:00:00+08:00",
                            "last_spawned_at": "",
                            "expires_at": "2026-05-14T00:00:00+08:00",
                        }
                    ],
                },
                ensure_ascii=False,
            ),
        )
        result = run_impulse_soup(root, checked_at=CHECKED_AT)
        state = _state(root)
        if result["spawned_count"] != 1:
            failures.append(f"high-energy thoughtlet should spawn one child: {result}")
        if not any(item.get("parent_id") == "impulse-parent" for item in state.get("thoughtlets", [])):
            failures.append("spawned child lineage was not recorded")
        _assert_no_dispatch(root, failures)

    with tempfile.TemporaryDirectory(prefix="xinyu-impulse-style-limit-") as tmp:
        root = Path(tmp)
        for index in range(7):
            _seed_style_trace(root, index)
        result = run_impulse_soup(root, checked_at=CHECKED_AT)
        state = _state(root)
        thoughtlets = state.get("thoughtlets", [])
        active_style = [
            item
            for item in thoughtlets
            if item.get("desire_shape") == "expression_repair_habit" and item.get("status") == "active"
        ]
        if len(active_style) > 4:
            failures.append(f"style repair should stay capped in active pool: {len(active_style)} result={result}")
        if any(item.get("energy", 0) > 58 for item in active_style):
            failures.append(f"style repair energy should stay background-capped: {active_style}")
        if result["spawned_count"] != 0:
            failures.append(f"style repair should not spawn child thoughtlets: {result}")
        _assert_no_dispatch(root, failures)

    with tempfile.TemporaryDirectory(prefix="xinyu-impulse-quarantine-") as tmp:
        root = Path(tmp)
        _seed_leaky_trace(root)
        result = run_impulse_soup(root, checked_at=CHECKED_AT)
        if result["quarantined_count"] != 1:
            failures.append(f"internal marker seed should be quarantined: {result}")
        _assert_no_dispatch(root, failures)

    if failures:
        print("Impulse soup smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Impulse soup smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
