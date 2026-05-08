from __future__ import annotations

import asyncio
from pathlib import Path

import xinyu_qq_attachment_resolver as attachment_resolver
from xinyu_qq_gateway import NativeQQGateway


def main() -> int:
    failures: list[str] = []

    if not attachment_resolver.looks_like_file_path(r"C:\XinYu\file.png"):
        failures.append("Windows file path detection changed")
    if not attachment_resolver.looks_like_file_path("file:///D:/XinYu/file.png"):
        failures.append("file URI detection changed")
    if attachment_resolver.looks_like_file_path("not-a-path"):
        failures.append("plain file id should not look like a path")

    learning = attachment_resolver.learning_material_from_data(
        "file",
        {"name": "report.md", "file": "abc123"},
    )
    if learning != {"segment_type": "file", "name": "report.md", "url": "", "path": "", "file_id": "abc123"}:
        failures.append(f"learning material from file id changed: {learning!r}")

    sticker = attachment_resolver.sticker_import_material_from_data(
        "mface",
        {"summary": "funny", "file": r"D:\XinYu\sticker.webp"},
    )
    expected_sticker = {
        "segment_type": "mface",
        "name": r"D:\XinYu\sticker.webp",
        "summary": "funny",
        "url": "",
        "path": r"D:\XinYu\sticker.webp",
        "file_id": "",
    }
    if sticker != expected_sticker:
        failures.append(f"sticker import material changed: {sticker!r}")

    if (
        NativeQQGateway._sticker_import_material_from_data
        is not attachment_resolver.sticker_import_material_from_data
    ):
        failures.append("gateway sticker import material helper is not a direct alias")
    if NativeQQGateway._sticker_import_material_from_data(
        "mface",
        {"summary": "funny", "file": r"D:\XinYu\sticker.webp"},
    ) != expected_sticker:
        failures.append("gateway sticker import material wrapper no longer delegates")
    if NativeQQGateway._learning_material_from_data is not attachment_resolver.learning_material_from_data:
        failures.append("gateway learning material helper is not a direct alias")
    if NativeQQGateway._learning_material_from_data("file", {"file_id": "f1"}) != {
        "segment_type": "file",
        "name": "qq-file",
        "url": "",
        "path": "",
        "file_id": "f1",
    }:
        failures.append("gateway learning material wrapper no longer delegates")
    if NativeQQGateway._looks_like_file_path is not attachment_resolver.looks_like_file_path:
        failures.append("gateway file path helper is not a direct alias")
    if not NativeQQGateway._looks_like_file_path(r"D:\XinYu\a.txt"):
        failures.append("gateway file path wrapper no longer delegates")
    if NativeQQGateway._path_from_file_uri("file:///D:/XinYu/a.txt") != Path("D:/XinYu/a.txt"):
        failures.append("gateway file URI path alias no longer delegates")
    if NativeQQGateway._onebot_local_image_file is not attachment_resolver.onebot_local_image_file:
        failures.append("gateway local image helper is not a direct method alias")
    if NativeQQGateway._onebot_local_file is not attachment_resolver.onebot_local_file:
        failures.append("gateway local file helper is not a direct method alias")
    if NativeQQGateway._resolve_sticker_import_payload is not attachment_resolver.resolve_sticker_import_payload:
        failures.append("gateway sticker import resolver is not a direct method alias")
    if NativeQQGateway._resolve_learning_ingest_payload is not attachment_resolver.resolve_learning_ingest_payload:
        failures.append("gateway learning ingest resolver is not a direct method alias")
    gateway = object.__new__(NativeQQGateway)
    learning_payload = {"file_path": r"D:\XinYu\report.md", "metadata": {"segment_type": "file"}}
    if asyncio.run(gateway._resolve_learning_ingest_payload(None, learning_payload)) != learning_payload:
        failures.append("gateway learning ingest resolver alias no longer delegates")
    if NativeQQGateway._resolve_onebot_media is not attachment_resolver.resolve_onebot_media:
        failures.append("gateway OneBot media resolver is not a direct method alias")
    if NativeQQGateway._resolve_onebot_file is not attachment_resolver.resolve_onebot_file:
        failures.append("gateway OneBot file resolver is not a direct method alias")

    if failures:
        print("XinYu QQ attachment material smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu QQ attachment material smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
