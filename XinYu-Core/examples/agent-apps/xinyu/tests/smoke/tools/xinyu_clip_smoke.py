from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import tempfile
from pathlib import Path

from xinyu_clip_command import classify_image


def main() -> int:
    try:
        from PIL import Image, ImageDraw
        import torch
        import open_clip
    except Exception as exc:
        print(f"xinyu_clip_smoke: skipped ({type(exc).__name__}: {exc})")
        return 0

    with tempfile.TemporaryDirectory(prefix="xinyu-clip-smoke-") as tmp:
        image_path = Path(tmp) / "happy-sticker.png"
        image = Image.new("RGB", (224, 224), "#fff7fb")
        draw = ImageDraw.Draw(image)
        draw.ellipse((58, 58, 88, 88), fill="#ff8abb")
        draw.ellipse((136, 58, 166, 88), fill="#ff8abb")
        draw.arc((72, 82, 152, 164), start=10, end=170, fill="#6b3150", width=8)
        image.save(image_path)

        try:
            result = classify_image(image_path, top_k=3)
        except Exception as exc:
            print(f"xinyu_clip_smoke: failed classify {type(exc).__name__}: {exc}")
            return 1
        if not result.get("top_mood") or not result.get("scores"):
            print(f"xinyu_clip_smoke: failed empty result {result}")
            return 1
        print(
            "xinyu_clip_smoke: ok "
            f"torch={torch.__version__} "
            f"open_clip={getattr(open_clip, '__version__', 'unknown')} "
            f"device={result.get('device')} "
            f"top={result.get('top_mood')}:{result.get('confidence')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
