"""QQ voice-reply support: turn a visible text reply into a OneBot voice clip.

- Per-scope enable flags are read LIVE from xinyu.local.env (so the desktop
  toggle takes effect without restarting the gateway):
    XINYU_QQ_VOICE_REPLY_PRIVATE  -> private chats
    XINYU_QQ_VOICE_REPLY_GROUP    -> group chats
- Synthesis goes through the same Genie TTS adapter XinYu already uses
  (XINYU_GENIE_TTS_BASE_URL, default http://127.0.0.1:8001) `POST /tts`.
The WAV is returned as a `base64://...` payload NapCat transcodes to silk.
"""
from __future__ import annotations

import array
import base64
from dataclasses import dataclass
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path

try:
    import winsound
except ImportError:  # pragma: no cover - non-Windows test/runtime fallback
    winsound = None  # type: ignore[assignment]

_ENV_PATH = Path(__file__).resolve().parent / "xinyu.local.env"
_TRUE = {"1", "true", "yes", "on"}

# tiny mtime cache so we re-read the env file only when it changes
_env_cache: dict[str, str] = {}
_env_mtime: float = -1.0


@dataclass(frozen=True)
class VoiceSynthesisResult:
    ok: bool
    record_file: str = ""
    wav_bytes: bytes = b""
    reason: str = ""
    elapsed_ms: int = 0
    status_code: int = 0
    audio_bytes: int = 0
    base_url: str = ""


def _env_flags() -> dict[str, str]:
    """Read xinyu.local.env, refreshing only when the file changes."""
    global _env_mtime, _env_cache
    try:
        mtime = _ENV_PATH.stat().st_mtime
    except OSError:
        return _env_cache
    if mtime != _env_mtime:
        parsed: dict[str, str] = {}
        try:
            for raw in _ENV_PATH.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                parsed[key.strip()] = val.strip().strip('"').strip("'")
        except OSError:
            return _env_cache
        _env_cache = parsed
        _env_mtime = mtime
    return _env_cache


def _flag(name: str) -> bool:
    # live env file wins; fall back to the process environment
    env = _env_flags()
    value = (env.get(name) if name in env else os.environ.get(name, "")) or ""
    return value.strip().lower() in _TRUE


def _env_value(name: str, default: str = "") -> str:
    env = _env_flags()
    return (env.get(name) if name in env else os.environ.get(name, default)) or default


def _as_bool(value: str, *, default: bool = False) -> bool:
    text = (value or "").strip().lower()
    if text in _TRUE:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _as_int(value: str, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def local_playback_enabled() -> bool:
    if not _as_bool(_env_value("XINYU_TTS_ENABLED", "0"), default=False):
        return False
    return _as_bool(_env_value("XINYU_QQ_VOICE_LOCAL_PLAYBACK", "1"), default=True)


def strict_voice_reply_enabled(message_kind: str) -> bool:
    if message_kind == "group":
        return _as_bool(_env_value("XINYU_QQ_VOICE_REPLY_STRICT_GROUP", "0"), default=False)
    return _as_bool(_env_value("XINYU_QQ_VOICE_REPLY_STRICT_PRIVATE", "1"), default=True)


def voice_reply_enabled(message_kind: str) -> bool:
    if message_kind == "group":
        return _flag("XINYU_QQ_VOICE_REPLY_GROUP")
    return _flag("XINYU_QQ_VOICE_REPLY_PRIVATE")


def _tts_base_url() -> str:
    return _env_value("XINYU_GENIE_TTS_BASE_URL", "http://127.0.0.1:8001").rstrip("/")


def _tts_character() -> str:
    return _env_value("XINYU_GENIE_TTS_CHARACTER", "xinyu").strip() or "xinyu"


def _tts_split_sentence() -> bool:
    return _as_bool(_env_value("XINYU_GENIE_TTS_SPLIT_SENTENCE", "0"), default=False)


def _tts_sample_rate() -> int:
    # 24000 matches Higgs v3 output; 32000 was the old GPT-SoVITS engine's rate and
    # would garble ("电子音") if a non-RIFF raw-PCM response ever bypasses the header.
    return max(8000, min(96000, _as_int(_env_value("XINYU_GENIE_TTS_SAMPLE_RATE", "24000"), 24000)))


def _tts_channels() -> int:
    return max(1, min(2, _as_int(_env_value("XINYU_GENIE_TTS_CHANNELS", "1"), 1)))


def _tts_sample_width() -> int:
    return max(1, min(4, _as_int(_env_value("XINYU_GENIE_TTS_SAMPLE_WIDTH", "2"), 2)))


def _pcm_to_wav_bytes(pcm: bytes, *, sample_rate: int, channels: int, sample_width: int) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(sample_width)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm)
    return buffer.getvalue()


