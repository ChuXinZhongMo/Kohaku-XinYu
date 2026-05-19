from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_sticker_pack import (
    MOOD_MARKERS,
    MOOD_ALIASES,
    MOOD_MEANINGS,
    SUPPORTED_STICKER_SUFFIXES,
    canonical_mood,
    infer_sticker_semantics,
    mood_dir_name,
    shared_asset_sticker_dir,
)
from xinyu_clip_command import MOOD_PROMPTS


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


DEFAULT_UNSORTED_NAMES = ("待分类", "unsorted", "inbox")
REFERENCE_DIR_NAMES = ("参考图", ".references")
GENERATED_MANIFEST = "manifest.generated.json"
UNCLEAR_DIR = "unclear"
IMPORT_SOURCE_SUFFIXES = frozenset((*SUPPORTED_STICKER_SUFFIXES, ".avif"))
CONVERT_TO_PNG_SUFFIXES = frozenset({".avif"})
DEFAULT_CLIP_THRESHOLD = 0.16
DEFAULT_CLIP_HIGH_THRESHOLD = 0.45
DEFAULT_OCR_THRESHOLD = 3.0
REFERENCE_INDEX_NAME = "reference_index.generated.json"
CORRECTIONS_MANIFEST = "corrections.generated.json"
KNOWN_MOOD_DIRS = {*MOOD_MEANINGS, *MOOD_PROMPTS}


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _timestamp_or_now_iso(value: Any = None) -> str:
    text = _safe_str(value).strip()
    if not text or text.lower() in {"none", "unknown", "null", "n/a", "na"}:
        return datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now().astimezone().isoformat(timespec="seconds")
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone().isoformat(timespec="seconds")


@dataclass
class ImportPlanItem:
    source: Path
    destination: Path
    mood: str
    confidence: str
    score: int
    keywords: list[str]
    meaning: str
    action: str
    clip_mood: str = ""
    clip_confidence: float = 0.0
    clip_scores: list[dict[str, Any]] = field(default_factory=list)
    vision_inferred: bool = False
    converted_from: str = ""
    ocr_text: str = ""
    ocr_inferred: bool = False
    text_keywords: list[str] = field(default_factory=list)
    ocr_error: str = ""
    reference_mood: str = ""
    reference_confidence: float = 0.0
    reference_inferred: bool = False
    confirmed: bool = False
    previous_mood: str = ""
    previous_file: str = ""

    def to_dict(self, base: Path) -> dict[str, Any]:
        data = {
            "source": _rel(self.source, base),
            "destination": _rel(self.destination, base),
            "mood": self.mood,
            "confidence": self.confidence,
            "score": self.score,
            "keywords": list(self.keywords),
            "meaning": self.meaning,
            "action": self.action,
        }
        if self.clip_mood:
            data["clip_mood"] = self.clip_mood
            data["clip_confidence"] = self.clip_confidence
            data["clip_scores"] = self.clip_scores
            data["vision_inferred"] = self.vision_inferred
        if self.converted_from:
            data["converted_from"] = self.converted_from
        if self.ocr_text or self.ocr_inferred or self.text_keywords or self.ocr_error:
            data["ocr_text"] = self.ocr_text
            data["ocr_inferred"] = self.ocr_inferred
            data["text_keywords"] = list(self.text_keywords)
        if self.ocr_error:
            data["ocr_error"] = self.ocr_error
        if self.reference_mood:
            data["reference_mood"] = self.reference_mood
            data["reference_confidence"] = self.reference_confidence
            data["reference_inferred"] = self.reference_inferred
        if self.confirmed:
            data["confirmed"] = True
            data["previous_mood"] = self.previous_mood
            data["previous_file"] = self.previous_file
        return data


