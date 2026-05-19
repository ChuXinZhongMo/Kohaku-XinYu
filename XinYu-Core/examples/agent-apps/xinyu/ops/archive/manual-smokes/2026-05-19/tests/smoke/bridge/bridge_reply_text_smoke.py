from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from xinyu_bridge_reply_text import normalize_bridge_reply
from xinyu_core_bridge import _normalize_reply


def main() -> int:
    failures: list[str] = []

    if normalize_bridge_reply("\n - hello\n2. world\n") != "hello world":
        failures.append("bridge reply list/ASCII normalization changed")
    if normalize_bridge_reply("**你好**\n世界") != "你好**世界":
        failures.append("bridge reply markdown/Chinese join changed")
    if normalize_bridge_reply("alpha\r\n\r\nbeta") != "alpha beta":
        failures.append("bridge reply CRLF folding changed")
    if normalize_bridge_reply("   \n\t") != "":
        failures.append("bridge reply empty fallback changed")
    if _normalize_reply("• one\n• two") != normalize_bridge_reply("• one\n• two"):
        failures.append("core bridge normalize reply alias no longer delegates")

    if failures:
        print("XinYu bridge reply text smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu bridge reply text smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
