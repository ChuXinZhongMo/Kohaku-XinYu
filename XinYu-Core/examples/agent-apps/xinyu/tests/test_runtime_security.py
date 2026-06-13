from __future__ import annotations

import pytest

from xinyu_runtime_security import (
    enforce_bridge_token_guard,
    enforce_llm_http_guard,
    is_loopback_host,
)


MODEL_ENDPOINT_ENV_KEYS = (
    "XINYU_API_KEY",
    "XINYU_BASE_URL",
    "XINYU_ALLOW_INSECURE_LLM_HTTP",
    "XINYU_IMAGE_VISION_ENABLED",
    "XINYU_IMAGE_VISION_API_KEY",
    "XINYU_IMAGE_VISION_BASE_URL",
    "XINYU_ALLOW_INSECURE_IMAGE_VISION_HTTP",
    "XINYU_VOICE_STT_ENABLED",
    "XINYU_VOICE_STT_API_KEY",
    "XINYU_VOICE_STT_BASE_URL",
    "XINYU_ALLOW_INSECURE_VOICE_STT_HTTP",
    "XINYU_VOICE_MIMO_API_KEY",
    "XINYU_VOICE_MIMO_BASE_URL",
    "XINYU_ALLOW_INSECURE_VOICE_MIMO_HTTP",
    "XINYU_TTS_ENABLED",
    "XINYU_TTS_API_KEY",
    "XINYU_TTS_BASE_URL",
    "XINYU_ALLOW_INSECURE_TTS_HTTP",
    "XINYU_OPENAI_API_KEY",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
)


@pytest.fixture(autouse=True)
def _clear_endpoint_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in MODEL_ENDPOINT_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_llm_http_guard_blocks_plain_http_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XINYU_API_KEY", "test-key")
    monkeypatch.setenv("XINYU_BASE_URL", "http://example.test/v1")

    with pytest.raises(RuntimeError, match="LLM endpoint"):
        enforce_llm_http_guard()


def test_modality_http_guard_blocks_inherited_plain_http_base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XINYU_IMAGE_VISION_ENABLED", "1")
    monkeypatch.setenv("XINYU_IMAGE_VISION_API_KEY", "vision-key")
    monkeypatch.setenv("XINYU_BASE_URL", "http://example.test/v1")

    with pytest.raises(RuntimeError, match="vision endpoint"):
        enforce_llm_http_guard()


def test_modality_http_guard_allows_explicit_local_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XINYU_TTS_ENABLED", "1")
    monkeypatch.setenv("XINYU_TTS_API_KEY", "tts-key")
    monkeypatch.setenv("XINYU_TTS_BASE_URL", "http://127.0.0.1:8123/v1")
    monkeypatch.setenv("XINYU_ALLOW_INSECURE_TTS_HTTP", "1")

    enforce_llm_http_guard()


def test_bridge_token_guard_allows_loopback_without_token() -> None:
    for host in ("", "localhost", "127.0.0.1", "127.10.0.5", "::1"):
        assert is_loopback_host(host)
        enforce_bridge_token_guard(host, "")


def test_bridge_token_guard_requires_token_for_non_loopback() -> None:
    for host in ("0.0.0.0", "192.168.1.10", "example.test"):
        assert not is_loopback_host(host)
        with pytest.raises(RuntimeError, match="Non-loopback XinYu core bridge host"):
            enforce_bridge_token_guard(host, "")
        enforce_bridge_token_guard(host, "bridge-token")
