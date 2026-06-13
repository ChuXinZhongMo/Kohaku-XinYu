from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from xinyu_visible_state_hygiene_store import iter_visible_state_candidate_rels
from xinyu_visible_state_hygiene_store import read_visible_state_text
from xinyu_visible_state_hygiene_store import write_visible_state_text
from xinyu_visible_text_sanitizer import sanitize_visible_text


DEFAULT_RELATIVE_FILES = (
    "memory/context/proactive_request_state.md",
    "memory/context/proactive_presence_state.md",
    "memory/context/proactive_qq_dispatch_state.md",
    "memory/context/self_thought_state.md",
    "memory/context/thought_seeds.md",
    "memory/context/continuity_index.md",
    "memory/emotions/current_state.md",
    "memory/dreams/dream_seeds.md",
    "memory/dreams/dream_log.md",
    "memory/dreams/dream_output_trace.log",
    "memory/dreams/dream_output_state.md",
    "memory/dreams/dream_weight_state.md",
    "memory/reflection/reflection_queue.md",
    "memory/reflection/reflection_log.md",
    "memory/reflection/reflection_output_trace.log",
    "memory/reflection/reflection_output_state.md",
    "runtime/gateway_ack_spool.jsonl",
    "runtime/sent_reply_index.json",
)

DEFAULT_RELATIVE_GLOBS = (
    "runtime/dialogue_working_memory/*.jsonl",
)

FORBIDDEN_VISIBLE_MARKERS = (
    "local action pressure",
    "codex_delegate:none",
    "codex_delegate:",
    "status_probe",
    "log_scan:",
    "reflection queue strong topic",
    "action residue after",
    "ended as failure",
    "ended as success",
    "ended as timeout",
    "pressure=low",
    "pressure=medium",
    "pressure=high",
    "[Tool batch completed]",
    "Tool batch completed",
    "## read_",
    "## read",
    "OK 1→",
    "OK 1->",
)


def _read_text(path: Path) -> str:
    return read_visible_state_text(path)


def _write_text_atomic(path: Path, text: str) -> None:
    write_visible_state_text(path, text)


def sanitize_visible_state_files(
    root: Path,
    *,
    relative_files: tuple[str, ...] = DEFAULT_RELATIVE_FILES,
    relative_globs: tuple[str, ...] = DEFAULT_RELATIVE_GLOBS,
    dry_run: bool = False,
) -> dict[str, Any]:
    changed: list[str] = []
    scanned = 0
    for rel in iter_visible_state_candidate_rels(
        root,
        relative_files=relative_files,
        relative_globs=relative_globs,
    ):
        path = root / rel
        original = _read_text(path)
        if not original:
            continue
        scanned += 1
        sanitized = sanitize_visible_text(original)
        sanitized = _repair_markdown_layout(rel, sanitized)
        if sanitized == original:
            continue
        changed.append(rel)
        if not dry_run:
            _write_text_atomic(path, sanitized)
    return {
        "scanned": scanned,
        "changed": changed,
        "changed_count": len(changed),
        "dry_run": dry_run,
        "notes": ["visible_state_hygiene_v1"],
    }


def visible_state_marker_hits(
    root: Path,
    *,
    relative_files: tuple[str, ...] = DEFAULT_RELATIVE_FILES,
    relative_globs: tuple[str, ...] = DEFAULT_RELATIVE_GLOBS,
) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for rel in iter_visible_state_candidate_rels(
        root,
        relative_files=relative_files,
        relative_globs=relative_globs,
    ):
        text = _read_text(root / rel)
        if not text:
            continue
        file_hits = [marker for marker in FORBIDDEN_VISIBLE_MARKERS if marker in text]
        if file_hits:
            hits[rel] = file_hits
    return hits


def _repair_markdown_layout(rel: str, text: str) -> str:
    if not rel.endswith(".md"):
        return text
    repaired = text
    repaired = re.sub(r"(?m)^---\s+#", "---\n\n#", repaired)
    repaired = re.sub(r"\s+(#{1,3})\s+", r"\n\n\1 ", repaired)
    repaired = re.sub(r"(?m)([^\n])(\s+-\s+[A-Za-z0-9_]+:\s*)", r"\1\n\2", repaired)
    repaired = re.sub(r"\n{3,}", "\n\n", repaired)
    return repaired


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sanitize internal action markers from visible XinYu state sidecars.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent))
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    root = Path(args.root)
    result = sanitize_visible_state_files(root, dry_run=bool(args.dry_run))
    hits = visible_state_marker_hits(root)
    print(f"visible_state_hygiene changed={result['changed_count']} scanned={result['scanned']}")
    for rel in result["changed"]:
        print(f"- changed: {rel}")
    if hits:
        print("remaining marker hits:")
        for rel, markers in hits.items():
            print(f"- {rel}: {', '.join(markers)}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
