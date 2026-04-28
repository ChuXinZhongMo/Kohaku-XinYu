"""Read-only legacy Markdown memory adapter."""

from __future__ import annotations

from pathlib import Path

from ..types import MemoryLayer
from .models import MemoryChunk


LAYER_HINTS: tuple[tuple[str, MemoryLayer], ...] = (
    ("memory/self/", MemoryLayer.SELF),
    ("memory/emotions/", MemoryLayer.EMOTION),
    ("memory/relationships/", MemoryLayer.RELATIONSHIP_OWNER),
    ("memory/people/", MemoryLayer.RELATIONSHIP_PEOPLE),
    ("memory/knowledge/", MemoryLayer.KNOWLEDGE),
    ("memory/dreams/", MemoryLayer.DREAMS),
    ("memory/archive/", MemoryLayer.ARCHIVE),
    ("memory/context/", MemoryLayer.CONTEXT),
)


class LegacyMarkdownMemory:
    def __init__(self, memory_root: Path) -> None:
        self.memory_root = memory_root

    def iter_chunks(self, *, max_chars: int = 1200) -> tuple[MemoryChunk, ...]:
        chunks: list[MemoryChunk] = []
        if not self.memory_root.exists():
            return ()
        for path in sorted(self.memory_root.rglob("*.md")):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8-sig")
            except OSError:
                continue
            relative = path.relative_to(self.memory_root.parent).as_posix()
            layer = self._layer_for(relative)
            for index, part in enumerate(split_markdown(text, max_chars=max_chars)):
                chunks.append(
                    MemoryChunk.stable(
                        text=part,
                        layer=layer,
                        source_path=relative,
                        tags=("legacy_md",),
                        metadata={"chunk_index": index},
                    )
                )
        return tuple(chunks)

    def _layer_for(self, relative_path: str) -> MemoryLayer:
        normalized = relative_path.replace("\\", "/")
        for prefix, layer in LAYER_HINTS:
            if normalized.startswith(prefix):
                return layer
        return MemoryLayer.CONTEXT


def split_markdown(text: str, *, max_chars: int) -> tuple[str, ...]:
    paragraphs = [part.strip() for part in text.replace("\r\n", "\n").split("\n\n") if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if not current:
            current = paragraph
        elif len(current) + len(paragraph) + 2 <= max_chars:
            current = f"{current}\n\n{paragraph}"
        else:
            chunks.append(current)
            current = paragraph
    if current:
        chunks.append(current)
    return tuple(chunk[:max_chars] for chunk in chunks if chunk.strip())

