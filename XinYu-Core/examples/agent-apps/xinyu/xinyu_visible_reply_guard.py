from __future__ import annotations

import re
from dataclasses import dataclass


_CLOSING_QUOTES = "\"')]} \u201d\u2019\u300b\u300d\u300f".replace(" ", "")
_SENTENCE_END = "\u3002\uff01\uff1f!?\uff1b;"
_CONTENT_PUNCT_RE = re.compile(
    "[\u3002\uff01\uff1f!?\uff1b;\uff0c,\u3001\uff1a:\u00b7.\\-"
    "\u2014~\uff5e\"'\u201c\u201d\u2018\u2019()\\[\\]{}<>\u300a\u300b\u300c\u300d\u300e\u300f]"
)
_WRITER_BLOCK_RE = re.compile(
    r"\[\s*(?:context|emotion|relationship|reflection|question|learner|archive|dream|time|output)_writer\s*\].*?"
    r"\[\s*/\s*(?:context|emotion|relationship|reflection|question|learner|archive|dream|time|output)_writer\s*\]",
    re.IGNORECASE | re.DOTALL,
)
_WRITER_TAG_RE = re.compile(
    r"\[\s*(/?)\s*(?:context|emotion|relationship|reflection|question|learner|archive|dream|time|output)_writer\s*\]",
    re.IGNORECASE,
)
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_WRITER_METADATA_RE = re.compile(
    r"(^[\[{]|[:：]\s*(?:true|false|null|none|no_update|update|skip)|"
    r"\b(?:memory|context|emotion|relationship|reflection|archive|writer|delta|score|state|event)\b)",
    re.IGNORECASE,
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


def _strip_writer_blocks(text: str) -> tuple[str, bool]:
    without_complete_blocks = _WRITER_BLOCK_RE.sub("", text)
    changed = without_complete_blocks != text

    kept_lines: list[str] = []
    inside_writer = False
    for raw_line in without_complete_blocks.splitlines():
        line = raw_line.strip()
        if not line:
            if not inside_writer:
                kept_lines.append(raw_line)
            continue

        tags = list(_WRITER_TAG_RE.finditer(line))
        if tags:
            changed = True
            line_without_tags = _WRITER_TAG_RE.sub("", line).strip()
            has_closing = any(match.group(1) for match in tags)
            has_opening = any(not match.group(1) for match in tags)
            if has_closing:
                inside_writer = not has_opening and not line_without_tags
            elif has_opening:
                inside_writer = True
            if line_without_tags and _looks_like_visible_reply_tail(line_without_tags):
                kept_lines.append(line_without_tags)
                inside_writer = False
            continue

        if inside_writer:
            changed = True
            if _looks_like_visible_reply_tail(line):
                kept_lines.append(line)
                inside_writer = False
            continue

        kept_lines.append(raw_line)

    cleaned = "\n".join(kept_lines).strip()
    if cleaned == text.strip():
        return text.strip(), False
    return cleaned, changed


def _looks_like_visible_reply_tail(line: str) -> bool:
    compact = line.strip()
    if not compact:
        return False
    if len(compact) > 180:
        return False
    if _WRITER_METADATA_RE.search(compact):
        return False
    return bool(_CJK_RE.search(compact))


def dedupe_visible_reply(text: str) -> VisibleReplyDedupeResult:
    """Remove exact repeated visible units without rewriting the reply."""
    original = text.strip()
    if not original:
        return VisibleReplyDedupeResult(text="", changed=False, notes=())

    notes: list[str] = []
    writer_text, writer_changed = _strip_writer_blocks(original)
    if writer_changed:
        notes.append("visible_writer_block_removed")

    paragraph_text, paragraph_changed = _dedupe_duplicate_paragraphs(writer_text)
    if paragraph_changed:
        notes.append("visible_reply_duplicate_paragraph_removed")

    sentence_text, sentence_changed = _dedupe_duplicate_sentences(paragraph_text)
    if sentence_changed:
        notes.append("visible_reply_duplicate_sentence_removed")

    result = sentence_text.strip()
    changed = result != original
    return VisibleReplyDedupeResult(text=result, changed=changed, notes=tuple(notes))
