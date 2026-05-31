from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import os
import re
import shlex
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from state_service import append_jsonl
from xinyu_qq_attachment_resolver import looks_like_file_path, path_from_file_uri
from xinyu_qq_gateway_utils import hash_id as _hash_id
from xinyu_qq_gateway_utils import safe_str as _safe_str
import xinyu_qq_normalizer
import xinyu_qq_rich_context


TRACE_REL = Path("runtime") / "voice_input_trace.jsonl"
TEMP_REL = Path("runtime") / "qq_voice_transcript_tmp"
LOCAL_ENV_FILES = ("xinyu.local.env", ".env")
VOICE_OUT_FORMAT_DEFAULT = "mp3"
VOICE_TRANSCRIBED_STATUSES = {"transcribed", "completed", "ok"}
VOICE_FAILURE_MARKERS = ("fail", "error", "timeout", "unavailable", "disabled", "missing", "empty")
HEARING_MODES = {"stt", "mimo_audio"}
HEARING_FALLBACK_MODES = {"none", "stt"}
MIMO_HEARING_DEFAULT_MODEL = "mimo-v2.5"
MIMO_HEARING_MAX_AUDIO_BYTES = 24 * 1024 * 1024
MIMO_INAUDIBLE_MARKERS = {"[[inaudible]]", "[inaudible]", "inaudible", "听不清", "听不太清", "无法听清"}
MIMO_META_MARKERS = (
    "according to the audio",
    "transcription record",
    "i cannot fulfill this request",
    "i am unable to",
    "根据您提供",
    "根据你提供",
    "转录记录",
    "请问您",
    "如果您能提供",
    "这段内容分为",
    "语音识别系统",
    "帮您纠正",
    "我无法满足",
    "不能满足该请求",
)


@dataclass(frozen=True)
class VoiceAudioRef:
    status: str
    audio_path: Path | None = None
    file_name: str = ""
    file_size: int = 0
    resolved_by: str = ""
    attempts: tuple[str, ...] = ()
    audio_ref_hash: str = "none"
    error: str = ""


@dataclass(frozen=True)
class VoiceTranscriptResult:
    status: str
    event_id: str
    message_id: str = ""
    transcript: str = ""
    confidence: float | None = None
    engine: str = ""
    model: str = ""
    language: str = ""
    trace_ref: str = "none"
    audio_ref: VoiceAudioRef | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)
    error: str = ""
    recorded_at: str = ""

    @property
    def transcribed(self) -> bool:
        return bool(self.transcript.strip()) and self.status in VOICE_TRANSCRIBED_STATUSES


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _one_line(value: Any, *, limit: int = 240) -> str:
    text = " ".join(_safe_str(value).split())
    if not text:
        return ""
    text = re.sub(r"(?i)(?:[a-z]:\\|/users/|/home/|\\\\)[^\s<>'\"]+", "<local_path>", text)
    text = re.sub(r"(?i)\b(?:authorization|api[_-]?key|token|password|cookie)\s*[:=]\s*[^\s<>'\"]+", "<secret>", text)
    text = re.sub(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}", "<secret>", text)
    text = re.sub(r"(?i)\bsk-[a-z0-9_-]{12,}", "<secret>", text)
    return text[: max(1, int(limit))]


def _hash_ref(value: Any) -> str:
    text = _safe_str(value).strip()
    if not text:
        return "none"
    return "sha256:" + hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def _event_message_id(event: dict[str, Any]) -> str:
    return _safe_str(event.get("message_id")).strip()


def _event_id(event: dict[str, Any], segment: dict[str, Any] | None = None) -> str:
    segment = segment if isinstance(segment, dict) else {}
    data = xinyu_qq_normalizer.segment_data_value(segment) if segment else {}
    anchor = "|".join(
        part
        for part in (
            _safe_str(event.get("message_id")).strip(),
            _safe_str(event.get("user_id")).strip(),
            _safe_str(event.get("group_id")).strip(),
            _safe_str(data.get("file") or data.get("file_id") or data.get("path")).strip(),
        )
        if part
    )
    if not anchor:
        anchor = json.dumps(event, ensure_ascii=False, sort_keys=True, default=str)[:500]
    return "qq-voice-" + hashlib.sha256(anchor.encode("utf-8", errors="replace")).hexdigest()[:16]


def _trace_ref(event_id: str) -> str:
    return _hash_ref(event_id)