def trim_wav_trailing_silence(
    wav_bytes: bytes,
    *,
    floor_ratio: float = 0.04,
    tail_pad_seconds: float = 0.25,
    min_keep_seconds: float = 0.4,
    min_trim_seconds: float = 0.8,
) -> bytes:
    """Cut a long silent tail off a synthesized WAV.

    GPT-SoVITS / Genie sometimes fails to emit an end token and keeps generating
    silence until it hits the max length, producing clips that are mostly dead
    air (observed: 7.4s of speech + 33s of silence in a 40s clip). This finds the
    last audible sample (relative to the clip's own peak) and keeps up to there
    plus a short pad. Conservative by design: only trims when it would remove at
    least ``min_trim_seconds``, never cuts below ``min_keep_seconds``, and returns
    the input unchanged on any unexpected shape so voice replies never break.
    """
    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as handle:
            channels = handle.getnchannels()
            sample_width = handle.getsampwidth()
            rate = handle.getframerate()
            frames = handle.getnframes()
            raw = handle.readframes(frames)
        if sample_width != 2 or channels < 1 or rate <= 0 or frames <= 0:
            return wav_bytes
        samples = array.array("h")
        samples.frombytes(raw)
        if sys.byteorder == "big":
            samples.byteswap()
        peak = 0
        for value in samples:
            magnitude = value if value >= 0 else -value
            if magnitude > peak:
                peak = magnitude
        if peak <= 0:
            return wav_bytes
        threshold = peak * floor_ratio
        last_audible_frame = -1
        for frame_index in range(frames - 1, -1, -1):
            base = frame_index * channels
            loud = False
            for channel in range(channels):
                value = samples[base + channel]
                magnitude = value if value >= 0 else -value
                if magnitude > threshold:
                    loud = True
                    break
            if loud:
                last_audible_frame = frame_index
                break
        if last_audible_frame < 0:
            return wav_bytes
        keep_frames = last_audible_frame + 1 + int(tail_pad_seconds * rate)
        keep_frames = max(int(min_keep_seconds * rate), min(keep_frames, frames))
        if frames - keep_frames < int(min_trim_seconds * rate):
            return wav_bytes
        kept = samples[: keep_frames * channels]
        if sys.byteorder == "big":
            kept.byteswap()
        out = io.BytesIO()
        with wave.open(out, "wb") as writer:
            writer.setnchannels(channels)
            writer.setsampwidth(sample_width)
            writer.setframerate(rate)
            writer.writeframes(kept.tobytes())
        return out.getvalue()
    except (wave.Error, OSError, ValueError):
        return wav_bytes


def _wav_duration_seconds(wav_bytes: bytes) -> float:
    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as handle:
            frames = handle.getnframes()
            rate = handle.getframerate()
    except (wave.Error, OSError):
        return 0.0
    if frames <= 0 or rate <= 0:
        return 0.0
    return float(frames) / float(rate)


def _playback_dir() -> Path:
    return Path(__file__).resolve().parent / "runtime" / "qq_voice_audio_tmp"


def _cleanup_playback_dir(directory: Path, *, now: float | None = None) -> None:
    current = time.time() if now is None else now
    try:
        for path in directory.glob("qq-voice-*.wav"):
            try:
                if current - path.stat().st_mtime > 3600:
                    path.unlink(missing_ok=True)
            except OSError:
                continue
    except OSError:
        return


def play_voice_result_locally(result: VoiceSynthesisResult) -> dict[str, object]:
    if not result.ok or not result.wav_bytes:
        return {"played": False, "reason": "empty_audio"}
    if not local_playback_enabled():
        return {"played": False, "reason": "disabled"}
    if winsound is None or not sys.platform.startswith("win"):
        return {"played": False, "reason": "winsound_unavailable"}
    directory = _playback_dir()
    try:
        directory.mkdir(parents=True, exist_ok=True)
        _cleanup_playback_dir(directory)
        path = directory / f"qq-voice-{int(time.time() * 1000)}.wav"
        path.write_bytes(result.wav_bytes)
        flags = winsound.SND_FILENAME | winsound.SND_NODEFAULT | winsound.SND_ASYNC
        winsound.PlaySound(str(path), flags)
    except Exception as exc:
        return {"played": False, "reason": f"{type(exc).__name__}:{_one_line(exc)}"}
    return {
        "played": True,
        "path": str(path),
        "duration_seconds": round(_wav_duration_seconds(result.wav_bytes), 3),
    }


def _timeout() -> float:
    raw = _env_value("XINYU_TTS_TIMEOUT_SECONDS", "60")
    try:
        return max(5.0, float(raw))
    except (TypeError, ValueError):
        return 60.0


def _retry_count() -> int:
    raw = _env_value("XINYU_TTS_RETRY_COUNT", "1")
    try:
        return min(2, max(0, int(raw)))
    except (TypeError, ValueError):
        return 1


