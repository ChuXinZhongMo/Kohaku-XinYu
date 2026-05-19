# XinYu P29 QQ / Self Action / Sticker / Voice Direct Writer Guard Batch

Date: 2026-05-19

## Goal

Clear the remaining runtime-facing direct timestamp writer candidates in the QQ, self-action, sent-reply index, sticker import, voice learning, and v1 emotion compatibility surfaces.

## Completed

- `xinyu_qq_gateway.py`
  - Renamed the owner-private coalescing buffer's internal `updated_at` monotonic clock field to `updated_monotonic_at`.
  - Kept a read fallback for any live in-memory buffer that still has the previous key.
- `xinyu_self_action_gateway.py`
  - Normalized `checked_at` / `decided_at` through `_timestamp_or_now_iso`.
  - Guarded state and handoff `updated_at` writes.
- `xinyu_self_action_patch_executor.py`
  - Normalized executor `checked_at`.
  - Guarded patch task `created_at`, state `updated_at`, and markdown compatibility timestamps.
- `xinyu_sent_reply_index.py`
  - Added `_timestamp_or_now_iso`.
  - Guarded `sent_at`, `first_seen_at`, `last_seen_at`, and index `updated_at`.
- `xinyu_sticker_import.py`
  - Added `_timestamp_or_now_iso`.
  - Guarded corrections and generated sticker manifest `updated_at` writes.
- `xinyu_voice_learning.py`
  - Added `_timestamp_or_now_iso`.
  - Guarded voice correction `recorded_at` and log `updated_at`.
- `xinyu_v1/emotion/persistence.py`
  - Guarded compatibility markdown `updated_at`.

## Result

- Target direct writer candidates: 8 -> 0.
- Global direct writer candidates: 10 -> 2.

Post-P29 timestamp writer guard audit counts:

```json
{
  "direct_writer_candidate": 2,
  "guarded": 306,
  "reference_only": 82,
  "report_metadata_candidate": 73,
  "template_timestamp_candidate": 167,
  "unguarded_candidate": 85
}
```

Remaining direct writer candidates:

- `xinyu_creative_writing.py:1080` `updated_at`
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/BRAIN/chat_with_ai.py:88` `timestamp`

Sidecar scout result:

- `xinyu_creative_writing.py` is active/core and should be normalized in the next code batch.
- `learning/self_found/.../chat_with_ai.py` is archive/vendor/sample material under a timestamped learning import bundle. Prefer excluding or classifying it out of active audit scope instead of editing vendor/sample code.

## Validation

- `python -m py_compile` on all P29 touched files: passed.
- Focused pytest:
  `tests/test_timestamp_writer_guard_audit.py tests/test_self_action_gateway.py tests/test_self_action_patch_executor.py tests/test_gateway_ack_spool.py tests/v1/test_emotion_state_machine.py tests/v1/test_v1_smoke_contract.py -q`
  passed: 32 passed.
- Focused smoke checks passed:
  `self_action_gateway`, `self_action_patch_executor`, `voice_learning`, `xinyu_sticker_import`, `xinyu_qq_gateway`.
- Full pytest passed: 574 passed.
- Quick smoke passed: `smoke_run.py --group quick --restore-after`.
- `git diff --check` passed with LF/CRLF warnings only.

## Next

Run P30:

1. Normalize the active `xinyu_creative_writing.py:1080` direct writer.
2. Classify or exclude the archive/vendor sample under `learning/self_found/.../chat_with_ai.py` from active timestamp writer audit scope.
3. Re-run timestamp writer guard audit and close this direct-writer sequence only when direct writer candidates reach 0.
