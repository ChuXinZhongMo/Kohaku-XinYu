from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import json
import shutil
from contextlib import contextmanager
from pathlib import Path

import xinyu_sticker_import as sticker_import
from xinyu_sticker_import import (
    apply_import_plan,
    build_import_plan,
    build_semantic_index_plan,
    ensure_unsorted_dir,
    write_semantic_index,
)
from xinyu_sticker_pack import mood_dir_name


@contextmanager
def _smoke_root(name: str):
    root = ROOT / "runtime" / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main() -> int:
    failures: list[str] = []
    with _smoke_root(".sticker_import_smoke_runtime") as root:
        ensure_unsorted_dir(root)
        source = root / "待分类" / "哈哈好耶.png"
        source.write_bytes(b"fake png")
        unclear = root / "待分类" / "abc123.webp"
        unclear.write_bytes(b"fake webp")

        plan = build_import_plan(root)
        if len(plan) != 2:
            failures.append(f"expected 2 plan items, got {len(plan)}")
        happy = next((item for item in plan if item.source.name == "哈哈好耶.png"), None)
        if happy is None or happy.mood not in {"happy", "laugh"}:
            failures.append(f"happy sticker was not inferred: {happy}")
        low = next((item for item in plan if item.source.name == "abc123.webp"), None)
        if low is None or low.mood != "unclear":
            failures.append(f"unclear sticker should stay in unclear: {low}")

        result = apply_import_plan(root, plan)
        if int(result.get("moved") or 0) != 2:
            failures.append(f"apply did not move both files: {result}")
        if not any((root / mood_dir_name(mood) / "哈哈好耶.png").exists() for mood in ("happy", "laugh")):
            failures.append("semantic sticker destination missing")
        manifest_path = root / "manifest.generated.json"
        if not manifest_path.exists():
            failures.append("generated manifest missing")
        else:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            if len(data.get("stickers", [])) != 2:
                failures.append("generated manifest did not record moved stickers")
            meanings = [item.get("meaning", "") for item in data.get("stickers", []) if isinstance(item, dict)]
            if not any("开心" in meaning or "大笑" in meaning for meaning in meanings):
                failures.append("generated manifest did not write readable semantics")

        index_plan = build_semantic_index_plan(root)
        if not index_plan:
            failures.append("semantic index plan did not include existing classified stickers")
        index_result = write_semantic_index(root, index_plan)
        if int(index_result.get("indexed") or 0) < 2:
            failures.append(f"semantic index did not write existing stickers: {index_result}")
        moved_semantic = next((path for mood in ("happy", "laugh") if (path := root / mood_dir_name(mood) / "哈哈好耶.png").exists()), None)
        if moved_semantic is not None:
            corrected = root / mood_dir_name("deadpan") / moved_semantic.name
            corrected.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(moved_semantic), str(corrected))
            corrected_plan = build_semantic_index_plan(root)
            corrected_item = next((item for item in corrected_plan if item.destination == corrected), None)
            if corrected_item is None or not corrected_item.confirmed or corrected_item.previous_mood not in {"happy", "laugh"}:
                failures.append(f"manual correction was not detected: {corrected_item}")
            corrected_result = write_semantic_index(root, corrected_plan)
            if int(corrected_result.get("corrections") or 0) < 1:
                failures.append(f"correction index did not record folder move: {corrected_result}")
            corrections_path = root / "corrections.generated.json"
            expected_file = f"{mood_dir_name('deadpan')}/哈哈好耶.png"
            if not corrections_path.exists():
                failures.append("corrections.generated.json missing")
            else:
                corrections = json.loads(corrections_path.read_text(encoding="utf-8"))
                if not any(item.get("file") == expected_file for item in corrections.get("items", [])):
                    failures.append("corrections manifest did not contain moved sticker")
            manifest = json.loads((root / "manifest.generated.json").read_text(encoding="utf-8"))
            confirmed = next((item for item in manifest.get("stickers", []) if item.get("file") == expected_file), None)
            if not confirmed or not confirmed.get("confirmed") or confirmed.get("weight") != 3 or not confirmed.get("auto_send"):
                failures.append(f"confirmed manifest fields missing: {confirmed}")

        ocr_source = root / "待分类" / "text-only.png"
        ocr_source.write_bytes(b"fake png")
        old_ocr = sticker_import._run_ocr_for_sources
        try:
            sticker_import._run_ocr_for_sources = lambda sources: {
                str(path.resolve()): {"texts": ["哈哈 好耶"], "error": ""} for path in sources
            }
            ocr_plan = build_import_plan(root, use_ocr=True)
        finally:
            sticker_import._run_ocr_for_sources = old_ocr
        ocr_item = next((item for item in ocr_plan if item.source.name == "text-only.png"), None)
        if ocr_item is None or not ocr_item.ocr_inferred or not ocr_item.ocr_text or not ocr_item.text_keywords:
            failures.append(f"OCR semantics were not merged into plan item: {ocr_item}")
        if ocr_item is not None and ocr_item.mood not in {"happy", "laugh", "cheer"}:
            failures.append(f"OCR text did not influence mood: {ocr_item}")

    if failures:
        print("xinyu_sticker_import_smoke: failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("xinyu_sticker_import_smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
