from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import argparse
import os
import subprocess
import tempfile
import zipfile
from argparse import Namespace
from pathlib import Path
from xml.sax.saxutils import escape

from xinyu_learning_library import command_add, command_stage, extract_text_from_bytes, load_manifest, pdf_text_looks_garbled
from xinyu_text_variants import legacy_mojibake_variants, looks_like_legacy_mojibake, repair_legacy_mojibake


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate XinYu learning library staging.")
    parser.add_argument("--keep-temp", action="store_true")
    return parser


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _has_tokens(text: str, *tokens: str) -> bool:
    normalized = text.lower()
    return all(token.lower() in normalized for token in tokens)


def _mojibake_fixture_text() -> str:
    text = "IM Context 中文 DeepSeek-V4 注意力 Sliding Window Attention Sink Partial ROPE"
    variants = legacy_mojibake_variants(text)
    return variants[0] if variants else text


def _repairable_mojibake_pair() -> tuple[str, str]:
    text = "中文抽取应该保持可读不要变成乱码"
    raw = text.encode("utf-8")
    try:
        return text, raw.decode("gb18030")
    except UnicodeDecodeError:
        return text, raw.decode("gb18030", errors="replace")


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


def _garbled_pdf_bytes() -> bytes:
    bad_hex = "FFFD" * 80
    stream = f"BT /F1 12 Tf 72 720 Td <{bad_hex}> Tj ET".encode("ascii")
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n"
        + f"<< /Length {len(stream)} >>\n".encode("ascii")
        + b"stream\n"
        + stream
        + b"\nendstream\n"
        b"endobj\n"
        b"trailer\n<<>>\n%%EOF\n"
    )


def _extract_garbled_pdf_with_ocr_disabled() -> str:
    previous = os.environ.get("XINYU_OCR_ENABLED")
    os.environ["XINYU_OCR_ENABLED"] = "0"
    try:
        return extract_text_from_bytes(_garbled_pdf_bytes(), "garbled.pdf", "application/pdf")
    finally:
        if previous is None:
            os.environ.pop("XINYU_OCR_ENABLED", None)
        else:
            os.environ["XINYU_OCR_ENABLED"] = previous


def _write_pptx(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    slide_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        f"<p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>{escape(text)}</a:t></a:r></a:p>"
        "</p:txBody></p:sp></p:spTree></p:cSld></p:sld>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("ppt/slides/slide1.xml", slide_xml)


def _write_xlsx(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    shared_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<si><t>{escape(text)}</t></si></sst>"
    )
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData><row r="1"><c r="A1" t="s"><v>0</v></c></row></sheetData></worksheet>'
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/sharedStrings.xml", shared_xml)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def _write_rtf(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(r"{\rtf1\ansi " + text + r"\par}", encoding="ascii")


def _write_ocr_image(path: Path, text: str, *, image_format: str = "Png") -> bool:
    if os.name != "nt":
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    script = f"""
Add-Type -AssemblyName System.Drawing
$bmp = New-Object System.Drawing.Bitmap 1600,320
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.Clear([System.Drawing.Color]::White)
$font = New-Object System.Drawing.Font 'Arial', 54
$brush = [System.Drawing.Brushes]::Black
$g.DrawString('{text}', $font, $brush, 40, 110)
$bmp.Save('{str(path)}', [System.Drawing.Imaging.ImageFormat]::{image_format})
$g.Dispose()
$bmp.Dispose()
"""
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return completed.returncode == 0 and path.exists()


def _build_pdf(objects: list[bytes]) -> bytes:
    chunks: list[bytes] = [b"%PDF-1.4\n"]
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(sum(len(chunk) for chunk in chunks))
        chunks.append(f"{index} 0 obj\n".encode("ascii") + obj + b"\nendobj\n")
    xref = sum(len(chunk) for chunk in chunks)
    chunks.append(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
    for offset in offsets[1:]:
        chunks.append(f"{offset:010d} 00000 n \n".encode("ascii"))
    chunks.append(
        f"trailer\n<< /Root 1 0 R /Size {len(objects) + 1} >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
    )
    return b"".join(chunks)


def _write_scanned_pdf(path: Path, text: str) -> bool:
    if os.name != "nt":
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="xinyu-ocr-fixture-") as tmp:
        image_path = Path(tmp) / "scan.jpg"
        if not _write_ocr_image(image_path, text, image_format="Jpeg"):
            return False
        image = image_path.read_bytes()
    content = b"q 520 0 0 104 46 620 cm /Im1 Do Q"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /XObject << /Im1 4 0 R >> >> /Contents 5 0 R >>",
        (
            b"<< /Type /XObject /Subtype /Image /Width 1600 /Height 320 "
            b"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode "
            + f"/Length {len(image)} >>\nstream\n".encode("ascii")
            + image
            + b"\nendstream"
        ),
        f"<< /Length {len(content)} >>\nstream\n".encode("ascii") + content + b"\nendstream",
    ]
    path.write_bytes(_build_pdf(objects))
    return True


