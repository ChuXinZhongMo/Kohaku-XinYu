from __future__ import annotations

from xinyu_qq_config import (
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

    if failures:
        print("XinYu QQ config smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu QQ config smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
