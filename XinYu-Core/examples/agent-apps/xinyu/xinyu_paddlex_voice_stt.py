from __future__ import annotations

import argparse
import contextlib
import os
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from typing import Any, Iterator


def _configure_stdio() -> None:
    for name, errors in (("stdout", "strict"), ("stderr", "backslashreplace")):
        stream = getattr(sys, name, None)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors=errors)


def _as_float(value: str | None, default: float) -> float:
    try:
        return float(value) if value not in (None, "") else default
    except ValueError:
        return default


def _as_int(value: str | None, default: int) -> int:
    try:
        return int(float(value)) if value not in (None, "") else default
    except ValueError:
        return default


def _env(name: str, default: str = "", *aliases: str) -> str:
    for key in (name, *aliases):
        value = os.environ.get(key)
        if value not in (None, ""):
            return value
    return default


def _clean_text(value: Any) -> str:
    text = " ".join(str(value or "").split())
    return text.strip()


def _ffmpeg_path() -> str:
    configured = os.environ.get("XINYU_FFMPEG_PATH", "").strip()
    if configured:
        return configured
    found = shutil.which("ffmpeg")
    if found:
        return found
    return "ffmpeg"


def _convert_to_wav(audio_path: Path, work_dir: Path) -> Path:
    wav_path = work_dir / "input.wav"
    timeout = _as_int(
        _env(
            "XINYU_PADDLEX_STT_FFMPEG_TIMEOUT_SECONDS",
            "",
            "XINYU_PADDLEx_STT_FFMPEG_TIMEOUT_SECONDS",
        ),
        60,
    )
    completed = subprocess.run(
        [
            _ffmpeg_path(),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(audio_path),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-acodec",
            "pcm_s16le",
            str(wav_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=max(1, timeout),
        check=False,
    )
    if completed.returncode != 0 or not wav_path.is_file():
        err = " ".join((completed.stderr or completed.stdout or "ffmpeg_failed").split())
        raise RuntimeError(f"ffmpeg_convert_failed:{err[:300]}")
    return wav_path


def _wav_energy(wav_path: Path) -> tuple[float, float]:
    with wave.open(str(wav_path), "rb") as wav_file:
        sample_width = wav_file.getsampwidth()
        frames = wav_file.readframes(wav_file.getnframes())
    if sample_width != 2 or not frames:
        return 0.0, 0.0
    count = len(frames) // 2
    if count <= 0:
        return 0.0, 0.0
    total = 0.0
    peak = 0
    for index in range(0, len(frames) - 1, 2):
        sample = int.from_bytes(frames[index : index + 2], "little", signed=True)
        abs_sample = abs(sample)
        peak = max(peak, abs_sample)
        total += float(sample * sample)
    rms = (total / count) ** 0.5 / 32768.0
    peak_norm = peak / 32768.0
    return rms, peak_norm


def _is_low_energy_silence(wav_path: Path) -> bool:
    rms, peak = _wav_energy(wav_path)
    min_rms = _as_float(
        _env("XINYU_PADDLEX_STT_MIN_RMS", "", "XINYU_PADDLEx_STT_MIN_RMS"),
        0.0003,
    )
    min_peak = _as_float(
        _env("XINYU_PADDLEX_STT_MIN_PEAK", "", "XINYU_PADDLEx_STT_MIN_PEAK"),
        0.002,
    )
    return rms < min_rms and peak < min_peak


@contextlib.contextmanager
def _redirect_process_output(log_path: Path) -> Iterator[None]:
    sys.stdout.flush()
    sys.stderr.flush()
    saved_stdout = os.dup(1)
    saved_stderr = os.dup(2)
    try:
        with log_path.open("ab") as sink:
            os.dup2(sink.fileno(), 1)
            os.dup2(sink.fileno(), 2)
            yield
            sys.stdout.flush()
            sys.stderr.flush()
    finally:
        os.dup2(saved_stdout, 1)
        os.dup2(saved_stderr, 2)
        os.close(saved_stdout)
        os.close(saved_stderr)


def _result_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    data = getattr(value, "json", None)
    if isinstance(data, dict):
        return data
    return {}


def _extract_result_payload(value: Any) -> dict[str, Any]:
    data = _result_dict(value)
    if isinstance(data.get("res"), dict):
        data = data["res"]
    result = data.get("result")
    return result if isinstance(result, dict) else {}


def _looks_like_silence(result: dict[str, Any], text: str) -> bool:
    trivial = text in {"", ".", "...", "\u3002", "\u2026"}
    if not trivial:
        return False
    threshold = _as_float(
        _env(
            "XINYU_PADDLEX_STT_NO_SPEECH_THRESHOLD",
            "",
            "XINYU_PADDLEx_STT_NO_SPEECH_THRESHOLD",
        ),
        0.75,
    )
    segments = result.get("segments")
    if not isinstance(segments, list):
        return trivial
    probs: list[float] = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        try:
            probs.append(float(segment.get("no_speech_prob")))
        except (TypeError, ValueError):
            continue
    return trivial and (not probs or max(probs) >= threshold)


def _build_pipeline(model_name: str, device: str):
    from paddlex import create_pipeline

    cfg = {
        "pipeline_name": "multilingual_speech_recognition",
        "SubModules": {
            "MultilingualSpeechRecognition": {
                "module_name": "multilingual_speech_recognition",
                "model_name": model_name,
                "model_dir": None,
                "batch_size": 1,
            }
        },
    }
    return create_pipeline(config=cfg, device=device)


def _configure_pipeline(pipeline: Any, language: str) -> None:
    model = getattr(pipeline, "multilingual_speech_recognition_model", None)
    config = getattr(model, "config", None)
    if config is None:
        return
    try:
        config["verbose"] = False
        config["language"] = None if language.lower() in {"", "auto", "none", "null"} else language
    except Exception:
        return


def transcribe(audio_path: Path) -> str:
    if not audio_path.is_file():
        raise FileNotFoundError(str(audio_path))
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    os.environ.setdefault("GLOG_minloglevel", "2")
    os.environ.setdefault("FLAGS_minloglevel", "2")

    model_name = (
        _env("XINYU_PADDLEX_STT_MODEL", "whisper_tiny", "XINYU_PADDLEx_STT_MODEL").strip()
        or "whisper_tiny"
    )
    device = _env("XINYU_PADDLEX_STT_DEVICE", "cpu", "XINYU_PADDLEx_STT_DEVICE").strip() or "cpu"
    language = _env("XINYU_PADDLEX_STT_LANGUAGE", "auto", "XINYU_PADDLEx_STT_LANGUAGE").strip()

    work_dir = Path(tempfile.mkdtemp(prefix="xinyu_paddlex_stt_"))
    try:
        wav_path = _convert_to_wav(audio_path, work_dir)
        if _is_low_energy_silence(wav_path):
            return ""
        log_path = work_dir / "paddlex.log"
        with _redirect_process_output(log_path):
            pipeline = _build_pipeline(model_name, device)
            _configure_pipeline(pipeline, language)
            results = list(pipeline.predict(str(wav_path)))
        texts: list[str] = []
        for item in results:
            result = _extract_result_payload(item)
            text = _clean_text(result.get("text"))
            if _looks_like_silence(result, text):
                continue
            if text:
                texts.append(text)
        return _clean_text(" ".join(texts))
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    parser = argparse.ArgumentParser(description="XinYu PaddleX voice STT command")
    parser.add_argument("audio", help="Audio file path")
    args = parser.parse_args(argv)
    try:
        text = transcribe(Path(args.audio).expanduser().resolve())
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    if not text:
        print("empty_transcript", file=sys.stderr)
        return 2
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
