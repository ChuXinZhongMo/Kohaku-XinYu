from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from v1_canary_gate import payload_has_attachment_signal
from xinyu_core_bridge import _payload_has_attachment_signal


def main() -> int:
    failures: list[str] = []

    if _payload_has_attachment_signal is not payload_has_attachment_signal:
        failures.append("core bridge attachment signal alias no longer delegates")
    if not payload_has_attachment_signal({"image_path": "D:/XinYu/runtime/test.png"}):
        failures.append("top-level image path attachment signal changed")
    if not payload_has_attachment_signal({"metadata": {"attachments": [{"name": "a.txt"}]}}):
        failures.append("metadata attachments signal changed")
    if payload_has_attachment_signal({"image_path": "", "metadata": {"file": ""}}):
        failures.append("empty attachment fields should not count as attachment signal")
    if payload_has_attachment_signal({"text": "hello"}):
        failures.append("plain text payload should not count as attachment signal")

    if failures:
        print("XinYu bridge payload attachment smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu bridge payload attachment smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