def load_local_env(root: Path) -> None:
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


def _notes_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    notes: list[str] = []
    for item in value:
        text = _safe_str(item).strip()
        if text and text not in notes:
            notes.append(text)
    return notes


def _with_notes(result: dict[str, Any], *notes: str) -> dict[str, Any]:
    merged = _notes_list(result.get("notes"))
    for note in notes:
        text = _safe_str(note).strip()
        if text and text not in merged:
            merged.append(text)
    next_result = dict(result)
    if merged:
        next_result["notes"] = merged
    return next_result


def _message_segments(event: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        segment
        for segment in xinyu_qq_normalizer.message_segments_from_event(event)
        if isinstance(segment, dict)
    ]


def voice_segments_from_event(event: dict[str, Any]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for segment in _message_segments(event):
        segment_type = _safe_str(segment.get("type")).strip().lower()
        if segment_type in xinyu_qq_rich_context.VOICE_SEGMENT_TYPES:
            segments.append(segment)
    return segments


def _first_text(data: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        text = _safe_str(data.get(key)).strip()
        if text:
            return text
    return ""


def _provided_transcript_from_segment(segment: dict[str, Any]) -> str:
    data = xinyu_qq_normalizer.segment_data_value(segment)
    text = _first_text(data, ("transcript", "transcript_text", "recognized_text", "text"))
    if text and text.strip().lower() not in {"record", "voice", "audio"}:
        return text.strip()
    return ""


def _path_from_text(value: str) -> Path:
    text = value.strip().strip('"')
    lowered = text.lower()
    if lowered.startswith("file://"):
        return path_from_file_uri(text)
    return Path(text)


def _local_path_from_value(value: str, *, root: Path) -> Path | None:
    text = value.strip().strip('"')
    if not text:
        return None
    lowered = text.lower()
    if lowered.startswith(("http://", "https://", "base64://")):
        return None
    if not looks_like_file_path(text):
        return None
    path = _path_from_text(text)
    if not path.is_absolute():
        path = root / path
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        return None
    return resolved if resolved.is_file() else None


def _tmp_audio_path(root: Path, event_id: str, suffix: str) -> Path:
    clean_suffix = suffix if suffix.startswith(".") else f".{suffix}"
    if len(clean_suffix) > 12 or not re.match(r"^\.[a-zA-Z0-9]+$", clean_suffix):
        clean_suffix = ".mp3"
    path = root / TEMP_REL / f"{event_id}{clean_suffix.lower()}"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _write_base64_audio(root: Path, *, event_id: str, value: str, suffix: str) -> Path | None:
    text = value.strip()
    if text.lower().startswith("base64://"):
        text = text.split("://", 1)[1]
    if "," in text and text.lower().startswith("data:"):
        text = text.split(",", 1)[1]
    try:
        data = base64.b64decode(text, validate=False)
    except (ValueError, TypeError):
        return None
    if not data:
        return None
    path = _tmp_audio_path(root, event_id, suffix)
    path.write_bytes(data)
    return path


def _download_audio(root: Path, *, event_id: str, url: str, suffix: str) -> Path | None:
    parsed = urlparse(url.strip())
    if parsed.scheme == "file":
        path = path_from_file_uri(url)
        try:
            resolved = path.resolve(strict=True)
        except OSError:
            return None
        return resolved if resolved.is_file() else None
    if parsed.scheme not in {"http", "https"}:
        return None
    path = _tmp_audio_path(root, event_id, suffix)
    request = urllib.request.Request(url, headers={"User-Agent": "XinYu-QQ-Voice-Transcriber/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read(25 * 1024 * 1024)
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    if not data:
        return None
    path.write_bytes(data)
    return path


def _audio_ref_for_path(
    path: Path,
    *,
    status: str,
    resolved_by: str,
    attempts: list[str],
    error: str = "",
) -> VoiceAudioRef:
    size = 0
    try:
        size = path.stat().st_size
    except OSError:
        pass
    return VoiceAudioRef(
        status=status,
        audio_path=path,
        file_name=path.name,
        file_size=size,
        resolved_by=resolved_by,
        attempts=tuple(attempts),
        audio_ref_hash=_hash_ref(str(path.resolve()) if path.exists() else path.name),
        error=_one_line(error),
    )


def _audio_ref_unavailable(*, attempts: list[str], error: str) -> VoiceAudioRef:
    return VoiceAudioRef(
        status="voice_resolution_failed",
        attempts=tuple(attempts),
        error=_one_line(error),
    )


def _path_from_action_data(root: Path, data: dict[str, Any], *, event_id: str, out_format: str) -> Path | None:
    for key in ("file", "file_path", "path", "real_path", "url", "file_url", "download_url"):
        value = _safe_str(data.get(key)).strip()
        if not value:
            continue
        local = _local_path_from_value(value, root=root)
        if local is not None:
            return local
        downloaded = _download_audio(root, event_id=event_id, url=value, suffix=out_format)
        if downloaded is not None:
            return downloaded
    encoded = _first_text(data, ("base64", "data"))
    if encoded:
        return _write_base64_audio(root, event_id=event_id, value=encoded, suffix=out_format)
    return None


async def resolve_voice_audio(
    gateway: Any,
    websocket: Any,
    event: dict[str, Any],
    *,
    root: Path,
    out_format: str | None = None,
) -> VoiceAudioRef:
    segments = voice_segments_from_event(event)
    attempts: list[str] = []
    if not segments:
        return _audio_ref_unavailable(attempts=attempts, error="no_voice_segment")

    segment = segments[0]
    event_id = _event_id(event, segment)
    data = xinyu_qq_normalizer.segment_data_value(segment)
    out_format = (out_format or os.environ.get("XINYU_VOICE_STT_RECORD_FORMAT") or VOICE_OUT_FORMAT_DEFAULT).strip().lower()
    if out_format not in {"mp3", "wav", "m4a", "ogg", "flac", "amr", "wma", "spx"}:
        out_format = VOICE_OUT_FORMAT_DEFAULT

    file_id = _first_text(data, ("file", "file_id", "id", "fid"))
    if file_id:
        for params in ({"file": file_id, "out_format": out_format}, {"file_id": file_id, "out_format": out_format}):
            attempts.append("get_record")
            record_data = await gateway._onebot_action_data(websocket, "get_record", params)
            if not record_data:
                continue
            path = _path_from_action_data(root, record_data, event_id=event_id, out_format=out_format)
            if path is not None:
                return _audio_ref_for_path(path, status="resolved", resolved_by="get_record", attempts=attempts)

    direct_path_value = _first_text(data, ("path", "file_path", "local_path", "real_path"))
    if not direct_path_value and file_id and looks_like_file_path(file_id):
        direct_path_value = file_id
    if direct_path_value:
        attempts.append("direct_path")
        path = _local_path_from_value(direct_path_value, root=root)
        if path is not None:
            return _audio_ref_for_path(path, status="resolved", resolved_by="direct_path", attempts=attempts)

    direct_url = _first_text(data, ("url", "file_url", "download_url"))
    if direct_url:
        attempts.append("direct_url")
        suffix = Path(unquote(urlparse(direct_url).path)).suffix.lstrip(".") or out_format
        path = _download_audio(root, event_id=event_id, url=direct_url, suffix=suffix)
        if path is not None:
            return _audio_ref_for_path(path, status="resolved", resolved_by="direct_url", attempts=attempts)

    encoded = _first_text(data, ("base64", "data"))
    if encoded:
        attempts.append("base64")
        path = _write_base64_audio(root, event_id=event_id, value=encoded, suffix=out_format)
        if path is not None:
            return _audio_ref_for_path(path, status="resolved", resolved_by="base64", attempts=attempts)

    return _audio_ref_unavailable(attempts=attempts, error="voice_audio_not_resolved")


def _command_transcribe(root: Path, audio_path: Path) -> dict[str, Any] | None:
    command = os.environ.get("XINYU_VOICE_STT_COMMAND", "").strip()
    if not command:
        return None
    timeout = _as_float(os.environ.get("XINYU_VOICE_STT_TIMEOUT_SECONDS"), 120.0)
    if "{audio}" in command:
        command = command.replace("{audio}", str(audio_path))
        args = shlex.split(command, posix=False)
    else:
        args = shlex.split(command, posix=False) + [str(audio_path)]
    env = dict(os.environ)
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        completed = subprocess.run(
            args,
            cwd=str(root),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(1.0, timeout),
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "status": "transcription_failed",
            "engine": "command",
            "error": f"{type(exc).__name__}: {_one_line(exc)}",
        }
    stdout = (completed.stdout or "").strip()
    stderr = _one_line(completed.stderr, limit=300)
    if completed.returncode != 0:
        return {
            "status": "transcription_failed",
            "engine": "command",
            "error": f"returncode={completed.returncode} stderr={stderr}",
        }
    if not stdout:
        return {"status": "transcription_empty", "engine": "command", "error": "empty_stdout"}
    return {"status": "transcribed", "engine": "command", "transcript": stdout}


def _hearing_mode() -> str:
    mode = os.environ.get("XINYU_VOICE_HEARING_MODE", "stt").strip().lower()
    return mode if mode in HEARING_MODES else "stt"


def _hearing_fallback_mode() -> str:
    mode = os.environ.get("XINYU_VOICE_HEARING_FALLBACK", "stt").strip().lower()
    return mode if mode in HEARING_FALLBACK_MODES else "stt"


def _stt_api_key() -> str:
    return (
        os.environ.get("XINYU_VOICE_STT_API_KEY", "").strip()
        or os.environ.get("XINYU_OPENAI_API_KEY", "").strip()
        or os.environ.get("OPENAI_API_KEY", "").strip()
        or os.environ.get("XINYU_API_KEY", "").strip()
    )


def _stt_base_url() -> str:
    return (
        os.environ.get("XINYU_VOICE_STT_BASE_URL", "").strip()
        or os.environ.get("OPENAI_BASE_URL", "").strip()
        or os.environ.get("XINYU_BASE_URL", "").strip()
        or "https://api.openai.com/v1"
    ).rstrip("/")


def _stt_model() -> str:
    return (
        os.environ.get("XINYU_VOICE_STT_MODEL", "").strip()
        or os.environ.get("OPENAI_AUDIO_TRANSCRIPTION_MODEL", "").strip()
        or "whisper-1"
    )


def _mimo_hearing_api_key() -> str:
    return (
        os.environ.get("XINYU_VOICE_MIMO_API_KEY", "").strip()
        or _stt_api_key()
    )


def _mimo_hearing_base_url() -> str:
    return (
        os.environ.get("XINYU_VOICE_MIMO_BASE_URL", "").strip()
        or _stt_base_url()
    ).rstrip("/")


def _mimo_hearing_model() -> str:
    return (
        os.environ.get("XINYU_VOICE_MIMO_MODEL", "").strip()
        or MIMO_HEARING_DEFAULT_MODEL
    )


def _mimo_hearing_timeout_seconds() -> float:
    return max(
        1.0,
        _as_float(
            os.environ.get("XINYU_VOICE_MIMO_TIMEOUT_SECONDS"),
            _as_float(os.environ.get("XINYU_VOICE_STT_TIMEOUT_SECONDS"), 120.0),
        ),
    )


def _audio_mime_type(audio_path: Path) -> str:
    suffix = audio_path.suffix.lower()
    explicit = {
        ".amr": "audio/amr",
        ".flac": "audio/flac",
        ".m4a": "audio/mp4",
        ".mp3": "audio/mpeg",
        ".ogg": "audio/ogg",
        ".spx": "audio/ogg",
        ".wav": "audio/wav",
        ".wma": "audio/x-ms-wma",
    }.get(suffix)
    if explicit:
        return explicit
    guessed = mimetypes.guess_type(audio_path.name)[0]
    return guessed or "audio/mpeg"


def _audio_data_uri(audio_path: Path) -> tuple[str, str]:
    try:
        payload = audio_path.read_bytes()
    except OSError as exc:
        return "", f"audio_read_failed:{type(exc).__name__}"
    if not payload:
        return "", "audio_empty"
    if len(payload) > MIMO_HEARING_MAX_AUDIO_BYTES:
        return "", f"audio_too_large:{len(payload)}"
    encoded = base64.b64encode(payload).decode("ascii")
    return f"data:{_audio_mime_type(audio_path)};base64,{encoded}", ""


def _extract_transcript_text(response: Any) -> str:
    if isinstance(response, str):
        return response.strip()
    if isinstance(response, dict):
        return _safe_str(response.get("text") or response.get("transcript")).strip()
    text = getattr(response, "text", "")
    if text:
        return _safe_str(text).strip()
    try:
        data = response.model_dump()
    except Exception:
        data = {}
    if isinstance(data, dict):
        return _safe_str(data.get("text") or data.get("transcript")).strip()
    return ""


def _extract_chat_content_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        pieces: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = _safe_str(item.get("text") or item.get("content")).strip()
                if text:
                    pieces.append(text)
        return "\n".join(pieces).strip()
    if isinstance(content, dict):
        return _safe_str(content.get("text") or content.get("content")).strip()
    return ""


def _extract_chat_completion_text(response: Any) -> tuple[str, str]:
    if not isinstance(response, dict):
        return "", ""
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        return "", ""
    first = choices[0]
    if not isinstance(first, dict):
        return "", ""
    message = first.get("message")
    if not isinstance(message, dict):
        return "", ""
    content = _extract_chat_content_text(message.get("content"))
    reasoning = _extract_chat_content_text(message.get("reasoning_content"))
    return content, reasoning


def _normalize_transcript_text(text: str) -> str:
    clean = re.sub(r"\s+", " ", _safe_str(text)).strip()
    clean = clean.strip("`").strip()
    if len(clean) >= 2 and clean[0] == clean[-1] and clean[0] in {'"', "'"}:
        clean = clean[1:-1].strip()
    return clean


def _mimo_quality_issue(transcript: str) -> str:
    clean = _normalize_transcript_text(transcript)
    if not clean:
        return "empty_transcript"
    lower = clean.lower()
    if lower in MIMO_INAUDIBLE_MARKERS:
        return "inaudible"
    if any(marker in lower for marker in MIMO_META_MARKERS):
        return "non_transcript_reply"
    if len(clean) <= 1:
        return "too_short"
    if ("\n" in transcript or "1." in clean or "2." in clean) and any(marker in clean for marker in ("请问", "可能", "纠正", "内容分为")):
        return "non_transcript_reply"
    return ""


def _mimo_audio_transcribe(audio_path: Path) -> dict[str, Any]:
    if not _as_bool(os.environ.get("XINYU_VOICE_STT_ENABLED", "1"), default=True):
        return {"status": "transcription_disabled", "engine": "mimo_chat_audio"}
    api_key = _mimo_hearing_api_key()
    if not api_key:
        return {"status": "transcription_unavailable", "engine": "mimo_chat_audio", "error": "missing_api_key"}
    base_url = _mimo_hearing_base_url()
    if not base_url:
        return {"status": "transcription_unavailable", "engine": "mimo_chat_audio", "error": "missing_base_url"}
    model = _mimo_hearing_model()
    language = os.environ.get("XINYU_VOICE_STT_LANGUAGE", "zh").strip()
    timeout = _mimo_hearing_timeout_seconds()
    data_uri, uri_error = _audio_data_uri(audio_path)
    if uri_error:
        return {
            "status": "transcription_failed",
            "engine": "mimo_chat_audio",
            "model": model,
            "language": language,
            "error": uri_error,
        }
    prompt = (
        "You are a speech-to-text transcriber. "
        "Transcribe the speech into Simplified Chinese when the audio is Mandarin Chinese. "
        "Return only the transcript text. No explanation. No summary. No speaker labels. "
        "If the audio is unintelligible, output [[inaudible]]."
    )
    user_text = "Transcribe this audio and return only the transcript."
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": [
                    {"type": "input_audio", "input_audio": {"data": data_uri}},
                    {"type": "text", "text": user_text},
                ],
            },
        ],
        "thinking": {"type": "disabled"},
        "temperature": 0,
        "max_completion_tokens": 128,
    }
    request = urllib.request.Request(
        base_url + "/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {api_key}",
            "api-key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        try:
            error_body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            error_body = ""
        return {
            "status": "transcription_failed",
            "engine": "mimo_chat_audio",
            "model": model,
            "language": language,
            "error": f"http_{exc.code}:{_one_line(error_body, limit=320)}",
        }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {
            "status": "transcription_failed",
            "engine": "mimo_chat_audio",
            "model": model,
            "language": language,
            "error": f"{type(exc).__name__}: {_one_line(exc, limit=320)}",
        }
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "status": "transcription_failed",
            "engine": "mimo_chat_audio",
            "model": model,
            "language": language,
            "error": "non_json_response",
        }
    if isinstance(data, dict) and isinstance(data.get("error"), dict):
        message = _one_line(data["error"].get("message"), limit=320)
        return {
            "status": "transcription_failed",
            "engine": "mimo_chat_audio",
            "model": model,
            "language": language,
            "error": message or "api_error",
        }
    content, reasoning = _extract_chat_completion_text(data)
    transcript = _normalize_transcript_text(content or reasoning)
    quality_issue = _mimo_quality_issue(transcript)
    if quality_issue:
        return {
            "status": "transcription_unreliable",
            "engine": "mimo_chat_audio",
            "model": model,
            "language": language,
            "error": quality_issue,
            "notes": ["thinking_disabled", "reasoning_fallback_used"] if not content and reasoning else ["thinking_disabled"],
        }
    result = {
        "status": "transcribed",
        "engine": "mimo_chat_audio",
        "model": model,
        "language": language,
        "transcript": transcript,
        "notes": ["thinking_disabled"],
    }
    if not content and reasoning:
        result["notes"] = ["thinking_disabled", "reasoning_fallback_used"]
    return result


