from __future__ import annotations

import argparse
import tempfile
import zipfile
from argparse import Namespace
from pathlib import Path
from xml.sax.saxutils import escape

from xinyu_learning_library import command_add, command_stage, load_manifest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate XinYu learning library staging.")
    parser.add_argument("--keep-temp", action="store_true")
    return parser


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


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

    rc = command_add(_add_args(root, owner_file, "owner_supplied", "owner supplied fixture"))
    if rc:
        return rc
    rc = command_add(_add_args(root, self_file, "self_found", "self found fixture"))
    if rc:
        return rc
    rc = command_add(_add_args(root, docx_file, "owner_supplied", "owner supplied docx fixture"))
    if rc:
        return rc

    manifest = load_manifest(root)
    owner_item = next(item for item in manifest if item["origin"] == "owner_supplied")
    self_item = next(item for item in manifest if item["origin"] == "self_found")
    docx_item = next(item for item in manifest if item["title"] == docx_file.name)
    docx_extract_path = root / str(docx_item.get("extracted_text_path") or "")
    docx_extract = docx_extract_path.read_text(encoding="utf-8-sig") if docx_extract_path.is_file() else ""

    rc = command_stage(_stage_args(root, str(owner_item["id"])))
    if rc:
        return rc
    rc = command_stage(_stage_args(root, str(self_item["id"])))
    if rc:
        return rc

    source_materials = (root / "memory/knowledge/source_materials.md").read_text(encoding="utf-8-sig")
    checks = {
        "owner_origin": "- learning_origin: owner_supplied" in source_materials,
        "self_origin": "- learning_origin: self_found" in source_materials,
        "owner_curated": "- comparison_status: curated" in source_materials,
        "self_not_compared": "- comparison_status: not_compared" in source_materials,
        "owner_item_id": str(owner_item["id"]) in source_materials,
        "self_item_id": str(self_item["id"]) in source_materials,
        "docx_extracted": "XinYu docx fixture memory" in docx_extract,
    }

    print("=== LEARNING LIBRARY SMOKE ===")
    print("manifest_items:", len(manifest))
    print("owner_item:", owner_item["id"])
    print("self_item:", self_item["id"])
    print("docx_item:", docx_item["id"])
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
