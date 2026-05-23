# XinYu Persona / Memory Review Worklog - 2026-05-23

## Scope
- Review current memory candidate and personality gate state without printing private candidate text.
- Keep stable personality and long-term memory writes blocked unless owner explicitly applies a reviewed candidate.

## Current candidate inventory
- total_unique_candidates: 209
- by_status:
  - applied_growth_log: 1
  - owner_review_required: 1
  - self_approved_recent_context: 164
  - self_approved_voice_review: 43
- by_type:
  - post_reply_growth_candidate: 1
  - owner_preference: 1
  - project_fact: 130
  - codex_result: 34
  - voice_correction: 43
- by_target:
  - memory/reflection/growth_log.md: 1
  - memory/people/owner.md: 1
  - memory/context/recent_context.md: 164
  - memory/self/voice_calibration_log.md: 43

## Growth-log candidates
- pending_apply_count: 0
- applied_count: 1
- applied candidate:
  - candidate_id: manual-growth-e2e-20260523-1845
  - status: applied_growth_log
  - target_memory_layer: memory/reflection/growth_log.md
  - stable_memory_write: already_applied

## Owner-review candidate requiring decision
- candidate_id: memcand-3fec6175ce50bc68f6
- status: owner_review_required
- candidate_type: owner_preference
- target_memory_layer: memory/people/owner.md
- target_gate: owner_memory_review
- risk_flags:
  - memory_immune:observe_more
  - danger:medium
  - action:observe_for_repetition
  - scope:owner_private
- recommended_action: keep owner_review_required / observe_more unless owner explicitly confirms the preference should become durable owner memory.
- stable_memory_write: blocked

## Personality gate snapshot
- personality_change_state: profile_review_ready, change_pressure=100, stable profile write review-only.
- personality_evolution_state: active_trial, runtime_trial_only.
- personality_self_review_state: continue_trial, profile_changed=false.
- recommended_action: continue runtime trial; prepare stable profile candidate report only after visible behavior feedback, not auto-apply.

## Desktop owner-review status
- Growth candidate status now includes `owner_review_required_count` and `owner_review_required` summary rows.
- Owner-review rows expose only candidate id, status, type, target layer, target gate, and risk flags.
- Owner-review candidate body is hidden as `hidden_owner_review_required` for Desktop/API summary surfaces.
- Desktop panel now shows a read-only `待审查` count and local-CLI review hint.

## Validation
- `python -m pytest tests/test_memory_promotion.py -q` -> 7 passed.
- `npm run typecheck` in `D:\XinYu\XinYu_Desktop` -> passed.
- `npm run build` in `D:\XinYu\XinYu_Desktop` -> passed.
- Core API read-only spot check: `owner_review_required_count=1`, `candidate_text_preview=hidden_owner_review_required`, `body_hidden=True`.

## Boundaries kept
- No private candidate body printed.
- No stable personality write performed.
- No owner memory write performed.
- No automatic growth_log apply needed because pending growth candidates are zero.
