from __future__ import annotations

import base64
import json
import urllib.error

from xinyu_image_context import describe_image_with_vision


MINIMAL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_describe_image_with_vision_falls_back_from_bad_key_and_bad_model(monkeypatch, tmp_path) -> None:
    for name in (
        "XINYU_IMAGE_VISION_API_KEY",
        "XINYU_API_KEY",
        "XINYU_OPENAI_API_KEY",
        "OPENAI_API_KEY",
        "XINYU_IMAGE_VISION_MODEL",
        "XINYU_LLM_MODEL",
        "XINYU_IMAGE_VISION_BASE_URL",
        "XINYU_BASE_URL",
        "OPENAI_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("XINYU_IMAGE_VISION_ENABLED", "1")
    monkeypatch.setenv("XINYU_IMAGE_VISION_BASE_URL", "https://vision.example.test/v1")
    monkeypatch.setenv("XINYU_IMAGE_VISION_API_KEY", "bad-key")
    monkeypatch.setenv("XINYU_API_KEY", "good-key")
    monkeypatch.setenv("XINYU_IMAGE_VISION_MODEL", "bad-image-model")
    monkeypatch.setenv("XINYU_LLM_MODEL", "good-image-model")

    attempts: list[tuple[str, str]] = []

    def fake_urlopen(request, timeout):  # noqa: ANN001, ARG001
        headers = dict(request.header_items())
        auth = headers.get("Authorization", "")
        body = json.loads(request.data.decode("utf-8"))
        model = body["model"]
        attempts.append((auth, model))
        if auth == "Bearer bad-key":
            raise urllib.error.HTTPError(request.full_url, 401, "invalid key", {}, None)
        if model == "bad-image-model":
            raise urllib.error.HTTPError(request.full_url, 404, "no image endpoint", {}, None)
        return _FakeResponse({"choices": [{"message": {"content": "这张图显示了一个设置菜单。"}}]})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    image_path = tmp_path / "scan.png"
    image_path.write_bytes(MINIMAL_PNG)

    summary, notes = describe_image_with_vision(
        image_path,
        {"file_name": "scan.png"},
        owner_text="看看这张图",
    )

    assert summary == "这张图显示了一个设置菜单。"
    assert ("Bearer bad-key", "bad-image-model") in attempts
    assert ("Bearer good-key", "good-image-model") in attempts
    assert "vision_http_401" in notes
    assert "vision_http_404" in notes
    assert "vision_api_key_fallback_used" in notes
    assert "vision_model_fallback_used:good-image-model" in notes
    assert "vision_summary_created" in notes
