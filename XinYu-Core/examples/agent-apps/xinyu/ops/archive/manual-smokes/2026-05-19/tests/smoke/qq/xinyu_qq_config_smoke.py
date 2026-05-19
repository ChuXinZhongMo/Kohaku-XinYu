from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

import tempfile
from pathlib import Path

from xinyu_qq_config import (
    GatewayConfig,
    derive_codex_execute_url,
    derive_core_route_url,
    derive_goldmark_mark_url,
    derive_learning_ingest_url,
    derive_package_install_url,
    derive_review_inbox_command_url,
    derive_sticker_import_url,
)


def main() -> int:
    failures: list[str] = []
    core_chat_url = "http://127.0.0.1:8765/chat"

    expected = {
        derive_codex_execute_url(core_chat_url): "http://127.0.0.1:8765/codex/execute",
        derive_learning_ingest_url(core_chat_url): "http://127.0.0.1:8765/learning/ingest",
        derive_sticker_import_url(core_chat_url): "http://127.0.0.1:8765/sticker/import",
        derive_package_install_url(core_chat_url): "http://127.0.0.1:8765/package/install",
        derive_review_inbox_command_url(core_chat_url): "http://127.0.0.1:8765/review/inbox/command",
        derive_goldmark_mark_url(core_chat_url): "http://127.0.0.1:8765/review/goldmark/mark_request",
        derive_core_route_url("", "/health"): "http://127.0.0.1:8765/health",
        derive_core_route_url("http://core.local/custom", "/health"): "http://127.0.0.1:8765/health",
    }
    for actual, wanted in expected.items():
        if actual != wanted:
            failures.append(f"route derivation changed: {actual!r} != {wanted!r}")

    with tempfile.TemporaryDirectory() as tmp:
        config_path = Path(tmp) / "xinyu_qq_gateway.config.json"
        config_path.write_text(
            """{
  "core_chat_url": "http://127.0.0.1:9900/chat",
  "onebot_port": "6200",
  "codex_command_prefixes": "/codex,/study",
  "trusted_user_ids": ["42"],
  "ignore_prefixes": ["#"]
}
""",
            encoding="utf-8",
        )
        config = GatewayConfig.from_file(config_path)
        if config.onebot_port != 6200:
            failures.append("GatewayConfig integer parsing changed")
        if config.codex_execute_url != "http://127.0.0.1:9900/codex/execute":
            failures.append("GatewayConfig derived codex URL changed")
        if config.codex_command_prefixes != ("/codex", "/study"):
            failures.append("GatewayConfig command prefix parsing changed")
        if config.trusted_user_ids != frozenset({"42"}):
            failures.append("GatewayConfig trusted user parsing changed")
        if config.ignore_prefixes != ("#", "/", "!", "\uff01", "."):
            failures.append("GatewayConfig required ignore prefixes changed")
        overridden = config.with_overrides(core_chat_url="http://127.0.0.1:9911/chat", port=6300)
        if overridden.onebot_port != 6300:
            failures.append("GatewayConfig port override changed")
        if overridden.codex_execute_url != "http://127.0.0.1:9911/codex/execute":
            failures.append("GatewayConfig derived URL override changed")

    if failures:
        print("XinYu QQ config smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu QQ config smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
