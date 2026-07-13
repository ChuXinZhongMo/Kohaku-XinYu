"""Map XinYu's cognitive emotion state -> a coarse TTS delivery category.

This is the bridge that finally feeds the emotion council / 21-dim emotion vector
into the synthesis layer (the Higgs adapter's acoustic lever). Pure + tiny so it
can be unit-tested without importing the council or its model deps.

The vector (continuous truth) decides first; only when it is below threshold do
we fall back to the council's discrete `strongest_lens`. Weak emotion => neutral,
so the voice does not over-act on noise.
"""
from __future__ import annotations

# Council lens -> delivery category (used only as a fallback when the bare vector
# is too weak to speak for itself).
LENS_TO_CATEGORY: dict[str, str] = {
    "attachment": "warm",
    "guardedness": "cold",
    "curiosity": "playful",
    "hurt": "hurt",
    "irritation": "angry",
    "stability": "neutral",
    "fatigue": "tired",
}

# Emotion dimension(s) -> category, highest priority first. Positive activation =
# the feeling is present (dims are in [-1, 1]); negatives mean absence, ignored.
VECTOR_TO_CATEGORY: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("hurt",    ("hurt", "resentment")),
    ("angry",   ("anger", "annoyance", "irritation")),
    ("cold",    ("guardedness", "distance_impulse", "aversion", "disgust", "dislike")),
    ("tired",   ("fatigue",)),
    ("warm",    ("warmth", "trust", "attachment")),
    ("playful", ("curiosity", "openness")),
)


def _val(vector: dict, key: str) -> float:
    try:
        return float(vector.get(key, 0.0))
    except (TypeError, ValueError):
        return 0.0


def derive_delivery(vector: dict | None, strongest_lens: str = "", *, threshold: float = 0.3) -> str:
    """Return one of higgs_emotion.DELIVERY_CATEGORIES for the current state."""
    vector = vector or {}
    best_cat, best_mag = "neutral", float(threshold)
    for category, dims in VECTOR_TO_CATEGORY:
        mag = max((_val(vector, d) for d in dims), default=0.0)
        if mag > best_mag:
            best_cat, best_mag = category, mag
    # warmth + attachment together read as tender rather than merely warm.
    if best_cat == "warm" and _val(vector, "attachment") >= 0.45 and _val(vector, "warmth") >= 0.45:
        best_cat = "tender"
    if best_cat != "neutral":
        return best_cat
    return LENS_TO_CATEGORY.get((strongest_lens or "").strip().lower(), "neutral")
