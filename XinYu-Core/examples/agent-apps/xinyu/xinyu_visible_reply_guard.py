from __future__ import annotations

import re
from dataclasses import dataclass


_CLOSING_QUOTES = "\"')]} \u201d\u2019\u300b\u300d\u300f".replace(" ", "")
_SENTENCE_END = "\u3002\uff01\uff1f!?\uff1b;"
_CONTENT_PUNCT_RE = re.compile(
    "[\u3002\uff01\uff1f!?\uff1b;\uff0c,\u3001\uff1a:\u00b7.\\-"
    "\u2014~\uff5e\"'\u201c\u201d\u2018\u2019()\\[\\]{}<>\u300a\u300b\u300c\u300d\u300e\u300f]"
)


@dataclass(frozen=True)
class VisibleReplyDedupeResult:
    text: str
    changed: bool
    notes: tuple[str, ...] = ()


def _compact_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _unit_key(text: str) -> str:
    return re.sub(r"\s+", "", text).strip().strip(_CLOSING_QUOTES).lower()


def _content_len(key: str) -> int:
    return len(_CONTENT_PUNCT_RE.sub("", key))


def _join_units(units: list[str]) -> str:
    if not units:
        return ""
    reply = units[0].strip()
    for unit in units[1:]:
        item = unit.strip()
        if not item:
            continue
        if reply and reply[-1].isascii() and item[0].isascii():
            reply += " " + item
        else:
            reply += item
    return reply.strip()


def _split_sentences(text: str) -> list[str]:
    compact = _compact_whitespace(text)
    if not compact:
        return []

    sentences: list[str] = []
    start = 0
    idx = 0
    while idx < len(compact):
        ch = compact[idx]
        if ch not in _SENTENCE_END:
            idx += 1
            continue
        end = idx + 1
        while end < len(compact) and compact[end] in _CLOSING_QUOTES:
            end += 1
        sentence = compact[start:end].strip()
        if sentence:
            sentences.append(sentence)
        start = end
        idx = end

    tail = compact[start:].strip()
    if tail:
        sentences.append(tail)
    return sentences


def _repeated_prefix_size(keys: list[str]) -> int:
    count = len(keys)
    if count < 2:
        return 0
    for size in range(1, (count // 2) + 1):
        if count % size != 0:
            continue
        prefix = keys[:size]
        if not all(keys[index : index + size] == prefix for index in range(size, count, size)):
            continue
        if sum(_content_len(key) for key in prefix) >= 8:
            return size
    return 0


def _dedupe_duplicate_paragraphs(text: str) -> tuple[str, bool]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", text.strip()) if part.strip()]
    if len(paragraphs) < 2:
        return text.strip(), False

    keys = [_unit_key(part) for part in paragraphs]
    prefix_size = _repeated_prefix_size(keys)
    if prefix_size:
        return "\n\n".join(paragraphs[:prefix_size]).strip(), True

    changed = False
    seen: set[str] = set()
    kept: list[str] = []
    for paragraph, key in zip(paragraphs, keys):
        if _content_len(key) >= 8 and key in seen:
            changed = True
            continue
        seen.add(key)
        kept.append(paragraph)
    return "\n\n".join(kept).strip(), changed


def _dedupe_duplicate_sentences(text: str) -> tuple[str, bool]:
    sentences = _split_sentences(text)
    if len(sentences) < 2:
        return text.strip(), False

    keys = [_unit_key(sentence) for sentence in sentences]
    prefix_size = _repeated_prefix_size(keys)
    if prefix_size:
        return _join_units(sentences[:prefix_size]), True

    changed = False
    seen: set[str] = set()
    kept: list[str] = []
    for sentence, key in zip(sentences, keys):
        if _content_len(key) >= 6 and key in seen:
            changed = True
            continue
        seen.add(key)
        kept.append(sentence)
    return _join_units(kept), changed


def dedupe_visible_reply(text: str) -> VisibleReplyDedupeResult:
    """Remove exact repeated visible units without rewriting the reply."""
    original = text.strip()
    if not original:
        return VisibleReplyDedupeResult(text="", changed=False, notes=())

    notes: list[str] = []
    paragraph_text, paragraph_changed = _dedupe_duplicate_paragraphs(original)
    if paragraph_changed:
        notes.append("visible_reply_duplicate_paragraph_removed")

    sentence_text, sentence_changed = _dedupe_duplicate_sentences(paragraph_text)
    if sentence_changed:
        notes.append("visible_reply_duplicate_sentence_removed")

    result = sentence_text.strip()
    changed = result != original
    return VisibleReplyDedupeResult(text=result, changed=changed, notes=tuple(notes))
