from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from xinyu_sticker_pack import canonical_mood


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


DEFAULT_MODEL = "ViT-B-32"
DEFAULT_PRETRAINED = "openai"
DEFAULT_REFERENCE_WEIGHT = 0.35
DEFAULT_REFERENCE_THRESHOLD = 0.24
DEFAULT_REFERENCE_MARGIN = 0.03
MOOD_PROMPTS = {
    "happy": "a happy smiling reaction sticker, cheerful positive joy",
    "laugh": "a laughing meme reaction sticker, hahaha, very funny and amused",
    "cheer": "a cheering celebration reaction sticker, yay, success, good job",
    "tease": "a smug teasing mocking reaction sticker, playful ridicule and smirk",
    "ok": "an OK reaction sticker, understood or agreed",
    "thinking": "a thinking reaction sticker, considering or waiting",
    "confused": "a confused question-mark reaction sticker, what, puzzled",
    "deadpan": "a deadpan blank stare reaction sticker, expressionless and speechless",
    "awkward": "an awkward nervous sweat reaction sticker, embarrassed and uncomfortable",
    "comfort": "a comforting hug reaction sticker, gentle and supportive",
    "tired": "a tired exhausted reaction sticker, low energy",
    "sleepy": "a sleepy drowsy reaction sticker, going to bed, dozing",
    "work": "a working coding task reaction sticker, getting things done",
    "annoyed": "an annoyed irritated reaction sticker, mild displeasure",
    "angry": "an angry scolding reaction sticker, mad, rage marks",
    "refuse": "a refusal reaction sticker, saying no, reject, do not want",
    "panic": "a panicked scared reaction sticker, alarmed and anxious",
    "plead": "a pleading begging reaction sticker, puppy eyes, please",
    "shy": "a clearly shy blushing embarrassed reaction sticker, bashful with pink cheeks",
    "cute": "a cute mascot reaction sticker",
    "silent": "a silent quiet reaction sticker, no words",
    "proud": "a proud successful reaction sticker",
    "surprised": "a surprised shocked reaction sticker",
    "sad": "a sad disappointed reaction sticker",
}


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _rank_scores(labels: list[str], probs: list[float], top_k: int) -> tuple[str, float, list[dict[str, Any]]]:
    ranked = sorted(zip(labels, probs), key=lambda item: item[1], reverse=True)
    return (
        ranked[0][0] if ranked else "",
        round(float(ranked[0][1]), 4) if ranked else 0.0,
        [{"mood": label, "score": round(float(score), 4)} for label, score in ranked[: max(1, top_k)]],
    )


@dataclass(frozen=True)
class ReferenceIndex:
    labels: list[str]
    embeddings: list[list[float]]
    source_path: Path


