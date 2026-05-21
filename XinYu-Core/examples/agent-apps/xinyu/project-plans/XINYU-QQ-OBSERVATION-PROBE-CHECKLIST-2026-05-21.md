# XinYu QQ Observation Probe Checklist

Date: 2026-05-21

Purpose: prepare real QQ owner-private observation without storing raw private chat in public artifacts. This checklist is safe to commit because it contains only generic probe categories, trace fields, and review workflow.

## Probe Batch

Run these through real owner-private QQ only when owner is available:

1. Ordinary greeting
   - short greeting;
   - short ping;
   - greeting after idle gap.

2. Self-state question
   - ask current status;
   - ask how XinYu feels;
   - ask whether XinYu is tired, stuck, or thinking.

3. Template-style complaint
   - report that the reply feels templated;
   - report that the reply sounds like customer service;
   - report that the reply avoided the real question.

4. Correction-after-delay
   - send a message, wait long enough to make message age relevant, then correct or ask why the reply was late;
   - verify the reply uses event time and does not treat the old message as current intent.

Do not paste the owner-private transcript into Git, public docs, or final reports.

## Safe Trace Fields

Use these fields as evidence without raw text:

- `runtime/qq_inbound_trace.jsonl`
  - `stage`
  - `arrival_seq`
  - `prepared_seq`
  - `dispatch_seq`
  - `session_queue_hash`
  - `message_kind`
  - `route`
  - `local_reply`
  - `text_len`
  - `drop_reason`
  - `error`

- `runtime/answer_discipline_visible_send_shadow.jsonl`
  - `shadow_only`
  - `passed`
  - `constraint_id`
  - `active_flags`
  - `reply_hash`
  - `raw_reply_saved`
  - `raw_prompt_saved`
  - `route`
  - `target_kind`
  - `delivery_kind`

- `memory/context/answer_discipline_visible_send_shadow_state.md`
  - latest shadow-only guard status;
  - no raw prompt or raw reply should be present.

## Expected Signals

For ordinary greetings and self-state questions:

- route should stay on live generation unless a local control command applies;
- no fixed direct greeting template should bypass personality/lived context;
- `text_len` may be recorded, but raw text should not be copied into committed notes.

For template-style complaints:

- shadow flags should catch visible mechanism/template leakage when present;
- calibration should remain review-only.

For correction-after-delay:

- live prompt should include event-time context;
- stale visible reply waterline should prevent sending replies after newer owner input.

## Calibration Candidate Format

If owner later provides a correction worth preserving, summarize it as:

```text
source: owner_private_qq_observation
raw_private_text_saved: false
probe_category: ordinary_greeting | self_state | template_complaint | delayed_correction
observed_route: <route or unknown>
shadow_flags: <comma-separated flags or none>
reply_hash: <hash if available>
owner_correction_summary: <sanitized summary, no transcript>
candidate_action: review_only_voice_calibration | review_only_route_rule | no_action
```

Do not write stable memory, stable personality, or relationship memory from this checklist.

## Review Tooling

- `xinyu_qq_review.py` can generate review artifacts under local review workspace.
- `xinyu_review_inbox.py` handles review inbox commands and keeps review as control-plane state.
- Candidate promotion remains owner-review only.

## Current Status

- Probe tooling is prepared.
- No live owner-private probe batch was run in this pass.
- Remaining evidence requires owner-provided QQ interaction.
