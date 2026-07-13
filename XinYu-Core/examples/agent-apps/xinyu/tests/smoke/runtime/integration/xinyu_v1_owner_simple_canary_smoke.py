from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import asyncio
import os
import tempfile
from pathlib import Path

from xinyu_core_bridge import XinYuBridgeRuntime


def _runtime(root: Path) -> XinYuBridgeRuntime:
    return XinYuBridgeRuntime(
        xinyu_dir=root,
        turn_timeout_seconds=30,
        max_text_chars=2000,
        settle_seconds=0,
        outward_renderer=False,
        renderer_mode="off",
        autonomous_maintenance_enabled=False,
    )


def _owner_payload(text: str, *, message_type: str = "private_text") -> dict[str, object]:
    return {
        "platform": "qq",
        "message_type": message_type,
        "session_id": "qq:private:owner-smoke",
        "user_id": "owner-smoke",
        "text": text,
        "metadata": {"is_owner_user": True},
    }


async def _run() -> None:
    previous_env = {
        key: os.environ.get(key)
        for key in (
            "XINYU_V1_ENABLED",
            "XINYU_V1_OWNER_SIMPLE_CANARY",
            "XINYU_V1_SHADOW_MODE",
            "XINYU_OWNER_USER_IDS",
        )
    }
    os.environ["XINYU_V1_ENABLED"] = "1"
    os.environ["XINYU_V1_OWNER_SIMPLE_CANARY"] = "1"
    os.environ["XINYU_V1_SHADOW_MODE"] = "0"
    os.environ["XINYU_OWNER_USER_IDS"] = "owner-smoke"
    try:
        with tempfile.TemporaryDirectory(prefix="xinyu-v1-canary-smoke-") as temp_dir:
            runtime = _runtime(Path(temp_dir))
            greeting = "\u4f60\u597d"
            simple = _owner_payload(greeting)
            allowed, reasons = runtime._v1_canary_payload_allowed(simple, greeting)
            assert allowed, reasons

            complex_text = (
                "\u597d\uff0c\u90a3\u5c31\u6309\u4f60\u7684\u5207\uff0c"
                "\u7136\u540e\u91cd\u590d\u8fdb\u7a0b\u662f\u4ec0\u4e48\uff0c"
                "\u6e05\u7406\u4e00\u4e0b"
            )
            complex_payload = _owner_payload(complex_text)
            allowed, reasons = runtime._v1_canary_payload_allowed(complex_payload, str(complex_payload["text"]))
            assert not allowed, reasons

            group_payload = _owner_payload(greeting, message_type="group_text")
            group_payload["group_id"] = "123"
            allowed, reasons = runtime._v1_canary_payload_allowed(group_payload, greeting)
            assert not allowed, reasons

            attachment_payload = _owner_payload(greeting)
            attachment_payload["image_path"] = "local.png"
            allowed, reasons = runtime._v1_canary_payload_allowed(attachment_payload, greeting)
            assert not allowed, reasons

            result = await runtime.chat(simple)
            assert result["accepted"] is True
            assert result["reply"] == "\u5728"
            assert result["v1_canary"]["scope"] == "owner_private_simple_messages_only"
            assert result["v1_canary"]["route"] == "fast_path"
            assert "v1_canary_intercepted" in result["notes"]
    finally:
        for key, value in previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


if __name__ == "__main__":
    asyncio.run(_run())
    print("v1 owner simple canary smoke passed")
