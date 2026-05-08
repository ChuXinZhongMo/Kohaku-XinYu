from __future__ import annotations

import json
import tempfile
from pathlib import Path

from xinyu_action_experience_digest import (
    compose_action_digest_followup,
    digest_action_experience_residue,
    read_recent_action_digest_context,
    read_recent_action_digest_snapshot,
)


def _write_action_residue(root: Path) -> str:
    exp_id = "exp-action-digest-smoke"
    path = root / "runtime/life_kernel/action_experience_residue.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "experience_id": exp_id,
        "created_at": "2026-05-06T04:40:00+08:00",
        "tool": "log_scan",
        "target_alias": "minecraft_server",
        "result": "success",
        "pressure": {"score": 0.68, "band": "high", "reasons": ["owner_requested_action", "error_lines"]},
        "salience": 0.81,
        "memory_candidates": [
            "owner asked XinYu to inspect registered logs: minecraft_server",
            "initial diagnosis: Java memory overflow, check JVM heap and mod leak pressure",
        ],
        "outcome_summary": [
            "found 6 error/warn/timeout keywords across 1 file",
            "latest fragment: java.lang.OutOfMemoryError: Java heap space",
        ],
        "notes": ["dream_reflection_residue_candidate", "stdout_stderr_not_included"],
    }
    path.write_text(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return exp_id


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace") if path.exists() else ""


def main() -> int:
    failures: list[str] = []
    scratch = Path(__file__).resolve().parent / "runtime/action_experience_digest_smoke_tmp"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="xinyu-action-digest-", dir=str(scratch)) as tmp:
        root = Path(tmp)
        exp_id = _write_action_residue(root)

        result = digest_action_experience_residue(
            root,
            produced_at="2026-05-06T04:45:00+08:00",
            salience_threshold=0.6,
        )
        if result.get("digested_count") != 1:
            failures.append(f"expected one digested item, got {result.get('digested_count')}")
        seed_ids = result.get("dream_seed_ids")
        if not isinstance(seed_ids, list) or not seed_ids:
            failures.append("digest should create a dream seed id")
        reflection_ids = result.get("reflection_item_ids")
        if not isinstance(reflection_ids, list) or not reflection_ids:
            failures.append("high pressure residue should create a reflection queue item")

        dream_seeds = _read(root / "memory/dreams/dream_seeds.md")
        forbidden = ("local action pressure", "log_scan:", "action residue after", "ended as", "pressure=high")
        if exp_id not in dream_seeds or "minecraft_server 日志扫描" not in dream_seeds:
            failures.append("dream seed should include action experience source and visible theme")
        if any(marker in dream_seeds for marker in forbidden):
            failures.append("dream seed should not leak internal action markers")
        if "dream_permission: can_recombine_but_not_rewrite_fact" not in dream_seeds:
            failures.append("dream seed should keep fact rewrite boundary")

        reflection_queue = _read(root / "memory/reflection/reflection_queue.md")
        if exp_id not in reflection_queue or "行动残留来自 minecraft_server 日志扫描" not in reflection_queue:
            failures.append("reflection queue should include action experience source and visible topic")
        if any(marker in reflection_queue for marker in forbidden):
            failures.append("reflection queue should not leak internal action markers")
        if "do not invent facts" not in reflection_queue:
            failures.append("reflection queue should keep boundary")

        state = json.loads(_read(root / "runtime/life_kernel/action_experience_digest_state.json"))
        if exp_id not in state.get("digested_ids", []):
            failures.append("digest state should remember consumed experience id")

        snapshot = read_recent_action_digest_snapshot(root)
        if int(snapshot.get("digested_count") or 0) != 1:
            failures.append("digest snapshot should expose digested count")
        context = read_recent_action_digest_context(root)
        if "recent action digestion sidecar" not in context or "minecraft_server" not in context:
            failures.append("digest context should expose recent action digestion sidecar")
        followup = compose_action_digest_followup(root, "刚才有进入梦和反思吗？", max_age_seconds=7 * 24 * 3600)
        followup_reply = str((followup or {}).get("reply", ""))
        if not followup_reply or "梦种" not in followup_reply or "反思队列" not in followup_reply:
            failures.append("digest followup should answer dream/reflection routing")
        residue_followup = compose_action_digest_followup(root, "刚才那次留下了什么残留？", max_age_seconds=7 * 24 * 3600)
        residue_reply = str((residue_followup or {}).get("reply", ""))
        if "Java memory overflow" not in residue_reply and "memory overflow" not in residue_reply:
            failures.append("digest residue followup should answer from seed residue")

        second = digest_action_experience_residue(
            root,
            produced_at="2026-05-06T04:46:00+08:00",
            salience_threshold=0.6,
        )
        if second.get("digested_count") != 0:
            failures.append("second digest should not reprocess the same experience")

        dream_seeds_after = _read(root / "memory/dreams/dream_seeds.md")
        if dream_seeds_after.count(exp_id) != 1:
            failures.append("dream seed should not be duplicated")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS xinyu_action_experience_digest_smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
