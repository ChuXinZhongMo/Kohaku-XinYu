from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import tempfile
from pathlib import Path

from xinyu_proactive_request_loop import run_proactive_request_loop


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _seed_self_thought(
    root: Path,
    *,
    candidate_enabled: bool = True,
    intention: str = "ask_owner",
    focus_kind: str = "active_question",
    question: str = "Should I continue the current plan?",
    requested_action: str = "owner_answer",
    evidence_label: str = "active question marked proactive_ok",
    evidence_hash: str = "sha256:abcdef1234567890",
) -> None:
    _write(
        root / "memory/context/self_thought_state.md",
        f"""---
title: Self Thought State
---

# Self Thought State

## Latest Pass
- pass_id: selfthought-smoke
- checked_at: 2026-05-01T10:00:00+08:00
- status: candidate
- outcome: request_candidate
- focus_kind: {focus_kind}
- focus_label: q-smoke
- evidence_label: {evidence_label}
- evidence_hash: {evidence_hash}

## Inner Intention
- intention_id: intent-smoke
- intention_status: candidate
- intention: {intention}
- owner_relevance: owner_is_needed
- delivery_ceiling: preview_only

## Request Candidate
- candidate_enabled: {str(candidate_enabled).lower()}
- kind: clarify
- concrete_question: {question}
- requested_action: {requested_action}
- why_now: {evidence_label}
- after_owner_replies: continue the current thread
""",
    )


def _seed_clear_posture(root: Path) -> None:
    _write(root / "memory/context/current_life_posture.md", "- no_proactive_constraint: unchanged\n")
    _write(root / "memory/context/owner_permission_grants.md", "")
    _write(root / "memory/context/capability_zones_state.md", "")


def _assert_no_dispatch(root: Path, failures: list[str]) -> None:
    forbidden = (
        root / "memory/context/qq_outbox_queue.json",
        root / "memory/context/proactive_qq_dispatch_state.md",
    )
    for path in forbidden:
        if path.exists():
            failures.append(f"proactive request loop created dispatch file: {path.name}")
    stable = root / "memory/self/core.md"
    if stable.exists() and _read(stable).strip() != "stable self":
        failures.append("proactive request loop modified memory/self")


