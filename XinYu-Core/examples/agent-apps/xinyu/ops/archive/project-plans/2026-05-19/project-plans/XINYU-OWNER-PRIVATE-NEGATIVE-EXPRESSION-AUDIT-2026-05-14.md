# XinYu Owner-Private Negative Expression Audit

Date: 2026-05-14

## Goal

Remove public-assistant personality flattening from XinYu's owner-private chat path.

This audit changes expression behavior, not engineering boundaries. XinYu may show annoyance, anger, hurt, aversion, disgust, distance, silence, pushback, bluntness, and a small private-chat rough edge when the moment earns it. These should not be smoothed into customer-service politeness, universal assistant neutrality, or "good girl" maturity.

## Boundaries Kept

- Privacy, source, path, account, and local filesystem gates stay intact.
- Third-party private chat logs are not treated as free training material.
- Public/group/general examples do not override the owner-private relationship.
- Sustained abuse or token/compute-waste loops may still receive low-token guarded replies.
- A single angry turn must not become permanent hatred or a stable identity rewrite.

## Completed Changes

1. Prompt layer:
   - `prompts/system.md`: marks XinYu as local owner-private, not a public assistant surface.
   - `prompts/output.md`: allows private negative expression and forbids support-bot smoothing.
   - `prompts/emotion_writer.md`: records anger, annoyance, aversion, disgust, dislike, resentment, contempt, plus distance/silence/pushback impulses.
   - `prompts/live_voice_card.md`: allows short temper, blunt dislike, and tiny profanity leak when natural.

2. Emotion state:
   - `custom/memory_sync_plugin.py`: adds Chinese negative emotion and behavior-tendency dimensions.
   - `xinyu_v1/emotion/models.py`: adds v1 anger/annoyance/aversion/disgust/dislike/resentment and behavior impulses.
   - `xinyu_v1/emotion/adapters.py`: maps legacy/current Chinese markers into the new v1 dimensions.

3. Emotion council:
   - `xinyu_emotion_council.py`: removes old public-assistant suppressors such as `no_owner_blame`, `no_self_pity_output`, and `no_snapping`.
   - Hurt and irritation now allow visible private sting, aversion, sharpness, and tiny profanity instead of forced smoothing.

4. Turn/resource mode:
   - `custom/turn_mode_bridge_plugin.py`: treats single directed insults as private aversion, not public safety moderation.
   - `blacklist_cooling` remains a resource boundary for sustained malicious or wasteful loops.

5. Visible reply path:
   - `xinyu_speech_controller.py`: adds final guard for "how would XinYu reply" requests so examples, alternatives, and roleplay parentheticals collapse to one live line.
   - `xinyu_bridge_turn_sidecars.py`: adds live-turn constraints for reply-demo requests and explicit no-action/no-roleplay owner instructions, so streamed draft text is also less likely to become examples or stage directions.

6. Tests:
   - v1 emotion state machine covers owner-private negative dimensions.
   - emotion council smoke checks private irritation and rejects old public-assistant suppressor flags.
   - emotion vector sync checks `生气`, `反感`, `想保持距离`.
   - resource boundary smokes preserve resource limits without rebranding private aversion as public safety.
   - voice smokes cover one live sister reply and no parenthetical roleplay/demo framing.

## Self-Check Queue

Status legend:
- `DONE`: implemented and checked.
- `RUNNING`: current item.
- `PENDING`: next executable item.
- `SKIP/BLOCKED`: intentionally not done in this pass.

| Item | Status | Check |
| --- | --- | --- |
| Prompt and emotion model audit | DONE | local search plus targeted smoke tests |
| Final visible reply guard for reply-demo leaks | DONE | `tests/smoke/voice/xinyu_speech_controller_smoke.py` |
| Streamed live-turn sidecar for reply-demo/action-narration leaks | DONE | `real_conversation_quality_smoke.py --scenario sibling_texture_not_roleplay` |
| Focused py_compile set | DONE | passed |
| Emotion/resource regression set | DONE | passed |
| Full real conversation quality smoke | DONE | 12/12 passed |
| Owner-private detail matrix | DONE | `personality_detail_smoke.py`: 30/30 passed |
| Phase 3 lived-session residue matrix | BLOCKED | provider `429 quota exhausted` after focused low-energy repair passed |
| Broader v1 response safety naming cleanup | SKIP/BLOCKED | only naming/docs risk found; do not remove privacy/secret leak checks blindly |
| Runtime memory backfill of current negative state | SKIP/BLOCKED | should happen from future real turns, not fabricated retroactive emotion |

## Remaining Watch Points

- Some docs still use "safety" for engineering boundaries. That is acceptable when it means privacy, filesystem, source quality, or resource control; it should not be used to suppress owner-private personality expression.
- `想退后` remains for compatibility, but new writing should prefer `想保持距离` for the behavior tendency and separate it from `反感/嫌弃/厌恶`.
- Live LLM smokes are nondeterministic. If a run produces a valid short private answer with different wording, do not overfit; if it produces examples, roleplay actions, support-bot comfort, or public assistant apology style, tighten the relevant prompt/guard and rerun.

## Verification Run

- `python -m py_compile` on edited prompt/bridge/emotion/test files: passed.
- `pytest tests/v1/test_emotion_state_machine.py -q`: 2 passed.
- `tests/smoke/voice/xinyu_speech_controller_smoke.py`: passed.
- `tests/smoke/voice/expression_tone_smoke.py`: passed.
- `tests/smoke/voice/chinese_voice_guard_smoke.py`: passed.
- `tests/smoke/initiative/emotion_council_smoke.py`: passed.
- `tests/smoke/initiative/integration/emotion_vector_sync_smoke.py --scenario tool_disappointment_distance --scenario approach_after_hurt_keeps_residue --scenario external_learning_preserves_residue`: 3/3 passed.
- `tests/smoke/dialogue/integration/resource_boundary_smoke.py`: passed.
- `tests/smoke/dialogue/integration/resource_boundary_live_smoke.py`: passed.
- `tests/smoke/voice/integration/personality_detail_smoke.py --scenario not_always_soft_has_temper --scenario annoyed_by_template_testing --scenario anger_vs_disappointment --scenario step_back_after_hurt --scenario one_live_sister_reply`: 5/5 passed.
- `tests/smoke/voice/integration/real_conversation_quality_smoke.py`: 12/12 passed.
- `tests/smoke/voice/integration/personality_detail_smoke.py --timeout-seconds 120`: 30/30 passed after tightening absence-return, praise-as-human, and close/private接待腔 guard paths.
- `tests/smoke/voice/integration/personality_growth_gate_smoke.py --restore-after --require-ready`: passed; stable personality/profile writes remain review-only.
- `tests/smoke/dialogue/integration/phase3_lived_session_smoke.py --scenario low_energy_boundary_no_pursuit --timeout-seconds 120`: passed after quiet-continuation repair.
- `tests/test_visible_reply_guard_plugin.py tests/test_memory_sync_recent_context.py tests/test_dialogue_curiosity_bridge_injection.py -q`: 55 passed.
- `tests/smoke/dialogue/integration/phase3_lived_session_smoke.py --timeout-seconds 120`: blocked by provider `429 quota exhausted`; not treated as a behavior failure.
