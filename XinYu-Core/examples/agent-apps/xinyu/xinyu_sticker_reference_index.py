from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_clip_command import DEFAULT_MODEL, DEFAULT_PRETRAINED
from xinyu_sticker_pack import SUPPORTED_STICKER_SUFFIXES, canonical_mood, shared_asset_sticker_dir


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


REFERENCE_DIR_NAME = "参考图"
LEGACY_REFERENCE_DIR_NAME = ".references"
REFERENCE_INDEX_NAME = "reference_index.generated.json"


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _workspace_root(path: Path) -> Path | None:
    resolved = path.resolve()
    for candidate in (resolved, *resolved.parents):
        if candidate.name == "XinYu":
            return candidate
    return None


def default_vision_python(xinyu_dir: Path) -> Path | None:
    workspace = _workspace_root(xinyu_dir)
    if workspace is None:
        return None
    candidates = (
        workspace / "runtime" / "deps" / "vision-venv" / "Scripts" / "python.exe",
        workspace / "vision-venv" / "Scripts" / "python.exe",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _is_running_in_vision_env() -> bool:
    try:
        import open_clip  # noqa: F401
        import torch  # noqa: F401
    except Exception:
        return False
    return True


def _reference_images(references_dir: Path) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = {}
    if not references_dir.exists():
        return groups
    for mood_dir in sorted(references_dir.iterdir(), key=lambda item: item.name.lower()):
        if not mood_dir.is_dir() or mood_dir.name.startswith("."):
            continue
        mood = canonical_mood(mood_dir.name, "")
        if not mood:
            continue
        images = [
            path.resolve()
            for path in sorted(mood_dir.rglob("*"), key=lambda item: item.as_posix().lower())
            if path.is_file() and path.suffix.lower() in SUPPORTED_STICKER_SUFFIXES
        ]
        if images:
            groups.setdefault(mood, []).extend(images)
    return groups


def build_reference_index(
    references_dir: Path,
    *,
    model_name: str = DEFAULT_MODEL,
    pretrained: str = DEFAULT_PRETRAINED,
    device: str = "",
    batch_size: int = 16,
) -> dict[str, Any]:
    references_dir = references_dir.resolve()
    groups = _reference_images(references_dir)
    if not groups:
        return {
            "version": 1,
            "generated_by": "xinyu_sticker_reference_index",
            "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "model": model_name,
            "pretrained": pretrained,
            "device": device or "",
            "references_dir": str(references_dir),
            "items": [],
        }
    import torch
    import open_clip
    from PIL import Image

    selected_device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    model, _, preprocess = open_clip.create_model_and_transforms(
        model_name,
        pretrained=pretrained,
        device=selected_device,
    )
    model.eval()

    items: list[dict[str, Any]] = []
    for mood, paths in groups.items():
        vectors = []
        effective_batch_size = max(1, int(batch_size or 1))
        for start in range(0, len(paths), effective_batch_size):
            batch_paths = paths[start : start + effective_batch_size]
            images = []
            for image_path in batch_paths:
                with Image.open(image_path) as image:
                    images.append(preprocess(image.convert("RGB")))
            image_tensor = torch.stack(images, dim=0).to(selected_device)
            with torch.no_grad():
                features = model.encode_image(image_tensor)
                features /= features.norm(dim=-1, keepdim=True)
            vectors.append(features.detach().cpu())
        if not vectors:
            continue
        stacked = torch.cat(vectors, dim=0)
        centroid = stacked.mean(dim=0)
        centroid /= centroid.norm(dim=-1, keepdim=True)
        items.append(
            {
                "mood": mood,
                "count": len(paths),
                "files": [path.relative_to(references_dir).as_posix() for path in paths],
                "embedding": [round(float(value), 8) for value in centroid.tolist()],
            }
        )

    return {
        "version": 1,
        "generated_by": "xinyu_sticker_reference_index",
        "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model": model_name,
        "pretrained": pretrained,
        "device": selected_device,
        "references_dir": str(references_dir),
        "items": sorted(items, key=lambda item: _safe_str(item.get("mood")).lower()),
    }


def write_reference_index(base: Path, index: dict[str, Any], output: Path | None = None) -> Path:
    path = output or (base / REFERENCE_INDEX_NAME)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def default_references_dir(base: Path) -> Path:
    preferred = base / REFERENCE_DIR_NAME
    legacy = base / LEGACY_REFERENCE_DIR_NAME
    if preferred.exists() or not legacy.exists():
        return preferred
    return legacy


def _delegate_to_vision_python(argv: list[str], vision_python: Path) -> int:
    import subprocess

    completed = subprocess.run(
        [str(vision_python), str(Path(__file__).resolve()), *argv, "--no-delegate"],
        check=False,
    )
    return int(completed.returncode)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build XinYu sticker CLIP reference image index.")
    parser.add_argument("--xinyu-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--asset-dir", type=Path, default=None)
    parser.add_argument("--references-dir", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--pretrained", default=DEFAULT_PRETRAINED)
    parser.add_argument("--device", default="")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--vision-python", type=Path, default=None)
    parser.add_argument("--no-delegate", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    base = args.asset_dir or shared_asset_sticker_dir(args.xinyu_dir)
    if base is None:
        raise SystemExit("Could not resolve shared sticker asset directory.")
    base = base.resolve()
    references_dir = (args.references_dir or default_references_dir(base)).resolve()
    references_dir.mkdir(parents=True, exist_ok=True)
    has_references = bool(_reference_images(references_dir))

    if has_references and not args.no_delegate and not _is_running_in_vision_env():
        vision_python = args.vision_python or default_vision_python(args.xinyu_dir)
        if vision_python is not None:
            forwarded = list(argv if argv is not None else sys.argv[1:])
            return _delegate_to_vision_python(forwarded, vision_python)

    try:
        index = build_reference_index(
            references_dir,
            model_name=args.model,
            pretrained=args.pretrained,
            device=args.device,
            batch_size=args.batch_size,
        )
    except Exception as exc:
        print(f"xinyu_sticker_reference_index: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    output = write_reference_index(base, index, args.output)
    result = {
        "references_dir": str(references_dir),
        "output": str(output),
        "items": len(index.get("items", [])),
        "image_count": sum(int(item.get("count") or 0) for item in index.get("items", []) if isinstance(item, dict)),
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            "xinyu_sticker_reference_index: "
            f"items={result['items']} images={result['image_count']} output={output}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
