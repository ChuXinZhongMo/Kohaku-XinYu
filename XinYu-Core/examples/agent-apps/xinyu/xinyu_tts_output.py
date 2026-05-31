from __future__ import annotations

import base64
import json
import os
import queue
import re
import sys
import threading
import time
import urllib.error
import urllib.request
import wave
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from state_service import append_jsonl

try:
    import winsound
except ImportError:  # pragma: no cover - non-Windows fallback
    winsound = None


TRACE_REL = Path("runtime") / "tts_output_trace.jsonl"
TEMP_REL = Path("runtime") / "tts_audio_tmp"
LOCAL_ENV_FILES = ("xinyu.local.env", ".env")
REQUEST_MODES = {"auto", "chat_audio", "audio_speech"}
DEFAULT_TTS_MODEL = "mimo-v2.5-tts"
DEFAULT_TTS_FORMAT = "wav"
DEFAULT_TTS_TIMEOUT_SECONDS = 60.0
MAX_PENDING_JOBS = 4
MAX_TEXT_CHARS = 1200


@dataclass(frozen=True)
class TTSJob:
    text: str
    created_at: str
    reply_hash: str = ""
    session_key: str = ""
    turn_id: str = ""
    source: str = ""
    message_type: str = ""


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _one_line(value: Any, *, limit: int = 240) -> str:
    text = " ".join(_safe_str(value).split())
    if not text:
        return ""
    text = re.sub(r"(?i)\b(?:authorization|api[_-]?key|token|password|cookie)\s*[:=]\s*[^\s<>'\"]+", "<secret>", text)
    text = re.sub(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}", "<secret>", text)
    return text[: max(1, int(limit))]


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    if value is None:
        return default
    return bool(value)


def _as_float(value: Any, default: float) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def _clean_text(text: str) -> str:
    clean = re.sub(r"\s+", " ", _safe_str(text)).strip()
    if len(clean) > MAX_TEXT_CHARS:
        clean = clean[:MAX_TEXT_CHARS].rstrip()
    return clean


def _load_local_env(root: Path) -> None:
    for name in LOCAL_ENV_FILES:
        path = root / name
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            if not key or key in os.environ:
                continue
            os.environ[key] = value.strip().strip('"').strip("'")


def _tts_api_key() -> str:
    return (
        os.environ.get("XINYU_TTS_API_KEY", "").strip()
        or os.environ.get("XINYU_OPENAI_API_KEY", "").strip()
        or os.environ.get("OPENAI_API_KEY", "").strip()
        or os.environ.get("XINYU_API_KEY", "").strip()
    )


def _tts_base_url() -> str:
    return (
        os.environ.get("XINYU_TTS_BASE_URL", "").strip()
        or os.environ.get("OPENAI_BASE_URL", "").strip()
        or os.environ.get("XINYU_BASE_URL", "").strip()
        or "https://api.openai.com/v1"
    ).rstrip("/")


def _tts_model() -> str:
    return (
        os.environ.get("XINYU_TTS_MODEL", "").strip()
        or os.environ.get("OPENAI_AUDIO_SPEECH_MODEL", "").strip()
        or DEFAULT_TTS_MODEL
    )


def _tts_voice(model: str) -> str:
    configured = os.environ.get("XINYU_TTS_VOICE", "").strip()
    if configured:
        return configured
    if model.lower().startswith("mimo-"):
        return "mimo_default"
    return "alloy"


def _tts_format() -> str:
    value = os.environ.get("XINYU_TTS_FORMAT", DEFAULT_TTS_FORMAT).strip().lower()
    return value or DEFAULT_TTS_FORMAT


def _tts_request_mode() -> str:
    mode = os.environ.get("XINYU_TTS_REQUEST_MODE", "auto").strip().lower()
    return mode if mode in REQUEST_MODES else "auto"


