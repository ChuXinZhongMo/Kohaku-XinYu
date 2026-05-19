from __future__ import annotations

from xinyu_bridge_session import session_key_from_payload


def test_session_key_prefers_top_level_session_then_user() -> None:
    assert session_key_from_payload({"session_id": "s1", "user_id": "u1"}) == "s1"
    assert session_key_from_payload({"user_id": "u1"}) == "u1"


def test_session_key_uses_metadata_fallback_for_adapter_payloads() -> None:
    assert session_key_from_payload({"metadata": {"session_id": "meta-s1", "user_id": "meta-u1"}}) == "meta-s1"
    assert session_key_from_payload({"metadata": {"user_id": "meta-u1"}}) == "meta-u1"


def test_session_key_default_is_stable() -> None:
    assert session_key_from_payload({}) == "qq:default"
    assert session_key_from_payload({"metadata": {}}) == "qq:default"