def _add_args(root: Path, source: Path, origin: str, reason: str) -> Namespace:
    return Namespace(
        path=str(source),
        max_bytes=10_000_000,
        origin=origin,
        reason=reason,
        question_id="q-learning-library-smoke",
        title="",
        label="",
        stage=False,
        curated=False,
        root=str(root),
    )


def _stage_args(root: Path, item_id: str) -> Namespace:
    return Namespace(id=item_id, all=False, curated=False, root=str(root))


def _run_case(root: Path) -> int:
    fixture_dir = root / "fixtures"
    owner_file = fixture_dir / "owner_supplied_note.md"
    self_file = fixture_dir / "self_found_note.md"
    docx_file = fixture_dir / "owner_persona_memory.docx"
    pdf_file = fixture_dir / "owner_reference.pdf"
    pptx_file = fixture_dir / "owner_slides.pptx"
    xlsx_file = fixture_dir / "owner_sheet.xlsx"
    rtf_file = fixture_dir / "owner_note.rtf"
    ocr_image_file = fixture_dir / "owner_scan.png"
    scanned_pdf_file = fixture_dir / "owner_scanned.pdf"
    _write(
        owner_file,
        """# Owner Supplied Learning Note

Owner-supplied material should enter the learning library as curated local material.
It may become source material without rewriting identity or relationship memory.
""",
    )
    _write(
        self_file,
        """# Self Found Learning Note

Self-found material should be stored, but it should still need comparison or review
before learner integration treats it as learned knowledge.
""",
    )
    _write_docx(
        docx_file,
        [
            "XinYu docx fixture memory should be extracted from Word XML.",
            "The learning library must not treat QQ docx files as unreadable binaries.",
        ],
    )
    _write_pdf(pdf_file, "XinYu PDF fixture should be extracted from a text PDF.")
    _write_pptx(pptx_file, "XinYu PPTX fixture should be extracted from slides.")
    _write_xlsx(xlsx_file, "XinYu XLSX fixture should be extracted from sheets.")
    _write_rtf(rtf_file, "XinYu RTF fixture should be extracted from rich text.")
    ocr_fixture_enabled = _write_ocr_image(ocr_image_file, "XinYu OCR image fixture 123")
    scanned_pdf_enabled = _write_scanned_pdf(scanned_pdf_file, "XinYu OCR scanned PDF 789")

    rc = command_add(_add_args(root, owner_file, "owner_supplied", "owner supplied fixture"))
    if rc:
        return rc
    rc = command_add(_add_args(root, self_file, "self_found", "self found fixture"))
    if rc:
        return rc
    rc = command_add(_add_args(root, docx_file, "owner_supplied", "owner supplied docx fixture"))
    if rc:
        return rc
    rc = command_add(_add_args(root, pdf_file, "owner_supplied", "owner supplied pdf fixture"))
    if rc:
        return rc
    for path, reason in (
        (pptx_file, "owner supplied pptx fixture"),
        (xlsx_file, "owner supplied xlsx fixture"),
        (rtf_file, "owner supplied rtf fixture"),
    ):
        rc = command_add(_add_args(root, path, "owner_supplied", reason))
        if rc:
            return rc
    if ocr_fixture_enabled:
        rc = command_add(_add_args(root, ocr_image_file, "owner_supplied", "owner supplied image OCR fixture"))
        if rc:
            return rc
    if scanned_pdf_enabled:
        rc = command_add(_add_args(root, scanned_pdf_file, "owner_supplied", "owner supplied scanned pdf OCR fixture"))
        if rc:
            return rc

    manifest = load_manifest(root)
    owner_item = next(item for item in manifest if item["origin"] == "owner_supplied")
    self_item = next(item for item in manifest if item["origin"] == "self_found")
    docx_item = next(item for item in manifest if item["title"] == docx_file.name)
    pdf_item = next(item for item in manifest if item["title"] == pdf_file.name)
    pptx_item = next(item for item in manifest if item["title"] == pptx_file.name)
    xlsx_item = next(item for item in manifest if item["title"] == xlsx_file.name)
    rtf_item = next(item for item in manifest if item["title"] == rtf_file.name)
    ocr_image_item = next((item for item in manifest if item["title"] == ocr_image_file.name), None)
    scanned_pdf_item = next((item for item in manifest if item["title"] == scanned_pdf_file.name), None)
    md_extract_path = root / str(owner_item.get("extracted_text_path") or "")
    docx_extract_path = root / str(docx_item.get("extracted_text_path") or "")
    pdf_extract_path = root / str(pdf_item.get("extracted_text_path") or "")
    pptx_extract_path = root / str(pptx_item.get("extracted_text_path") or "")
    xlsx_extract_path = root / str(xlsx_item.get("extracted_text_path") or "")
    rtf_extract_path = root / str(rtf_item.get("extracted_text_path") or "")
    ocr_image_extract_path = root / str(ocr_image_item.get("extracted_text_path") or "") if ocr_image_item else Path()
    scanned_pdf_extract_path = root / str(scanned_pdf_item.get("extracted_text_path") or "") if scanned_pdf_item else Path()
    md_extract = md_extract_path.read_text(encoding="utf-8-sig") if md_extract_path.is_file() else ""
    docx_extract = docx_extract_path.read_text(encoding="utf-8-sig") if docx_extract_path.is_file() else ""
    pdf_extract = pdf_extract_path.read_text(encoding="utf-8-sig") if pdf_extract_path.is_file() else ""
    pptx_extract = pptx_extract_path.read_text(encoding="utf-8-sig") if pptx_extract_path.is_file() else ""
    xlsx_extract = xlsx_extract_path.read_text(encoding="utf-8-sig") if xlsx_extract_path.is_file() else ""
    rtf_extract = rtf_extract_path.read_text(encoding="utf-8-sig") if rtf_extract_path.is_file() else ""
    ocr_image_extract = (
        ocr_image_extract_path.read_text(encoding="utf-8-sig") if ocr_image_extract_path.is_file() else ""
    )
    scanned_pdf_extract = (
        scanned_pdf_extract_path.read_text(encoding="utf-8-sig") if scanned_pdf_extract_path.is_file() else ""
    )

    rc = command_stage(_stage_args(root, str(owner_item["id"])))
    if rc:
        return rc
    rc = command_stage(_stage_args(root, str(self_item["id"])))
    if rc:
        return rc

    source_materials = (root / "memory/knowledge/source_materials.md").read_text(encoding="utf-8-sig")
    readable_chinese, mojibake_chinese = _repairable_mojibake_pair()
    checks = {
        "owner_origin": "- learning_origin: owner_supplied" in source_materials,
        "self_origin": "- learning_origin: self_found" in source_materials,
        "owner_curated": "- comparison_status: curated" in source_materials,
        "self_not_compared": "- comparison_status: not_compared" in source_materials,
        "owner_item_id": str(owner_item["id"]) in source_materials,
        "self_item_id": str(self_item["id"]) in source_materials,
        "md_extracted": "Owner-supplied material should enter" in md_extract,
        "docx_extracted": "XinYu docx fixture memory" in docx_extract,
        "docx_octet_stream_extracted": "XinYu docx fixture memory"
        in extract_text_from_bytes(docx_file.read_bytes(), "qqdownloadftnv5", "application/octet-stream"),
        "pdf_extracted": "XinYu PDF fixture should be extracted" in pdf_extract,
        "pdf_octet_stream_extracted": "XinYu PDF fixture should be extracted"
        in extract_text_from_bytes(pdf_file.read_bytes(), "qqdownloadftnv5", "application/octet-stream"),
        "pptx_extracted": "XinYu PPTX fixture should be extracted" in pptx_extract,
        "xlsx_extracted": "XinYu XLSX fixture should be extracted" in xlsx_extract,
        "rtf_extracted": "XinYu RTF fixture should be extracted" in rtf_extract,
        "pdf_plain_quality_ok": not pdf_text_looks_garbled("XinYu PDF fixture should be extracted from a text PDF."),
        "pdf_garbled_quality_hold": pdf_text_looks_garbled(
            "\uf6b2.\x01$POUFYU\x01\u035b\x01\u4ef0\u4a63\ua75a\u962d\u4453\x01"
            "\u2623\x01%FFQ4FFL\u0017\u0014\u0015\u0016\u4d07\ua75a\u2515\u2516\u4e44"
        ),
        "pdf_mojibake_quality_hold": pdf_text_looks_garbled(
            _mojibake_fixture_text()
        ),
        "mojibake_detector_flags_chinese": looks_like_legacy_mojibake(mojibake_chinese),
        "mojibake_repair_restores_chinese": repair_legacy_mojibake(mojibake_chinese) == readable_chinese,
        "pdf_garbled_extraction_hold": _extract_garbled_pdf_with_ocr_disabled() == "",
    }
    if ocr_fixture_enabled:
        checks["image_ocr_extracted"] = _has_tokens(ocr_image_extract, "xinyu", "ocr", "123")
    if scanned_pdf_enabled:
        checks["scanned_pdf_ocr_extracted"] = _has_tokens(scanned_pdf_extract, "xinyu", "ocr", "789")

    print("=== LEARNING LIBRARY SMOKE ===")
    print("manifest_items:", len(manifest))
    print("owner_item:", owner_item["id"])
    print("self_item:", self_item["id"])
    print("docx_item:", docx_item["id"])
    print("pdf_item:", pdf_item["id"])
    print("pptx_item:", pptx_item["id"])
    print("xlsx_item:", xlsx_item["id"])
    print("rtf_item:", rtf_item["id"])
    if ocr_image_item:
        print("ocr_image_item:", ocr_image_item["id"])
    if scanned_pdf_item:
        print("scanned_pdf_item:", scanned_pdf_item["id"])
    for key, value in checks.items():
        print(f"{key}:", "ok" if value else "missing")

    return 0 if all(checks.values()) else 4


def main() -> int:
    args = _build_parser().parse_args()
    if args.keep_temp:
        temp_root = Path(tempfile.mkdtemp(prefix="xinyu-learning-library-smoke-"))
        print("temp_root:", temp_root)
        return _run_case(temp_root)
    with tempfile.TemporaryDirectory(prefix="xinyu-learning-library-smoke-") as tmp:
        return _run_case(Path(tmp))


if __name__ == "__main__":
    raise SystemExit(main())