def main() -> int:
    failures: list[str] = []

    with tempfile.TemporaryDirectory(prefix="xinyu-proreq-ready-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        _write(root / "memory/self/core.md", "stable self")
        _seed_self_thought(root)
        result = run_proactive_request_loop(root, evaluated_at="2026-05-01T11:00:00+08:00")
        state = _read(root / "memory/context/proactive_request_state.md")
        if result["status"] != "candidate_only" or result["delivery_level"] != "state_only":
            failures.append(f"valid self-thought request should become candidate_only state_only: {result}")
        for marker in (
            "Proactive Request State",
            "source: self_thought",
            "candidate_only",
            "delivery_level: state_only",
            "conversation_mode: threaded",
            "initial_message_budget: 3",
            "followup_budget: 6",
            "grounded_followups_allowed: true",
            "Memory Feedback",
            "memory_feedback_target: active_question_then_reflection_if_meaningful",
            "stable_memory_permission: blocked_until_owner_reply_and_memory_gates",
            "no_qq_enqueue: true",
        ):
            if marker not in state:
                failures.append(f"valid request state missing marker: {marker}")
        _assert_no_dispatch(root, failures)

    with tempfile.TemporaryDirectory(prefix="xinyu-proreq-disabled-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        _seed_self_thought(root, candidate_enabled=False)
        result = run_proactive_request_loop(root, evaluated_at="2026-05-01T11:30:00+08:00")
        if result["status"] != "none":
            failures.append(f"disabled self-thought candidate should not create request: {result}")
        if "self_thought_candidate_disabled" not in result["notes"]:
            failures.append(f"disabled candidate note missing: {result['notes']}")

    with tempfile.TemporaryDirectory(prefix="xinyu-proreq-generic-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        _seed_self_thought(root, question="Are you there?")
        result = run_proactive_request_loop(root, evaluated_at="2026-05-01T12:00:00+08:00")
        state = _read(root / "memory/context/proactive_request_state.md")
        if result["status"] != "blocked":
            failures.append(f"generic attention request should be blocked: {result}")
        if "not_generic_attention: false" not in state:
            failures.append("generic gate was not recorded")

    with tempfile.TemporaryDirectory(prefix="xinyu-proreq-abstract-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        _seed_self_thought(root, question="What is the meaning of a system becoming a person?")
        result = run_proactive_request_loop(root, evaluated_at="2026-05-01T12:10:00+08:00")
        state = _read(root / "memory/context/proactive_request_state.md")
        if result["status"] != "blocked":
            failures.append(f"abstract request should be blocked: {result}")
        if "not_abstract: false" not in state:
            failures.append("abstract gate was not recorded")

    with tempfile.TemporaryDirectory(prefix="xinyu-proreq-dream-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        _seed_self_thought(
            root,
            focus_kind="dream_residue",
            intention="queue_reflection",
            candidate_enabled=False,
            question="none",
            requested_action="none",
            evidence_label="dream residue requires reality boundary",
        )
        result = run_proactive_request_loop(root, evaluated_at="2026-05-01T13:00:00+08:00")
        state = _read(root / "memory/context/proactive_request_state.md")
        if result["status"] != "none":
            failures.append(f"dream residue should not create request: {result}")
        if "source_allowed: false" not in state:
            failures.append("dream/source gate should be false")

    with tempfile.TemporaryDirectory(prefix="xinyu-proreq-dream-share-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        _seed_self_thought(
            root,
            focus_kind="dream_residue",
            intention="share_dream",
            question="I had a dream about a classroom and a chat window folding into each other.",
            requested_action="owner_response_optional",
            evidence_label="shareable dream residue with reality boundary",
            evidence_hash="sha256:feedface12345678",
        )
        result = run_proactive_request_loop(root, evaluated_at="2026-05-01T13:05:00+08:00")
        state = _read(root / "memory/context/proactive_request_state.md")
        if result["status"] != "candidate_only" or result["kind"] != "dream_share":
            failures.append(f"dream share should become candidate_only: {result}")
        for marker in (
            "kind: dream_share",
            "focus_kind: dream_residue",
            "requested_action: owner_response_optional",
            "source_allowed: true",
            "dream_framed_as_dream: true",
            "memory_feedback_target: dream_log_then_reflection_if_owner_responds",
        ):
            if marker not in state:
                failures.append(f"dream share request missing marker: {marker}")
        if "not a new real event" in state or "不是现实新发生的事" in state:
            failures.append("dream share request required a visible reality disclaimer")

    with tempfile.TemporaryDirectory(prefix="xinyu-proreq-dream-share-long-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        long_dream = (
            "刚才梦里有个画面一直卡着：我梦见一条不断改名的窄街，四周是雨后的紫的，风从地板缝里吹上来。"
            "一支写不出声音的铅笔放在路中央，旁边却长着一张没有写完的纸。"
            "远处有人把雨声拧小，房间马上亮了一点；我回头时，你坐在灯下，把一张写好的纸折成很小的船。"
        )
        _seed_self_thought(
            root,
            focus_kind="dream_residue",
            intention="share_dream",
            question=long_dream,
            requested_action="owner_response_optional",
            evidence_label="shareable dream residue with reality boundary",
            evidence_hash="sha256:feedface12345679",
        )
        result = run_proactive_request_loop(root, evaluated_at="2026-05-01T13:06:00+08:00")
        state = _read(root / "memory/context/proactive_request_state.md")
        if result["status"] != "candidate_only" or result["kind"] != "dream_share":
            failures.append(f"long dream share should become candidate_only: {result}")
        if "你坐在灯下，把一张写好的纸折成很小的船" not in state:
            failures.append(f"long dream share was truncated in proactive request state: {state}")
        for bad_tail in ("把。", "像是在。", "没有。"):
            if bad_tail in state:
                failures.append(f"long dream share kept truncated tail {bad_tail}: {state}")

    with tempfile.TemporaryDirectory(prefix="xinyu-proreq-reflection-share-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        _seed_self_thought(
            root,
            focus_kind="reflection_queue",
            intention="share_reflection",
            question="那个 Codex 学习超时的事我还没当结束。我可以继续慢慢补，也可以先放后台；你想让我怎么处理？",
            requested_action="owner_response_optional",
            evidence_label="reflection queue strong topic: Codex 学习任务超时后不能关闭",
            evidence_hash="sha256:1234feed1234feed",
        )
        result = run_proactive_request_loop(root, evaluated_at="2026-05-01T13:10:00+08:00")
        state = _read(root / "memory/context/proactive_request_state.md")
        if result["status"] != "candidate_only" or result["kind"] != "reflection_share":
            failures.append(f"reflection share should become candidate_only: {result}")
        for marker in (
            "kind: reflection_share",
            "focus_kind: reflection_queue",
            "requested_action: owner_response_optional",
            "source_allowed: true",
            "memory_feedback_target: reflection_queue_then_owner_feedback_if_meaningful",
        ):
            if marker not in state:
                failures.append(f"reflection share request missing marker: {marker}")

    with tempfile.TemporaryDirectory(prefix="xinyu-proreq-reflection-dismissed-") as tmp:
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
        _seed_self_thought(
            root,
            focus_kind="reflection_queue",
            intention="share_reflection",
            question="我还在想这件事：说话和连续性问题。要不要我继续顺着它查原因？",
            requested_action="owner_response_optional",
            evidence_label="reflection queue strong topic: owner flagged shallow context and mechanical voice",
            evidence_hash="sha256:1234feed1234feed",
        )
        result = run_proactive_request_loop(root, evaluated_at="2026-05-02T13:10:00+08:00")
        state = _read(root / "memory/context/proactive_request_state.md")
        if result["status"] != "blocked":
            failures.append(f"dismissed reflection share should be blocked: {result}")
        for marker in ("owner_not_dismissed_reflection: false", "reflection_share_owner_dismissed"):
            if marker not in state and marker not in result["notes"]:
                failures.append(f"dismissed reflection request missing marker: {marker}")

    with tempfile.TemporaryDirectory(prefix="xinyu-proreq-action-sanitize-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        _seed_self_thought(
            root,
            focus_kind="reflection_queue",
            intention="share_reflection",
            question="我刚才还在压那段 log_scan:minecraft_server 的行动残留，要不要继续看？",
            requested_action="owner_response_optional",
            evidence_label="reflection queue strong topic: action residue after local action pressure after log_scan:minecraft_server",
            evidence_hash="sha256:beadfeed1234feed",
        )
        result = run_proactive_request_loop(root, evaluated_at="2026-05-01T13:12:00+08:00")
        state = _read(root / "memory/context/proactive_request_state.md")
        if result["status"] != "candidate_only" or result["kind"] != "reflection_share":
            failures.append(f"action residue request should become candidate_only: {result}")
        for marker in (
            "reflection queue strong topic",
            "action residue after",
            "local action pressure",
            "log_scan:",
        ):
            if marker in state:
                failures.append(f"proactive request state leaked action marker: {marker}")
        for marker in ("我后面想反复想的是", "那次动作留下的是", "minecraft_server 的日志扫过"):
            if marker not in state:
                failures.append(f"proactive request state missing sanitized marker: {marker}")

    with tempfile.TemporaryDirectory(prefix="xinyu-proreq-posture-") as tmp:
        root = Path(tmp)
        _seed_self_thought(root)
        _write(
            root / "memory/context/current_life_posture.md",
            "- no_proactive_constraint: block proactive while rest/silence boundary is active\n",
        )
        result = run_proactive_request_loop(root, evaluated_at="2026-05-01T13:30:00+08:00")
        state = _read(root / "memory/context/proactive_request_state.md")
        if result["status"] != "blocked":
            failures.append(f"life posture should block request: {result}")
        if "quiet_window_open: false" not in state:
            failures.append("quiet window gate was not recorded")

    with tempfile.TemporaryDirectory(prefix="xinyu-proreq-cooldown-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        _seed_self_thought(root)
        first = run_proactive_request_loop(
            root,
            evaluated_at="2026-05-01T14:00:00+08:00",
            cooldown_seconds=21600,
        )
        second = run_proactive_request_loop(
            root,
            evaluated_at="2026-05-01T14:10:00+08:00",
            cooldown_seconds=21600,
        )
        state = _read(root / "memory/context/proactive_request_state.md")
        if first["status"] != "candidate_only":
            failures.append(f"cooldown setup first request failed: {first}")
        if second["status"] != "blocked":
            failures.append(f"duplicate request should be blocked by cooldown: {second}")
        if "not_duplicate: false" not in state or "cooldown_open: false" not in state:
            failures.append("duplicate/cooldown gates were not recorded")

    with tempfile.TemporaryDirectory(prefix="xinyu-proreq-send-block-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        _seed_self_thought(root)
        result = run_proactive_request_loop(
            root,
            evaluated_at="2026-05-01T15:00:00+08:00",
            delivery_level="queue_owner_private",
        )
        state = _read(root / "memory/context/proactive_request_state.md")
        if result["status"] != "blocked":
            failures.append(f"send delivery should stay blocked without grant: {result}")
        if "grant_allows_send: false" not in state:
            failures.append("grant gate was not recorded for send delivery")
        _assert_no_dispatch(root, failures)

    with tempfile.TemporaryDirectory(prefix="xinyu-proreq-send-ready-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        _write(root / "memory/context/capability_zones_state.md", "- proactive_qq_send: enabled_gated_one_short_message\n")
        _seed_self_thought(root)
        result = run_proactive_request_loop(
            root,
            evaluated_at="2026-05-01T15:30:00+08:00",
            delivery_level="queue_owner_private",
        )
        state = _read(root / "memory/context/proactive_request_state.md")
        if result["status"] != "ready" or result["delivery_level"] != "queue_owner_private":
            failures.append(f"send delivery with grant should become ready: {result}")
        if "status: ready" not in state or "grant_allows_send: true" not in state:
            failures.append("ready send state did not record grant/status")
        _write(root / "memory/context/proactive_request_state.md", state.replace("- status: ready", "- status: sent", 1))
        preserved = run_proactive_request_loop(
            root,
            evaluated_at="2026-05-01T15:40:00+08:00",
            delivery_level="queue_owner_private",
        )
        if preserved["status"] != "sent" or "previous_live_request_preserved" not in preserved["notes"]:
            failures.append(f"sent proactive request should be preserved by loop: {preserved}")
        _assert_no_dispatch(root, failures)

    with tempfile.TemporaryDirectory(prefix="xinyu-proreq-path-") as tmp:
        root = Path(tmp)
        _seed_clear_posture(root)
        _seed_self_thought(
            root,
            question=r"Codex finished D:\XinYu\secret\report.md. Should I integrate it?",
            evidence_label=r"Codex report at D:\XinYu\secret\report.md",
        )
        result = run_proactive_request_loop(root, evaluated_at="2026-05-01T16:00:00+08:00")
        state = _read(root / "memory/context/proactive_request_state.md")
        trace = _read(root / "runtime/proactive_request_trace.jsonl")
        if result["status"] not in {"candidate_only", "blocked"}:
            failures.append(f"path scrub request returned unexpected status: {result}")
        if "D:\\XinYu" in state or "D:\\XinYu" in trace:
            failures.append("proactive request state leaked full local path")

    if failures:
        print("Proactive request loop smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Proactive request loop smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
