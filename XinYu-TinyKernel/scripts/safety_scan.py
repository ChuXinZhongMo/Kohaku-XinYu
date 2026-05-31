from __future__ import annotations

import argparse
import re
from pathlib import Path


SECRET_PATTERNS = {
    "api_key_assignment": re.compile(r"(?i)(api[_-]?key|token|secret|cookie)\s*[:=]\s*[A-Za-z0-9_\-\.]{8,}"),
    "openai_key": re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),
    "raw_xinyu_path": re.compile(r"[A-Za-z]:(?:\\\\|\\)XinYu(?:\\\\|\\|\b)"),
    "raw_user_path": re.compile(r"[A-Za-z]:(?:\\\\|\\)Users(?:\\\\|\\|\b)"),
    "env_file": re.compile(r"(?i)(^|[\\/\s])\.env([\\/\s]|$)"),
    "bridge_token_file": re.compile(r"(?i)\.xinyu_bridge_token"),
    "qq_like_id": re.compile(r"(?i)\b(qq|uin|group_id|user_id)\s*[:=]\s*\d{5,}"),
}

TEXT_SUFFIXES = {
    ".json",
    ".jsonl",
    ".md",
    ".txt",
    ".py",
    ".ps1",
    ".yaml",
    ".yml",
}

SKIP_DIRS = {".git", ".venv", ".venv-train", "__pycache__", "node_modules", "models", "adapters"}


def _iter_scan_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    files: list[Path] = []
    for item in path.rglob("*"):
        if not item.is_file():
            continue
        if any(part in SKIP_DIRS for part in item.parts):
            continue
        if item.suffix.lower() in TEXT_SUFFIXES:
            files.append(item)
    return files


def _scan_text(path: Path, text: str) -> list[str]:
    failures: list[str] = []
    for name, pattern in SECRET_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            failures.append(f"{path}: {name}: {len(matches)}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", default=["data\\sft\\xinyu_tinykernel_v0.jsonl"])
    args = parser.parse_args()

    failures: list[str] = []
    scanned = 0
    for raw_path in args.paths:
        path = Path(raw_path)
        if not path.exists():
            failures.append(f"{path}: missing")
            continue
        for file_path in _iter_scan_files(path):
            scanned += 1
            try:
                text = file_path.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                failures.append(f"{file_path}: not utf-8 text")
                continue
            failures.extend(_scan_text(file_path, text))

    print(f"scanned_files={scanned}")
    if failures:
        for failure in failures[:50]:
            print("FAIL " + failure)
        print(f"failure_count={len(failures)}")
        return 1
    print("safety_scan_ok=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
