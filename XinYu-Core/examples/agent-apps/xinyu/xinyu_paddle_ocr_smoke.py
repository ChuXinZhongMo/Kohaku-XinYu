from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parent
TEST_TEXT = "\u5fc3\u7389\u8868\u60c5\u5305\u6d4b\u8bd5123"


def _find_python() -> str:
    configured = os.environ.get("XINYU_OCR_PYTHON", "").strip()
    if configured:
        return configured
    local_python = Path("D:/XinYu/Python312/python.exe")
    if local_python.is_file():
        return str(local_python)
    return sys.executable


def _find_existing_test_image() -> Path | None:
    candidates = [
        Path("D:/XinYu/ocr-test-cn.png"),
        ROOT / "runtime" / "paddle_ocr_test.png",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _create_test_image(path: Path) -> bool:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (760, 180), "white")
    draw = ImageDraw.Draw(image)
    font_paths = [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/simsun.ttc"),
    ]
    font = None
    for font_path in font_paths:
        if font_path.is_file():
            font = ImageFont.truetype(str(font_path), 42)
            break
    if font is None:
        return False
    draw.text((36, 58), TEST_TEXT, fill=(20, 42, 72), font=font)
    image.save(path)
    return True


def main() -> int:
    paddleocr = Path(os.environ.get("XINYU_PADDLEOCR_EXE", "D:/XinYu/ocr-venv/Scripts/paddleocr.exe"))
    if not paddleocr.is_file() and shutil.which("paddleocr") is None:
        print("xinyu_paddle_ocr_smoke: skipped (paddleocr executable not found)")
        return 0

    with tempfile.TemporaryDirectory(prefix="xinyu-paddle-ocr-smoke-") as tmp:
        image_path = _find_existing_test_image()
        if image_path is None:
            image_path = Path(tmp) / "paddle_ocr_test.png"
            if not _create_test_image(image_path):
                print("xinyu_paddle_ocr_smoke: skipped (Pillow or Chinese font not available)")
                return 0

        command = [_find_python(), str(ROOT / "xinyu_paddle_ocr_command.py"), str(image_path)]
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
        output = completed.stdout.strip()
        if completed.returncode != 0:
            print("xinyu_paddle_ocr_smoke: failed")
            print((completed.stderr or output).strip()[:1000])
            return 1
        if "\u5fc3\u7389" not in output or "123" not in output:
            print("xinyu_paddle_ocr_smoke: failed")
            print(f"unexpected output: {output!r}")
            return 1
    print("xinyu_paddle_ocr_smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
