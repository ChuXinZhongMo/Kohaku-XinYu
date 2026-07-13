"""XinYu cognitive emotion state -> TTS delivery category mapping."""

from __future__ import annotations

from xinyu_tts_emotion import derive_delivery


def test_vector_drives_strong_emotions():
    assert derive_delivery({"hurt": 0.5}) == "hurt"
    assert derive_delivery({"anger": 0.6}) == "angry"
    assert derive_delivery({"annoyance": 0.4}) == "angry"
    assert derive_delivery({"fatigue": 0.45}) == "tired"
    assert derive_delivery({"guardedness": 0.5}) == "cold"
    assert derive_delivery({"curiosity": 0.4}) == "playful"


def test_warm_vs_tender_refinement():
    assert derive_delivery({"warmth": 0.5, "attachment": 0.2}) == "warm"
    assert derive_delivery({"warmth": 0.5, "attachment": 0.5}) == "tender"


def test_weak_vector_falls_back_to_lens():
    # Nothing above threshold -> use the council's strongest_lens.
    assert derive_delivery({"hurt": 0.1}, "hurt") == "hurt"
    assert derive_delivery({}, "guardedness") == "cold"
    assert derive_delivery({"warmth": 0.1}, "attachment") == "warm"


def test_strong_vector_overrides_lens():
    # Vector evidence wins over a disagreeing lens.
    assert derive_delivery({"anger": 0.7}, "attachment") == "angry"


def test_neutral_when_nothing_speaks():
    assert derive_delivery({}, "") == "neutral"
    assert derive_delivery(None, "") == "neutral"
    assert derive_delivery({"warmth": 0.1, "hurt": 0.1}, "stability") == "neutral"


def test_negative_activations_ignored():
    # Negative = absence of the feeling; must not trigger a category.
    assert derive_delivery({"hurt": -0.8, "warmth": -0.5}) == "neutral"


def test_threshold_is_respected():
    assert derive_delivery({"hurt": 0.31}) == "hurt"
    assert derive_delivery({"hurt": 0.29}) == "neutral"


def test_malformed_values_do_not_raise():
    assert derive_delivery({"hurt": "oops", "anger": None}) == "neutral"
