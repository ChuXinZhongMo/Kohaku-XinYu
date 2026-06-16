from __future__ import annotations

import importlib.util
import io
import zipfile

import pytest

import xinyu_image_context as image_context
import xinyu_learning_library as library

# The markitdown fallback path does a real `from markitdown import StreamInfo`
# (xinyu_learning_library.py), so the fallback cases need the package installed
# even though the converter instance is monkeypatched. Skip just those when it's
# absent — the non-markitdown cases in this module still run.
requires_markitdown = pytest.mark.skipif(
    importlib.util.find_spec("markitdown") is None,
    reason="markitdown not installed",
)


def test_unknown_extension_text_file_is_extracted(tmp_path) -> None:
    path = tmp_path / "Dockerfile"
    path.write_text("FROM python:3.12\nCOPY . /app\n", encoding="utf-8")

    assert library.can_extract_local_text(path)
    assert "FROM python" in library.extract_text_from_bytes(path.read_bytes(), path.name, "application/octet-stream")


def test_unknown_binary_file_is_not_extracted() -> None:
    data = b"\x00\x01\x02\x03" * 64

    assert not library.bytes_look_like_text(data)
    assert library.extract_text_from_bytes(data, "blob.bin", "application/octet-stream") == ""


@requires_markitdown
def test_markitdown_fallback_reads_supported_archive(monkeypatch) -> None:
    class Result:
        markdown = "XinYu archive fallback text"

    class FakeMarkItDown:
        def convert_stream(self, stream, *, stream_info=None):
            assert stream_info.extension == ".zip"
            assert stream_info.filename == "bundle.zip"
            assert stream.read(2) == b"PK"
            return Result()

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("note.txt", "XinYu archive note")

    monkeypatch.setattr(library, "_MARKITDOWN_INSTANCE", FakeMarkItDown())
    monkeypatch.setattr(library, "_MARKITDOWN_UNAVAILABLE", False)

    assert (
        library.extract_text_from_bytes(buffer.getvalue(), "bundle.zip", "application/zip")
        == "XinYu archive fallback text"
    )


@requires_markitdown
def test_markitdown_fallback_uses_content_type_for_hidden_qq_xls_name(monkeypatch) -> None:
    class Result:
        markdown = "XinYu legacy xls fallback text"

    class FakeMarkItDown:
        def convert_stream(self, stream, *, stream_info=None):
            assert stream_info.extension == ".xls"
            assert stream_info.filename == "qqdownloadftnv5"
            assert stream.read(4) == b"\xd0\xcf\x11\xe0"
            return Result()

    monkeypatch.setattr(library, "_MARKITDOWN_INSTANCE", FakeMarkItDown())
    monkeypatch.setattr(library, "_MARKITDOWN_UNAVAILABLE", False)

    data = b"\xd0\xcf\x11\xe0" + (b"\x00\x01\x02\x03" * 32)
    assert (
        library.extract_text_from_bytes(data, "qqdownloadftnv5", "application/vnd.ms-excel")
        == "XinYu legacy xls fallback text"
    )


def test_image_ocr_garbled_text_is_not_extracted(monkeypatch) -> None:
    bad_text = ("\ufffd\ufffd " * 80).strip()

    monkeypatch.setattr(
        library,
        "extract_ocr_text_from_bytes",
        lambda data, filename, force=False: bad_text,
    )

    assert library.extract_text_from_bytes(b"\xff\xd8\xfffake", "bad.jpg", "image/jpeg") == ""


def test_prepared_ocr_input_path_resizes_large_image(tmp_path, monkeypatch) -> None:
    Image = pytest.importorskip("PIL.Image")
    image_path = tmp_path / "huge.png"
    Image.new("RGB", (2400, 900), "white").save(image_path)
    monkeypatch.setenv("XINYU_OCR_MAX_IMAGE_DIMENSION", "600")

    with library.prepared_ocr_input_path(image_path) as prepared:
        assert prepared != image_path
        assert prepared.is_file()
        with Image.open(prepared) as resized:
            assert max(resized.size) <= 600
        prepared_path = prepared

    assert not prepared_path.exists()


def test_image_vision_data_uri_compresses_large_static_image(tmp_path, monkeypatch) -> None:
    Image = pytest.importorskip("PIL.Image")
    image_path = tmp_path / "huge.png"
    Image.new("RGB", (2200, 1200), (120, 160, 220)).save(image_path)
    monkeypatch.setenv("XINYU_IMAGE_VISION_MAX_BYTES", "25000")
    monkeypatch.setenv("XINYU_IMAGE_VISION_MAX_DIMENSION", "900")

    data_uri, error, notes = image_context._image_data_uri(image_path, {"file_name": image_path.name})

    assert error == ""
    assert data_uri.startswith("data:image/jpeg;base64,")
    assert any(note.startswith("animated_single_frame") for note in notes)
    assert any(note.startswith("animated_compressed_for_vision:") for note in notes)


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
