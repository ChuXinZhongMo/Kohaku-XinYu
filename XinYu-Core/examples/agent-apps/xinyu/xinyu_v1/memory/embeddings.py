"""Embedding providers for v1 memory."""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from ..types import Embedding


class EmbeddingProvider(Protocol):
    async def embed_texts(self, texts: Sequence[str]) -> tuple[Embedding, ...]:
        """Embed text strings."""


@dataclass(frozen=True, slots=True)
class HashEmbeddingProvider:
    """Deterministic local fallback embedding.

    This is not semantic enough for production recall, but it gives tests,
    migration dry-runs, and degraded mode a stable vector representation.
    """

    dimensions: int = 128

    async def embed_texts(self, texts: Sequence[str]) -> tuple[Embedding, ...]:
        return tuple(self._embed(text) for text in texts)

    def _embed(self, text: str) -> Embedding:
        dims = max(8, self.dimensions)
        values = [0.0 for _ in range(dims)]
        tokens = _tokenize(text)
        if not tokens:
            tokens = [text.lower()]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8", errors="replace")).digest()
            index = int.from_bytes(digest[:4], "big") % dims
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            values[index] += sign
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return tuple(value / norm for value in values)


def _tokenize(text: str) -> list[str]:
    lowered = text.lower()
    tokens = [token for token in re.findall(r"[a-z0-9_]+", lowered) if token]
    cjk_chars = [char for char in lowered if "\u4e00" <= char <= "\u9fff"]
    tokens.extend(cjk_chars)
    tokens.extend("".join(cjk_chars[index : index + 2]) for index in range(max(0, len(cjk_chars) - 1)))
    return list(dict.fromkeys(tokens))
