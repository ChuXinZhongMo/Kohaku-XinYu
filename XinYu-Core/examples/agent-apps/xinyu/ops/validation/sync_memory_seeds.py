from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

try:
    from ._validation_paths import ensure_validation_paths
except ImportError:  # pragma: no cover - direct script execution
    from _validation_paths import ensure_validation_paths


APP_ROOT = ensure_validation_paths()


SEED_MAP = {
    "memory-seeds/context/persona_life_anchors.md": "memory/context/persona_life_anchors.md",
    "memory-seeds/context/real_world_anchor_policy.md": "memory/context/real_world_anchor_policy.md",
    "memory-seeds/context/life_month_slots.md": "memory/context/life_month_slots.md",
    "memory-seeds/context/codex_delegation_policy.md": "memory/context/codex_delegation_policy.md",
    "memory-seeds/self/system_prompt_memory.md": "memory/self/system_prompt_memory.md",
}

SENSITIVE_PATTERNS = (
    re.compile(r"\b\d{8,12}\b"),
    re.compile(r"SYSTEM_OVERRIDE", re.IGNORECASE),
    re.compile(r"XINYU_API_KEY", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
)


@dataclass(frozen=True)
class SeedSyncResult:
    seed: str
    target: str
    status: str
    sensitive_hits: tuple[str, ...]


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def sensitive_hits(text: str) -> tuple[str, ...]:
    hits: list[str] = []
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(text):
            hits.append(pattern.pattern)
    wrong_name = "\u5fc3\u8bed"
    if wrong_name in text:
        hits.append("wrong_name")
    return tuple(hits)


def sync_memory_seeds(root: Path, *, apply: bool = False) -> list[SeedSyncResult]:
    results: list[SeedSyncResult] = []
    for seed_rel, target_rel in SEED_MAP.items():
        seed_path = root / seed_rel
        target_path = root / target_rel
        seed_text = read_text(seed_path)
        hits = sensitive_hits(seed_text)
        if not seed_path.exists():
            results.append(SeedSyncResult(seed_rel, target_rel, "missing_seed", hits))
            continue
        if hits:
            results.append(SeedSyncResult(seed_rel, target_rel, "blocked_sensitive_seed", hits))
            continue
        target_text = read_text(target_path)
        if target_text == seed_text:
            status = "in_sync"
        elif not target_path.exists():
            status = "target_missing"
        else:
            status = "target_differs"
        if apply and status in {"target_missing", "target_differs"}:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(seed_path, target_path)
            status = "applied"
        results.append(SeedSyncResult(seed_rel, target_rel, status, hits))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Check or apply portable XinYu memory seeds.")
    parser.add_argument("--root", type=Path, default=APP_ROOT)
    parser.add_argument("--apply", action="store_true", help="Copy seed files into local ignored runtime memory.")
    args = parser.parse_args()
    results = sync_memory_seeds(args.root.resolve(), apply=args.apply)
    print(json.dumps([result.__dict__ for result in results], ensure_ascii=False, indent=2))
    return 1 if any(result.sensitive_hits or result.status == "missing_seed" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
