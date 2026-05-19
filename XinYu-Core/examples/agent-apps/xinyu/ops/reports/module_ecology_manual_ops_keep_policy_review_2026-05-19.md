# XinYu Manual Ops Keep Policy Review - 2026-05-19

Scope: act on the remaining no-reference ops candidates that are intentionally
manual/template surfaces, not live runtime modules.

Privacy note: this report records paths and policy decisions only. It does not
include private memory, runtime data, QQ payloads, owner-supplied material
bodies, raw prompts, raw replies, URLs, or tokens.

## Summary

- manual runner candidates reviewed: 7
- sticker template candidates reviewed: 1
- explicitly kept: 8
- archived: 0
- deleted: 0

## Kept

Manual operator entrances registered in `ops/manual/README.md`:

- `ops/manual/manual_archive_commit.py`
- `ops/manual/manual_archive_output.py`
- `ops/manual/manual_consolidation.py`
- `ops/manual/manual_maintenance_recommendation.py`
- `ops/manual/manual_retention_gate.py`
- `ops/manual/manual_source_integration_gate.py`
- `ops/manual/manual_source_reliability.py`

Sticker template registered in `emotions/stickers/README.md`:

- `emotions/stickers/manifest.example.json`

## Direct Effect

- Removes these files from the no-reference archive-candidate bucket by giving
  them explicit owner/operator documentation.
- Keeps manual scripts out of the live turn path.
- Defines the retirement condition: if the matching engine/plugin disappears,
  archive the manual runner in the same batch.
