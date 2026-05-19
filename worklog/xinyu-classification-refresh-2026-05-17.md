# XinYu Classification Refresh - 2026-05-17

Status: applied as documentation/evidence refresh.

## Batch Scope

- Capability group: module classification.
- Goal: update the active classification map after the recall owner/provider
  batches and delete/archive reference audit.

## Completed

- Updated `worklog/xinyu-module-classification-2026-05-17.md` so recall rows
  match current code:
  - `xinyu_living_memory_recall.py`: canonical core owner.
  - `xinyu_context_retrieval.py`: core provider/compatibility layer.
  - retrieval envelope/reranker/router: core components.
  - contextual recall/self-loop: core providers.
  - contextual self observatory: ops observability/no behavior change.
  - contextual self replay: lab/offline replay.
  - conversation experience matcher/sidecar: advisory providers.
- Added the deletion/reference audit summary to the classification worklog:
  - `247` deleted root Python entries.
  - `247` migrated or archived counterparts found.
  - stale live old-root filename references reduced from `3` to `0`.
- Updated `STRUCTURE-NOTES.md` current owner surfaces with the same boundaries.

## Validation

Passed:

```powershell
rg -n "keep as current engine|wrap as `LivingMemoryRecall` owner|likely completed migration|provider/compatibility|renderer/offline context pack|counterpart_missing=0|xinyu-delete-archive-reference-audit" D:\XinYu\worklog\xinyu-module-classification-2026-05-17.md D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\STRUCTURE-NOTES.md
git diff --check -- worklog/xinyu-module-classification-2026-05-17.md XinYu-Core/examples/agent-apps/xinyu/STRUCTURE-NOTES.md
```

Results:

- Old stale classification phrases are absent.
- New provider/offline/delete-audit phrases are present.
- Diff check: whitespace clean; only CRLF normalization warning for
  `STRUCTURE-NOTES.md`.

## Not Changed

- No live module moved.
- No code behavior changed in this batch.
- No private memory/log contents were read or printed.
- No git commit was made.

## Remaining

- Classification is now current for recall/context/delete evidence, but the
  broader flat root still has many live modules that should be moved only one
  capability group at a time.
- Storage fallback paths still need cleanup boundaries for old
  `memory/knowledge`, `data/external`, and `data/conversation_experience`.

## Next Batch

Move to storage fallback cleanup. The safest next target is making the
remaining legacy storage paths auditable with explicit canonical/legacy
constants and tests, without moving private memory bodies.