def _openai_transcribe(audio_path: Path) -> dict[str, Any]:
    if not _as_bool(os.environ.get("XINYU_VOICE_STT_ENABLED", "1"), default=True):
        return {"status": "transcription_disabled", "engine": "openai_compatible"}
    api_key = _stt_api_key()
    if not api_key:
        return {"status": "transcription_unavailable", "engine": "openai_compatible", "error": "missing_api_key"}
    model = _stt_model()
    language = os.environ.get("XINYU_VOICE_STT_LANGUAGE", "zh").strip()
    timeout = _as_float(os.environ.get("XINYU_VOICE_STT_TIMEOUT_SECONDS"), 120.0)
    try:
        from openai import OpenAI
    except ImportError as exc:
        return {
            "status": "transcription_unavailable",
            "engine": "openai_compatible",
            "model": model,
            "language": language,
            "error": f"openai_sdk_missing:{type(exc).__name__}",
        }
    try:
        client = OpenAI(api_key=api_key, base_url=_stt_base_url())
        with audio_path.open("rb") as audio_file:
            response = client.audio.transcriptions.create(
                file=audio_file,
                model=model,
                language=language or None,
                response_format="json",
                timeout=timeout,
            )
    except Exception as exc:
        return {
            "status": "transcription_failed",
            "engine": "openai_compatible",
            "model": model,
            "language": language,
            "error": f"{type(exc).__name__}: {_one_line(exc, limit=300)}",
        }
    transcript = _extract_transcript_text(response)
    if not transcript:
        return {
            "status": "transcription_empty",
            "engine": "openai_compatible",
            "model": model,
            "language": language,
            "error": "empty_transcript",
        }
    return {
        "status": "transcribed",
        "engine": "openai_compatible",
        "model": model,
        "language": language,
        "transcript": transcript,
    }


