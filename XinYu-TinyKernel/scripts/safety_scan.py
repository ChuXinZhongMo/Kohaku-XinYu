from __future__ import annotations

import argparse
import re
from pathlib import Path


SECRET_PATTERNS = {
    "api_key": re.compile(r"(?i)(api[_-]?key|token|secret|cookie)\s*[:=]\s*[A-Za-z0-9_\-\.]{8,}"),
    "openai_key": re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),
    "raw_xinyu_path": re.compile(r"[A-Za-z]:\\XinYu\\(?!XinYu-TinyKernel\\)"),
    "raw_user_path": re.compile(r"[A-Za-z]:\\Users\\"),
    "long_numeric_id": re.compile(r"\b\d{8,}\b"),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="data\\sft\\xinyu_tinykernel_v0.jsonl")
    args = parser.parse_args()
    path = Path(args.path)
    text = path.read_text(encoding="utf-8-sig")
    failures: list[str] = []
    for name, pattern in SECRET_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            failures.append(f"{name}: {len(matches)}")
    print(f"scanned={path}")
    if failures:
        for failure in failures:
            print("FAIL " + failure)
        return 1
    print("safety_scan_ok=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
