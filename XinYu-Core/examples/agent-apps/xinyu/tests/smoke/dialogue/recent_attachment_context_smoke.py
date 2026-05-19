from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import json
import tempfile
from pathlib import Path

from xinyu_recent_attachment_context import (
    load_recent_attachment_context,
    record_recent_attachment_context,
)


def main() -> int:
    failures: list[str] = []
    scratch = ROOT / "runtime" / "recent_attachment_context_smoke_tmp"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="xinyu-recent-attachment-", dir=str(scratch)) as tmp:
        root = Path(tmp)
        extracted = root / "runtime/attachments/extracted.txt"
        extracted.parent.mkdir(parents=True, exist_ok=True)
        extracted.write_text("owner attachment text: XinYu should remember this for the next question.\n", encoding="utf-8")

        payload = {
            "session_id": "qq:private:42",
            "message_id": "msg-1",
            "reason": "owner supplied QQ file",
            "metadata": {"message_id": "msg-1", "segment_type": "file"},
        }
        result = {
            "extracted_text_path": "runtime/attachments/extracted.txt",
            "learning_item_id": "learn-1",
            "material_id": "mat-1",
            "title": "owner-note.txt",
        }
        if not record_recent_attachment_context(root, payload, result):
            failures.append("record_recent_attachment_context returned false")

        context_dir = root / "runtime/recent_attachment_context"
        context_files = list(context_dir.glob("*.json"))
        if len(context_files) != 1:
            failures.append(f"expected one context json, got {len(context_files)}")
        else:
            data = json.loads(context_files[0].read_text(encoding="utf-8-sig"))
            attachments = data.get("attachments")
            if not isinstance(attachments, list) or len(attachments) != 1:
                failures.append("context json should contain one attachment")
            elif attachments[0].get("learning_item_id") != "learn-1":
                failures.append("context json should preserve learning_item_id")

        context = load_recent_attachment_context(root, "qq:private:42", "帮我总结刚才那个附件")
        if "Recent readable attachment context" not in context or "owner attachment text" not in context:
            failures.append("recent attachment prompt context did not include stored text")

        second_result = dict(result)
        second_result["learning_item_id"] = "learn-2"
        if not record_recent_attachment_context(root, payload, second_result):
            failures.append("second record should still succeed")
        if len(list(context_dir.glob("*.tmp"))) != 0:
            failures.append("state_service atomic write should not leave temp files")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS recent_attachment_context_smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