def _legacy_stt_transcribe(root: Path, audio_path: Path) -> dict[str, Any]:
    command_result = _command_transcribe(root, audio_path)
    if command_result is not None:
        return command_result
    return _openai_transcribe(audio_path)


def transcribe_audio_file(root: Path, audio_path: Path) -> dict[str, Any]:
    load_local_env(root)
    mode = _hearing_mode()
    if mode == "mimo_audio":
        primary = _with_notes(_mimo_audio_transcribe(audio_path), "hearing_mode:mimo_audio")
        if _safe_str(primary.get("status")) == "transcribed":
            return primary
        if _hearing_fallback_mode() == "stt":
            fallback = _legacy_stt_transcribe(root, audio_path)
            return _with_notes(
                fallback,
                "hearing_mode:mimo_audio",
                "fallback_mode:stt",
                f"primary_engine:{_safe_str(primary.get('engine')) or 'mimo_chat_audio'}",
                f"primary_status:{_safe_str(primary.get('status')) or 'unknown'}",
                f"primary_reason:{_safe_str(primary.get('error')) or 'primary_failed'}",
            )
        return primary
    return _with_notes(_legacy_stt_transcribe(root, audio_path), "hearing_mode:stt")


def _result_from_stt(
    event: dict[str, Any],
    segment: dict[str, Any] | None,
    *,
    audio_ref: VoiceAudioRef | None,
    stt: dict[str, Any],
    recorded_at: str,
) -> VoiceTranscriptResult:
    event_id = _event_id(event, segment)
    confidence: float | None = None
    if "confidence" in stt:
        try:
            confidence = float(stt.get("confidence"))
        except (TypeError, ValueError):
            confidence = None
    return VoiceTranscriptResult(
        status=_safe_str(stt.get("status") or "transcription_failed"),
        event_id=event_id,
        message_id=_event_message_id(event),
        transcript=_safe_str(stt.get("transcript") or stt.get("text")).strip(),
        confidence=confidence,
        engine=_safe_str(stt.get("engine")),
        model=_safe_str(stt.get("model")),
        language=_safe_str(stt.get("language")),
        trace_ref=_trace_ref(event_id),
        audio_ref=audio_ref,
        notes=tuple(str(item) for item in stt.get("notes", []) if str(item).strip())
        if isinstance(stt.get("notes"), list)
        else (),
        error=_one_line(stt.get("error")),
        recorded_at=recorded_at,
    )


