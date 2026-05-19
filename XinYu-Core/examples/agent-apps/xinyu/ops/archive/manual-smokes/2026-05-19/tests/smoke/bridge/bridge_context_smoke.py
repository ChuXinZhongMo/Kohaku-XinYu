from __future__ import annotations

import tempfile
from pathlib import Path

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from xinyu_bridge_context import prompt_context_signature


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-bridge-context-") as tmp:
        root = Path(tmp)
        rel_paths = ("config.yaml", "memory/self/core.md", "missing.md")
        first = prompt_context_signature(root, rel_paths)
        if "config.yaml:missing" not in first or "missing.md:missing" not in first:
            failures.append(f"missing file signature changed: {first}")

        core = root / "memory/self/core.md"
        core.parent.mkdir(parents=True, exist_ok=True)
        core.write_text("core\n", encoding="utf-8")
        second = prompt_context_signature(root, rel_paths)
        if second == first or "memory/self/core.md:missing" in second:
            failures.append("created context file did not change the signature")

        core.write_text("core changed\n", encoding="utf-8")
        third = prompt_context_signature(root, rel_paths)
        if third == second:
            failures.append("context file content change did not change the signature")

    if failures:
        print("Bridge context smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Bridge context smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
