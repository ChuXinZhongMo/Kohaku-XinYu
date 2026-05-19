# XinYu Core Compatibility Keep Policy Review - 2026-05-19

Scope: act on five no-reference core compatibility/provider candidates without
moving code that still has an explicit operator or optional-provider role.

Privacy note: this report records paths and policy decisions only. It does not
include private memory, runtime data, QQ payloads, owner-supplied material
bodies, raw prompts, raw replies, URLs, or tokens.

## Summary

- core compatibility/provider candidates reviewed: 5
- explicitly kept: 5
- archived: 0
- deleted: 0

## Kept

Sticker material maintenance:

- `xinyu_sticker_reference_index.py`

v1 operator CLI:

- `xinyu_v1/cli/inspect_memory.py`
- `xinyu_v1/cli/migrate_memory.py`

v1 optional vector providers:

- `xinyu_v1/memory/chroma_store.py`
- `xinyu_v1/memory/qdrant_store.py`

## Policy Surface Added

- `emotions/stickers/README.md` now records the sticker reference-index tool as
  explicit local maintenance, not live reply logic.
- `xinyu_v1/cli/README.md` now records v1 CLI keep/retire rules.
- `xinyu_v1/memory/README.md` now records optional provider boundaries and
  retirement rules.

## Direct Effect

- Removes these files from the no-reference core archive-candidate bucket by
  giving them explicit policy references.
- Keeps the canonical live recall algorithm unchanged.
- Keeps optional v1 provider code out of the live default path unless config,
  health checks, and tests explicitly opt in later.
