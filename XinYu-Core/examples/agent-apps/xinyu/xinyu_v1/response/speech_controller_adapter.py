"""Compatibility adapter for the current speech controller."""

from __future__ import annotations


class SpeechControllerAdapter:
    def refine(self, text: str) -> tuple[str, tuple[str, ...]]:
        try:
            from xinyu_bridge_renderer import normalize_reply  # type: ignore
        except Exception:
            return text, ("speech_controller_unavailable",)
        try:
            return normalize_reply(text), ("legacy_normalize_reply",)
        except Exception as exc:
            return text, ("legacy_normalize_failed", str(exc))

