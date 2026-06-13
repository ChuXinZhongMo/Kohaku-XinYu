from __future__ import annotations

from xinyu_qq_rich_context import prompt_sidecar_from_payload


def test_prompt_sidecar_includes_rich_reply_forward_and_image_context() -> None:
    sidecar = prompt_sidecar_from_payload(
        {
            "metadata": {
                "qq_rich_message": True,
                "qq_rich_summary": "sticker plus forwarded screenshot",
                "qq_sticker_count": 1,
                "qq_image_count": 1,
                "qq_forward_count": 1,
                "qq_message_segments": [
                    {"kind": "sticker", "summary": "animated sticker", "confidence": "low"},
                ],
                "qq_reply_message_id": "quoted-1",
                "qq_reply_context": {"sender_name": "Owner", "text": "quoted text"},
                "qq_forward_context_available": True,
                "qq_forward_message_ids": ["fw-1"],
                "qq_forward_context": {
                    "message_count": 1,
                    "messages": [{"sender_name": "Alice", "text": "forwarded text"}],
                },
                "qq_image_context_available": True,
                "qq_image_context": {
                    "ocr_text": "screenshot OCR",
                    "vision_summary": "screenshot summary",
                    "notes": ["image_context_requested"],
                },
            }
        }
    )

    assert "non-text rich segments" in sidecar
    assert "quoted_message_id: quoted-1" in sidecar
    assert "forward_ids: fw-1" in sidecar
    assert "Alice: forwarded text" in sidecar
    assert "image_ocr_text:" in sidecar
    assert "screenshot summary" in sidecar


def test_prompt_sidecar_warns_when_low_information_sticker_has_no_image_context() -> None:
    sidecar = prompt_sidecar_from_payload(
        {
            "metadata": {
                "qq_rich_message": True,
                "qq_sticker_count": 1,
                "qq_message_segments": [
                    {"kind": "sticker", "summary": "animated sticker", "confidence": "low"},
                ],
            }
        }
    )

    assert "generic sticker label" in sidecar
    assert "Do not claim you saw an empty/blank frame" in sidecar


def test_prompt_sidecar_warns_when_current_image_context_unavailable() -> None:
    sidecar = prompt_sidecar_from_payload(
        {
            "metadata": {
                "qq_rich_message": True,
                "qq_image_count": 1,
                "qq_image_context_available": False,
                "qq_image_context": {
                    "available": False,
                    "notes": ["image_context_requested", "ocr_text_empty", "vision_disabled"],
                },
            }
        }
    )

    assert "current QQ image was received" in sidecar
    assert "no readable OCR text or visual summary" in sidecar
    assert "Do not use previous attachments" in sidecar
    assert "image_context_notes:" in sidecar


def test_prompt_sidecar_returns_empty_for_plain_payload() -> None:
    assert prompt_sidecar_from_payload({"metadata": {}}) == ""
    assert prompt_sidecar_from_payload({}) == ""
