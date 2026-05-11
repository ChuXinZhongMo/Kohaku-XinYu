from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from xinyu_emotion_council import (
    LENS_MEMORY_DIR_REL,
    RESIDUE_REL,
    STATE_REL,
    TRACE_REL,
    build_emotion_council_prompt_block,
    run_emotion_council_shadow,
)


CHECKED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
OWNER_PAYLOAD = {"message_type": "private_text", "user_id": "42", "metadata": {"is_owner_user": True}}


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _read_json(path: Path) -> dict:
    return json.loads(_read(path))


def _seed_context(root: Path) -> None:
    for lens in ("attachment", "guardedness", "curiosity", "hurt", "irritation", "stability", "fatigue"):
        _write(
            root / LENS_MEMORY_DIR_REL / f"{lens}.md",
            f"""# {lens} lens memory
- lens_memory_seed: {lens}
- boundary: private bias only
""",
        )
    _write(
        root / "memory/emotions/current_state.md",
        """# Current Emotion

## 当前细分情绪向量
| 情绪 | 强度 | 说明 |
|------|------|------|
| 平静 | 0.55 | 稳定 |
| 想靠近 | 0.15 | 微弱 |
""",
    )
    _write(
        root / "memory/context/self_thought_state.md",
        """# Self Thought State

## Latest Pass
- status: held
- outcome: queue_reflection
- focus_kind: reflection_queue
""",
    )
    _write(
        root / "memory/context/proactive_request_state.md",
        """# Proactive Request State

## Current Request
- status: answered
- kind: reflection_share

## Last Owner Reply To Proactive
- owner_reply_preview: 你这个一直惦记有点问题啊
""",
    )
    _write(
        root / "memory/context/impulse_soup_state.md",
        """# Impulse Soup State

## Summary
- top_desire_shape: dream_residue_compression
""",
    )


def _assert_no_forbidden_side_effects(root: Path, failures: list[str], stable_before: str) -> None:
    if (root / "memory/context/qq_outbox_queue.json").exists():
        failures.append("emotion council created QQ outbox")
    stable = root / "memory/self/core.md"
    if stable.exists() and _read(stable) != stable_before:
        failures.append("emotion council modified stable self memory")