def _rel(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return str(path)


def _dedupe_destination(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(2, 1000):
        candidate = path.with_name(f"{stem}-{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"could not allocate destination for {path}")


def _safe_inside(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _candidate_sources(base: Path, *, include_root_loose: bool) -> list[Path]:
    sources: list[Path] = []
    for name in DEFAULT_UNSORTED_NAMES:
        directory = base / name
        if directory.exists() and directory.is_dir():
            sources.extend(
                path
                for path in directory.rglob("*")
                if path.is_file() and path.suffix.lower() in IMPORT_SOURCE_SUFFIXES
            )
    if include_root_loose:
        sources.extend(
            path
            for path in base.iterdir()
            if path.is_file() and path.suffix.lower() in IMPORT_SOURCE_SUFFIXES
        )
    deduped: dict[str, Path] = {}
    for path in sources:
        try:
            resolved = path.resolve(strict=True)
        except OSError:
            continue
        if _safe_inside(resolved, base):
            deduped[str(resolved)] = resolved
    return sorted(deduped.values(), key=lambda item: item.name.lower())


def _workspace_root(path: Path) -> Path | None:
    resolved = path.resolve()
    for candidate in (resolved, *resolved.parents):
        if candidate.name == "XinYu":
            return candidate
    return None


def default_vision_python(xinyu_dir: Path) -> Path | None:
    workspace = _workspace_root(xinyu_dir)
    if workspace is None:
        return None
    candidate = workspace / "vision-venv" / "Scripts" / "python.exe"
    return candidate if candidate.exists() else None


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _run_clip_classifier(
    image_paths: list[Path],
    *,
    vision_python: Path,
    top_k: int,
    batch_size: int,
    reference_index: Path | None = None,
) -> dict[str, dict[str, Any]]:
    if not image_paths:
        return {}
    if not vision_python.exists():
        raise FileNotFoundError(f"vision python not found: {vision_python}")
    clip_script = Path(__file__).resolve().parent / "xinyu_clip_command.py"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as handle:
        json.dump({"images": [str(path) for path in image_paths]}, handle, ensure_ascii=False)
        input_path = Path(handle.name)
    try:
        command = [
                str(vision_python),
                str(clip_script),
                "--input-json",
                str(input_path),
                "--top-k",
                str(max(1, top_k)),
                "--batch-size",
                str(max(1, batch_size)),
        ]
        if reference_index is not None and reference_index.is_file():
            command.extend(["--reference-index", str(reference_index)])
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
    finally:
        input_path.unlink(missing_ok=True)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"CLIP classification failed: {detail}")
    data = json.loads(completed.stdout)
    raw_results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(raw_results, list):
        raw_results = [data] if isinstance(data, dict) else []
    results: dict[str, dict[str, Any]] = {}
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        raw_path = _safe_str(item.get("image_path"))
        if not raw_path:
            continue
        try:
            key = str(Path(raw_path).resolve(strict=True))
        except OSError:
            key = str(Path(raw_path).resolve())
        results[key] = item
    return results


def _clip_for_source(source: Path, clip_results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    try:
        return clip_results.get(str(source.resolve(strict=True)), {})
    except OSError:
        return clip_results.get(str(source.resolve()), {})


def _destination_for_source(base: Path, mood: str, source: Path) -> tuple[Path, str]:
    suffix = source.suffix.lower()
    target_name = source.with_suffix(".png").name if suffix in CONVERT_TO_PNG_SUFFIXES else source.name
    target = base / mood_dir_name(mood) / target_name
    try:
        if target.resolve() == source.resolve():
            return target, ""
    except OSError:
        pass
    if suffix in CONVERT_TO_PNG_SUFFIXES:
        return _dedupe_destination(target), suffix.lstrip(".")
    return _dedupe_destination(target), ""


def _mood_keywords(mood: str) -> list[str]:
    mood = canonical_mood(mood)
    return list(MOOD_ALIASES.get(mood, ()))[:8]


def _infer_text_mood(text: str) -> tuple[str, int, list[str]]:
    combined = text.lower()
    best_mood = "cute"
    best_score = 0
    best_hits: list[str] = []
    for mood in MOOD_MEANINGS:
        markers = MOOD_MARKERS.get(mood, ())
        hits = [marker for marker in markers if marker.lower() in combined]
        alias_hits = [marker for marker in MOOD_ALIASES.get(mood, ()) if marker.lower() in combined]
        score = len(hits) * 2 + len(alias_hits)
        if score > best_score:
            best_mood = mood
            best_score = score
            best_hits = [*hits, *alias_hits]
    return best_mood, best_score, best_hits[:8]


def _text_keywords(text: str, mood: str, hits: list[str]) -> list[str]:
    tokens: list[str] = []
    compact = text.replace("\n", " ").strip()
    if compact:
        tokens.extend(part for part in compact.split() if part)
        if not tokens and len(compact) <= 16:
            tokens.append(compact)
    tokens.extend(hits)
    tokens.extend(_mood_keywords(mood))
    return list(dict.fromkeys(token for token in tokens if token))[:16]


def _ocr_text_from_result(result: dict[str, Any]) -> str:
    texts = result.get("texts")
    if isinstance(texts, list):
        return "\n".join(_safe_str(item).strip() for item in texts if _safe_str(item).strip())
    return ""


def _run_ocr_for_sources(sources: list[Path]) -> dict[str, dict[str, Any]]:
    if not sources:
        return {}
    try:
        from xinyu_paddle_ocr_command import run_ocr
    except Exception as exc:
        return {
            str(source.resolve()): {"texts": [], "error": f"{type(exc).__name__}: {exc}"}
            for source in sources
        }
    results: dict[str, dict[str, Any]] = {}
    for source in sources:
        try:
            texts = run_ocr(source)
            results[str(source.resolve())] = {"texts": texts, "error": ""}
        except Exception as exc:
            results[str(source.resolve())] = {"texts": [], "error": f"{type(exc).__name__}: {exc}"}
    return results


def _ocr_for_source(source: Path, ocr_results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    try:
        return ocr_results.get(str(source.resolve(strict=True)), {})
    except OSError:
        return ocr_results.get(str(source.resolve()), {})


def _should_run_ocr(
    source: Path,
    semantic: dict[str, Any],
    clip: dict[str, Any],
    *,
    merged_mood: str,
    merged_confidence: str,
    merged_score: int,
    clip_threshold: float,
) -> bool:
    if source.suffix.lower() == ".gif":
        return False
    if merged_mood == UNCLEAR_DIR or merged_confidence == "low":
        return True
    if _safe_str(semantic.get("confidence"), "low") == "low":
        return True
    clip_confidence = _as_float(clip.get("confidence"))
    if clip and clip_confidence < clip_threshold:
        return True
    return merged_score < 3


def _merge_semantics(
    source: Path,
    semantic: dict[str, Any],
    clip: dict[str, Any],
    *,
    clip_threshold: float,
    clip_high_threshold: float,
    ocr: dict[str, Any] | None = None,
    ocr_threshold: float = DEFAULT_OCR_THRESHOLD,
    prefer_clip: bool = False,
) -> tuple[str, str, int, list[str], str, bool, bool, list[str]]:
    mood = canonical_mood(semantic.get("mood"), "cute")
    confidence = _safe_str(semantic.get("confidence"), "low")
    score = int(semantic.get("score") or 0)
    ignored_keywords = {name.lower() for name in DEFAULT_UNSORTED_NAMES}
    keywords = [
        keyword
        for keyword in dict.fromkeys([*_as_file_keywords(source), *list(semantic.get("keywords", []))])
        if keyword.lower() not in ignored_keywords
    ]
    meaning = _safe_str(semantic.get("meaning")) or MOOD_MEANINGS.get(mood, "")

    clip_mood = canonical_mood(clip.get("top_mood"), "")
    clip_confidence = _as_float(clip.get("confidence"))
    vision_inferred = False
    usable_clip = clip_mood in KNOWN_MOOD_DIRS and clip_mood != UNCLEAR_DIR and clip_confidence >= clip_threshold

    if prefer_clip and usable_clip:
        mood = clip_mood
        confidence = "high" if clip_confidence >= clip_high_threshold else "medium"
        score = max(score, int(round(clip_confidence * 100)))
        meaning = MOOD_MEANINGS.get(mood, meaning)
        keywords = list(dict.fromkeys([*keywords, *_mood_keywords(mood), f"clip:{mood}"]))
        vision_inferred = True
    elif confidence == "low":
        if usable_clip:
            mood = clip_mood
            confidence = "high" if clip_confidence >= clip_high_threshold else "medium"
            score = max(score, int(round(clip_confidence * 100)))
            meaning = MOOD_MEANINGS.get(mood, meaning)
            keywords = list(dict.fromkeys([*keywords, *_mood_keywords(mood), f"clip:{mood}"]))
            vision_inferred = True
        else:
            mood = UNCLEAR_DIR
            meaning = MOOD_MEANINGS.get(UNCLEAR_DIR, meaning)
    elif usable_clip:
        keywords = list(dict.fromkeys([*keywords, f"clip:{clip_mood}"]))

    ocr_inferred = False
    text_keywords: list[str] = []
    ocr_text = _ocr_text_from_result(ocr or {})
    if ocr_text:
        ocr_mood, ocr_score, hits = _infer_text_mood(ocr_text)
        text_keywords = _text_keywords(ocr_text, ocr_mood, hits)
        strong_ocr = ocr_score >= ocr_threshold and ocr_mood in KNOWN_MOOD_DIRS and ocr_mood != UNCLEAR_DIR
        weak_ocr = ocr_score > 0 and ocr_mood in KNOWN_MOOD_DIRS and ocr_mood != UNCLEAR_DIR
        conflicts_with_clip = bool(usable_clip and clip_mood != ocr_mood)
        if strong_ocr:
            if conflicts_with_clip and clip_confidence >= clip_high_threshold and ocr_score < ocr_threshold + 2:
                mood = UNCLEAR_DIR
                confidence = "low"
                meaning = MOOD_MEANINGS.get(UNCLEAR_DIR, meaning)
                keywords = list(dict.fromkeys([*keywords, *text_keywords, f"ocr_conflict:{ocr_mood}", f"clip:{clip_mood}"]))
            else:
                mood = ocr_mood
                confidence = "medium" if conflicts_with_clip else ("high" if ocr_score >= ocr_threshold + 2 else "medium")
                score = max(score, int(ocr_score * 10))
                meaning = MOOD_MEANINGS.get(mood, meaning)
                keywords = list(dict.fromkeys([*keywords, *text_keywords, f"ocr:{mood}"]))
            ocr_inferred = True
        elif weak_ocr:
            keywords = list(dict.fromkeys([*keywords, *text_keywords, f"ocr_weak:{ocr_mood}"]))
            if confidence == "low" and not usable_clip:
                mood = ocr_mood
                confidence = "medium" if ocr_score >= 2 else "low"
                score = max(score, int(ocr_score * 10))
                meaning = MOOD_MEANINGS.get(mood, meaning)
                ocr_inferred = True

    return mood, confidence, score, keywords[:16], meaning, vision_inferred, ocr_inferred, text_keywords


def build_import_plan(
    base: Path,
    *,
    include_root_loose: bool = False,
    use_clip: bool = False,
    use_ocr: bool = False,
    vision_python: Path | None = None,
    clip_threshold: float = DEFAULT_CLIP_THRESHOLD,
    clip_high_threshold: float = DEFAULT_CLIP_HIGH_THRESHOLD,
    clip_top_k: int = 5,
    clip_batch_size: int = 16,
    ocr_threshold: float = DEFAULT_OCR_THRESHOLD,
    reference_index: Path | None = None,
) -> list[ImportPlanItem]:
    base = base.resolve()
    sources = _candidate_sources(base, include_root_loose=include_root_loose)
    return build_import_plan_for_sources(
        base,
        sources,
        use_clip=use_clip,
        use_ocr=use_ocr,
        vision_python=vision_python,
        clip_threshold=clip_threshold,
        clip_high_threshold=clip_high_threshold,
        clip_top_k=clip_top_k,
        clip_batch_size=clip_batch_size,
        ocr_threshold=ocr_threshold,
        reference_index=reference_index,
    )


def build_import_plan_for_sources(
    base: Path,
    sources: list[Path],
    *,
    use_clip: bool = False,
    use_ocr: bool = False,
    vision_python: Path | None = None,
    clip_threshold: float = DEFAULT_CLIP_THRESHOLD,
    clip_high_threshold: float = DEFAULT_CLIP_HIGH_THRESHOLD,
    clip_top_k: int = 5,
    clip_batch_size: int = 16,
    ocr_threshold: float = DEFAULT_OCR_THRESHOLD,
    reference_index: Path | None = None,
) -> list[ImportPlanItem]:
    base = base.resolve()
    normalized_sources: dict[str, Path] = {}
    for source in sources:
        try:
            resolved = Path(source).resolve(strict=True)
        except OSError:
            continue
        if not resolved.is_file() or resolved.suffix.lower() not in IMPORT_SOURCE_SUFFIXES:
            continue
        if _safe_inside(resolved, base):
            normalized_sources[str(resolved)] = resolved
    sources = sorted(normalized_sources.values(), key=lambda item: item.name.lower())
    plan: list[ImportPlanItem] = []
    clip_results: dict[str, dict[str, Any]] = {}
    if use_clip and sources:
        if vision_python is None:
            raise RuntimeError("vision_python is required when use_clip=True")
        clip_results = _run_clip_classifier(
            sources,
            vision_python=vision_python,
            top_k=clip_top_k,
            batch_size=clip_batch_size,
            reference_index=reference_index,
        )
    preliminaries: list[tuple[Path, dict[str, Any], dict[str, Any], tuple[str, str, int, list[str], str, bool, bool, list[str]]]] = []
    ocr_sources: list[Path] = []
    for source in sources:
        semantic = infer_sticker_semantics(source)
        clip = _clip_for_source(source, clip_results) if clip_results else {}
        merged = _merge_semantics(
            source,
            semantic,
            clip,
            clip_threshold=clip_threshold,
            clip_high_threshold=clip_high_threshold,
            prefer_clip=True,
        )
        mood, confidence, score, _keywords, _meaning, _vision_inferred, _ocr_inferred, _text_keywords = merged
        preliminaries.append((source, semantic, clip, merged))
        if use_ocr and _should_run_ocr(
            source,
            semantic,
            clip,
            merged_mood=mood,
            merged_confidence=confidence,
            merged_score=score,
            clip_threshold=clip_threshold,
        ):
            ocr_sources.append(source)
    ocr_results = _run_ocr_for_sources(ocr_sources) if use_ocr else {}
    for source, semantic, clip, merged in preliminaries:
        ocr = _ocr_for_source(source, ocr_results) if ocr_results else {}
        if ocr:
            mood, confidence, score, keywords, meaning, vision_inferred, ocr_inferred, text_keywords = _merge_semantics(
                source,
                semantic,
                clip,
                clip_threshold=clip_threshold,
                clip_high_threshold=clip_high_threshold,
                ocr=ocr,
                ocr_threshold=ocr_threshold,
                prefer_clip=True,
            )
        else:
            mood, confidence, score, keywords, meaning, vision_inferred, ocr_inferred, text_keywords = merged
        destination, converted_from = _destination_for_source(base, mood, source)
        plan.append(
            ImportPlanItem(
                source=source,
                destination=destination,
                mood=mood,
                confidence=confidence,
                score=score,
                keywords=keywords,
                meaning=meaning,
                action="move",
                clip_mood=canonical_mood(clip.get("top_mood"), ""),
                clip_confidence=round(_as_float(clip.get("confidence")), 4) if clip else 0.0,
                clip_scores=list(clip.get("scores", [])) if isinstance(clip.get("scores"), list) else [],
                vision_inferred=vision_inferred,
                converted_from=converted_from,
                ocr_text=_ocr_text_from_result(ocr),
                ocr_inferred=ocr_inferred,
                text_keywords=text_keywords,
                ocr_error=_safe_str(ocr.get("error")) if ocr else "",
                reference_mood=canonical_mood(clip.get("reference_top_mood"), ""),
                reference_confidence=round(_as_float(clip.get("reference_confidence")), 4) if clip else 0.0,
                reference_inferred=bool(clip.get("reference_inferred")),
            )
        )
    return plan


def _classified_sources(base: Path, moods: list[str]) -> list[Path]:
    selected = {canonical_mood(mood, "").lower() for mood in moods if mood.strip()}
    selected.discard("")
    sources: list[Path] = []
    for directory in sorted(base.iterdir(), key=lambda item: item.name.lower()):
        if not directory.is_dir():
            continue
        if directory.name.startswith(".") or directory.name in REFERENCE_DIR_NAMES:
            continue
        if directory.name.lower() in {name.lower() for name in DEFAULT_UNSORTED_NAMES}:
            continue
        directory_mood = canonical_mood(directory.name, "")
        if selected and directory_mood.lower() not in selected:
            continue
        sources.extend(
            path
            for path in directory.rglob("*")
            if path.is_file() and path.suffix.lower() in IMPORT_SOURCE_SUFFIXES
        )
    return sorted(sources, key=lambda item: item.as_posix().lower())


def build_reclassify_plan(
    base: Path,
    *,
    moods: list[str],
    use_clip: bool,
    use_ocr: bool = False,
    vision_python: Path | None = None,
    clip_threshold: float = DEFAULT_CLIP_THRESHOLD,
    clip_high_threshold: float = DEFAULT_CLIP_HIGH_THRESHOLD,
    clip_top_k: int = 5,
    clip_batch_size: int = 16,
    ocr_threshold: float = DEFAULT_OCR_THRESHOLD,
    reference_index: Path | None = None,
) -> list[ImportPlanItem]:
    if not use_clip:
        raise RuntimeError("reclassifying existing folders requires --use-clip")
    base = base.resolve()
    confirmed_files = _confirmed_manifest_files(base)
    sources = [
        source
        for source in _classified_sources(base, moods)
        if _rel(source, base) not in confirmed_files
    ]
    if not sources:
        return []
    if vision_python is None:
        raise RuntimeError("vision_python is required when use_clip=True")
    clip_results = _run_clip_classifier(
        sources,
        vision_python=vision_python,
        top_k=clip_top_k,
        batch_size=clip_batch_size,
        reference_index=reference_index,
    )
    preliminaries: list[tuple[Path, dict[str, Any], dict[str, Any], tuple[str, str, int, list[str], str, bool, bool, list[str]]]] = []
    ocr_sources: list[Path] = []
    for source in sources:
        semantic = infer_sticker_semantics(source)
        clip = _clip_for_source(source, clip_results)
        merged = _merge_semantics(
            source,
            semantic,
            clip,
            clip_threshold=clip_threshold,
            clip_high_threshold=clip_high_threshold,
        )
        mood, confidence, score, _keywords, _meaning, _vision_inferred, _ocr_inferred, _text_keywords = merged
        preliminaries.append((source, semantic, clip, merged))
        if use_ocr and _should_run_ocr(
            source,
            semantic,
            clip,
            merged_mood=mood,
            merged_confidence=confidence,
            merged_score=score,
            clip_threshold=clip_threshold,
        ):
            ocr_sources.append(source)
    ocr_results = _run_ocr_for_sources(ocr_sources) if use_ocr else {}
    plan: list[ImportPlanItem] = []
    for source, semantic, clip, merged in preliminaries:
        ocr = _ocr_for_source(source, ocr_results) if ocr_results else {}
        if ocr:
            mood, confidence, score, keywords, meaning, vision_inferred, ocr_inferred, text_keywords = _merge_semantics(
                source,
                semantic,
                clip,
                clip_threshold=clip_threshold,
                clip_high_threshold=clip_high_threshold,
                ocr=ocr,
                ocr_threshold=ocr_threshold,
            )
        else:
            mood, confidence, score, keywords, meaning, vision_inferred, ocr_inferred, text_keywords = merged
        destination, converted_from = _destination_for_source(base, mood, source)
        plan.append(
            ImportPlanItem(
                source=source,
                destination=destination,
                mood=mood,
                confidence=confidence,
                score=score,
                keywords=keywords,
                meaning=meaning,
                action="reclassify",
                clip_mood=canonical_mood(clip.get("top_mood"), ""),
                clip_confidence=round(_as_float(clip.get("confidence")), 4) if clip else 0.0,
                clip_scores=list(clip.get("scores", [])) if isinstance(clip.get("scores"), list) else [],
                vision_inferred=vision_inferred,
                converted_from=converted_from,
                ocr_text=_ocr_text_from_result(ocr),
                ocr_inferred=ocr_inferred,
                text_keywords=text_keywords,
                ocr_error=_safe_str(ocr.get("error")) if ocr else "",
                reference_mood=canonical_mood(clip.get("reference_top_mood"), ""),
                reference_confidence=round(_as_float(clip.get("reference_confidence")), 4) if clip else 0.0,
                reference_inferred=bool(clip.get("reference_inferred")),
            )
        )
    return plan


def build_semantic_index_plan(base: Path) -> list[ImportPlanItem]:
    base = base.resolve()
    plan: list[ImportPlanItem] = []
    excluded = {name.lower() for name in (*DEFAULT_UNSORTED_NAMES, *REFERENCE_DIR_NAMES)}
    existing_manifest = _load_generated_manifest(base / GENERATED_MANIFEST)
    moved_by_file = _detect_manifest_moves(base, existing_manifest)
    existing_by_file = {
        _safe_str(item.get("file")): item
        for item in existing_manifest.get("stickers", [])
        if isinstance(item, dict) and _safe_str(item.get("file"))
    }
    for path in sorted(base.rglob("*"), key=lambda item: item.as_posix().lower()):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_STICKER_SUFFIXES:
            continue
        try:
            resolved = path.resolve(strict=True)
        except OSError:
            continue
        if not _safe_inside(resolved, base):
            continue
        rel_parts = resolved.relative_to(base).parts
        if not rel_parts or rel_parts[0].lower() in excluded:
            continue
        if rel_parts[0].startswith("."):
            continue
        rel = resolved.relative_to(base).as_posix()
        parent_dir = rel_parts[0]
        parent_mood = canonical_mood(parent_dir, "")
        semantic = infer_sticker_semantics(resolved, extra_text=parent_dir)
        mood = parent_mood if parent_mood in KNOWN_MOOD_DIRS else canonical_mood(semantic.get("mood"), "cute")
        meaning = MOOD_MEANINGS.get(mood, _safe_str(semantic.get("meaning")))
        confidence = _safe_str(semantic.get("confidence"), "low")
        if mood == UNCLEAR_DIR:
            confidence = "low"
        elif parent_mood in KNOWN_MOOD_DIRS and confidence == "low":
            confidence = "medium"
        previous_item = existing_by_file.get(rel)
        moved_item = moved_by_file.get(rel)
        confirmed = bool(previous_item.get("confirmed")) if isinstance(previous_item, dict) else False
        previous_mood = canonical_mood(previous_item.get("previous_mood"), "") if isinstance(previous_item, dict) else ""
        previous_file = ""
        if moved_item:
            confirmed = True
            previous_mood = canonical_mood(moved_item.get("mood"), "")
            previous_file = _safe_str(moved_item.get("file"))
            confidence = "high"
        plan.append(
            ImportPlanItem(
                source=resolved,
                destination=resolved,
                mood=mood,
                confidence=confidence,
                score=int(semantic.get("score") or 0),
                keywords=list(dict.fromkeys([*_as_file_keywords(resolved), *list(semantic.get("keywords", []))])),
                meaning=meaning,
                action="index",
                confirmed=confirmed,
                previous_mood=previous_mood,
                previous_file=previous_file,
            )
        )
    return plan


def _as_file_keywords(path: Path) -> list[str]:
    text = f"{path.parent.name} {path.stem}"
    tokens: list[str] = []
    for raw in text.replace("_", " ").replace("-", " ").split():
        token = raw.strip()
        if token and token not in tokens:
            tokens.append(token)
    return tokens[:8]


def _load_generated_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "generated_by": "xinyu_sticker_import", "stickers": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "generated_by": "xinyu_sticker_import", "stickers": []}
    if not isinstance(data, dict):
        return {"version": 1, "generated_by": "xinyu_sticker_import", "stickers": []}
    stickers = data.get("stickers")
    if not isinstance(stickers, list):
        data["stickers"] = []
    return data


def _confirmed_manifest_files(base: Path) -> set[str]:
    data = _load_generated_manifest(base / GENERATED_MANIFEST)
    return {
        _safe_str(item.get("file"))
        for item in data.get("stickers", [])
        if isinstance(item, dict) and _safe_str(item.get("file")) and bool(item.get("confirmed"))
    }


def _detect_manifest_moves(base: Path, data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    missing: list[dict[str, Any]] = []
    for item in data.get("stickers", []):
        if not isinstance(item, dict):
            continue
        rel = _safe_str(item.get("file"))
        if not rel:
            continue
        path = base / rel
        if not path.exists():
            missing.append(item)
    if not missing:
        return {}
    current_by_name: dict[str, list[Path]] = {}
    excluded = {name.lower() for name in (*DEFAULT_UNSORTED_NAMES, *REFERENCE_DIR_NAMES)}
    for path in base.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_STICKER_SUFFIXES:
            continue
        try:
            rel_parts = path.resolve(strict=True).relative_to(base).parts
        except (OSError, ValueError):
            continue
        if not rel_parts or rel_parts[0].lower() in excluded or rel_parts[0].startswith("."):
            continue
        current_by_name.setdefault(path.name.lower(), []).append(path)
    moved: dict[str, dict[str, Any]] = {}
    for item in missing:
        old_file = _safe_str(item.get("file"))
        matches = current_by_name.get(Path(old_file).name.lower(), [])
        if len(matches) != 1:
            continue
        current_rel = _rel(matches[0], base)
        old_mood = canonical_mood(item.get("mood"), "")
        current_mood = canonical_mood(current_rel.split("/", 1)[0], "")
        if old_file != current_rel and current_mood:
            moved[current_rel] = item
    return moved


def _load_corrections(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "generated_by": "xinyu_sticker_import", "items": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "generated_by": "xinyu_sticker_import", "items": []}
    if not isinstance(data, dict):
        return {"version": 1, "generated_by": "xinyu_sticker_import", "items": []}
    if not isinstance(data.get("items"), list):
        data["items"] = []
    return data


def _write_corrections_manifest(base: Path, items: list[ImportPlanItem]) -> Path:
    path = base / CORRECTIONS_MANIFEST
    data = _load_corrections(path)
    existing = {
        _safe_str(item.get("file")): item
        for item in data.get("items", [])
        if isinstance(item, dict) and _safe_str(item.get("file"))
    }
    now = _timestamp_or_now_iso()
    for item in items:
        if not item.confirmed or not item.previous_file:
            continue
        rel = _rel(item.destination, base)
        existing[rel] = {
            "file": rel,
            "confirmed_mood": item.mood,
            "previous_mood": item.previous_mood,
            "previous_file": item.previous_file,
            "source": "owner_folder_move",
            "updated_at": _timestamp_or_now_iso(now),
        }
    data["version"] = 1
    data["generated_by"] = "xinyu_sticker_import"
    data["updated_at"] = _timestamp_or_now_iso(now)
    data["items"] = [existing[key] for key in sorted(existing)]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _write_generated_manifest(base: Path, items: list[ImportPlanItem]) -> Path:
    path = base / GENERATED_MANIFEST
    data = _load_generated_manifest(path)
    existing = {
        _safe_str(item.get("file")): item
        for item in data.get("stickers", [])
        if isinstance(item, dict) and _safe_str(item.get("file"))
    }
    for rel in list(existing):
        raw = Path(rel)
        candidate = raw if raw.is_absolute() else base / raw
        try:
            resolved = candidate.resolve()
            resolved.relative_to(base.resolve())
        except (OSError, ValueError):
            existing.pop(rel, None)
            continue
        if not resolved.exists():
            existing.pop(rel, None)
    now = _timestamp_or_now_iso()
    for item in items:
        rel = _rel(item.destination, base)
        source_rel = _rel(item.source, base)
        if source_rel != rel:
            existing.pop(source_rel, None)
        if item.previous_file and item.previous_file != rel:
            existing.pop(item.previous_file, None)
        old_item = existing.get(rel, {})
        old_confirmed = bool(old_item.get("confirmed")) if isinstance(old_item, dict) else False
        confirmed = item.confirmed or old_confirmed
        confirmed_at = _safe_str(old_item.get("confirmed_at")) if isinstance(old_item, dict) else ""
        old_auto_send = bool(old_item.get("auto_send")) if isinstance(old_item, dict) else False
        try:
            old_weight = int(old_item.get("weight") or 1) if isinstance(old_item, dict) else 1
        except (TypeError, ValueError):
            old_weight = 1
        inferred_auto_send = item.confidence in {"medium", "high"} and item.mood != UNCLEAR_DIR
        inferred_weight = 2 if item.confidence == "high" else 1
        existing[rel] = {
            "file": rel,
            "mood": item.mood,
            "meaning": item.meaning or f"XinYu inferred mood={item.mood}, confidence={item.confidence}",
            "keywords": item.keywords,
            "auto_send": True if confirmed else (old_auto_send or inferred_auto_send),
            "weight": 3 if confirmed else max(old_weight, inferred_weight),
            "inferred": True,
            "inferred_at": now,
        }
        if confirmed:
            existing[rel]["confirmed"] = True
            existing[rel]["confirmed_mood"] = item.mood
            existing[rel]["confirmed_at"] = confirmed_at or now
            old_previous_mood = canonical_mood(old_item.get("previous_mood"), "") if isinstance(old_item, dict) else ""
            old_previous_file = _safe_str(old_item.get("previous_file")) if isinstance(old_item, dict) else ""
            previous_mood = item.previous_mood or old_previous_mood
            previous_file = item.previous_file or old_previous_file
            if previous_mood:
                existing[rel]["previous_mood"] = previous_mood
            if previous_file:
                existing[rel]["previous_file"] = previous_file
        if item.vision_inferred or item.clip_mood:
            existing[rel]["vision_inferred"] = item.vision_inferred
            existing[rel]["clip_mood"] = item.clip_mood
            existing[rel]["clip_confidence"] = item.clip_confidence
            existing[rel]["clip_scores"] = item.clip_scores
        elif isinstance(old_item, dict):
            for key in ("vision_inferred", "clip_mood", "clip_confidence", "clip_scores"):
                if key in old_item:
                    existing[rel][key] = old_item[key]
        if item.converted_from:
            existing[rel]["converted_from"] = item.converted_from
        elif isinstance(old_item, dict) and "converted_from" in old_item:
            existing[rel]["converted_from"] = old_item["converted_from"]
        if item.ocr_text or item.ocr_inferred or item.text_keywords or item.ocr_error:
            existing[rel]["ocr_text"] = item.ocr_text
            existing[rel]["ocr_inferred"] = item.ocr_inferred
            existing[rel]["text_keywords"] = item.text_keywords
        elif isinstance(old_item, dict):
            for key in ("ocr_text", "ocr_inferred", "text_keywords"):
                if key in old_item:
                    existing[rel][key] = old_item[key]
        if item.ocr_error:
            existing[rel]["ocr_error"] = item.ocr_error
        elif isinstance(old_item, dict) and "ocr_error" in old_item:
            existing[rel]["ocr_error"] = old_item["ocr_error"]
        if item.reference_mood:
            existing[rel]["reference_mood"] = item.reference_mood
            existing[rel]["reference_confidence"] = item.reference_confidence
            existing[rel]["reference_inferred"] = item.reference_inferred
        elif isinstance(old_item, dict):
            for key in ("reference_mood", "reference_confidence", "reference_inferred"):
                if key in old_item:
                    existing[rel][key] = old_item[key]
    data["version"] = 1
    data["generated_by"] = "xinyu_sticker_import"
    data["updated_at"] = _timestamp_or_now_iso(now)
    data["stickers"] = [existing[key] for key in sorted(existing)]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _convert_image_to_png(source: Path, destination: Path) -> None:
    from PIL import Image

    with Image.open(source) as image:
        frame = image.convert("RGBA") if "A" in image.getbands() else image.convert("RGB")
        frame.save(destination, format="PNG")


def apply_import_plan(base: Path, plan: list[ImportPlanItem]) -> dict[str, Any]:
    moved: list[ImportPlanItem] = []
    failures: list[dict[str, str]] = []
    for item in plan:
        if not _safe_inside(item.source, base) or not _safe_inside(item.destination, base):
            continue
        item.destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            same_path = item.source.resolve() == item.destination.resolve()
            if same_path:
                pass
            elif item.converted_from:
                _convert_image_to_png(item.source, item.destination)
                item.source.unlink()
            else:
                shutil.move(str(item.source), str(item.destination))
            moved.append(item)
        except Exception as exc:
            failures.append({"source": _rel(item.source, base), "error": f"{type(exc).__name__}: {exc}"})
    manifest_path = _write_generated_manifest(base, moved) if moved else base / GENERATED_MANIFEST
    return {
        "moved": len(moved),
        "converted": sum(1 for item in moved if item.converted_from),
        "failed": len(failures),
        "failures": failures,
        "manifest_path": str(manifest_path),
        "items": [item.to_dict(base) for item in moved],
    }


def write_semantic_index(base: Path, plan: list[ImportPlanItem]) -> dict[str, Any]:
    indexed = [item for item in plan if item.action == "index" and _safe_inside(item.destination, base)]
    manifest_path = _write_generated_manifest(base, indexed) if indexed else base / GENERATED_MANIFEST
    corrections_path = _write_corrections_manifest(base, indexed)
    corrections = [item for item in indexed if item.confirmed and item.previous_file]
    return {
        "indexed": len(indexed),
        "corrections": len(corrections),
        "manifest_path": str(manifest_path),
        "corrections_path": str(corrections_path),
        "items": [item.to_dict(base) for item in indexed],
    }


def ensure_unsorted_dir(base: Path) -> Path:
    target = base / "待分类"
    target.mkdir(parents=True, exist_ok=True)
    readme = target / "README.md"
    if not readme.exists():
        readme.write_text(
            "把未分类表情图拖到这里，然后运行 xinyu_sticker_import.py。默认只预览，带 --apply 才会移动。\n",
            encoding="utf-8",
        )
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Infer and import XinYu sticker semantics from the shared asset library.")
    parser.add_argument("--xinyu-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--asset-dir", type=Path, default=None)
    parser.add_argument("--include-root-loose", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--write-semantics", action="store_true", help="Index already-classified sticker folders into manifest.generated.json.")
    parser.add_argument("--reclassify-mood", action="append", default=[], help="Re-run CLIP classification for an existing mood folder. Repeat for multiple folders.")
    parser.add_argument("--reclassify-all", action="store_true", help="Re-run CLIP classification for all existing classified sticker folders.")
    parser.add_argument("--use-clip", action="store_true", help="Use the local CLIP vision environment to classify visually ambiguous stickers.")
    parser.add_argument("--use-ocr", action="store_true", help="Use local PaddleOCR for low-confidence or unclear stickers.")
    parser.add_argument("--vision-python", type=Path, default=None)
    parser.add_argument("--clip-threshold", type=float, default=DEFAULT_CLIP_THRESHOLD)
    parser.add_argument("--clip-high-threshold", type=float, default=DEFAULT_CLIP_HIGH_THRESHOLD)
    parser.add_argument("--clip-top-k", type=int, default=5)
    parser.add_argument("--clip-batch-size", type=int, default=16)
    parser.add_argument("--ocr-threshold", type=float, default=DEFAULT_OCR_THRESHOLD)
    parser.add_argument("--reference-index", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    base = args.asset_dir or shared_asset_sticker_dir(args.xinyu_dir)
    if base is None:
        raise SystemExit("Could not resolve shared sticker asset directory.")
    base = base.resolve()
    base.mkdir(parents=True, exist_ok=True)
    ensure_unsorted_dir(base)
    vision_python = args.vision_python or default_vision_python(args.xinyu_dir)
    if args.use_clip and vision_python is None:
        raise SystemExit("Could not resolve vision python. Pass --vision-python D:\\XinYu\\vision-venv\\Scripts\\python.exe")
    reference_index = args.reference_index
    if reference_index is None:
        candidate_reference_index = base / REFERENCE_INDEX_NAME
        reference_index = candidate_reference_index if candidate_reference_index.is_file() else None
    reclassify_moods = [] if args.reclassify_all else list(args.reclassify_mood)
    if args.write_semantics:
        plan = build_semantic_index_plan(base)
    elif args.reclassify_all or args.reclassify_mood:
        plan = build_reclassify_plan(
            base,
            moods=reclassify_moods,
            use_clip=args.use_clip,
            use_ocr=args.use_ocr,
            vision_python=vision_python,
            clip_threshold=args.clip_threshold,
            clip_high_threshold=args.clip_high_threshold,
            clip_top_k=args.clip_top_k,
            clip_batch_size=args.clip_batch_size,
            ocr_threshold=args.ocr_threshold,
            reference_index=reference_index,
        )
    else:
        plan = build_import_plan(
            base,
            include_root_loose=args.include_root_loose,
            use_clip=args.use_clip,
            use_ocr=args.use_ocr,
            vision_python=vision_python,
            clip_threshold=args.clip_threshold,
            clip_high_threshold=args.clip_high_threshold,
            clip_top_k=args.clip_top_k,
            clip_batch_size=args.clip_batch_size,
            ocr_threshold=args.ocr_threshold,
            reference_index=reference_index,
        )
    result = {
        "asset_dir": str(base),
        "apply": bool(args.apply),
        "write_semantics": bool(args.write_semantics),
        "reclassify_moods": reclassify_moods,
        "reclassify_all": bool(args.reclassify_all),
        "use_clip": bool(args.use_clip),
        "use_ocr": bool(args.use_ocr),
        "vision_python": str(vision_python) if vision_python else "",
        "reference_index": str(reference_index) if reference_index else "",
        "planned": len(plan),
        "items": [item.to_dict(base) for item in plan],
    }
    if args.write_semantics and args.apply:
        result.update(write_semantic_index(base, plan))
    elif args.apply:
        result.update(apply_import_plan(base, plan))

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        mode = "APPLY" if args.apply else "DRY-RUN"
        if args.write_semantics:
            mode += " SEMANTICS"
        if args.reclassify_all or args.reclassify_mood:
            mode += " RECLASSIFY"
        if args.use_clip:
            mode += " CLIP"
        if args.use_ocr:
            mode += " OCR"
        print(f"xinyu_sticker_import: {mode} asset_dir={base}")
        if not plan:
            print("no unsorted stickers found")
        for item in plan:
            clip_note = f" clip={item.clip_mood}:{item.clip_confidence}" if item.clip_mood else ""
            reference_note = f" ref={item.reference_mood}:{item.reference_confidence}" if item.reference_mood else ""
            ocr_note = f" ocr={item.ocr_text[:24]!r}" if item.ocr_text else (" ocr_error" if item.ocr_error else "")
            confirmed_note = " confirmed" if item.confirmed else ""
            converted_note = f" converted_from={item.converted_from}" if item.converted_from else ""
            print(
                f"- {item.action}: {_rel(item.source, base)} -> {_rel(item.destination, base)} "
                f"mood={item.mood} confidence={item.confidence} score={item.score}"
                f"{clip_note}{reference_note}{ocr_note}{confirmed_note}{converted_note} "
                f"meaning={item.meaning}"
            )
        if args.apply:
            if args.write_semantics:
                print(f"indexed: {result.get('indexed', 0)}")
                print(f"corrections: {result.get('corrections', 0)}")
            else:
                print(f"moved: {result.get('moved', 0)}")
                print(f"converted: {result.get('converted', 0)}")
                print(f"failed: {result.get('failed', 0)}")
            print(f"manifest: {result.get('manifest_path', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