def append_voice_transcript_trace(root: Path, result: VoiceTranscriptResult, *, target: Any | None = None) -> Path:
    audio = result.audio_ref or VoiceAudioRef(status="missing")
    transcript_len = len(result.transcript.strip())
    row = {
        "recorded_at": result.recorded_at or _now_iso(),
        "event_id": result.event_id,
        "message_id": result.message_id,
        "status": result.status,
        "engine": result.engine,
        "model": result.model,
        "language": result.language,
        "transcript": result.transcript if result.transcribed else "",
        "transcript_len": transcript_len,
        "transcript_hash": _hash_ref(result.transcript) if transcript_len else "none",
        "confidence": result.confidence,
        "message_kind": _safe_str(getattr(target, "message_kind", "")),
        "user_id_hash": _hash_id(_safe_str(getattr(target, "user_id", ""))),
        "group_id_hash": _hash_id(_safe_str(getattr(target, "group_id", ""))),
        "audio_resolution_status": audio.status,
        "audio_resolved_by": audio.resolved_by,
        "audio_file_size": audio.file_size,
        "audio_ref_hash": audio.audio_ref_hash,
        "resolution_attempts": list(audio.attempts),
        "error": _one_line(result.error or audio.error),
        "raw_audio_path_retained": False,
        "raw_audio_bytes_retained": False,
        "stable_memory_write": "blocked",
    }
    path = root / TRACE_REL
    append_jsonl(path, row)
    return path


