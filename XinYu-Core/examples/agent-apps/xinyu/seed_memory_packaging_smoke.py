from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from sync_memory_seeds import SEED_MAP, sensitive_hits, sync_memory_seeds


EXPECTED_SEEDS = {
    "examples/agent-apps/xinyu/memory-seeds/context/persona_life_anchors.md": (
        "# Background Texture Seed",
        "Stable name: 心玉 / XinYu",
        "low-frequency background texture",
        "should not appear as repeated visible motifs",
        "Let repeated owner interaction",
    ),
    "examples/agent-apps/xinyu/memory-seeds/context/real_world_anchor_policy.md": (
        "# 现实锚点原则",
        "现实大事件只能作为 `world_anchor`",
        "不能自动变成亲身经历",
        "精确隐私地址",
        "`life_month_slots.md` 可以使用现实锚点",
    ),
    "examples/agent-apps/xinyu/memory-seeds/context/life_month_slots.md": (
        "# Life Month Slots",
        "slot_count: 192",
        "Empty months are valid memory nodes",
        "World anchors are not personal memories",
        "Do not invent one important memory per month",
    ),
    "examples/agent-apps/xinyu/memory-seeds/context/codex_delegation_policy.md": (
        "# Codex Delegation Policy",
        "direct_qq_to_codex_execution",
        "explicit local/API request",
        "Timeout is not treated as closing the task",
    ),
    "examples/agent-apps/xinyu/memory-seeds/self/system_prompt_memory.md": (
        "# System Prompt Memory",
        "should no longer act as a hard personality constitution",
        "keep only the XinYu concept",
        "Prompt material is a seed, not law",
        "less machinery at the surface",
    ),
}


def _check_not_ignored(repo_root: Path, seed_rel: str, failures: list[str]) -> None:
    try:
        check = subprocess.run(
            ["git", "check-ignore", "-q", seed_rel],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if check.returncode == 0:
            failures.append(f"memory seed is unexpectedly ignored by git: {seed_rel}")
        elif check.returncode not in {1}:
            failures.append(f"git check-ignore returned unexpected code for {seed_rel}: {check.returncode}")
    except Exception as exc:
        failures.append(f"git check-ignore could not run for {seed_rel}: {type(exc).__name__}: {exc}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    root = Path(__file__).resolve().parent
    repo_root = root.parents[2]
    failures: list[str] = []

    expected_local = {
        rel.removeprefix("examples/agent-apps/xinyu/"): markers for rel, markers in EXPECTED_SEEDS.items()
    }
    if set(SEED_MAP) != set(expected_local):
        failures.append(f"SEED_MAP mismatch: {sorted(SEED_MAP)} != {sorted(expected_local)}")

    for seed_rel, markers in EXPECTED_SEEDS.items():
        seed_path = repo_root / seed_rel
        seed_text = seed_path.read_text(encoding="utf-8-sig", errors="replace") if seed_path.exists() else ""
        if not seed_path.exists():
            failures.append(f"seed is missing: {seed_rel}")
            continue
        for marker in markers:
            if marker not in seed_text:
                failures.append(f"{seed_rel} missing marker: {marker}")
        hits = sensitive_hits(seed_text)
        if hits:
            failures.append(f"{seed_rel} contains sensitive or wrong-name pattern: {', '.join(hits)}")
        _check_not_ignored(repo_root, seed_rel, failures)

    results = sync_memory_seeds(root, apply=False)
    if len(results) != len(SEED_MAP):
        failures.append(f"sync_memory_seeds returned {len(results)} results for {len(SEED_MAP)} seeds")
    for result in results:
        if result.status in {"missing_seed", "blocked_sensitive_seed"}:
            failures.append(f"bad seed sync status: {result}")
        if result.sensitive_hits:
            failures.append(f"seed sync sensitive hits: {result.sensitive_hits}")

    if failures:
        print("Seed memory packaging smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Seed memory packaging smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