def main() -> int:
    failures: list[str] = []

    with tempfile.TemporaryDirectory(prefix="xinyu-emotion-council-dismissal-") as tmp:
        root = Path(tmp)
        _seed_context(root)
        _write(root / "memory/self/core.md", "stable self")
        stable_before = _read(root / "memory/self/core.md")
        result = run_emotion_council_shadow(
            root,
            text="你这个一直惦记有点问题啊，别再提了",
            payload=OWNER_PAYLOAD,
            checked_at=CHECKED_AT,
            trigger="live_turn",
        )
        state = _read(root / STATE_REL)
        trace = _read(root / TRACE_REL)
        if result["status"] != "active" or result["strongest_lens"] != "guardedness":
            failures.append(f"dismissal should activate guardedness: {result}")
        for marker in (
            "do_not_repeat",
            "no_proactive_followup",
            "short_concrete_no_repeat_no_question",
            "no_visible_reply: true",
            "no_qq_enqueue: true",
            "no_tool_execution: true",
            "no_stable_memory_write: true",
            "lens_model_no_tools: true",
            "lens_model_json_only: true",
            "Lens Memory Banks",
            "lens=guardedness status=loaded",
            "memory/emotions/lenses/guardedness.md",
            "Parallel Lens Reviews",
            "Short Term Residue",
        ):
            if marker not in state:
                failures.append(f"dismissal state missing marker: {marker}")
        if "emotion_council_shadow" not in trace:
            failures.append("emotion council trace was not written")
        residue = _read_json(root / RESIDUE_REL)
        if residue.get("strongest_residue") != "guardedness" or residue.get("active_residue_count", 0) < 1:
            failures.append(f"residue cache did not retain guardedness: {residue}")
        if not residue.get("boundaries", {}).get("no_stable_memory_write"):
            failures.append(f"residue cache missing stable memory boundary: {residue}")
        block = build_emotion_council_prompt_block(root)
        if "private_observation_only" not in block or "do not repeat" not in block or "short_term_residue_cache" not in block:
            failures.append(f"prompt block did not summarize guardedness safely: {block}")
        _assert_no_forbidden_side_effects(root, failures, stable_before)

    with tempfile.TemporaryDirectory(prefix="xinyu-emotion-council-idea-") as tmp:
        root = Path(tmp)
        _seed_context(root)
        result = run_emotion_council_shadow(
            root,
            text="我有一个新的idea，你看看适不适配我们现有的框架，之后做一个plan",
            payload=OWNER_PAYLOAD,
            checked_at=CHECKED_AT,
            trigger="live_turn",
        )
        state = _read(root / STATE_REL)
        if result["status"] != "active":
            failures.append(f"idea turn should activate council: {result}")
        if "curiosity" not in state or "stability" not in state:
            failures.append(f"idea turn should activate curiosity and stability: {state}")
        if "explore" not in result["consensus"] and "stable" not in result["output_bias"]:
            failures.append(f"idea consensus should stay exploratory/stable: {result}")

    with tempfile.TemporaryDirectory(prefix="xinyu-emotion-council-parallel-") as tmp:
        root = Path(tmp)
        _seed_context(root)
        calls: list[str] = []
        memory_seen: dict[str, tuple[str, str]] = {}

        def fake_runner(config, context):
            calls.append(config.name)
            memory_seen[config.name] = (
                str(context.get("lens_memory_path", "")),
                str(context.get("lens_memory", "")),
            )
            if config.name == "hurt":
                raise RuntimeError("simulated lens failure")
            if config.name == "curiosity":
                return {
                    "activation_delta": 0.18,
                    "confidence": 0.9,
                    "suggested_bias": "use a small architecture experiment",
                    "risk_flags": ["json_only_checked"],
                    "note": context["lens"],
                }
            return json.dumps(
                {
                    "activation_delta": 0.02,
                    "confidence": 0.6,
                    "suggested_bias": "",
                    "risk_flags": ["no_tool"],
                    "note": config.name,
                },
                ensure_ascii=False,
            )

        result = run_emotion_council_shadow(
            root,
            text="我有一个新idea，看看怎么接入框架，然后做计划",
            payload=OWNER_PAYLOAD,
            checked_at=CHECKED_AT,
            trigger="live_turn",
            parallel_model=True,
            lens_runner=fake_runner,
        )
        state = _read(root / STATE_REL)
        trace_rows = [json.loads(line) for line in _read(root / TRACE_REL).splitlines() if line.strip()]
        latest = trace_rows[-1]
        parallel = latest.get("parallel_model", {})
        if len(calls) != 7:
            failures.append(f"parallel model should call all seven lenses: {calls}")
        curiosity_path, curiosity_memory = memory_seen.get("curiosity", ("", ""))
        if "memory/emotions/lenses/curiosity.md" not in curiosity_path or "lens_memory_seed: curiosity" not in curiosity_memory:
            failures.append(f"curiosity lens did not receive its memory bank: {memory_seen.get('curiosity')}")
        if parallel.get("status") != "partial" or parallel.get("ok_count") != 6 or parallel.get("error_count") != 1:
            failures.append(f"parallel model should isolate one lens failure: {parallel}")
        if "parallel_model:partial" not in result["notes"]:
            failures.append(f"parallel model note missing from result: {result}")
        if "json_only_checked" not in state or "Parallel Lens Reviews" not in state:
            failures.append(f"parallel model review was not reflected in state: {state}")

    with tempfile.TemporaryDirectory(prefix="xinyu-emotion-council-residue-") as tmp:
        root = Path(tmp)
        now = datetime.now().astimezone()
        run_emotion_council_shadow(
            root,
            text="你这个一直惦记有点问题啊，别再提了",
            payload=OWNER_PAYLOAD,
            checked_at=now.isoformat(timespec="seconds"),
            trigger="live_turn",
        )
        quiet = run_emotion_council_shadow(
            root,
            text="今天晚饭吃什么",
            payload=OWNER_PAYLOAD,
            checked_at=(now + timedelta(minutes=30)).isoformat(timespec="seconds"),
            trigger="live_turn",
        )
        block = build_emotion_council_prompt_block(root)
        residue = _read_json(root / RESIDUE_REL)
        if quiet["status"] != "quiet":
            failures.append(f"residue follow-up should leave current turn quiet: {quiet}")
        if "short_term_residue_cache" not in block or "guardedness" not in block:
            failures.append(f"residue prompt block did not survive quiet turn: {block}")
        if residue.get("active_residue_count", 0) < 1:
            failures.append(f"residue cache was not retained across quiet turn: {residue}")

    with tempfile.TemporaryDirectory(prefix="xinyu-emotion-council-ordinary-") as tmp:
        root = Path(tmp)
        _write(root / "memory/self/core.md", "stable self")
        stable_before = _read(root / "memory/self/core.md")
        result = run_emotion_council_shadow(
            root,
            text="今天晚饭吃什么",
            payload=OWNER_PAYLOAD,
            checked_at=CHECKED_AT,
            trigger="live_turn",
        )
        if result["status"] != "quiet" or result["strongest_lens"] != "none":
            failures.append(f"ordinary fact-ish chat should stay quiet: {result}")
        _assert_no_forbidden_side_effects(root, failures, stable_before)

    with tempfile.TemporaryDirectory(prefix="xinyu-emotion-council-non-owner-") as tmp:
        root = Path(tmp)
        result = run_emotion_council_shadow(
            root,
            text="这个框架怎么样",
            payload={"message_type": "group_text", "metadata": {"is_owner_user": False}},
            checked_at=CHECKED_AT,
            trigger="live_turn",
        )
        if result["status"] != "not_applicable":
            failures.append(f"non-owner live turn should not apply emotion council: {result}")

    if failures:
        print("Emotion council smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Emotion council smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
