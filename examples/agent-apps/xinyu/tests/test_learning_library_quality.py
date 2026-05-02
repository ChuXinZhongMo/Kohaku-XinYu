from __future__ import annotations

import xinyu_learning_library as library


def test_unknown_extension_text_file_is_extracted(tmp_path) -> None:
    path = tmp_path / "Dockerfile"
    path.write_text("FROM python:3.12\nCOPY . /app\n", encoding="utf-8")

    assert library.can_extract_local_text(path)
    assert "FROM python" in library.extract_text_from_bytes(path.read_bytes(), path.name, "application/octet-stream")


def test_unknown_binary_file_is_not_extracted() -> None:
    data = b"\x00\x01\x02\x03" * 64

    assert not library.bytes_look_like_text(data)
    assert library.extract_text_from_bytes(data, "blob.bin", "application/octet-stream") == ""


def test_image_ocr_garbled_text_is_not_extracted(monkeypatch) -> None:
    bad_text = ("\ufffd\ufffd " * 80).strip()

    monkeypatch.setattr(
        library,
        "extract_ocr_text_from_bytes",
        lambda data, filename, force=False: bad_text,
    )

    assert library.extract_text_from_bytes(b"\xff\xd8\xfffake", "bad.jpg", "image/jpeg") == ""


def test_garbled_image_url_is_not_registered_as_readable(monkeypatch, tmp_path) -> None:
    bad_text = ("\ufffd\ufffd " * 80).strip()

    monkeypatch.setattr(
        library,
        "download_bytes",
        lambda url, max_bytes: (b"\xff\xd8\xfffake", url, "image/jpeg"),
    )
    monkeypatch.setattr(
        library,
        "extract_text_from_bytes",
        lambda data, filename, content_type: bad_text,
    )

    metadata = library.add_url_material(
        root=tmp_path,
        url="https://example.com/bad.jpg",
        origin="owner_supplied",
        reason="garbled image OCR regression",
        question_id="q-quality",
    )

    assert metadata["extracted_text_path"] == ""
    assert not (tmp_path / str(metadata["item_dir"]) / "extracted_text.md").exists()
