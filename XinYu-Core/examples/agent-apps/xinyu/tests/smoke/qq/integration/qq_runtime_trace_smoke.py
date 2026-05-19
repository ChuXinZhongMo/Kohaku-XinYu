from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import json
import time
from pathlib import Path

from xinyu_qq_gateway import (
    QQ_INBOUND_TRACE_REL,
    QQ_RICH_CONTEXT_TRACE_REL,
    QQ_STICKER_IMPORT_TRACE_REL,
    GatewayConfig,
    NativeQQGateway,
    PreparedMessage,
    ReplyTarget,
)


def _has_stage(path: Path, stage: str) -> bool:
    if not path.exists():
        return False
    lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()[-40:]
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("stage") == stage:
            return True
    return False


def main() -> int:
    failures: list[str] = []
    stage = f"state_service_smoke_{int(time.time() * 1000)}"
    gateway = NativeQQGateway(GatewayConfig(require_whitelist=False, bridge_token=""))
    target = ReplyTarget(message_kind="private", user_id="42", group_id="")
    event = {
        "post_type": "message",
        "message_type": "private",
        "message_id": "trace-smoke",
        "user_id": "42",
        "message": [{"type": "text", "data": {"text": "trace smoke"}}],
    }
    prepared = PreparedMessage(
        target=target,
        route="chat",
        payload={
            "message_id": "trace-smoke",
            "metadata": {
                "source": "qq_runtime_trace_smoke",
                "qq_rich_message": True,
                "qq_message_segments": [
                    {
                        "kind": "sticker",
                        "segment_type": "face",
                        "summary": "trace smoke sticker",
                        "mood": "happy",
                    }
                ],
            },
        },
    )
    sticker_payload = {
        "message_id": "trace-smoke",
        "file_id": "trace-smoke.webp",
        "metadata": {"source": "qq_runtime_trace_smoke", "message_id": "trace-smoke"},
    }

    gateway._trace_qq_inbound(event, stage=stage, prepared=prepared)
    gateway._trace_qq_rich_context(event, prepared, stage=stage)
    gateway._trace_sticker_import(
        event,
        target=target,
        payload=sticker_payload,
        stage=stage,
        response={"accepted": True, "imported": False, "mood": "happy"},
    )

    expected = [
        ROOT / QQ_INBOUND_TRACE_REL,
        ROOT / QQ_RICH_CONTEXT_TRACE_REL,
        ROOT / QQ_STICKER_IMPORT_TRACE_REL,
    ]
    for path in expected:
        if not _has_stage(path, stage):
            failures.append(f"missing trace stage in {path.name}")

    if failures:
        print("QQ runtime trace smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("QQ runtime trace smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
