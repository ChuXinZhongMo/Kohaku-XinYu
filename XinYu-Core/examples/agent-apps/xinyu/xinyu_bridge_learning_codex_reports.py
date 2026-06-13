from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path

from xinyu_bridge_learning_codex_reports_store import codex_report_is_file
from xinyu_bridge_learning_codex_reports_store import codex_report_mtime
from xinyu_bridge_learning_codex_reports_store import read_codex_report_text
from xinyu_bridge_learning_codex_reports_store import read_codex_report_text_for_update
from xinyu_bridge_learning_codex_reports_store import write_codex_report_text
from xinyu_learning_library import (
    claim_from_text,
    ensure_source_materials_file,
    next_material_id,
    pdf_text_looks_garbled,
    sanitize_field,
)


def _resolve_report_path(root: Path, report_path: str) -> Path:
    path = Path(str(report_path or "").strip())
    if not path:
        return path
    return path if path.is_absolute() else root / path


def _codex_report_key(report_path: Path) -> str:
    return hashlib.sha256(str(report_path.resolve()).encode("utf-8", errors="replace")).hexdigest()[:16]


def _existing_codex_report_material_id(source_materials: str, report_key: str) -> str:
    marker = f"- codex_report_key: {report_key}"
    marker_index = source_materials.find(marker)
    if marker_index < 0:
        return ""
    preceding = source_materials[:marker_index]
    matches = re.findall(r"(?m)^## (material-\d{4}-\d{2}-\d{2}-\d{3})\n", preceding)
    return matches[-1] if matches else ""


def _append_report_learning_registration(report_path: Path, material_id: str, registered_at: str) -> None:
    readable, text = read_codex_report_text_for_update(report_path)
    if not readable:
        return
    if "## XinYu Learning Registration" in text:
        return
    addition = (
        "\n\n## XinYu Learning Registration\n\n"
        f"- material_id: {material_id}\n"
        f"- registered_at: {registered_at}\n"
        "- learning_followup: queued_through_existing_gates\n"
    )
    write_codex_report_text(report_path, text + addition + "\n")


def stage_codex_report_material(
    root: Path,
    *,
    report_path: str,
    task_text: str = "",
    job_id: str = "",
    registered_at: str | None = None,
) -> dict[str, object]:
    registered_at = registered_at or datetime.now().astimezone().isoformat()
    path = _resolve_report_path(root, report_path)
    if not path or not codex_report_is_file(path):
        return {
            "material_id": "",
            "registered": False,
            "status": "missing_report",
            "notes": ["codex_report_material_missing"],
        }

    source_path = ensure_source_materials_file(root)
    source_text = read_codex_report_text(source_path).rstrip()
    report_key = _codex_report_key(path)
    existing = _existing_codex_report_material_id(source_text, report_key)
    if existing:
        _append_report_learning_registration(path, existing, registered_at)
        return {
            "material_id": existing,
            "registered": False,
            "status": "already_staged",
            "notes": ["codex_report_material_already_staged"],
        }

    report_text = read_codex_report_text(path)
    readable = bool(report_text.strip()) and not pdf_text_looks_garbled(report_text)
    fetched_at = datetime.fromtimestamp(codex_report_mtime(path)).astimezone().isoformat()
    date_part = fetched_at[:10]
    material_id = next_material_id(source_text, date_part)
    fallback = f"Codex report for owner-delegated task: {task_text[:240] or path.name}"
    claim = claim_from_text(report_text, fallback)
    status = "ready" if readable else "hold"
    extraction_status = "readable_text" if readable else "unreadable"
    addition = (
        f"\n\n## {material_id}\n"
        "- question_id: qq-codex-delegation\n"
        f"- source_question: {sanitize_field(task_text or path.name)}\n"
        f"- url: codex-report://{sanitize_field(job_id or report_key, 120)}\n"
        "- source_type: codex_search_report\n"
        "- reliability: curated\n"
        "- integration_scope: knowledge_only\n"
        f"- status: {status}\n"
        f"- fetched_at: {fetched_at}\n"
        "- comparison_status: curated\n"
        "- evidence_hosts: 1\n"
        "- learning_origin: codex_report\n"
        "- learning_item_id: none\n"
        f"- local_path: {sanitize_field(str(path))}\n"
        f"- extracted_text_path: {sanitize_field(str(path))}\n"
        f"- extraction_status: {extraction_status}\n"
        f"- codex_job_id: {sanitize_field(job_id or 'none', 120)}\n"
        f"- codex_report_key: {report_key}\n"
        f"- claim: {sanitize_field(claim)}\n"
    )
    write_codex_report_text(source_path, source_text + addition + "\n")
    _append_report_learning_registration(path, material_id, registered_at)
    return {
        "material_id": material_id,
        "registered": True,
        "status": status,
        "notes": ["codex_report_material_staged"],
    }