def _load_reference_index(path: Path | None) -> ReferenceIndex | None:
    if path is None or not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    raw_items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(raw_items, list):
        return None
    labels: list[str] = []
    embeddings: list[list[float]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        mood = canonical_mood(item.get("mood"), "")
        raw_embedding = item.get("embedding")
        if mood not in MOOD_PROMPTS or not isinstance(raw_embedding, list):
            continue
        embedding: list[float] = []
        for value in raw_embedding:
            try:
                embedding.append(float(value))
            except (TypeError, ValueError):
                embedding = []
                break
        if embedding:
            labels.append(mood)
            embeddings.append(embedding)
    if not labels:
        return None
    return ReferenceIndex(labels=labels, embeddings=embeddings, source_path=path)


def _combine_text_and_reference_scores(
    labels: list[str],
    text_probs: list[float],
    reference_labels: list[str],
    reference_sims: list[float],
    *,
    reference_weight: float,
    reference_threshold: float,
    reference_margin: float,
) -> tuple[list[float], str, float, list[dict[str, Any]], bool]:
    by_label = {label: float(score) for label, score in zip(labels, text_probs)}
    ref_by_label = {label: float(score) for label, score in zip(reference_labels, reference_sims)}
    top_ref_label, top_ref_score, ref_scores = _rank_scores(reference_labels, reference_sims, len(reference_labels) or 1)
    top_text_label, top_text_score, _ = _rank_scores(labels, text_probs, 1)
    reference_inferred = False
    if top_ref_label and top_ref_score >= reference_threshold:
        ref_text_score = by_label.get(top_ref_label, 0.0)
        reference_inferred = top_ref_label != top_text_label and (top_ref_score - ref_text_score) >= reference_margin
    combined: list[float] = []
    for label in labels:
        combined_score = by_label.get(label, 0.0) + max(0.0, ref_by_label.get(label, 0.0)) * reference_weight
        if reference_inferred and label == top_ref_label:
            combined_score += reference_margin
        combined.append(combined_score)
    return combined, top_ref_label, top_ref_score, ref_scores, reference_inferred


def classify_images(
    image_paths: list[Path],
    *,
    model_name: str = DEFAULT_MODEL,
    pretrained: str = DEFAULT_PRETRAINED,
    device: str = "",
    top_k: int = 5,
    batch_size: int = 16,
    reference_index_path: Path | None = None,
    reference_weight: float = DEFAULT_REFERENCE_WEIGHT,
    reference_threshold: float = DEFAULT_REFERENCE_THRESHOLD,
    reference_margin: float = DEFAULT_REFERENCE_MARGIN,
) -> list[dict[str, Any]]:
    import torch
    import open_clip
    from PIL import Image

    normalized = [Path(path) for path in image_paths]
    for image_path in normalized:
        if not image_path.is_file():
            raise FileNotFoundError(str(image_path))

    selected_device = device
    if not selected_device:
        selected_device = "cuda" if torch.cuda.is_available() else "cpu"
        if selected_device == "cuda":
            try:
                torch.zeros(1, device="cuda")
            except Exception:
                selected_device = "cpu"
                print("[xinyu_clip_command] CUDA incompatible, falling back to CPU", flush=True)
    model, _, preprocess = open_clip.create_model_and_transforms(
        model_name,
        pretrained=pretrained,
        device=selected_device,
    )
    tokenizer = open_clip.get_tokenizer(model_name)
    model.eval()

    labels = list(MOOD_PROMPTS)
    prompts = [MOOD_PROMPTS[label] for label in labels]
    text = tokenizer(prompts).to(selected_device)
    with torch.no_grad():
        text_features = model.encode_text(text)
        text_features /= text_features.norm(dim=-1, keepdim=True)
    reference_index = _load_reference_index(reference_index_path)
    reference_labels: list[str] = []
    reference_features = None
    if reference_index is not None:
        reference_labels = reference_index.labels
        reference_features = torch.tensor(reference_index.embeddings, dtype=text_features.dtype, device=selected_device)
        reference_features /= reference_features.norm(dim=-1, keepdim=True)

    results: list[dict[str, Any]] = []
    effective_batch_size = max(1, int(batch_size or 1))
    for start in range(0, len(normalized), effective_batch_size):
        batch_paths = normalized[start : start + effective_batch_size]
        images = []
        for image_path in batch_paths:
            with Image.open(image_path) as image:
                images.append(preprocess(image.convert("RGB")))
        image_tensor = torch.stack(images, dim=0).to(selected_device)
        with torch.no_grad():
            image_features = model.encode_image(image_tensor)
            image_features /= image_features.norm(dim=-1, keepdim=True)
            probs_batch = (100.0 * image_features @ text_features.T).softmax(dim=-1).detach().cpu().tolist()
            reference_sims_batch = []
            if reference_features is not None:
                reference_sims_batch = (image_features @ reference_features.T).detach().cpu().tolist()
        for image_path, probs in zip(batch_paths, probs_batch):
            text_top_mood, text_confidence, text_scores = _rank_scores(labels, probs, top_k)
            top_mood = text_top_mood
            confidence = text_confidence
            scores = text_scores
            reference_top_mood = ""
            reference_confidence = 0.0
            reference_scores: list[dict[str, Any]] = []
            reference_inferred = False
            if reference_features is not None:
                ref_index = len(results) % effective_batch_size
                reference_sims = reference_sims_batch[ref_index]
                combined, reference_top_mood, reference_confidence, reference_scores, reference_inferred = (
                    _combine_text_and_reference_scores(
                        labels,
                        probs,
                        reference_labels,
                        reference_sims,
                        reference_weight=reference_weight,
                        reference_threshold=reference_threshold,
                        reference_margin=reference_margin,
                    )
                )
                top_mood, confidence, scores = _rank_scores(labels, combined, top_k)
            item = {
                "image_path": str(image_path),
                "model": model_name,
                "pretrained": pretrained,
                "device": selected_device,
                "top_mood": top_mood,
                "confidence": min(1.0, confidence),
                "scores": scores,
                "text_top_mood": text_top_mood,
                "text_confidence": text_confidence,
                "text_scores": text_scores,
            }
            if reference_features is not None:
                item.update(
                    {
                        "reference_index": str(reference_index.source_path) if reference_index else "",
                        "reference_top_mood": reference_top_mood,
                        "reference_confidence": round(float(reference_confidence), 4),
                        "reference_scores": reference_scores[: max(1, top_k)],
                        "reference_inferred": bool(reference_inferred),
                    }
                )
            results.append(item)
    return results


def classify_image(
    image_path: Path,
    *,
    model_name: str = DEFAULT_MODEL,
    pretrained: str = DEFAULT_PRETRAINED,
    device: str = "",
    top_k: int = 5,
    reference_index_path: Path | None = None,
) -> dict[str, Any]:
    return classify_images(
        [image_path],
        model_name=model_name,
        pretrained=pretrained,
        device=device,
        top_k=top_k,
        batch_size=1,
        reference_index_path=reference_index_path,
    )[0]


def _image_paths_from_json(path: Path) -> list[Path]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, list):
        return [Path(_safe_str(item)) for item in data if _safe_str(item)]
    if isinstance(data, dict):
        values = data.get("images") or data.get("image_paths") or data.get("paths")
        if isinstance(values, list):
            return [Path(_safe_str(item)) for item in values if _safe_str(item)]
    raise ValueError("input json must be a list of paths or an object with images/image_paths/paths")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Classify an image into XinYu sticker moods with CLIP.")
    parser.add_argument("image_paths", type=Path, nargs="*")
    parser.add_argument("--input-json", type=Path, default=None)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--pretrained", default=DEFAULT_PRETRAINED)
    parser.add_argument("--device", default="")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--reference-index", type=Path, default=None)
    parser.add_argument("--reference-weight", type=float, default=DEFAULT_REFERENCE_WEIGHT)
    parser.add_argument("--reference-threshold", type=float, default=DEFAULT_REFERENCE_THRESHOLD)
    parser.add_argument("--reference-margin", type=float, default=DEFAULT_REFERENCE_MARGIN)
    args = parser.parse_args(argv)
    try:
        image_paths = list(args.image_paths)
        if args.input_json is not None:
            image_paths.extend(_image_paths_from_json(args.input_json))
        if not image_paths:
            raise ValueError("at least one image path or --input-json is required")
        results = classify_images(
            image_paths,
            model_name=args.model,
            pretrained=args.pretrained,
            device=args.device,
            top_k=args.top_k,
            batch_size=args.batch_size,
            reference_index_path=args.reference_index,
            reference_weight=args.reference_weight,
            reference_threshold=args.reference_threshold,
            reference_margin=args.reference_margin,
        )
    except Exception as exc:
        print(f"xinyu_clip_command: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    if len(results) == 1 and args.input_json is None:
        print(json.dumps(results[0], ensure_ascii=True, indent=2))
    else:
        print(json.dumps({"results": results}, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
