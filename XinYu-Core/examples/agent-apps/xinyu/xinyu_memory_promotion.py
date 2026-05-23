from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_dialogue_archive import list_memory_candidates, update_memory_candidate_status


PROMOTION_DRY_RUN_REL = Path("runtime/memory_promotion_dry_runs")
APPLIED_GROWTH_LOG_STATUS = "applied_growth_log"
GROWTH_LOG_TARGET_MEMORY_LAYER = "memory/reflection/growth_log.md"
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
    apply_allowed = not blockers
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
        "apply_allowed": apply_allowed,
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


def list_growth_candidate_promotions(root: Path, *, limit: int = 50) -> dict[str, Any]:
    root = root.resolve()
    clean_limit = max(1, min(int(limit or 50), 200))
    pending_apply: list[dict[str, Any]] = []
    applied: list[dict[str, Any]] = []
    owner_review_required: list[dict[str, Any]] = []
    target_path = root / GROWTH_LOG_TARGET_MEMORY_LAYER
    seen: set[str] = set()

    for row in list_memory_candidates(root, status="owner_review_required", limit=max(clean_limit * 2, 50)):
        candidate_id = _safe_str(row.get("candidate_id")).strip()
        if not candidate_id:
            continue
        owner_review_required.append(
            {
                "candidate_id": candidate_id,
                "status": row.get("status"),
                "candidate_type": row.get("candidate_type"),
                "target_memory_layer": row.get("target_memory_layer"),
                "target_gate": row.get("target_gate"),
                "risk_flags": [_one_line(item, limit=120, default="") for item in row.get("risk_flags", []) if _safe_str(item)],
                "apply_allowed": False,
                "stable_memory_write": "owner_review_required",
                "stable_personality_write": "blocked",
                "reason_preview": _one_line(row.get("reason"), limit=240, default=""),
                "candidate_text_preview": "hidden_owner_review_required",
            }
        )
        if len(owner_review_required) >= clean_limit:
            break

    for status in ("approved", APPLIED_GROWTH_LOG_STATUS):
        for row in list_memory_candidates(root, status=status, limit=max(clean_limit * 2, 50)):
            candidate_id = _safe_str(row.get("candidate_id")).strip()
            if not candidate_id or candidate_id in seen:
                continue
            seen.add(candidate_id)
            if _safe_str(row.get("candidate_type")).strip() != "post_reply_growth_candidate":
                continue
            if _safe_str(row.get("target_memory_layer")).strip().replace("\\", "/") != GROWTH_LOG_TARGET_MEMORY_LAYER:
                continue
            if status == APPLIED_GROWTH_LOG_STATUS:
                applied.append(
                    {
                        "candidate_id": candidate_id,
                        "status": status,
                        "candidate_type": row.get("candidate_type"),
                        "target_memory_layer": row.get("target_memory_layer"),
                        "target_path": str(target_path),
                        "apply_allowed": False,
                        "stable_memory_write": "already_applied",
                        "stable_personality_write": "blocked",
                        "reason_preview": _one_line(row.get("reason"), limit=240, default=""),
                        "candidate_text_preview": _one_line(row.get("candidate_text"), limit=500, default=""),
                    }
                )
                continue

            preview = build_stable_memory_promotion_dry_run(root, candidate_id, write_preview=False)
            before_hash = _safe_str(preview.get("before_hash"))
            item = {
                "candidate_id": candidate_id,
                "status": row.get("status"),
                "candidate_type": row.get("candidate_type"),
                "target_memory_layer": row.get("target_memory_layer"),
                "target_path": _safe_str(preview.get("target_path"), str(target_path)),
                "before_hash": before_hash,
                "apply_command": (
                    f'python xinyu_memory_candidate_review_cli.py apply {candidate_id} '
                    f'--notes "owner_apply_confirmed after preview" --expected-before-hash {before_hash}'
                ),
                "blockers": preview.get("blockers") if isinstance(preview.get("blockers"), list) else [],
                "apply_allowed": False,
                "stable_memory_write": "dry_run_only",
                "stable_personality_write": "blocked",
                "reason_preview": _one_line(row.get("reason"), limit=240, default=""),
                "candidate_text_preview": _one_line(row.get("candidate_text"), limit=500, default=""),
            }
            preview_path = root / PROMOTION_DRY_RUN_REL / f"{_safe_filename(candidate_id, default='unknown')}.md"
            if preview_path.exists():
                item["preview_path"] = str(preview_path)
            pending_apply.append(item)
            if len(pending_apply) >= clean_limit:
                break

    return {
        "ok": True,
        "pending_apply_count": len(pending_apply),
        "applied_count": len(applied),
        "owner_review_required_count": len(owner_review_required),
        "pending_apply": pending_apply[:clean_limit],
        "applied": applied[:clean_limit],
        "owner_review_required": owner_review_required[:clean_limit],
        "target_path": str(target_path),
        "target_memory_layer": GROWTH_LOG_TARGET_MEMORY_LAYER,
        "notes": ["desktop_growth_candidate_status_read_only", "owner_review_body_hidden", "frontend_apply_blocked"],
    }


