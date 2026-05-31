# XinYu Proactive Direct Send Worklog — 2026-05-23

## Goal
Move proactive messaging from preview/candidate-only behavior to a bounded direct-send path.

## Implemented
- Added `xinyu_proactive_direct_sender.py`.
- The sender runs the existing proactive request loop with `delivery_level=queue_owner_private` instead of bypassing it.
- It claims only gated QQ candidates through `claim_proactive_qq_message`.
- It enqueues one owner-private QQ outbox item through `enqueue_owner_qq_outbox_message`.
- It acknowledges the proactive dispatch lifecycle after queueing.
- It keeps the existing owner-private, grant, concrete-question, non-generic, duplicate, cooldown, and boundary gates in front of direct send.
- It does not write stable persona or owner long-term memory.

## Safety notes
- No group dispatch is introduced.
- No candidate is sent unless the existing proactive gate marks it claimable.
- Repeated attempts dedupe by proactive request id.
- Dry-run claims are acknowledged as failed with `dry_run_not_enqueued`, so they do not leave a pending claim.

## Verification
- `python -m pytest tests/test_proactive_direct_sender.py tests/test_proactive_controlled_lifecycle.py tests/test_proactive_contract.py -q`
  - 12 passed
- `python -m pytest tests/test_memory_promotion.py tests/test_personality_evolution.py tests/test_proactive_direct_sender.py tests/test_proactive_controlled_lifecycle.py tests/test_proactive_contract.py -q`
  - 29 passed
