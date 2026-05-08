from __future__ import annotations

from types import SimpleNamespace

from xinyu_bridge_desktop_projection import (
    desktop_avatar_url,
    desktop_display_id,
    desktop_group_avatar_url,
    desktop_hash,
    desktop_marker_count,
    desktop_privacy_for_payload,
    desktop_proactive_expired,
    desktop_recall_count,
    desktop_session_kind,
    desktop_text_preview,
    desktop_top_recall_sources,
)
from xinyu_core_bridge import XinYuBridgeRuntime


def main() -> int:
    failures: list[str] = []

    if desktop_marker_count(["Suppressed once", "plain"], ("suppressed",)) != 1:
        failures.append("desktop marker count changed")
    result = SimpleNamespace(items=[SimpleNamespace(source="a"), SimpleNamespace(source="a"), SimpleNamespace(source="b")])
    if desktop_recall_count(result) != 3 or desktop_top_recall_sources(result) != ["a", "b"]:
        failures.append("desktop recall summary helpers changed")
    if not desktop_proactive_expired("2000-01-01T00:00:00+00:00") or desktop_proactive_expired("unknown"):
        failures.append("desktop proactive expiry helper changed")

    payload = {"platform": "qq", "message_type": "group", "group_id": "98765", "user_id": "123456"}
    if desktop_session_kind(payload) != "qq_group":
        failures.append("desktop session kind changed")
    if desktop_display_id("123456") != "123456" or desktop_display_id("abc") != "":
        failures.append("desktop display id helper changed")
    if "nk=123456" not in desktop_avatar_url(payload, session_kind="qq_group", user_display_id="123456"):
        failures.append("desktop QQ avatar url changed")
    if "98765/98765" not in desktop_group_avatar_url("98765"):
        failures.append("desktop group avatar url changed")
    if desktop_privacy_for_payload(payload) != "group_context":
        failures.append("desktop privacy helper changed")
    if not desktop_hash("abc", length=8).startswith("sha256:"):
        failures.append("desktop hash helper changed")
    if desktop_text_preview("one   two three", limit=10) != "one two...":
        failures.append("desktop text preview helper changed")

    aliases = (
        (XinYuBridgeRuntime._desktop_marker_count, desktop_marker_count),
        (XinYuBridgeRuntime._desktop_recall_count, desktop_recall_count),
        (XinYuBridgeRuntime._desktop_top_recall_sources, desktop_top_recall_sources),
        (XinYuBridgeRuntime._desktop_proactive_expired, desktop_proactive_expired),
        (XinYuBridgeRuntime._desktop_session_kind, desktop_session_kind),
        (XinYuBridgeRuntime._desktop_display_id, desktop_display_id),
        (XinYuBridgeRuntime._desktop_avatar_url, desktop_avatar_url),
        (XinYuBridgeRuntime._desktop_group_avatar_url, desktop_group_avatar_url),
        (XinYuBridgeRuntime._desktop_privacy_for_payload, desktop_privacy_for_payload),
        (XinYuBridgeRuntime._desktop_hash, desktop_hash),
        (XinYuBridgeRuntime._desktop_text_preview, desktop_text_preview),
    )
    if any(left is not right for left, right in aliases):
        failures.append("core desktop projection aliases no longer delegate")

    if failures:
        print("XinYu bridge desktop projection smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu bridge desktop projection smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
