# Claude Diagnostic: SUCCESS markers mojibake vs trial_success_streak

created_at: 2026-05-31
owner: Atimea
director: Codex
executor: Claude
mode: read_only_diagnostic (no code changed)
related: docs/plans/CLAUDE-HANDOFF-AUTONOMY-STAGE12-13.md (Phase C)
app_root: XinYu-Core/examples/agent-apps/xinyu

## 0. Question

During Phase C the Stage 8 learning-trial validation packet printed garbled
Chinese (e.g. `镇�锒跺�氛简`, contains `U+FFFD`) inside
`success_capture_contract`. Question raised: do the mojibaked SUCCESS markers in
`xinyu_learning_closed_loop.py` break owner success-feedback matching, and is
that why `trial_success_streak` stays 0 for the active key `memory_mechanics_leak`?

This document is read-only. No code was changed. It records the answer with
exact file:line references and a recommended (not yet applied) fix scope.

## 1. Verdict (TL;DR)

- The "mojibake" is **intentional**, not corruption. `readable_markers()`
  deliberately expands every clean marker with legacy GBK/CP936 decode variants
  (including `U+FFFD` and `?`-replaced forms) so matching also catches owner
  text that arrived through an old, wrongly-decoded pipeline. Source literals are
  clean (e.g. `"自然多了"`).
- It does **NOT** break matching of clean owner success text.
- It does **NOT** cause `trial_success_streak=0` for `memory_mechanics_leak`.
  That streak=0 is the designed gate behaviour (repeated guard failures + same
  -turn success suppression), unrelated to the markers.
- The only real problem is **display hygiene**: the variants leak into
  owner-visible packet text and previously crashed the CLI on a GBK console.

## 2. Where the markers / matching / streak logic live (exact lines)

`xinyu_learning_closed_loop.py`:
- `SUCCESS_MARKERS = readable_markers("自然多了", …)` — L126–165 (literals clean)
- `GENERIC_SUCCESS_MARKERS` / `SPECIFIC_SUCCESS_MARKERS` — L167–169
- `SUCCESS_REPLY_CONTEXT_MARKERS` — L171–184
- `STYLE_REPAIR_SUCCESS_MARKERS` — L186–208
- `SUCCESS_CANCEL_MARKERS` — L210–225
- `_contains_any` — L320–321 (`any(marker and marker in text …)`, OR over the set)
- failure assembly `_classify_*` — L447–476 (guard flags → failures)
- `_success_observed` — L479–488 (SPECIFIC, or GENERIC + REPLY_CONTEXT)
- `_owner_reported_style_repair_success` — L369 (STYLE_REPAIR and not CANCEL)
- `_filter_failures_for_explicit_success` — L491–500
- success/failure precedence (success suppressed by concurrent failure) — L746–753
- failure branch (streak reset) — L788–805 (`trial_success_streak="0"`,
  `success_evidence_status="reset_by_failure"`)
- success branch (streak increment) — L809–830 (`trial_success_streak`+1,
  `same_trial_explicit_owner_success`, `>=2` → `promotion_signal`)

`xinyu_text_variants.py`:
- `readable_markers()` — L109–118 (clean marker first, then variants)
- `legacy_mojibake_variants()` — L43–58 (utf-8 → gbk/gb18030/cp936 decode ×
  strict/replace/ignore; adds `variant` and `variant.replace("�","?")`).
  **This is the only source of `U+FFFD`/`?` strings; in-memory only.**

## 3. Is matching affected?

No. Two facts:
1. The clean marker is always the **first** element of each `readable_markers`
   group; `_contains_any` is an OR, so clean owner text matches the clean form.
   Variants only ADD coverage; they cannot make a clean match fail.
2. Variants are CJK-range / multi-char, so false-positive risk against normal
   text is negligible (and generic success is double-gated by
   `SUCCESS_REPLY_CONTEXT_MARKERS`, L488).

## 4. Is the current active learning key affected?

No. For `active_trial_key = memory_mechanics_leak`:
- The failure is raised from **guard flags**, not user-text markers:
  `_classify_*` L448–450 maps
  `CRITICAL_GUARD_FAILURES["visible_memory_mechanics_naturalized"]
  -> "memory_mechanics_leak"` (mapping at L27–32).
- Each such failure resets `trial_success_streak="0"` and
  `success_evidence_status="reset_by_failure"` (L799/L803); `repair_count=106`
  shows it fires repeatedly.