def _promotion_blockers(row: dict[str, Any], *, allow_unapproved: bool) -> list[str]:
    blockers: list[str] = []
    status = _safe_str(row.get("status"))
    if status not in PROMOTION_ELIGIBLE_STATUSES and not allow_unapproved:
        blockers.append(f"candidate_status_not_approved:{status or 'unknown'}")
    if not _target_rel(row):
        blockers.append("target_memory_layer_outside_memory_tree")
    if _safe_str(row.get("candidate_type")).strip() != "post_reply_growth_candidate":
        blockers.append("candidate_type_not_supported_for_stable_apply")
    target_rel = _target_rel(row)
    if target_rel != Path(GROWTH_LOG_TARGET_MEMORY_LAYER):
        blockers.append("target_memory_layer_not_growth_log")
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


def apply_stable_memory_promotion(
    root: Path,
    candidate_id: str,
    *,
    review_notes: str = "",
    expected_before_hash: str = "",
    applied_at: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    if "owner_apply_confirmed" not in review_notes:
        return {"ok": False, "error": "owner_apply_confirmation_required", "candidate_id": candidate_id}
    generated = applied_at or _now_iso()
    preview = build_stable_memory_promotion_dry_run(root, candidate_id, generated_at=generated)
    if not preview.get("ok"):
        return preview
    blockers = preview.get("blockers") if isinstance(preview.get("blockers"), list) else []
    if blockers:
        return {"ok": False, "error": "promotion_blocked", "candidate_id": candidate_id, "blockers": blockers}
    if expected_before_hash and expected_before_hash != preview.get("before_hash"):
        return {
            "ok": False,
            "error": "target_changed_since_preview",
            "candidate_id": candidate_id,
            "expected_before_hash": expected_before_hash,
            "actual_before_hash": preview.get("before_hash", ""),
        }
    proposed_entry = _safe_str(preview.get("proposed_entry"))
    if not proposed_entry.strip():
        return {"ok": False, "error": "empty_proposed_entry", "candidate_id": candidate_id}
    if any(pattern.search(proposed_entry) for pattern in SECRET_PATTERNS):
        return {"ok": False, "error": "proposed_entry_contains_secret", "candidate_id": candidate_id}
    target_path = Path(_safe_str(preview.get("target_path")))
    before = _read_text(target_path)
    if _text_hash(before) != preview.get("before_hash"):
        return {
            "ok": False,
            "error": "target_changed_during_apply",
            "candidate_id": candidate_id,
            "expected_before_hash": preview.get("before_hash", ""),
            "actual_before_hash": _text_hash(before),
        }
    after = _append_entry(before, proposed_entry)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(after, encoding="utf-8")
    status_notes = _one_line(f"{review_notes}; applied_at={generated}; stable_personality_write=blocked", limit=1000)
    if not update_memory_candidate_status(
        root,
        candidate_id=candidate_id,
        status=APPLIED_GROWTH_LOG_STATUS,
        review_notes=status_notes,
    ):
        return {"ok": False, "error": "candidate_status_update_failed", "candidate_id": candidate_id}
    return {
        "ok": True,
        "candidate_id": candidate_id,
        "status": APPLIED_GROWTH_LOG_STATUS,
        "target_path": str(target_path),
        "before_hash": preview.get("before_hash", ""),
        "after_hash": _text_hash(after),
        "stable_memory_write": "applied_growth_log_only",
        "stable_personality_write": "blocked",
        "applied_at": generated,
        "notes": ["growth_log_appended", "stable_personality_not_modified"],
    }


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