async def transcribe_owner_private_voice(
    gateway: Any,
    websocket: Any,
    event: dict[str, Any],
    *,
    target: Any | None = None,
) -> VoiceTranscriptResult:
    root = Path(getattr(gateway, "xinyu_dir", Path(__file__).resolve().parent)).resolve()
    segments = voice_segments_from_event(event)
    segment = segments[0] if segments else None
    recorded_at = _now_iso()
    event_id = _event_id(event, segment)

    if segment is not None:
        provided = _provided_transcript_from_segment(segment)
        if provided:
            result = VoiceTranscriptResult(
                status="transcribed",
                event_id=event_id,
                message_id=_event_message_id(event),
                transcript=provided,
                engine="onebot_payload",
                trace_ref=_trace_ref(event_id),
                recorded_at=recorded_at,
            )
            append_voice_transcript_trace(root, result, target=target)
            return result

    try:
        audio_ref = await resolve_voice_audio(gateway, websocket, event, root=root)
    except Exception as exc:
        audio_ref = _audio_ref_unavailable(attempts=["resolve_exception"], error=f"{type(exc).__name__}: {exc}")
    if audio_ref.audio_path is None or audio_ref.status != "resolved":
        result = VoiceTranscriptResult(
            status=audio_ref.status,
            event_id=event_id,
            message_id=_event_message_id(event),
            trace_ref=_trace_ref(event_id),
            audio_ref=audio_ref,
            error=audio_ref.error or "voice_audio_not_resolved",
            recorded_at=recorded_at,
        )
        append_voice_transcript_trace(root, result, target=target)
        return result

    try:
        stt = transcribe_audio_file(root, audio_ref.audio_path)
    except Exception as exc:
        stt = {"status": "transcription_failed", "error": f"{type(exc).__name__}: {_one_line(exc)}"}
    result = _result_from_stt(event, segment, audio_ref=audio_ref, stt=stt, recorded_at=recorded_at)
    append_voice_transcript_trace(root, result, target=target)
    return result


def transcript_status_is_failure(status: Any) -> bool:
    text = _safe_str(status).strip().lower()
    return any(marker in text for marker in VOICE_FAILURE_MARKERS)
