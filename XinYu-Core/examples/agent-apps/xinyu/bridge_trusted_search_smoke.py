from __future__ import annotations

from xinyu_bridge_trusted_search import trusted_public_search_task_allowed
from xinyu_core_bridge import (
    TRUSTED_CODEX_LOCAL_BLOCK_MARKERS,
    TRUSTED_CODEX_LOCAL_ENGLISH_BLOCK_MARKERS,
    TRUSTED_CODEX_LOCAL_PATH_RE,
    TRUSTED_CODEX_PUBLIC_SEARCH_MARKERS,
    XinYuBridgeRuntime,
)


def _allowed(task_text: str) -> bool:
    return trusted_public_search_task_allowed(
        task_text,
        public_search_markers=TRUSTED_CODEX_PUBLIC_SEARCH_MARKERS,
        local_block_markers=TRUSTED_CODEX_LOCAL_BLOCK_MARKERS,
        local_path_pattern=TRUSTED_CODEX_LOCAL_PATH_RE,
        local_english_block_markers=TRUSTED_CODEX_LOCAL_ENGLISH_BLOCK_MARKERS,
    )


def main() -> int:
    failures: list[str] = []

    if not _allowed("search public web sources for PyMuPDF docs"):
        failures.append("trusted public search task was not allowed")
    if _allowed(r"search public web sources and read D:\XinYu\config.yaml"):
        failures.append("trusted local path task was allowed")
    if _allowed("search public web sources for localconfig"):
        failures.append("trusted local config task was allowed")
    if _allowed("please summarize this normal chat"):
        failures.append("non-search task was allowed")

    if XinYuBridgeRuntime._trusted_public_search_task_allowed("search public web sources for PyMuPDF docs") is not True:
        failures.append("core bridge trusted search positive alias changed")
    if XinYuBridgeRuntime._trusted_public_search_task_allowed(r"search and read D:\XinYu\config.yaml") is not False:
        failures.append("core bridge trusted search local-path alias changed")

    if failures:
        print("XinYu bridge trusted search smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu bridge trusted search smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
