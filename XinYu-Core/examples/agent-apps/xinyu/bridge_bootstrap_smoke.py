from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from xinyu_bridge_bootstrap import ensure_repo_src, load_local_env
from xinyu_core_bridge import _ensure_repo_src, _load_local_env


def main() -> int:
    failures: list[str] = []
    old_path = list(sys.path)
    old_new = os.environ.get("XINYU_BOOTSTRAP_SMOKE_NEW")
    old_existing = os.environ.get("XINYU_BOOTSTRAP_SMOKE_EXISTING")

    try:
        with TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            xinyu_dir = root / "examples" / "agent-apps" / "xinyu"
            xinyu_dir.mkdir(parents=True)
            (xinyu_dir / "xinyu.local.env").write_text(
                "\n".join(
                    [
                        "# ignored",
                        "XINYU_BOOTSTRAP_SMOKE_NEW='from_file'",
                        "XINYU_BOOTSTRAP_SMOKE_EXISTING=from_file",
                        "malformed",
                    ]
                ),
                encoding="utf-8",
            )
            os.environ.pop("XINYU_BOOTSTRAP_SMOKE_NEW", None)
            os.environ["XINYU_BOOTSTRAP_SMOKE_EXISTING"] = "already_set"

            load_local_env(xinyu_dir)
            if os.environ.get("XINYU_BOOTSTRAP_SMOKE_NEW") != "from_file":
                failures.append("local env loader did not import new key")
            if os.environ.get("XINYU_BOOTSTRAP_SMOKE_EXISTING") != "already_set":
                failures.append("local env loader overwrote existing key")

            src_root = ensure_repo_src(xinyu_dir)
            if src_root != root / "src":
                failures.append(f"repo src root changed: {src_root}")
            if sys.path[0] != str(src_root):
                failures.append("repo src root was not prepended to sys.path")

        if _load_local_env is not load_local_env or _ensure_repo_src is not ensure_repo_src:
            failures.append("core bridge bootstrap aliases no longer delegate")
    finally:
        sys.path[:] = old_path
        for key, old_value in (
            ("XINYU_BOOTSTRAP_SMOKE_NEW", old_new),
            ("XINYU_BOOTSTRAP_SMOKE_EXISTING", old_existing),
        ):
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value

    if failures:
        print("XinYu bridge bootstrap smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu bridge bootstrap smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
