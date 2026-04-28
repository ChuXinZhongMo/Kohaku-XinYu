"""Memory consolidation helpers."""

from __future__ import annotations

from collections import defaultdict

from ..types import MemoryLayer
from .models import ConsolidationCandidate, MemoryChunk, sha256_text


def propose_consolidations(
    chunks: tuple[MemoryChunk, ...],
    *,
    min_cluster_size: int = 3,
    max_summary_chars: int = 800,
) -> tuple[ConsolidationCandidate, ...]:
    groups: dict[MemoryLayer, list[MemoryChunk]] = defaultdict(list)
    for chunk in chunks:
        groups[chunk.layer].append(chunk)

    candidates: list[ConsolidationCandidate] = []
    for layer, layer_chunks in groups.items():
        if len(layer_chunks) < min_cluster_size:
            continue
        summary = "\n".join(f"- {chunk.text[:160]}" for chunk in layer_chunks[:8])[:max_summary_chars]
        seed = "|".join(chunk.chunk_id for chunk in layer_chunks)
        candidates.append(
            ConsolidationCandidate(
                candidate_id=f"cons-{sha256_text(seed)[:16]}",
                chunks=tuple(layer_chunks),
                proposed_summary=summary,
                target_layer=layer,
                confidence=min(0.95, 0.45 + len(layer_chunks) * 0.05),
                notes=("deterministic_cluster",),
            )
        )
    return tuple(candidates)

