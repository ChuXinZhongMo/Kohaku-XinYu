from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from xinyu_bridge_promises import compact_promise_text
from xinyu_core_bridge import XinYuBridgeRuntime


def main() -> int:
    failures: list[str] = []

    text = ' A\uFF0C B\u3002 C\uFF01 D\uFF1F E\u3001 F\uFF1B G\uFF1A <H>\u300AI\u300B"J\'K`L. '
    if compact_promise_text(text) != "abcdefghijkl":
        failures.append("promise text separator compaction changed")

    if compact_promise_text(None) != "":
        failures.append("promise text safe_str fallback changed")

    if XinYuBridgeRuntime._compact_promise_text(text) != compact_promise_text(text):
        failures.append("core bridge promise compact alias no longer delegates")

    if failures:
        print("XinYu bridge promises smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu bridge promises smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
