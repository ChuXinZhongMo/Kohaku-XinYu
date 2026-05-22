from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_dialogue_archive import list_memory_candidates


PROMOTION_DRY_RUN_REL = Path("runtime/memory_promotion_dry_runs")
PROMOTION_ELIGIBLE_STATUSES = ("approved",)
REVIEWABLE_STATUSES = (
    "approved",
    "owner_review_required",
    "self_approved_recent_context",
    "self_approved_voice_review",
)
SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bauthorization\s*:\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bapi[_-]?key\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\btoken\s*[:=]\s*[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bpassword\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bprivate[_ -]?key\b"),
    re.compile(r"(?i)\bcookie\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bsession[_ -]?(?:key|token|cookie)\b"),
    re.compile(r"(?i)\bsk-[a-z0-9_-]{12,}"),
)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        text = str(value)
    except Exception:
        return default
    return text if text else default


def _one_line(value: Any, *, limit: int = 240, default: str = "none") -> str:
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    if not text:
        return default
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("<secret>", text)
    return text if len(text) <= limit else text[: max(0, limit - 3)].rstrip() + "..."


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _candidate_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for status in REVIEWABLE_STATUSES:
        for row in list_memory_candidates(root, status=status, limit=500):
            candidate_id = _safe_str(row.get("candidate_id")).strip()
            if not candidate_id or candidate_id in seen:
                continue
            seen.add(candidate_id)
            rows.append(row)
    return rows


def get_promotion_candidate(root: Path, candidate_id: str) -> dict[str, Any] | None:
    clean_id = _safe_str(candidate_id).strip()
    for row in _candidate_rows(root):
        if row.get("candidate_id") == clean_id:
            return row
    return None


def build_stable_memory_promotion_dry_run(
    root: Path,
    candidate_id: str,
    *,
    allow_unapproved: bool = False,
    write_preview: bool = False,
    generated_at: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    row = get_promotion_candidate(root, candidate_id)
    if row is None:
        return {"ok": False, "error": "candidate_not_found", "candidate_id": candidate_id}
    generated = generated_at or _now_iso()
    blockers = _promotion_blockers(row, allow_unapproved=allow_unapproved)
    target_rel = _target_rel(row)
    target_path = root / target_rel if target_rel else root
    before = _read_text(target_path) if target_rel else ""
    proposed_entry = _render_proposed_entry(row, generated_at=generated)
    after = _append_entry(before, proposed_entry)
    diff = "\n".join(
        difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile=f"a/{target_rel.as_posix() if target_rel else 'invalid-target'}",
            tofile=f"b/{target_rel.as_posix() if target_rel else 'invalid-target'}",
            lineterm="",
        )
    )
    result = {
        "ok": True,
        "candidate_id": row.get("candidate_id"),
        "status": row.get("status"),
        "candidate_type": row.get("candidate_type"),
        "target_memory_layer": row.get("target_memory_layer"),
        "target_path": str(target_path),
        "target_exists": target_path.exists() if target_rel else False,
        "before_hash": _text_hash(before),
        "after_hash": _text_hash(after),
        "stable_memory_write": "dry_run_only",
        "apply_allowed": False,
        "blockers": blockers,
        "proposed_entry": proposed_entry,
        "diff": diff,
        "generated_at": generated,
        "notes": ["promotion_preview_only", "no_files_modified"],
    }
    if write_preview:
        preview_path = write_promotion_dry_run(root, result)
        result["preview_path"] = str(preview_path)
    return result


def write_promotion_dry_run(root: Path, result: dict[str, Any]) -> Path:
    candidate_id = _safe_filename(result.get("candidate_id"), default="unknown")
    path = root / PROMOTION_DRY_RUN_REL / f"{candidate_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_promotion_dry_run(result), encoding="utf-8")
    return path


