from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import base64
import json
import shutil
from contextlib import contextmanager
from pathlib import Path

from xinyu_sticker_ingest import import_sticker_from_payload
MINIMAL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


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
    with _smoke_root(".sticker_ingest_smoke_runtime") as root:
        source = root / "owner-happy-good.png"
        source.write_bytes(MINIMAL_PNG)
        asset_dir = root / "stickers"
        result = import_sticker_from_payload(
            root,
            {
                "file_path": str(source),
                "file_name": "happy-good.png",
                "asset_dir": str(asset_dir),
                "allow_custom_asset_dir": True,
                "use_clip": False,
                "use_ocr": False,
            },
        )
        if not result.get("accepted") or not result.get("imported"):
            failures.append(f"local sticker was not imported: {result}")
        if int(result.get("moved") or 0) != 1:
            failures.append(f"expected one moved sticker: {result}")
        destination = asset_dir / str(result.get("destination") or "")
        if not destination.is_file():
            failures.append(f"destination missing: {destination}")
        if source.read_bytes() != MINIMAL_PNG:
            failures.append("source file should not be moved or modified")
        manifest_path = asset_dir / "manifest.generated.json"
        if not manifest_path.is_file():
            failures.append("manifest.generated.json missing")
        else:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            stickers = manifest.get("stickers", [])
            if len(stickers) != 1 or not stickers[0].get("mood") or not stickers[0].get("file"):
                failures.append(f"manifest did not record imported sticker: {manifest}")

        missing = import_sticker_from_payload(
            root,
            {
                "file_name": "missing.png",
                "asset_dir": str(asset_dir),
                "allow_custom_asset_dir": True,
                "use_clip": False,
                "use_ocr": False,
            },
        )
        if missing.get("accepted"):
            failures.append(f"missing source should be rejected: {missing}")

    if failures:
        print("xinyu_sticker_ingest_smoke: failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("xinyu_sticker_ingest_smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