def _one_line(value: object, limit: int = 180) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    return text[:limit]


def _failure(
    *,
    reason: str,
    started: float,
    base_url: str = "",
    status_code: int = 0,
    audio_bytes: int = 0,
) -> VoiceSynthesisResult:
    return VoiceSynthesisResult(
        ok=False,
        reason=reason,
        elapsed_ms=int((time.monotonic() - started) * 1000),
        status_code=status_code,
        audio_bytes=audio_bytes,
        base_url=base_url,
    )


def _tts_emotion_enabled() -> bool:
    """Mirror xinyu_tts_output: feed cognitive emotion into Higgs when enabled."""
    return _flag("XINYU_TTS_EMOTION")


def _read_delivery_category_for_voice() -> str:
    """Best-effort read of runtime emotion → delivery category (empty = neutral)."""
    if not _tts_emotion_enabled():
        return ""
    try:
        from xinyu_tts_emotion import derive_delivery
    except Exception:
        return ""
    root = Path(__file__).resolve().parent
    vector: dict = {}
    strongest = ""
    try:
        state_path = root / "runtime" / "emotion_state.json"
        if state_path.is_file() and state_path.stat().st_size <= 200_000:
            data = json.loads(state_path.read_text(encoding="utf-8", errors="replace"))
            if isinstance(data, dict) and isinstance(data.get("vector"), dict):
                vector = data["vector"]
    except (OSError, ValueError):
        vector = {}
    try:
        import re

        council_path = root / "memory" / "context" / "emotion_council_state.md"
        if council_path.is_file() and council_path.stat().st_size <= 200_000:
            md = council_path.read_text(encoding="utf-8", errors="replace")
            if re.search(r"^- status:\s*active\b", md, re.MULTILINE):
                match = re.search(r"^- strongest_lens:\s*([a-z_]+)", md, re.MULTILINE)
                if match:
                    strongest = match.group(1)
    except OSError:
        strongest = ""
    try:
        category = derive_delivery(vector, strongest)
    except Exception:
        return ""
    return "" if category == "neutral" else category


def synth_voice_b64_result(text: str) -> VoiceSynthesisResult:
    """Synthesize `text` to a WAV via the Genie adapter with failure details."""
    text = (text or "").strip()
    started = time.monotonic()
    if not text:
        return _failure(reason="empty_text", started=started)
    payload = {
        "character_name": _tts_character(),
        "text": text,
        "split_sentence": _tts_split_sentence(),
    }
    if _tts_emotion_enabled():
        emotion = _read_delivery_category_for_voice()
        if emotion:
            payload["emotion"] = emotion
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    base_url = _tts_base_url()
    req = urllib.request.Request(
        f"{base_url}/tts",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    last_failure: VoiceSynthesisResult = _failure(reason="not_attempted", started=started, base_url=base_url)
    for attempt in range(1, _retry_count() + 2):
        try:
            with urllib.request.urlopen(req, timeout=_timeout()) as resp:
                status = getattr(resp, "status", 0)
                audio = resp.read()
        except urllib.error.HTTPError as exc:
            last_failure = _failure(
                reason=f"http_error:{exc.code}:{_one_line(exc.reason)}",
                started=started,
                base_url=base_url,
                status_code=exc.code,
            )
        except Exception as exc:
            last_failure = _failure(
                reason=f"{type(exc).__name__}:{_one_line(exc)}",
                started=started,
                base_url=base_url,
            )
        else:
            audio_bytes = len(audio or b"")
            if status != 200:
                last_failure = _failure(
                    reason=f"http_status:{status}",
                    started=started,
                    base_url=base_url,
                    status_code=status,
                    audio_bytes=audio_bytes,
                )
            elif not audio:
                last_failure = _failure(reason="empty_audio", started=started, base_url=base_url, status_code=status)
            else:
                if audio[:4] != b"RIFF":
                    audio = _pcm_to_wav_bytes(
                        audio,
                        sample_rate=_tts_sample_rate(),
                        channels=_tts_channels(),
                        sample_width=_tts_sample_width(),
                    )
                audio = trim_wav_trailing_silence(audio)
                audio_bytes = len(audio)
                return VoiceSynthesisResult(
                    ok=True,
                    record_file="base64://" + base64.b64encode(audio).decode("ascii"),
                    wav_bytes=audio,
                    elapsed_ms=int((time.monotonic() - started) * 1000),
                    status_code=status,
                    audio_bytes=audio_bytes,
                    base_url=base_url,
                )
        if attempt <= _retry_count():
            time.sleep(0.35)
    return last_failure


def synth_voice_b64(text: str) -> str | None:
    """Synthesize `text` and return `base64://...` or None on failure."""
    result = synth_voice_b64_result(text)
    return result.record_file if result.ok else None
