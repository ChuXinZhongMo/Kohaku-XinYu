from __future__ import annotations

import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

from xinyu_bridge_state_text import iso_from_timestamp, parse_iso, payload_path, read_text_safe, seconds_since_iso, state_field
from xinyu_core_bridge import _payload_path, _read_text_safe, _seconds_since_iso, _state_field
from xinyu_core_bridge import XinYuBridgeRuntime


def main() -> int:
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "state.md"
        if read_text_safe(path) != "":
            failures.append("missing state text should read as empty")
        path.write_text("- status: ready\n- note: hello   world\n", encoding="utf-8")
        if read_text_safe(path) != "- status: ready\n- note: hello   world\n":
            failures.append("state text read changed")
        if state_field(read_text_safe(path), "status") != "ready":
            failures.append("state field extraction changed")
        if state_field(read_text_safe(path), "note") != "hello world":
            failures.append("state field whitespace normalization changed")
        if _read_text_safe(path) != read_text_safe(path) or _state_field(read_text_safe(path), "status") != "ready":
            failures.append("core bridge state text aliases no longer delegate")

    now = datetime.now().astimezone()
    if parse_iso(now.isoformat()) is None:
        failures.append("ISO timestamp parsing changed")
    if seconds_since_iso((now - timedelta(seconds=2)).isoformat(), default=-1) < 0:
        failures.append("seconds since ISO should not be negative")
    if seconds_since_iso("bad", default=123.0) != 123.0 or _seconds_since_iso("bad", default=5.0) != 5.0:
        failures.append("seconds since ISO default changed")
    sample_timestamp = time.time()
    if parse_iso(iso_from_timestamp(sample_timestamp)) is None:
        failures.append("timestamp ISO formatting changed")
    if XinYuBridgeRuntime._iso_from_timestamp(sample_timestamp) != iso_from_timestamp(sample_timestamp):
        failures.append("core bridge timestamp ISO alias no longer delegates")
    if payload_path(r"D:\XinYu\a.txt") != Path(r"D:\XinYu\a.txt"):
        failures.append("plain payload path parsing changed")
    if _payload_path(r"D:\XinYu\a.txt") != payload_path(r"D:\XinYu\a.txt"):
        failures.append("core bridge payload path alias no longer delegates")

    if failures:
        print("XinYu bridge state text smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu bridge state text smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
