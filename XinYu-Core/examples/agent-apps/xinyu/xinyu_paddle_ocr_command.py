from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


DEFAULT_PADDLEOCR_EXE = Path("D:/XinYu/ocr-venv/Scripts/paddleocr.exe")
DEFAULT_TIMEOUT_SECONDS = 160


def _default_tmp_root() -> Path:
    return Path(__file__).resolve().parent / "runtime" / "paddle_ocr_tmp"


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _paddleocr_executable() -> str:
    configured = os.environ.get("XINYU_PADDLEOCR_EXE", "").strip()
    if configured:
        return configured
    if DEFAULT_PADDLEOCR_EXE.is_file():
        return str(DEFAULT_PADDLEOCR_EXE)
    found = shutil.which("paddleocr")
    return found or str(DEFAULT_PADDLEOCR_EXE)


def _timeout_seconds() -> int:
    try:
        return max(15, int(os.environ.get("XINYU_PADDLEOCR_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))))
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS


def _score_text(value: str) -> int:
    score = 0
    for char in value:
        if "\u4e00" <= char <= "\u9fff":
            score += 4
        elif char.isalnum():
            score += 1
        elif char in "\ufffd?":
            score -= 4
    for marker in ("Ã", "Â", "å", "ç", "è", "é", "蹇", "鐨", "琛", "鍖", "呮", "儏"):
        score -= value.count(marker) * 3
    return score


def _repair_mojibake(value: str) -> str:
    candidates = [value]
    for encoding in ("latin1", "cp1252", "gbk", "cp936"):
        try:
            candidates.append(value.encode(encoding).decode("utf-8"))
        except UnicodeError:
            continue
    return max(candidates, key=_score_text).strip()


def _collect_texts(data: Any) -> list[str]:
    texts: list[str] = []
    if isinstance(data, dict):
        rec_texts = data.get("rec_texts")
        if isinstance(rec_texts, list):
            texts.extend(str(item) for item in rec_texts if str(item).strip())
        for key in ("result", "res", "data"):
            nested = data.get(key)
            if nested is not None:
                texts.extend(_collect_texts(nested))
    elif isinstance(data, list):
        for item in data:
            texts.extend(_collect_texts(item))
    return texts


def _read_saved_texts(output_dir: Path) -> list[str]:
    texts: list[str] = []
    for result_path in sorted(output_dir.rglob("*_res.json")):
        try:
            data = json.loads(result_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        texts.extend(_collect_texts(data))
    deduped: list[str] = []
    seen: set[str] = set()
    for text in texts:
        repaired = _repair_mojibake(text)
        if repaired and repaired not in seen:
            deduped.append(repaired)
            seen.add(repaired)
    return deduped


def _build_command(input_path: Path, output_dir: Path) -> list[str]:
    command = [
        _paddleocr_executable(),
        "ocr",
        "-i",
        str(input_path),
        "--device",
        os.environ.get("XINYU_PADDLEOCR_DEVICE", "cpu"),
        "--enable_mkldnn",
        os.environ.get("XINYU_PADDLEOCR_ENABLE_MKLDNN", "False"),
        "--use_doc_orientation_classify",
        "False",
        "--use_doc_unwarping",
        "False",
        "--use_textline_orientation",
        "False",
        "--text_detection_model_name",
        os.environ.get("XINYU_PADDLEOCR_DET_MODEL", "PP-OCRv5_mobile_det"),
        "--text_recognition_model_name",
        os.environ.get("XINYU_PADDLEOCR_REC_MODEL", "PP-OCRv5_mobile_rec"),
        "--save_path",
        str(output_dir),
    ]
    if _truthy(os.environ.get("XINYU_PADDLEOCR_VERBOSE", "")):
        command.append("--show_log")
    return command


def run_ocr(input_path: Path) -> list[str]:
    if not input_path.is_file():
        raise FileNotFoundError(str(input_path))
    tmp_root = Path(os.environ.get("XINYU_PADDLEOCR_TMP_DIR", "") or _default_tmp_root())
    tmp_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="xinyu-paddle-ocr-", dir=tmp_root) as tmp:
        output_dir = Path(tmp)
        completed = subprocess.run(
            _build_command(input_path, output_dir),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_timeout_seconds(),
        )
        if completed.returncode != 0:
            stderr = (completed.stderr or completed.stdout).strip().replace("\n", " ")[:500]
            raise RuntimeError(stderr or f"paddleocr exited with {completed.returncode}")
        return _read_saved_texts(output_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run XinYu's local PaddleOCR command wrapper.")
    parser.add_argument("input_path", help="Image or document path to OCR.")
    args = parser.parse_args(argv)
    try:
        texts = run_ocr(Path(args.input_path))
    except Exception as exc:
        print(f"xinyu_paddle_ocr_command: {exc}", file=sys.stderr)
        return 1
    if texts:
        sys.stdout.write("\n".join(texts))
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
