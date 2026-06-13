from __future__ import annotations

import array
import io
import math
import wave

from xinyu_qq_voice_reply import _wav_duration_seconds, trim_wav_trailing_silence

_RATE = 24000


def _wav(seconds_tone: float, seconds_silence: float, *, amp: int = 12000) -> bytes:
    samples = array.array("h")
    for i in range(int(seconds_tone * _RATE)):
        samples.append(int(amp * math.sin(2 * math.pi * 220 * i / _RATE)))
    samples.extend([0] * int(seconds_silence * _RATE))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(_RATE)
        handle.writeframes(samples.tobytes())
    return buf.getvalue()


def test_trims_long_silent_tail() -> None:
    wav = _wav(seconds_tone=7.0, seconds_silence=33.0)
    assert _wav_duration_seconds(wav) > 39.0
    trimmed = trim_wav_trailing_silence(wav)
    dur = _wav_duration_seconds(trimmed)
    # speech (7s) + small pad, silence gone
    assert 7.0 <= dur <= 7.6


def test_keeps_short_natural_clip_unchanged() -> None:
    wav = _wav(seconds_tone=5.0, seconds_silence=0.2)
    trimmed = trim_wav_trailing_silence(wav)
    assert trimmed == wav  # below min_trim threshold -> untouched


def test_all_silence_returns_unchanged() -> None:
    wav = _wav(seconds_tone=0.0, seconds_silence=4.0)
    trimmed = trim_wav_trailing_silence(wav)
    assert trimmed == wav  # peak == 0 -> never destroy audio


def test_non_pcm16_returns_unchanged() -> None:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(1)  # 8-bit, unsupported shape
        handle.setframerate(_RATE)
        handle.writeframes(bytes(_RATE))
    wav = buf.getvalue()
    assert trim_wav_trailing_silence(wav) == wav


def test_garbage_bytes_return_unchanged() -> None:
    assert trim_wav_trailing_silence(b"not a wav") == b"not a wav"
