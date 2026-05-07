from __future__ import annotations

import os
import re
import shutil
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from xinyu_sticker_import import (
    REFERENCE_INDEX_NAME,
    apply_import_plan,
    build_import_plan_for_sources,
    default_vision_python,
    ensure_unsorted_dir,
)
from xinyu_sticker_pack import SUPPORTED_STICKER_SUFFIXES, mood_dir_name, shared_asset_sticker_dir


MAX_STICKER_BYTES = 12 * 1024 * 1024
IMPORTABLE_STICKER_SUFFIXES = frozenset({*SUPPORTED_STICKER_SUFFIXES, ".avif"})


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


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


def _as_int(value: Any, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _payload_path(value: str) -> Path:
    text = value.strip().strip('"')
    if text.lower().startswith("file://"):
        parsed = urlparse(text)
        path_text = parsed.path
        if os.name == "nt" and len(path_text) > 2 and path_text[0] == "/" and path_text[2] == ":":
            path_text = path_text[1:]
        return Path(unquote(path_text))
    return Path(text)


def _safe_inside(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _resolve_asset_dir(xinyu_dir: Path, payload: dict[str, Any]) -> Path:
    custom = _safe_str(payload.get("asset_dir")).strip()
    if custom and _as_bool(payload.get("allow_custom_asset_dir"), default=False):
        return Path(custom).expanduser().resolve()
    shared = shared_asset_sticker_dir(xinyu_dir)
    if shared is None:
        raise RuntimeError("shared sticker asset directory is not available")
    return shared.resolve()


def _suffix_from_content_type(content_type: str) -> str:
    media_type = content_type.split(";", 1)[0].strip().lower()
    return {
        "image/avif": ".avif",
        "image/bmp": ".bmp",
        "image/gif": ".gif",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }.get(media_type, "")


def _suffix_from_bytes(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    if data.startswith(b"BM"):
        return ".bmp"
    if len(data) >= 12 and data[4:8] == b"ftyp" and data[8:12] in {b"avif", b"avis"}:
        return ".avif"
    return ""


def _suffix_from_url(url: str) -> str:
    path = unquote(urlparse(url).path or "")
    suffix = Path(path).suffix.lower()
    return suffix if suffix in IMPORTABLE_STICKER_SUFFIXES else ""


def _sanitize_filename(name: str, suffix: str) -> str:
    raw = unquote(name).strip().strip('"')
    if raw.lower().startswith(("http://", "https://", "file://")):
        raw = Path(unquote(urlparse(raw).path or "")).name
    raw = Path(raw).name
    raw = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", raw).strip(" .")
    if not raw:
        raw = "qq-sticker"
    path = Path(raw)
    if suffix and path.suffix.lower() not in IMPORTABLE_STICKER_SUFFIXES:
        raw = f"{path.stem or 'qq-sticker'}{suffix}"
    elif not path.suffix:
        raw = f"{raw}{suffix or '.png'}"
    if len(raw) > 140:
        path = Path(raw)
        raw = f"{path.stem[:100].rstrip(' ._-') or 'qq-sticker'}{path.suffix}"
    return raw


def _dedupe_destination(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(2, 1000):
        candidate = path.with_name(f"{stem}-{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"could not allocate sticker destination for {path}")


def _download_sticker(url: str, max_bytes: int) -> tuple[bytes, str, str]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RuntimeError("sticker URL must use http or https")
    if parsed.username or parsed.password:
        raise RuntimeError("sticker URL credentials are not allowed")
    request = urllib.request.Request(url, headers={"User-Agent": "XinYuStickerIngest/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            final_url = response.geturl()
            content_type = response.headers.get("content-type", "application/octet-stream")
            data = response.read(max_bytes + 1)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"sticker download failed with HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"sticker download failed: {exc.reason}") from exc
    if len(data) > max_bytes:
        raise RuntimeError(f"sticker download exceeds max bytes: {max_bytes}")
    return data, final_url, content_type


def _copy_local_sticker(payload: dict[str, Any], inbox: Path, max_bytes: int) -> Path:
    raw_path = _safe_str(payload.get("file_path") or payload.get("path")).strip()
    source = _payload_path(raw_path)
    try:
        resolved = source.resolve(strict=True)
    except OSError as exc:
        raise RuntimeError("sticker file not found") from exc
    if not resolved.is_file():
        raise RuntimeError("sticker path is not a file")
    if resolved.stat().st_size > max_bytes:
        raise RuntimeError(f"sticker file exceeds max bytes: {max_bytes}")
    suffix = resolved.suffix.lower()
    if suffix not in IMPORTABLE_STICKER_SUFFIXES:
        sample = resolved.read_bytes()[:32]
        suffix = _suffix_from_bytes(sample)
    if suffix not in IMPORTABLE_STICKER_SUFFIXES:
        raise RuntimeError("unsupported sticker image type")
    name = (
        _safe_str(payload.get("file_name")).strip()
        or _safe_str(payload.get("name")).strip()
        or _safe_str(payload.get("summary")).strip()
        or resolved.name
    )
    destination = _dedupe_destination(inbox / _sanitize_filename(name, suffix))
    if not _safe_inside(destination, inbox):
        raise RuntimeError("invalid sticker destination")
    shutil.copy2(resolved, destination)
    return destination


def _save_url_sticker(payload: dict[str, Any], inbox: Path, max_bytes: int) -> Path:
    url = _safe_str(payload.get("file_url") or payload.get("url")).strip()
    data, final_url, content_type = _download_sticker(url, max_bytes)
    suffix = (
        _suffix_from_content_type(content_type)
        or _suffix_from_url(final_url)
        or _suffix_from_bytes(data[:32])
    )
    if suffix not in IMPORTABLE_STICKER_SUFFIXES:
        raise RuntimeError("unsupported sticker download type")
    name = (
        _safe_str(payload.get("file_name")).strip()
        or _safe_str(payload.get("name")).strip()
        or _safe_str(payload.get("summary")).strip()
        or Path(unquote(urlparse(final_url).path or "")).name
        or "qq-sticker"
    )
    destination = _dedupe_destination(inbox / _sanitize_filename(name, suffix))
    if not _safe_inside(destination, inbox):
        raise RuntimeError("invalid sticker destination")
    destination.write_bytes(data)
    return destination


def _sticker_reply(result: dict[str, Any]) -> str:
    if not result.get("accepted"):
        return "这个表情还没拿到可下载的图片文件，暂时没能收进表情库。"
    if not result.get("imported"):
        return "收到了，先放进待分类了。"
    mood_label = _safe_str(result.get("mood_label")).strip()
    if result.get("mood") == "unclear":
        return f"收到了，已经放进表情库的{mood_label or mood_dir_name('unclear')}里。"
    return f"收到了，已经放进表情库：{mood_label or result.get('mood') or '已分类'}。"


def import_sticker_from_payload(xinyu_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
    payload = payload or {}
    file_path = _safe_str(payload.get("file_path") or payload.get("path")).strip()
    file_url = _safe_str(payload.get("file_url") or payload.get("url")).strip()
    notes: list[str] = ["sticker_import", "no_agent_turn"]
    if not file_path and not file_url:
        result = {
            "accepted": False,
            "imported": False,
            "reply": "",
            "notes": [*notes, "missing_file_path_or_url"],
        }
        result["reply"] = _sticker_reply(result)
        return result

    max_bytes = min(_as_int(payload.get("max_bytes"), MAX_STICKER_BYTES), MAX_STICKER_BYTES)
    if max_bytes <= 0:
        max_bytes = MAX_STICKER_BYTES

    base = _resolve_asset_dir(xinyu_dir, payload)
    base.mkdir(parents=True, exist_ok=True)
    inbox = ensure_unsorted_dir(base)
    if not _safe_inside(inbox, base):
        raise RuntimeError("sticker inbox is outside asset directory")

    try:
        saved = _copy_local_sticker(payload, inbox, max_bytes) if file_path else _save_url_sticker(payload, inbox, max_bytes)
    except RuntimeError as exc:
        result = {
            "accepted": False,
            "imported": False,
            "reply": "",
            "notes": [*notes, str(exc)],
        }
        result["reply"] = _sticker_reply(result)
        return result

    vision_python = default_vision_python(xinyu_dir)
    use_clip = _as_bool(payload.get("use_clip"), default=True) and vision_python is not None
    use_ocr = _as_bool(payload.get("use_ocr"), default=True)
    if _as_bool(payload.get("use_clip"), default=True) and vision_python is None:
        notes.append("clip_skipped:vision_python_missing")
    reference_index = base / REFERENCE_INDEX_NAME
    if not reference_index.is_file():
        reference_index = None

    plan = build_import_plan_for_sources(
        base,
        [saved],
        use_clip=use_clip,
        use_ocr=use_ocr,
        vision_python=vision_python,
        reference_index=reference_index,
    )
    applied = apply_import_plan(base, plan) if plan else {
        "moved": 0,
        "converted": 0,
        "failed": 0,
        "failures": [],
        "manifest_path": str(base / "manifest.generated.json"),
        "items": [],
    }
    item = applied.get("items", [])[0] if isinstance(applied.get("items"), list) and applied.get("items") else {}
    mood = _safe_str(item.get("mood") if isinstance(item, dict) else "").strip()
    destination = _safe_str(item.get("destination") if isinstance(item, dict) else "").strip()
    result = {
        "accepted": True,
        "imported": int(applied.get("moved") or 0) > 0,
        "stored_path": str(saved),
        "asset_dir": str(base),
        "destination": destination,
        "mood": mood,
        "mood_label": mood_dir_name(mood) if mood else "",
        "confidence": _safe_str(item.get("confidence") if isinstance(item, dict) else "").strip(),
        "manifest_path": applied.get("manifest_path", ""),
        "moved": int(applied.get("moved") or 0),
        "converted": int(applied.get("converted") or 0),
        "failed": int(applied.get("failed") or 0),
        "failures": applied.get("failures", []),
        "items": applied.get("items", []),
        "imported_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "reply": "",
        "notes": notes,
    }
    result["reply"] = _sticker_reply(result)
    return result
