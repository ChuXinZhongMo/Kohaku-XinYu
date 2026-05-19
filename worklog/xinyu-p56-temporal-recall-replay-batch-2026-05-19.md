# XinYu P56 Temporal Recall Replay Batch

Date: 2026-05-19

## Goal

Turn the owner's nap-time idea into a replayable engineering rule:

1. recall by normal keyword/need routing first,
2. then bind recalled items to event time,
3. then infer human-scale context such as "just woke from a nap".

## Completed

- Extended retrieval replay fixtures with a synthetic owner-private nap sequence.
- Allowed replay archive turns to inject safe `event_time` metadata without
  reading or printing private memory bodies.
- Passed `evaluated_at` from replay cases into the canonical living-memory
  recall path.
- Added a Chinese temporal-memory unit case:
  - `2026.5.18 12:30` owner starts a nap
  - `2026.5.18 13:30` owner wakes
  - evaluated at `2026-05-18T13:35:00+08:00`
  - expected inference: `recent_wake_from_nap` with `sleep_to_wake_minutes: 60`

## Direct Impact

- The recall path now has regression coverage for "keyword first, time second,
  human logic third".
- Chinese nap/wake summaries are covered, not only English marker text.
- The prompt block must include `## Temporal Context`, the nap inference, and
  `time_context:` hints after archive recall.

## Validation

- Focused pytest passed:
  `tests/test_retrieval_replay_cases.py tests/test_temporal_memory_context.py tests/test_living_memory_recall.py -q`
  passed: 21 passed.
- Replay smoke passed: `smoke_run.py --group replay --restore-after`, 23 passed.
- Full app pytest passed: 589 passed.
- Quick smoke passed: `smoke_run.py --group quick --restore-after`.
- `git diff --check` passed with LF/CRLF warnings only.

## Next

No additional temporal recall mutation is needed before review. The next
autonomous step should be a read-only readiness scan: refresh commit/readiness
and boundary audits after P53-P56, then decide whether any remaining risk is
safe to handle without human review.
