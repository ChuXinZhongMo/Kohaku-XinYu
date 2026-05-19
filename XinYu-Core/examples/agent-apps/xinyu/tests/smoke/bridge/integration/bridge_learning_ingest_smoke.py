from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()
LEARNING_SMOKE_DIR = ROOT / "tests" / "smoke" / "learning"
if str(LEARNING_SMOKE_DIR) not in sys.path:
    sys.path.insert(0, str(LEARNING_SMOKE_DIR))

from learning_library_smoke import _write_scanned_pdf
from xinyu_learning_library import DEFAULT_MAX_BYTES, load_manifest
from xinyu_text_variants import looks_like_legacy_mojibake
from xinyu_core_bridge import XinYuBridgeRuntime


def _has_tokens(text: str, *tokens: str) -> bool:
    normalized = text.lower()
    return all(token.lower() in normalized for token in tokens)


def _write_docx(path: Path, paragraphs: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(
        f"<w:p><w:r><w:t>{escape(paragraph)}</w:t></w:r></w:p>"
        for paragraph in paragraphs
    )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", document_xml)


def _write_pdf(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("latin-1")
    data = (
        b"%PDF-1.4\n"
        b"1 0 obj\n"
        + f"<< /Length {len(stream)} >>\n".encode("ascii")
        + b"stream\n"
        + stream
        + b"\nendstream\n"
        b"endobj\n"
        b"trailer\n<<>>\n%%EOF\n"
    )
    path.write_bytes(data)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _prepare_learning_memory(root: Path) -> None:
    now = "2026-04-27T00:00:00+08:00"
    _write(
        root / "memory/knowledge/source_gate_state.md",
        f"""---
title: Source Gate State
memory_type: source_gate_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: smoke
created_at: {now}
updated_at: {now}
last_confirmed_at: {now}
importance_score: 79
impact_score: 79
confidence_score: 100
status: active
tags: [knowledge, source_gate, smoke]
---

# Source Gate State
""",
    )
    _write(
        root / "memory/knowledge/source_reliability_state.md",
        f"""---
title: Source Reliability State
memory_type: source_reliability_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: smoke
created_at: {now}
updated_at: {now}
last_confirmed_at: {now}
importance_score: 79
impact_score: 79
confidence_score: 100
status: active
tags: [knowledge, source, reliability, smoke]
---

# Source Reliability State
""",
    )
    _write(
        root / "memory/knowledge/general.md",
        f"""---
title: General Knowledge Smoke
memory_type: knowledge_general
time_scope: long_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: {now}
updated_at: {now}
last_confirmed_at: {now}
importance_score: 71
impact_score: 56
confidence_score: 100
status: active
tags: [knowledge, general, smoke]
---

# General Knowledge
""",
    )
    _write(
        root / "memory/knowledge/source_notes.md",
        f"""---
title: Source Notes Smoke
memory_type: source_notes
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: {now}
updated_at: {now}
last_confirmed_at: {now}
importance_score: 74
impact_score: 72
confidence_score: 100
status: active
tags: [knowledge, source, notes, smoke]
---

# Source Notes
""",
    )
    _write(
        root / "memory/knowledge/learning_quality_state.md",
        f"""---
title: Learning Quality Smoke
memory_type: learning_quality_state
time_scope: mid_term
subject_ids: [xinyu]
protected: true
source: smoke
created_at: {now}
updated_at: {now}
last_confirmed_at: {now}
importance_score: 83
impact_score: 82
confidence_score: 100
status: active
tags: [knowledge, learning, quality, smoke]
---

# Learning Quality State
""",
    )
    _write(root / "memory/context/question_states.md", "# Current Question States")
    _write(root / "memory/context/exploration_queue.md", "# Exploration Queue")


async def _run_case(root: Path) -> int:
    source = root / "fixtures" / "qq_owner_memory.docx"
    pdf_source = root / "fixtures" / "qq_owner_reference.pdf"
    scanned_pdf_source = root / "fixtures" / "qq_owner_scan.pdf"
    _write_docx(
        source,
        [
            "QQ supplied docx should enter XinYu learning ingest.",
            "This smoke proves Word XML becomes readable learning text.",
        ],
    )
    _write_pdf(pdf_source, "QQ supplied PDF should enter XinYu learning ingest.")
    scanned_pdf_enabled = _write_scanned_pdf(scanned_pdf_source, "QQ supplied scanned PDF OCR 789")
    _prepare_learning_memory(root)

    runtime = XinYuBridgeRuntime(
        xinyu_dir=root,
        turn_timeout_seconds=5,
        max_text_chars=8000,
        settle_seconds=0.0,
        outward_renderer=False,
        render_timeout_seconds=5,
        session_idle_ttl_seconds=60,
        max_sessions=1,
        proactive_min_interval_seconds=0,
    )
    old_read_dirs = os.environ.get("XINYU_LOCAL_READ_DIRS")
    os.environ["XINYU_LOCAL_READ_DIRS"] = str(source.parent)
    try:
        result = await runtime.learning_ingest(
            {
                "file_path": str(source),
                "file_name": source.name,
                "origin": "owner_supplied",
                "reason": "QQ owner supplied docx smoke",
                "question_id": "q-qq-file-smoke",
                "stage": True,
                "curated": True,
                "max_bytes": DEFAULT_MAX_BYTES * 4,
            }
        )
        pdf_result = await runtime.learning_ingest(
            {
                "file_path": str(pdf_source),
                "file_name": pdf_source.name,
                "origin": "owner_supplied",
                "reason": "QQ owner supplied pdf smoke",
                "question_id": "q-qq-file-smoke",
                "stage": True,
                "curated": True,
            }
        )
        scanned_pdf_result = None
        if scanned_pdf_enabled:
            scanned_pdf_result = await runtime.learning_ingest(
                {
                    "file_path": str(scanned_pdf_source),
                    "file_name": scanned_pdf_source.name,
                    "origin": "owner_supplied",
                    "reason": "QQ owner supplied scanned pdf smoke",
                    "question_id": "q-qq-file-smoke",
                    "stage": True,
                    "curated": True,
                }
            )
        outside_source = root / "outside_scope.md"
        _write(outside_source, "outside scope should be rejected")
        outside_blocked = False
        try:
            await runtime.learning_ingest(
                {
                    "file_path": str(outside_source),
                    "file_name": outside_source.name,
                    "origin": "owner_supplied",
                    "reason": "outside scope smoke",
                    "question_id": "q-qq-file-smoke",
                }
            )
        except Exception as exc:
            outside_blocked = "outside" in str(exc).lower() or "read-only" in str(exc).lower()
        traversal_blocked = False
        try:
            await runtime.learning_ingest(
                {
                    "file_path": "..\\outside_scope.md",
                    "file_name": "outside_scope.md",
                    "origin": "owner_supplied",
                    "reason": "traversal smoke",
                    "question_id": "q-qq-file-smoke",
                }
            )
        except Exception as exc:
            traversal_blocked = "traversal" in str(exc).lower() or "outside" in str(exc).lower()
        internal_url_blocked = False
        try:
            await runtime.learning_ingest(
                {
                    "file_url": "http://127.0.0.1/private.txt",
                    "file_name": "private.txt",
                    "origin": "owner_supplied",
                    "reason": "internal URL smoke",
                    "question_id": "q-qq-file-smoke",
                }
            )
        except Exception as exc:
            internal_url_blocked = "internal" in str(exc).lower() or "blocked" in str(exc).lower()
        study_result = await runtime.learning_study(
            {
                "source": "bridge_learning_ingest_smoke",
                "mode": "bridge_learning_ingest_smoke_study",
                "text": "学习一下",
            }
        )
    finally:
        if old_read_dirs is None:
            os.environ.pop("XINYU_LOCAL_READ_DIRS", None)
        else:
            os.environ["XINYU_LOCAL_READ_DIRS"] = old_read_dirs
        await runtime.shutdown()

    source_materials = (root / "memory/knowledge/source_materials.md").read_text(encoding="utf-8-sig")
    manifest = load_manifest(root)
    first_item = next(item for item in manifest if item.get("id") == result.get("learning_item_id"))
    source_url = str(first_item.get("source_url") or "")
    extracted_rel = str(result.get("extracted_text_path") or "")
    extracted_path = root / extracted_rel
    extracted = extracted_path.read_text(encoding="utf-8-sig") if extracted_path.is_file() else ""
    pdf_extracted_rel = str(pdf_result.get("extracted_text_path") or "")
    pdf_extracted_path = root / pdf_extracted_rel
    pdf_extracted = pdf_extracted_path.read_text(encoding="utf-8-sig") if pdf_extracted_path.is_file() else ""
    scanned_pdf_extracted = ""
    if scanned_pdf_result:
        scanned_pdf_extracted_rel = str(scanned_pdf_result.get("extracted_text_path") or "")
        scanned_pdf_extracted_path = root / scanned_pdf_extracted_rel
        scanned_pdf_extracted = (
            scanned_pdf_extracted_path.read_text(encoding="utf-8-sig")
            if scanned_pdf_extracted_path.is_file()
            else ""
        )
    general = (root / "memory/knowledge/general.md").read_text(encoding="utf-8-sig")

    checks = {
        "accepted": result.get("accepted") is True,
        "pdf_accepted": pdf_result.get("accepted") is True,
        "no_session": result.get("session_created") is False,
        "library_item": bool(result.get("learning_item_id")),
        "pdf_library_item": bool(pdf_result.get("learning_item_id")),
        "staged": "material-" in str(result.get("material_id") or ""),
        "pdf_staged": "material-" in str(pdf_result.get("material_id") or ""),
        "owner_origin": "- learning_origin: owner_supplied" in source_materials,
        "curated": "- comparison_status: curated" in source_materials,
        "docx_extracted": "QQ supplied docx should enter XinYu learning ingest" in extracted,
        "pdf_extracted": "QQ supplied PDF should enter XinYu learning ingest" in pdf_extracted,
        "outside_scope_blocked": outside_blocked,
        "traversal_blocked": traversal_blocked,
        "internal_url_blocked": internal_url_blocked,
        "max_bytes_clamped": f"max_bytes:{DEFAULT_MAX_BYTES}" in result.get("notes", []),
        "reply_naturalized": "received:" not in str(result.get("reply") or "")
        and "learning library updated" not in str(result.get("reply") or ""),
        "reply_not_garbled": not looks_like_legacy_mojibake(str(result.get("reply") or "")),
        "metadata_source_redacted": not source_url.startswith("file://") and str(source.resolve()) not in source_url,
        "source_materials_path_redacted": str(source.resolve()) not in source_materials,
        "study_accepted": study_result.get("accepted") is True,
        "study_integrated": int(study_result.get("integrated_materials") or 0) >= 2,
        "general_learned": "- source_material: material-" in general,
    }
    if scanned_pdf_enabled and scanned_pdf_result:
        checks["scanned_pdf_ocr_extracted"] = _has_tokens(scanned_pdf_extracted, "qq", "ocr", "789")

    print("=== BRIDGE LEARNING INGEST SMOKE ===")
    print("learning_item_id:", result.get("learning_item_id"))
    print("material_id:", result.get("material_id"))
    print("extracted_text_path:", result.get("extracted_text_path") or "none")
    print("pdf_learning_item_id:", pdf_result.get("learning_item_id"))
    print("pdf_material_id:", pdf_result.get("material_id"))
    print("pdf_extracted_text_path:", pdf_result.get("extracted_text_path") or "none")
    print("study_integrated_materials:", study_result.get("integrated_materials"))
    print("study_quality_grade:", study_result.get("quality_grade"))
    if scanned_pdf_result:
        print("scanned_pdf_learning_item_id:", scanned_pdf_result.get("learning_item_id"))
        print("scanned_pdf_material_id:", scanned_pdf_result.get("material_id"))
        print("scanned_pdf_extracted_text_path:", scanned_pdf_result.get("extracted_text_path") or "none")
    for key, value in checks.items():
        print(f"{key}:", "ok" if value else "missing")
    return 0 if all(checks.values()) else 4


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="xinyu-bridge-learning-ingest-") as tmp:
        return asyncio.run(_run_case(Path(tmp)))


if __name__ == "__main__":
    raise SystemExit(main())
