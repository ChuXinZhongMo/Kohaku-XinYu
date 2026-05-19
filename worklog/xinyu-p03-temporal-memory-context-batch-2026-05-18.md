# XinYu P03 Temporal Memory Context Batch

Date: 2026-05-18
Workspace: `D:\XinYu`
Package: P03 `core-runtime-services-stores`

## Goal

Add human-like temporal context to canonical living-memory recall:

1. recall by keyword/source first
2. inspect recalled item time
3. convert time distance into human context
4. allow lightweight life-state inference, such as "just woke from a nap"

## Completed

- Added `xinyu_temporal_memory_context.py`.
- Updated `xinyu_living_memory_recall.py` so the canonical owner applies temporal context after provider recall/rerank.
- Added `Temporal Context` prompt section with recency, sequence, and safe inference hints.
- Added `time_context:` hints to recalled item relevance.
- Added `temporal_context_binding` to neuro-inspired recall rules.
- Added tests for:
  - dotted timestamp parsing like `2026.5.18 22:37`
  - ISO timezone preservation
  - recent same-scene labels
  - 12:30 nap + 13:30 wake -> `recent_wake_from_nap`
  - canonical recall owner integration

## Human Behavior Rule

If the recalled evidence says:

- sleep started around `12:30`
- wake/rest-end happened around `13:30`
- the current turn is near `13:30`

then XinYu can treat the reply as "刚午睡完/刚休息完" context.

This is context shaping only. It must not invent events, and the current owner message still wins.

## Validation

- Focused pytest:
  - `tests/test_temporal_memory_context.py`
  - `tests/test_living_memory_recall.py`
  - `tests/test_neuro_memory_rules.py`
  - `tests/test_context_retrieval_owner_scenarios.py`
  - `tests/test_retrieval_need_reranker.py`
  - result: `24 passed`
- Full app pytest: `545 passed`
- Quick smoke with `--restore-after`: passed
- `git diff --check`: passed; CRLF warnings only

## Next

- P03 still needs behavior review for how temporal context should affect visible voice strength.
- P04 should later verify QQ/desktop adapters pass enough timestamp metadata into the canonical recall path.

No private memory bodies, raw QQ payload bodies, tokens, or secrets were read or printed.
No git commit was made.