def render_promotion_dry_run(result: dict[str, Any]) -> str:
    blockers = result.get("blockers") if isinstance(result.get("blockers"), list) else []
    blocker_lines = "\n".join(f"- {_one_line(item, limit=180)}" for item in blockers) or "- none"
    return f"""# Memory Promotion Dry Run

- generated_at: {_one_line(result.get('generated_at'))}
- candidate_id: {_one_line(result.get('candidate_id'), limit=120)}
- status: {_one_line(result.get('status'))}
- candidate_type: {_one_line(result.get('candidate_type'))}
- target_memory_layer: {_one_line(result.get('target_memory_layer'), limit=180)}
- target_path: {_one_line(result.get('target_path'), limit=240)}
- stable_memory_write: dry_run_only
- apply_allowed: false
- before_hash: {_one_line(result.get('before_hash'), limit=80)}
- after_hash: {_one_line(result.get('after_hash'), limit=80)}

## Blockers
{blocker_lines}

## Proposed Entry
```markdown
{_safe_str(result.get('proposed_entry')).rstrip()}
```

## Diff
```diff
{_safe_str(result.get('diff')).rstrip()}
```
""".rstrip() + "\n"


def _promotion_blockers(row: dict[str, Any], *, allow_unapproved: bool) -> list[str]:
    blockers = ["stable_memory_apply_not_implemented_use_dry_run_for_owner_review"]
    status = _safe_str(row.get("status"))
    if status not in PROMOTION_ELIGIBLE_STATUSES and not allow_unapproved:
        blockers.append(f"candidate_status_not_approved:{status or 'unknown'}")
    if not _target_rel(row):
        blockers.append("target_memory_layer_outside_memory_tree")
    provenance = row.get("provenance") if isinstance(row.get("provenance"), dict) else {}
    if provenance.get("stable_memory_write_allowed") is False:
        blockers.append("provenance_blocks_direct_stable_write")
    return blockers


def _target_rel(row: dict[str, Any]) -> Path | None:
    raw = _safe_str(row.get("target_memory_layer")).strip().replace("\\", "/")
    if not raw or raw.startswith("/") or ":" in raw:
        return None
    rel = Path(raw)
    parts = rel.parts
    if not parts or parts[0] != "memory":
        return None
    if any(part in {"..", ""} for part in parts):
        return None
    return rel


def _render_proposed_entry(row: dict[str, Any], *, generated_at: str) -> str:
    evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
    review_summary = {
        "candidate_id": row.get("candidate_id"),
        "candidate_type": row.get("candidate_type"),
        "source_turn_id": row.get("source_turn_id", ""),
        "source_message_ids": row.get("source_message_ids", []),
        "claim_key": evidence.get("claim_key", ""),
        "claim_topic_key": evidence.get("claim_topic_key", ""),
        "confidence_score": row.get("confidence_score", 0),
        "reason": row.get("reason", ""),
    }
    return "\n".join(
        [
            "",
            f"## Candidate Promotion Draft: {_one_line(row.get('candidate_id'), limit=120)}",
            f"- drafted_at: {generated_at}",
            "- source: memory_candidate_promotion_dry_run",
            "- stable_write_status: owner_review_preview_only",
            f"- candidate_type: {_one_line(row.get('candidate_type'), limit=80)}",
            f"- confidence_score: {_one_line(row.get('confidence_score'), limit=20, default='0')}",
            f"- source_turn_id: {_one_line(row.get('source_turn_id'), limit=120)}",
            f"- source_message_ids: {_one_line(','.join(str(item) for item in row.get('source_message_ids', []) or []), limit=160)}",
            f"- claim_key: {_one_line(evidence.get('claim_key'), limit=80)}",
            f"- claim_topic_key: {_one_line(evidence.get('claim_topic_key'), limit=80)}",
            f"- reason: {_one_line(row.get('reason'), limit=220)}",
            f"- candidate_text_summary: {_one_line(row.get('candidate_text'), limit=500)}",
            f"- review_metadata_json: {json.dumps(review_summary, ensure_ascii=False, sort_keys=True)}",
        ]
    ).rstrip() + "\n"


def _append_entry(before: str, proposed_entry: str) -> str:
    base = before.rstrip()
    if not base:
        return proposed_entry.lstrip()
    return base + "\n\n" + proposed_entry.lstrip()


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _safe_filename(value: Any, *, default: str = "item") -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "-", _safe_str(value).strip()).strip(".-")
    return text or default


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a dry-run stable-memory promotion preview for a candidate.")
    parser.add_argument("candidate_id")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--allow-unapproved", action="store_true")
    parser.add_argument("--write-preview", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = build_stable_memory_promotion_dry_run(
        args.root.resolve(),
        args.candidate_id,
        allow_unapproved=args.allow_unapproved,
        write_preview=args.write_preview,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(render_promotion_dry_run(result), end="")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
