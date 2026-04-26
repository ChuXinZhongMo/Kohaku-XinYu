from __future__ import annotations

import asyncio
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from xinyu_core_bridge import XinYuBridgeRuntime


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


async def _run_case(root: Path) -> int:
    source = root / "fixtures" / "qq_owner_memory.docx"
    _write_docx(
        source,
        [
            "QQ supplied docx should enter XinYu learning ingest.",
            "This smoke proves Word XML becomes readable learning text.",
        ],
    )

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
            }
        )
    finally:
        await runtime.shutdown()

    source_materials = (root / "memory/knowledge/source_materials.md").read_text(encoding="utf-8-sig")
    extracted_rel = str(result.get("extracted_text_path") or "")
    extracted_path = root / extracted_rel
    extracted = extracted_path.read_text(encoding="utf-8-sig") if extracted_path.is_file() else ""

    checks = {
        "accepted": result.get("accepted") is True,
        "no_session": result.get("session_created") is False,
        "library_item": bool(result.get("learning_item_id")),
        "staged": "material-" in str(result.get("material_id") or ""),
        "owner_origin": "- learning_origin: owner_supplied" in source_materials,
        "curated": "- comparison_status: curated" in source_materials,
        "docx_extracted": "QQ supplied docx should enter XinYu learning ingest" in extracted,
    }

    print("=== BRIDGE LEARNING INGEST SMOKE ===")
    print("learning_item_id:", result.get("learning_item_id"))
    print("material_id:", result.get("material_id"))
    print("extracted_text_path:", result.get("extracted_text_path") or "none")
    for key, value in checks.items():
        print(f"{key}:", "ok" if value else "missing")
    return 0 if all(checks.values()) else 4


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="xinyu-bridge-learning-ingest-") as tmp:
        return asyncio.run(_run_case(Path(tmp)))


if __name__ == "__main__":
    raise SystemExit(main())