- Even with an explicit owner success in the same turn, the success is
  suppressed: `_filter_failures_for_explicit_success` (L491–500) only un-
  suppresses `owner_reported_template_voice_failure`, NOT
  `memory_mechanics_leak`, so `success=False` (L746–753).
- `latest_success_trial_key = owner_reported_template_voice_failure` (a
  different, older trial) does not count toward the `memory_mechanics_leak`
  streak.

=> streak=0 is correct gate behaviour: owner success only counts on a clean turn
(no memory-mechanics guard hit) for the same trial key.

## 5. Consumers of the SUCCESS markers

| module | matches? | note |
|---|---|---|
| `xinyu_learning_closed_loop.py` | YES | only true matcher (L369, L486–488) |
| `xinyu_owner_feedback_effects.py` | NO | does not import markers; reads learning STATE fields only |
| `xinyu_stage8_learning_trial_validation_packet.py` | DISPLAY ONLY | imports at L12–15; `_sample_markers` display at L273–276 — this is the `U+FFFD` leak into the packet |
| `xinyu_stage8_memory_review_packet.py` | NO | uses its own `CONTROLLED_TOPIC_HINTS` |
| `xinyu_status.py` | NO | reads STATE only |

## 6. Existing test coverage of success -> streak -> gate

Covered (clean input), `tests/test_learning_closed_loop.py`:
- L47 `..._updates_trial_counts` → `trial_success_streak: 1`, `same_trial_explicit_owner_success`
- L142 `..._resets_when_trial_key_changes` → streak 2 then `reset_by_failure`
- L197 `..._resolved_template_feedback_as_same_trial_success` → streak 2
- L234 `..._keeps_mixed_template_feedback_as_failure` → cancel marker → streak 0

Gaps (not bugs):
- No test feeds mojibaked owner success text and asserts it still matches (the
  variant path has no regression guard).
- No test for the `memory_mechanics_leak` concurrent-guard-failure suppression
  path (L746–753 with a critical guard flag).
- No dedicated unit test for `xinyu_text_variants.readable_markers /
  legacy_mojibake_variants`.

## 7. Recommended fix scope (NOT applied)

Matching logic needs no fix. Only display hygiene + test backfill:

- Scope A (recommended first): make `_sample_markers`
  (`xinyu_stage8_learning_trial_validation_packet.py:90`, called L273–276) emit
  only readable/clean markers — filter out any candidate containing `�` or
  `?`-replacement — so packets/worklogs never show `镇�锒跺�氛简` and do not
  depend on console encoding. Keep the variants in the matching set untouched.
- Scope B (optional): add a shared `display_markers()` that returns only clean
  forms, for any owner-visible renderer; keep `readable_markers()` for matching.
- DO NOT remove/rewrite `legacy_mojibake_variants` and DO NOT strip variants
  from `SUCCESS_MARKERS` — that would weaken tolerance to historically mojibaked
  input.
- Note: one CLI crash was already mitigated in Phase C by adding
  `sys.stdout.reconfigure(encoding="utf-8")` to
  `xinyu_stage8_learning_trial_validation_packet.py main()` (that change is the
  only code touched, and it was part of Phase C, not this diagnostic).

## 8. Recommended tests

1. `test_text_variants_readable_markers_keeps_clean_form_first` — first element
   is the clean literal; clean text matches via `_contains_any`.
2. `test_closed_loop_success_matches_legacy_mojibake_feedback` — feed a GBK-
   mojibaked "自然多了"; assert `_success_observed` True and streak+1.
3. `test_closed_loop_memory_mechanics_guard_suppresses_concurrent_success` —
   same turn with `visible_memory_mechanics_naturalized` guard flag + owner
   praise; assert `success=False`, `reset_by_failure`, streak 0.
4. (if Scope A taken) `test_learning_trial_validation_contract_samples_are_display_clean`
   — packet `accepted_success_marker_examples` contains no `�`/`?`.
5. (regression) keep the four clean-path tests in
   `tests/test_learning_closed_loop.py`.

## 9. One-line summary for Codex

The marker "mojibake" is `readable_markers` compatibility variants by design;
the matching path is correct and does not affect `memory_mechanics_leak`'s
streak=0 (that is normal gate behaviour from repeated guard failures + same-turn
suppression). The only real issue is variants leaking into owner-visible
display (which crashed a GBK console). Recommend a display-only filter plus the
three matching/suppression tests above. Do not alter the matching set.
