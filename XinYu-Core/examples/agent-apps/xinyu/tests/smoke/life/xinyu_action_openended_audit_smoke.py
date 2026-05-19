from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import hashlib
import json
import tempfile
from pathlib import Path

from xinyu_action_openended_audit import run_audit


TRACKED_RELS = (
    "runtime/life_kernel/recent_action_experience.jsonl",
    "runtime/life_kernel/action_experience_residue.jsonl",
    "memory/dreams/dream_seeds.md",
    "memory/reflection/reflection_queue.md",
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_fixture(root: Path) -> None:
    recent_rows = [
        {
            "experience_id": "exp-low-leak",
            "created_at": "2026-05-06T10:00:00+08:00",
            "tool": "status_probe",
            "target_alias": "",
            "result": "success",
            "pressure": {"score": 0.1, "band": "low"},
            "salience": 0.22,
            "summary": ["重复可见短语应该被审查"],
            "memory_candidates": ["owner asked XinYu to inspect local runtime status"],
        },
        {
            "experience_id": "exp-log-1",
            "created_at": "2026-05-06T10:01:00+08:00",
            "tool": "log_scan",
            "target_alias": "xinyu_logs",
            "result": "success",
            "pressure": {"score": 0.36, "band": "medium"},
            "salience": 0.61,
            "diagnosis": {"kind": "timeout", "summary": "重复可见短语应该被审查"},
            "summary": ["重复可见短语应该被审查"],
        },
        {
            "experience_id": "exp-log-2",
            "created_at": "2026-05-06T10:02:00+08:00",
            "tool": "log_scan",
            "target_alias": "xinyu_logs",
            "result": "success",
            "pressure": {"score": 0.36, "band": "medium"},
            "salience": 0.61,
            "diagnosis": {"kind": "timeout", "summary": "重复可见短语应该被审查"},
            "summary": ["重复可见短语应该被审查"],
        },
        {
            "experience_id": "exp-log-3",
            "created_at": "2026-05-06T10:03:00+08:00",
            "tool": "log_scan",
            "target_alias": "xinyu_logs",
            "result": "success",
            "pressure": {"score": 0.36, "band": "medium"},
            "salience": 0.61,
            "diagnosis": {"kind": "timeout", "summary": "重复可见短语应该被审查"},
            "summary": ["重复可见短语应该被审查"],
        },
        {
            "experience_id": "exp-log-4",
            "created_at": "2026-05-06T10:04:00+08:00",
            "tool": "log_scan",
            "target_alias": "xinyu_logs",
            "result": "success",
            "pressure": {"score": 0.36, "band": "medium"},
            "salience": 0.61,
            "diagnosis": {"kind": "timeout", "summary": "重复可见短语应该被审查"},
            "summary": ["重复可见短语应该被审查"],
        },
    ]
    residue_rows = [
        {
            "experience_id": "exp-low-leak",
            "created_at": "2026-05-06T10:05:00+08:00",
            "tool": "status_probe",
            "target_alias": "",
            "result": "success",
            "pressure": {"score": 0.1, "band": "low"},
            "salience": 0.22,
            "memory_candidates": ["重复可见短语应该被审查"],
            "outcome_summary": ["普通低显著性状态检查不应进入代谢层"],
        },
        {
            "experience_id": "exp-high",
            "created_at": "2026-05-06T10:06:00+08:00",
            "tool": "codex_delegate",
            "target_alias": "",
            "result": "failure",
            "pressure": {"score": 0.72, "band": "high"},
            "salience": 0.84,
            "memory_candidates": ["Codex failure left bounded action residue"],
            "outcome_summary": ["Codex failure left bounded action residue"],
        },
    ]
    _write_jsonl(root / "runtime/life_kernel/recent_action_experience.jsonl", recent_rows)
    _write_jsonl(root / "runtime/life_kernel/action_experience_residue.jsonl", residue_rows)
    (root / "memory/dreams").mkdir(parents=True, exist_ok=True)
    (root / "memory/dreams/dream_seeds.md").write_text(
        """# Dream Seeds

## seed-action-low
- source_event: action_experience / exp-low-leak
- theme: 低显著性状态检查
- residue: 普通低显著性状态检查不应进入代谢层
- factual_status: bounded local action residue

## seed-action-high-a
- source_event: action_experience / exp-high
- theme: Codex 委派的行动残留
- residue: Codex failure left bounded action residue
- factual_status: bounded local action residue

## seed-action-high-b
- source_event: action_experience / exp-high
- theme: Codex 委派的行动残留
- residue: Codex failure left bounded action residue
- factual_status: bounded local action residue
""",
        encoding="utf-8",
    )
    (root / "memory/reflection").mkdir(parents=True, exist_ok=True)
    (root / "memory/reflection/reflection_queue.md").write_text(
        """# Reflection Queue

## item-low
- topic: 行动残留来自低显著性状态检查
- source: action_experience_residue / exp-low-leak
- priority: high
- waking_residue: 普通低显著性状态检查不应进入代谢层

## item-high-a
- topic: 行动残留来自Codex 委派的行动残留
- source: action_experience_residue / exp-high
- priority: high
- waking_residue: Codex failure left bounded action residue

## item-high-b
- topic: 行动残留来自Codex 委派的行动残留
- source: action_experience_residue / exp-high
- priority: high
- waking_residue: Codex failure left bounded action residue
""",
        encoding="utf-8",
    )


def _snapshot(root: Path) -> tuple[dict[str, str], set[str]]:
    hashes: dict[str, str] = {}
    for rel in TRACKED_RELS:
        data = (root / rel).read_bytes()
        hashes[rel] = hashlib.sha256(data).hexdigest()
    files = {str(path.relative_to(root)).replace("\\", "/") for path in root.rglob("*") if path.is_file()}
    return hashes, files


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-action-audit-") as tmp:
        root = Path(tmp)
        _write_fixture(root)
        before_hashes, before_files = _snapshot(root)
        result = run_audit(root)
        after_hashes, after_files = _snapshot(root)

        if before_hashes != after_hashes:
            failures.append("audit should not modify tracked input files")
        if before_files != after_files:
            failures.append("audit should not create or delete files")
        if result.get("recent_action_count") != 5:
            failures.append("audit should count recent action rows")
        if result.get("residue_count") != 2:
            failures.append("audit should count action residue rows")
        if result.get("dream_seed_from_action_count") != 3:
            failures.append("audit should count action-origin dream seeds")
        if result.get("reflection_from_action_count") != 3:
            failures.append("audit should count action-origin reflection items")
        if int(result.get("low_salience_leaked_count") or 0) <= 0:
            failures.append("audit should detect low salience leakage")
        if "recommended_next_safe_challenge_candidates" in result:
            failures.append("audit v1 must not emit next safe challenge candidates")

        warnings = "\n".join(str(item) for item in result.get("warnings", []))
        for marker in (
            "low_salience_leak",
            "over_dreamized_action_residue",
            "over_reflectionized_action_residue",
            "repeated_action_theme",
            "repeated_visible_phrase",
        ):
            if marker not in warnings:
                failures.append(f"audit should warn about {marker}")
        if result.get("health_status") != "unhealthy":
            failures.append("audit should mark the fixture unhealthy")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS xinyu_action_openended_audit_smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
