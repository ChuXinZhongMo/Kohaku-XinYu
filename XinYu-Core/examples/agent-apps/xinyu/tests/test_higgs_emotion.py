"""Pure emotion->delivery logic shared by the Higgs v3 genie adapter.

The module lives next to the adapter under runtime/deps/higgs-audio (outside the
pytest path and excluded from recursion), so add that dir explicitly.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

HIGGS_DIR = Path(__file__).resolve().parents[5] / "runtime" / "deps" / "higgs-audio"
if not (HIGGS_DIR / "higgs_emotion.py").is_file():
    pytest.skip("higgs_emotion.py not present", allow_module_level=True)
if str(HIGGS_DIR) not in sys.path:
    sys.path.insert(0, str(HIGGS_DIR))

import higgs_emotion as he  # noqa: E402

DEFAULTS = {"temperature": 0.5, "top_k": 50, "max_new_tokens": 700, "normalize": "full"}


def test_classify_instruct_en_and_zh():
    assert he.classify_instruct("voice tight with restrained anger") == "angry"
    assert he.classify_instruct("有点被吓到了") == "tense"
    assert he.classify_instruct("Quiet tender whisper, soft") == "tender"
    assert he.classify_instruct("warm and reassuring") == "warm"
    assert he.classify_instruct("委屈，声音发颤") == "hurt"
    assert he.classify_instruct("疲惫，懒洋洋") == "tired"
    assert he.classify_instruct("cold and detached") == "cold"
    assert he.classify_instruct("measured narration") == "neutral"
    assert he.classify_instruct("") == "neutral"
    assert he.classify_instruct(None) == "neutral"


def test_resolve_explicit_emotion_wins():
    r = he.resolve_delivery("hurt", "furious shout", profiles=he.load_profiles(), defaults=DEFAULTS)
    assert r["category"] == "hurt"
    assert r["temperature"] == 0.45 and r["normalize"] == "soft"


def test_resolve_falls_back_to_instruct():
    r = he.resolve_delivery(None, "furious shout", profiles=he.load_profiles(), defaults=DEFAULTS)
    assert r["category"] == "angry" and r["temperature"] == 0.60


def test_resolve_unknown_emotion_then_neutral_inherits_defaults():
    r = he.resolve_delivery("bogus", "", profiles=he.load_profiles(), defaults=DEFAULTS)
    assert r["category"] == "neutral"
    assert r["temperature"] == 0.5 and r["top_k"] == 50 and r["max_new_tokens"] == 700
    assert r["normalize"] == "full" and r["ref_key"] == "neutral" and r["prefix"] == ""


def test_neutral_inherits_global_normalize_mode():
    soft_defaults = {**DEFAULTS, "normalize": "soft"}
    r = he.resolve_delivery("neutral", None, profiles=he.load_profiles(), defaults=soft_defaults)
    assert r["normalize"] == "soft"


def test_select_reference_lookup_and_fallback():
    bank = {"hurt": {"audio_path": "/refs/hurt.wav", "text": "x"}}
    assert he.select_reference("hurt", bank, "/refs/def.wav", "d") == ("/refs/hurt.wav", "x")
    assert he.select_reference("warm", bank, "/refs/def.wav", "d") == ("/refs/def.wav", "d")
    assert he.select_reference("", bank, "/refs/def.wav", "d") == ("/refs/def.wav", "d")
    assert he.select_reference(None, {}, "/refs/def.wav", "d") == ("/refs/def.wav", "d")


def test_normalize_full_flattens_prosody():
    assert he.normalize_text("好的……", "full") == "好的，"
    assert he.normalize_text("哈~~~", "full") == "哈"
    assert he.normalize_text("真的？？？", "full") == "真的？"


def test_normalize_soft_preserves_one_cue():
    assert he.normalize_text("好的……", "soft") == "好的…"
    assert he.normalize_text("哈~~~", "soft") == "哈~"
    assert he.normalize_text("嗯嗯嗯嗯", "soft") == "嗯嗯"
    # runaway-critical collapses still apply in soft mode
    assert he.normalize_text("真的？？？", "soft") == "真的？"


def test_profiles_overlay_from_dict_via_loader(tmp_path):
    import json
    override = tmp_path / "emotion_map.json"
    override.write_text(json.dumps({"hurt": {"temperature": 0.33}, "blue": {"temperature": 0.2}}), encoding="utf-8")
    profiles = he.load_profiles(str(override))
    assert profiles["hurt"]["temperature"] == 0.33  # overridden
    assert profiles["hurt"]["normalize"] == "soft"   # original key preserved
    assert profiles["blue"]["temperature"] == 0.2    # new category added


def test_load_ref_bank_filters_invalid(tmp_path):
    import json
    p = tmp_path / "ref_map.json"
    p.write_text(json.dumps({"hurt": {"audio_path": "/r/h.wav", "text": "t"}, "bad": {"text": "no path"}}), encoding="utf-8")
    bank = he.load_ref_bank(str(p))
    assert "hurt" in bank and "bad" not in bank
    assert he.load_ref_bank(None) == {}
