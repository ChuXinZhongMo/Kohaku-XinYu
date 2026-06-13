from __future__ import annotations

import base64
import io
import json
import mimetypes
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


IMAGE_SUFFIXES = frozenset({".bmp", ".gif", ".jfif", ".jpeg", ".jpg", ".png", ".webp"})
ANIMATED_CONTACT_SHEET_SUFFIXES = frozenset({".gif", ".png", ".webp"})
IMAGE_REFERENCE_MARKERS = (
    "图",
    "图片",
    "截图",
    "照片",
    "这张",
    "那张",
    "这个图",
    "看图",
    "图里",
    "图上",
    "画面",
    "表情包",
    "什么意思",
    "啥意思",
    "什么情况",
    "read this image",
    "look at this image",
    "screenshot",
    "picture",
    "image",
    "meme",
    "sticker",
)
DEFAULT_MAX_IMAGE_BYTES = 4 * 1024 * 1024
MIN_IMAGE_VISION_BYTES = 64 * 1024
LOCAL_ENV_FILES = ("xinyu.local.env", ".env")


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


def _metadata(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


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


def _is_image_name(value: str) -> bool:
    return Path(_safe_str(value)).suffix.lower() in IMAGE_SUFFIXES


def is_image_learning_payload(payload: dict[str, Any], result: dict[str, Any] | None = None) -> bool:
    metadata = _metadata(payload)
    if _safe_str(metadata.get("segment_type")).strip().lower() == "image":
        return True
    for key in ("file_name", "name", "title", "label", "file_path", "path", "file_url", "url"):
        if _is_image_name(_safe_str(payload.get(key))):
            return True
    result = result or {}
    for stored in result.get("stored_paths") if isinstance(result.get("stored_paths"), list) else []:
        if _is_image_name(_safe_str(stored)):
            return True
    return False


def wants_image_context(text: str, *, image_only: bool) -> bool:
    stripped = text.strip()
    if image_only:
        return True
    lowered = stripped.lower()
    return any(marker.lower() in lowered or marker in stripped for marker in IMAGE_REFERENCE_MARKERS)


def _resolve_under_root(root: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def _first_existing_image_path(root: Path, payload: dict[str, Any], result: dict[str, Any]) -> Path | None:
    candidates: list[str] = []
    candidates.extend(_safe_str(payload.get(key)).strip() for key in ("file_path", "path") if _safe_str(payload.get(key)).strip())
    stored_paths = result.get("stored_paths")
    if isinstance(stored_paths, list):
        candidates.extend(_safe_str(item).strip() for item in stored_paths if _safe_str(item).strip())
    for candidate in candidates:
        try:
            path = _resolve_under_root(root, candidate)
        except OSError:
            continue
        if path.is_file():
            return path
    return None


def _read_text_path(root: Path, rel_path: str, *, limit: int = 3500) -> str:
    if not rel_path:
        return ""
    try:
        path = _resolve_under_root(root, rel_path)
        if not path.is_file():
            return ""
        text = path.read_text(encoding="utf-8-sig", errors="replace").strip()
    except OSError:
        return ""
    if len(text) <= limit:
        return text
    return text[: int(limit * 0.7)].rstrip() + "\n\n[image OCR text truncated]\n\n" + text[-int(limit * 0.3) :].lstrip()


def _vision_enabled() -> bool:
    value = os.environ.get("XINYU_IMAGE_VISION_ENABLED", "0")
    return _as_bool(value, default=False)


def _vision_model() -> str:
    candidates = _vision_model_candidates()
    return candidates[0] if candidates else "gpt-4o-mini"


def _vision_base_url() -> str:
    return (
        os.environ.get("XINYU_IMAGE_VISION_BASE_URL", "").strip()
        or os.environ.get("XINYU_BASE_URL", "").strip()
        or os.environ.get("OPENAI_BASE_URL", "").strip()
        or "https://api.openai.com/v1"
    ).rstrip("/")


def _vision_api_key() -> str:
    candidates = _vision_api_key_candidates()
    return candidates[0] if candidates else ""


def _dedupe_non_empty(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _safe_str(value).strip()
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result


def _vision_model_candidates() -> list[str]:
    return _dedupe_non_empty(
        [
            os.environ.get("XINYU_IMAGE_VISION_MODEL", ""),
            os.environ.get("XINYU_LLM_MODEL", ""),
            "gpt-4o-mini",
        ]
    )


def _vision_api_key_candidates() -> list[str]:
    return _dedupe_non_empty(
        [
            os.environ.get("XINYU_IMAGE_VISION_API_KEY", ""),
            os.environ.get("XINYU_API_KEY", ""),
            os.environ.get("XINYU_OPENAI_API_KEY", ""),
            os.environ.get("OPENAI_API_KEY", ""),
        ]
    )


def _mime_type(path: Path, payload: dict[str, Any]) -> str:
    guessed = mimetypes.guess_type(_safe_str(payload.get("file_name") or path.name))[0]
    return guessed or mimetypes.guess_type(path.name)[0] or "image/png"


def _vision_max_image_bytes() -> int:
    return max(MIN_IMAGE_VISION_BYTES, _as_int(os.environ.get("XINYU_IMAGE_VISION_MAX_BYTES"), DEFAULT_MAX_IMAGE_BYTES))


def _vision_max_tokens() -> int:
    return max(256, min(2000, _as_int(os.environ.get("XINYU_IMAGE_VISION_MAX_TOKENS"), 900)))


def _animated_contact_sheet_data_uri(path: Path, *, max_bytes: int, note_prefix: str) -> tuple[str, str, list[str]]:
    try:
        from PIL import Image, ImageSequence
    except ImportError:
        return "", f"{note_prefix}_pillow_missing", []
    try:
        image = Image.open(path)
    except OSError as exc:
        return "", f"{note_prefix}_open_failed:{type(exc).__name__}", []

    total_frames = max(1, int(getattr(image, "n_frames", 1) or 1))
    if total_frames <= 1:
        return "", f"{note_prefix}_single_frame", []
    max_frames = max(1, min(12, _as_int(os.environ.get("XINYU_IMAGE_GIF_MAX_FRAMES"), 8)))
    if total_frames <= max_frames:
        sample_indexes = list(range(total_frames))
    else:
        sample_indexes = sorted({round(index * (total_frames - 1) / (max_frames - 1)) for index in range(max_frames)})

    tile_w = max(120, min(480, _as_int(os.environ.get("XINYU_IMAGE_GIF_TILE_WIDTH"), 260)))
    tile_h = max(90, min(360, _as_int(os.environ.get("XINYU_IMAGE_GIF_TILE_HEIGHT"), 200)))
    frames = []
    try:
        for index, frame in enumerate(ImageSequence.Iterator(image)):
            if index not in sample_indexes:
                continue
            rendered = frame.convert("RGBA")
            rendered.thumbnail((tile_w, tile_h), Image.Resampling.LANCZOS)
            tile = Image.new("RGBA", (tile_w, tile_h), (255, 255, 255, 255))
            tile.alpha_composite(rendered, ((tile_w - rendered.width) // 2, (tile_h - rendered.height) // 2))
            frames.append(tile.convert("RGB"))
    except Exception as exc:
        return "", f"{note_prefix}_frame_decode_failed:{type(exc).__name__}", []

    if not frames:
        return "", f"{note_prefix}_no_decodable_frames", []
    cols = min(4, len(frames))
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile_w, rows * tile_h), (255, 255, 255))
    for index, frame in enumerate(frames):
        sheet.paste(frame, ((index % cols) * tile_w, (index // cols) * tile_h))

    buffer = io.BytesIO()
    try:
        sheet.save(buffer, format="PNG", optimize=True)
    except OSError as exc:
        return "", f"{note_prefix}_contact_sheet_save_failed:{type(exc).__name__}", []
    data = buffer.getvalue()
    if len(data) > max_bytes:
        return "", f"{note_prefix}_contact_sheet_too_large:{len(data)}", []
    notes = [f"{note_prefix}_frames_sampled:{len(frames)}", f"{note_prefix}_total_frames:{total_frames}"]
    return f"data:image/png;base64,{base64.b64encode(data).decode('ascii')}", "", notes


def _gif_contact_sheet_data_uri(path: Path, *, max_bytes: int) -> tuple[str, str, list[str]]:
    return _animated_contact_sheet_data_uri(path, max_bytes=max_bytes, note_prefix="gif")


def _vision_max_dimension() -> int:
    return max(320, min(4096, _as_int(os.environ.get("XINYU_IMAGE_VISION_MAX_DIMENSION"), 1600)))


def _image_exceeds_vision_max_dimension(path: Path) -> bool:
    try:
        from PIL import Image
    except ImportError:
        return False
    try:
        with Image.open(path) as image:
            width, height = image.size
    except OSError:
        return False
    return max(width, height) > _vision_max_dimension()


def _compressed_static_image_data_uri(
    path: Path,
    *,
    max_bytes: int,
    note_prefix: str = "image",
) -> tuple[str, str, list[str]]:
    try:
        from PIL import Image
    except ImportError:
        return "", f"{note_prefix}_compress_pillow_missing", []
    try:
        image = Image.open(path)
        try:
            image.seek(0)
        except EOFError:
            pass
        source = image.convert("RGBA")
    except OSError as exc:
        return "", f"{note_prefix}_compress_open_failed:{type(exc).__name__}", []

    max_dimension = _vision_max_dimension()
    last_size = 0
    for scale in (1.0, 0.75, 0.5, 0.35):
        bound = max(240, int(max_dimension * scale))
        rendered = source.copy()
        rendered.thumbnail((bound, bound), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", rendered.size, (255, 255, 255))
        canvas.paste(rendered, mask=rendered.getchannel("A"))
        for quality in (86, 74, 62, 50, 40):
            buffer = io.BytesIO()
            try:
                canvas.save(buffer, format="JPEG", quality=quality, optimize=True)
            except OSError as exc:
                return "", f"{note_prefix}_compress_save_failed:{type(exc).__name__}", []
            data = buffer.getvalue()
            last_size = len(data)
            if last_size <= max_bytes:
                notes = [
                    f"{note_prefix}_compressed_for_vision:{canvas.width}x{canvas.height}",
                    f"{note_prefix}_compressed_bytes:{last_size}",
                ]
                return f"data:image/jpeg;base64,{base64.b64encode(data).decode('ascii')}", "", notes
    return "", f"{note_prefix}_compressed_too_large:{last_size}", []


def _image_data_uri(path: Path, payload: dict[str, Any]) -> tuple[str, str, list[str]]:
    try:
        max_bytes = _vision_max_image_bytes()
        suffix = path.suffix.lower()
        if suffix in ANIMATED_CONTACT_SHEET_SUFFIXES:
            note_prefix = "gif" if suffix == ".gif" else "animated"
            animated_uri, animated_error, animated_notes = _animated_contact_sheet_data_uri(
                path,
                max_bytes=max_bytes,
                note_prefix=note_prefix,
            )
            if animated_uri:
                return animated_uri, "", animated_notes
            data = path.read_bytes()
            should_compress_single_frame = (
                animated_error.endswith("_single_frame") and _image_exceeds_vision_max_dimension(path)
            )
            if len(data) > max_bytes or should_compress_single_frame:
                compressed_uri, compressed_error, compressed_notes = _compressed_static_image_data_uri(
                    path,
                    max_bytes=max_bytes,
                    note_prefix=note_prefix,
                )
                if compressed_uri:
                    notes = animated_notes + ([animated_error] if animated_error else []) + compressed_notes
                    return compressed_uri, "", notes
                if should_compress_single_frame and len(data) <= max_bytes:
                    notes = animated_notes + ([animated_error] if animated_error else []) + (
                        [compressed_error] if compressed_error else []
                    )
                    mime = "image/gif" if suffix == ".gif" else _mime_type(path, payload)
                    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}", "", notes
                notes = animated_notes + ([animated_error] if animated_error else []) + ([compressed_error] if compressed_error else [])
                return "", f"image_too_large:{len(data)}", notes
            mime = "image/gif" if suffix == ".gif" else _mime_type(path, payload)
            notes = animated_notes
            if animated_error and not animated_error.endswith("_single_frame"):
                notes = notes + [animated_error, f"{note_prefix}_raw_fallback"]
            return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}", "", notes
        data = path.read_bytes()
    except OSError as exc:
        return "", f"image_read_failed:{type(exc).__name__}", []
    if len(data) > max_bytes:
        compressed_uri, compressed_error, compressed_notes = _compressed_static_image_data_uri(
            path,
            max_bytes=max_bytes,
        )
        if compressed_uri:
            return compressed_uri, "", compressed_notes
        return "", f"image_too_large:{len(data)}", [compressed_error] if compressed_error else []
    mime = _mime_type(path, payload)
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}", "", []


def _append_unique_note(notes: list[str], note: str) -> None:
    if note and note not in notes:
        notes.append(note)


def _extract_vision_response_text(data: dict[str, Any]) -> str:
    choices = data.get("choices") if isinstance(data, dict) else None
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, list):
                    return "\n".join(_safe_str(part.get("text")) for part in content if isinstance(part, dict)).strip()
                text = _safe_str(content).strip()
                if text:
                    return text
            return _safe_str(first.get("text")).strip()
    return _safe_str(data.get("text") or data.get("reply")).strip() if isinstance(data, dict) else ""


def _request_vision_summary(
    *,
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    data_uri: str,
) -> tuple[str, str]:
    body = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ],
            }
        ],
        "temperature": 0.2,
        "max_tokens": _vision_max_tokens(),
    }
    request = urllib.request.Request(
        base_url + "/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=_as_int(os.environ.get("XINYU_IMAGE_VISION_TIMEOUT_SECONDS"), 45)) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return "", f"vision_http_{exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return "", f"vision_error:{type(exc).__name__}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return "", "vision_invalid_json"
    summary = re.sub(r"\s+", " ", _extract_vision_response_text(data)).strip()
    if not summary:
        return "", "vision_empty_summary"
    return summary[:1200], ""


def describe_image_with_vision(path: Path, payload: dict[str, Any], *, owner_text: str, ocr_text: str = "") -> tuple[str, list[str]]:
    notes: list[str] = []
    if not _vision_enabled():
        return "", ["vision_disabled"]
    api_keys = _vision_api_key_candidates()
    if not api_keys:
        return "", ["vision_missing_api_key"]
    data_uri, error, data_notes = _image_data_uri(path, payload)
    notes.extend(data_notes)
    if error:
        return "", notes + [error]

    prompt = (
        "请用中文简短描述这张 QQ 图片/截图对当前对话有用的信息。"
        "如果是聊天截图，优先读出关键发言和用户指出的问题；如果是表情包，给出可能语气。"
        "不要编造看不清的细节；不确定就写不确定。"
    )
    if owner_text.strip():
        prompt += f"\n用户随图文字：{owner_text.strip()[:500]}"
    if ocr_text.strip():
        prompt += f"\n已有 OCR 文本，可用来校对：{ocr_text.strip()[:1200]}"

    if any(note.startswith(("gif_", "animated_")) for note in notes):
        prompt += (
            "\n如果这张输入是 GIF 动图抽帧拼图，请按帧顺序理解表情、动作和语气变化；"
            "看不清或不确定就直接说不确定。"
        )
    if any(note.startswith("animated_") for note in notes):
        prompt += "\nThe frame sheet may come from animated WebP or APNG, not only GIF."

    models = _vision_model_candidates()
    for key_index, api_key in enumerate(api_keys):
        for model_index, model in enumerate(models):
            summary, failure_note = _request_vision_summary(
                base_url=_vision_base_url(),
                api_key=api_key,
                model=model,
                prompt=prompt,
                data_uri=data_uri,
            )
            if summary:
                if key_index > 0:
                    _append_unique_note(notes, "vision_api_key_fallback_used")
                if model_index > 0:
                    _append_unique_note(notes, f"vision_model_fallback_used:{model}")
                notes.append("vision_summary_created")
                return summary, notes
            if failure_note.startswith("vision_error:"):
                return "", notes + [failure_note]
            _append_unique_note(notes, failure_note)
    return "", notes or ["vision_empty_summary"]


def build_image_context(
    root: Path,
    *,
    learning_payload: dict[str, Any],
    learning_response: dict[str, Any],
    owner_text: str,
) -> dict[str, Any]:
    load_local_env(root)
    if not is_image_learning_payload(learning_payload, learning_response):
        return {}

    image_only = not owner_text.strip() or owner_text.strip() == "owner supplied QQ file"
    if not wants_image_context(owner_text, image_only=image_only):
        return {"available": False, "kind": "image", "notes": ["image_context_not_requested"]}

    notes: list[str] = ["image_context_requested"]
    ocr_path = _safe_str(learning_response.get("extracted_text_path")).strip()
    ocr_text = _read_text_path(root, ocr_path)
    if ocr_text:
        notes.append("ocr_text_available")
    else:
        notes.append("ocr_text_empty")

    vision_summary = ""
    image_path = _first_existing_image_path(root, learning_payload, learning_response)
    if image_path is not None and (not ocr_text or wants_image_context(owner_text, image_only=image_only)):
        vision_summary, vision_notes = describe_image_with_vision(
            image_path,
            learning_payload,
            owner_text=owner_text,
            ocr_text=ocr_text,
        )
        notes.extend(vision_notes)
    elif image_path is None:
        notes.append("image_file_not_found_for_vision")

    available = bool(ocr_text.strip() or vision_summary.strip())
    return {
        "available": available,
        "kind": "image",
        "ocr_text": ocr_text[:3500],
        "ocr_extracted_text_path": ocr_path,
        "vision_summary": vision_summary,
        "notes": notes,
    }


def build_image_context_from_path(
    root: Path,
    *,
    image_path: Path,
    image_payload: dict[str, Any],
    owner_text: str,
    image_only: bool = False,
) -> dict[str, Any]:
    load_local_env(root)
    try:
        resolved = image_path.resolve(strict=True)
    except OSError:
        return {"available": False, "kind": "image", "notes": ["image_file_not_found_for_context"]}
    if resolved.suffix.lower() not in IMAGE_SUFFIXES:
        return {"available": False, "kind": "image", "notes": ["unsupported_image_type_for_context"]}
    image_only = image_only or not owner_text.strip()
    if not wants_image_context(owner_text, image_only=image_only):
        return {"available": False, "kind": "image", "notes": ["image_context_not_requested"]}

    notes: list[str] = ["image_context_requested", "direct_current_turn_image_context"]
    try:
        from xinyu_learning_library import extract_ocr_text_from_path, pdf_text_looks_garbled
        from xinyu_text_variants import repair_legacy_mojibake

        ocr_text = repair_legacy_mojibake(extract_ocr_text_from_path(resolved, force=True)).strip()
        if ocr_text and pdf_text_looks_garbled(ocr_text):
            notes.append("ocr_text_garbled")
            ocr_text = ""
    except Exception as exc:
        notes.append(f"ocr_failed:{type(exc).__name__}")
        ocr_text = ""
    if ocr_text:
        notes.append("ocr_text_available")
    else:
        notes.append("ocr_text_empty")

    vision_summary = ""
    if not ocr_text or wants_image_context(owner_text, image_only=image_only):
        vision_summary, vision_notes = describe_image_with_vision(
            resolved,
            image_payload,
            owner_text=owner_text,
            ocr_text=ocr_text,
        )
        notes.extend(vision_notes)

    return {
        "available": bool(ocr_text.strip() or vision_summary.strip()),
        "kind": "image",
        "ocr_text": ocr_text[:3500],
        "ocr_extracted_text_path": "",
        "vision_summary": vision_summary,
        "notes": notes,
    }