class XinYuTTSOutput:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        _load_local_env(self.root)
        self.enabled = _as_bool(os.environ.get("XINYU_TTS_ENABLED"), default=False)
        self.base_url = _tts_base_url()
        self.api_key = _tts_api_key()
        self.model = _tts_model()
        self.voice = _tts_voice(self.model)
        self.audio_format = _tts_format()
        self.request_mode = _tts_request_mode()
        self.timeout_seconds = max(1.0, _as_float(os.environ.get("XINYU_TTS_TIMEOUT_SECONDS"), DEFAULT_TTS_TIMEOUT_SECONDS))
        self._jobs: queue.Queue[TTSJob | None] = queue.Queue(maxsize=MAX_PENDING_JOBS)
        self._retained_files: list[tuple[Path, float]] = []
        self._playback_lock = threading.Lock()
        self._closed = False
        self._disabled_reason = self._startup_disabled_reason()
        self._worker: threading.Thread | None = None
        if self.enabled and not self._disabled_reason:
            self._worker = threading.Thread(target=self._worker_loop, name="xinyu-tts-output", daemon=True)
            self._worker.start()

    def active(self) -> bool:
        return self.enabled and not self._disabled_reason and self._worker is not None

    def close(self) -> None:
        self._closed = True
        if self._worker is None:
            self._purge_playback(force=True)
            return
        try:
            self._jobs.put_nowait(None)
        except queue.Full:
            try:
                _ = self._jobs.get_nowait()
            except queue.Empty:
                pass
            try:
                self._jobs.put_nowait(None)
            except queue.Full:
                pass
        self._worker.join(timeout=2.0)
        self._purge_playback(force=True)

    def enqueue(
        self,
        text: str,
        *,
        reply_hash: str = "",
        session_key: str = "",
        turn_id: str = "",
        source: str = "",
        message_type: str = "",
    ) -> bool:
        clean = _clean_text(text)
        if not clean or not self.active():
            return False
        job = TTSJob(
            text=clean,
            created_at=_now_iso(),
            reply_hash=_safe_str(reply_hash),
            session_key=_safe_str(session_key),
            turn_id=_safe_str(turn_id),
            source=_safe_str(source),
            message_type=_safe_str(message_type),
        )
        try:
            self._jobs.put_nowait(job)
            return True
        except queue.Full:
            try:
                _ = self._jobs.get_nowait()
            except queue.Empty:
                return False
            try:
                self._jobs.put_nowait(job)
                return True
            except queue.Full:
                return False

    def speak_blocking(self, text: str) -> dict[str, Any]:
        clean = _clean_text(text)
        if not clean:
            return {"ok": False, "status": "empty_text"}
        if self._disabled_reason:
            return {"ok": False, "status": self._disabled_reason}
        started_at = time.perf_counter()
        status = "played"
        engine = ""
        audio_path: Path | None = None
        error = ""
        try:
            audio_bytes, engine = self._synthesize_audio(clean)
            audio_path = self._write_audio_file(audio_bytes)
            self._play_audio_file(audio_path, blocking=True)
        except Exception as exc:
            status = "tts_failed"
            error = f"{type(exc).__name__}: {_one_line(exc, limit=320)}"
        self._append_trace(
            TTSJob(text=clean, created_at=_now_iso()),
            status=status,
            engine=engine,
            error=error,
            elapsed_ms=int((time.perf_counter() - started_at) * 1000),
            audio_path=audio_path,
        )
        return {"ok": status == "played", "status": status, "engine": engine, "error": error, "path": str(audio_path or "")}

    def _startup_disabled_reason(self) -> str:
        if not self.enabled:
            return "tts_disabled"
        if winsound is None or not sys.platform.startswith("win"):
            return "winsound_unavailable"
        if not self.base_url:
            return "missing_base_url"
        if not self.api_key:
            return "missing_api_key"
        if not self.model:
            return "missing_model"
        if self.audio_format != "wav":
            return "playback_requires_wav"
        return ""

    def _worker_loop(self) -> None:
        while not self._closed:
            try:
                job = self._jobs.get(timeout=0.5)
            except queue.Empty:
                self._purge_playback()
                continue
            if job is None:
                break
            self._process_job(job)
        self._purge_playback(force=True)

    def _process_job(self, job: TTSJob) -> None:
        started_at = time.perf_counter()
        status = "played"
        engine = ""
        audio_path: Path | None = None
        error = ""
        try:
            audio_bytes, engine = self._synthesize_audio(job.text)
            audio_path = self._write_audio_file(audio_bytes)
            self._play_audio_file(audio_path)
        except Exception as exc:
            status = "tts_failed"
            error = f"{type(exc).__name__}: {_one_line(exc, limit=320)}"
        finally:
            self._append_trace(
                job,
                status=status,
                engine=engine,
                error=error,
                elapsed_ms=int((time.perf_counter() - started_at) * 1000),
                audio_path=audio_path,
            )

    def _synthesize_audio(self, text: str) -> tuple[bytes, str]:
        tried: list[str] = []
        errors: list[str] = []
        mode = self.request_mode
        if mode in {"auto", "chat_audio"}:
            tried.append("chat_audio")
            try:
                audio = self._request_chat_audio(text)
                if audio:
                    return audio, "chat_audio"
            except Exception as exc:
                errors.append(f"chat_audio:{_one_line(exc, limit=180)}")
                if mode != "auto":
                    raise
        if mode in {"auto", "audio_speech"}:
            tried.append("audio_speech")
            try:
                audio = self._request_audio_speech(text)
                if audio:
                    return audio, "audio_speech"
            except Exception as exc:
                errors.append(f"audio_speech:{_one_line(exc, limit=180)}")
                if mode != "auto":
                    raise
        suffix = f":{'; '.join(errors)}" if errors else ""
        raise RuntimeError("tts_request_failed:" + ",".join(tried or [mode]) + suffix)

    def _request_chat_audio(self, text: str) -> bytes:
        payload = {
            "model": self.model,
            "messages": [{"role": "assistant", "content": text}],
            "audio": {
                "format": self.audio_format,
                "voice": self.voice,
            },
        }
        data = self._post_json("/chat/completions", payload)
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("missing_chat_audio_choices")
        first = choices[0]
        if not isinstance(first, dict):
            raise RuntimeError("invalid_chat_audio_choice")
        message = first.get("message")
        if not isinstance(message, dict):
            raise RuntimeError("missing_chat_audio_message")
        audio = message.get("audio")
        if not isinstance(audio, dict):
            raise RuntimeError("missing_chat_audio_payload")
        encoded = _safe_str(audio.get("data"))
        if not encoded:
            raise RuntimeError("empty_chat_audio_payload")
        return base64.b64decode(encoded, validate=False)

    def _request_audio_speech(self, text: str) -> bytes:
        payload = {
            "model": self.model,
            "voice": self.voice,
            "input": text,
            "response_format": self.audio_format,
        }
        return self._post_binary("/audio/speech", payload)

    def _post_json(self, route: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            self.base_url + route,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"http_{exc.code}:{_one_line(body, limit=320)}") from exc
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            raise RuntimeError(_one_line(exc, limit=320)) from exc
        try:
            data = json.loads(body.decode("utf-8", errors="replace"))
        except json.JSONDecodeError as exc:
            raise RuntimeError("non_json_tts_response") from exc
        if isinstance(data, dict) and isinstance(data.get("error"), dict):
            message = _safe_str(data["error"].get("message"))
            if message:
                raise RuntimeError(message)
        if not isinstance(data, dict):
            raise RuntimeError("invalid_tts_json_payload")
        return data

    def _post_binary(self, route: str, payload: dict[str, Any]) -> bytes:
        request = urllib.request.Request(
            self.base_url + route,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                data = response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"http_{exc.code}:{_one_line(body, limit=320)}") from exc
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            raise RuntimeError(_one_line(exc, limit=320)) from exc
        if not data:
            raise RuntimeError("empty_tts_audio_response")
        return data

    def _write_audio_file(self, audio_bytes: bytes) -> Path:
        if not audio_bytes:
            raise RuntimeError("empty_audio_bytes")
        directory = self.root / TEMP_REL
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"tts-{int(time.time() * 1000)}.wav"
        path.write_bytes(audio_bytes)
        return path

    def _play_audio_file(self, path: Path, *, blocking: bool = False) -> None:
        duration_seconds = self._wav_duration(path)
        with self._playback_lock:
            self._stop_playback_locked()
            self._cleanup_retained_files_locked(force=True)
            assert winsound is not None
            flags = winsound.SND_FILENAME | winsound.SND_NODEFAULT
            if not blocking:
                flags |= winsound.SND_ASYNC
            winsound.PlaySound(str(path), flags)
            if blocking:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
                return
            self._retained_files.append((path, time.time() + max(2.0, duration_seconds + 2.0)))
            self._cleanup_retained_files_locked(force=False)

    def _wav_duration(self, path: Path) -> float:
        try:
            with wave.open(str(path), "rb") as handle:
                frames = handle.getnframes()
                rate = handle.getframerate()
        except (wave.Error, OSError) as exc:
            raise RuntimeError(f"invalid_wav:{_one_line(exc)}") from exc
        if frames <= 0 or rate <= 0:
            return 0.0
        return float(frames) / float(rate)

    def _purge_playback(self, *, force: bool = False) -> None:
        now = time.time()
        with self._playback_lock:
            if force:
                self._stop_playback_locked()
            self._cleanup_retained_files_locked(force=force, now=now)

    def _stop_playback_locked(self) -> None:
        if winsound is None:
            return
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass

    def _cleanup_retained_files_locked(self, *, force: bool, now: float | None = None) -> None:
        current = time.time() if now is None else now
        keep: list[tuple[Path, float]] = []
        for path, expires_at in self._retained_files:
            if not force and expires_at > current:
                keep.append((path, expires_at))
                continue
            try:
                path.unlink(missing_ok=True)
            except OSError:
                keep.append((path, expires_at))
        self._retained_files = keep

    def _append_trace(
        self,
        job: TTSJob,
        *,
        status: str,
        engine: str,
        error: str,
        elapsed_ms: int,
        audio_path: Path | None,
    ) -> None:
        file_size = 0
        if audio_path is not None and audio_path.exists():
            try:
                file_size = audio_path.stat().st_size
            except OSError:
                file_size = 0
        row = {
            "recorded_at": _now_iso(),
            "created_at": job.created_at,
            "status": status,
            "engine": engine,
            "request_mode": self.request_mode,
            "model": self.model,
            "voice": self.voice,
            "audio_format": self.audio_format,
            "timeout_seconds": self.timeout_seconds,
            "text_chars": len(job.text),
            "reply_hash": job.reply_hash or "none",
            "session_key": job.session_key,
            "turn_id": job.turn_id,
            "source": job.source,
            "message_type": job.message_type,
            "elapsed_ms": max(0, int(elapsed_ms)),
            "audio_file_size": file_size,
            "error": _one_line(error, limit=320),
            "stable_memory_write": "blocked",
            "visible_reply_text_retained": False,
        }
        append_jsonl(self.root / TRACE_REL, row)


def main() -> int:
    root = Path(__file__).resolve().parent
    speaker = XinYuTTSOutput(root)
    text = _clean_text(" ".join(sys.argv[1:]) or "你好，我是心玉。")
    result = speaker.speak_blocking(text)
    speaker.close()
    if result.get("ok"):
        print(f"tts_ok engine={result.get('engine')} path={result.get('path')}", flush=True)
        return 0
    print(f"tts_failed status={result.get('status')} error={result.get('error')}", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
