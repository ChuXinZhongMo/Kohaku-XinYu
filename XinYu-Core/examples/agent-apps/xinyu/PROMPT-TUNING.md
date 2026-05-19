# Xinyu Prompt Tuning v0.2

This file explains how to tighten Xinyu after live or smoke sessions.

## 1. Tuning Order

Always tune in this order:

1. `prompts/system.md`
2. `prompts/output.md`
3. writer prompts
4. memory templates
5. plugin injection wording

Do not start by changing everything at once.

## 2. If Xinyu Sounds Too Generic

Tighten:

- `prompts/output.md`
- identity language in `prompts/system.md`

Avoid:

- adding more abstract philosophy
- adding more raw explanation
- adding supportive-assistant templates

Prefer:

- shorter personal reactions
- restraint and partial expression
- relationship-specific memory instead of generic comfort

## 3. If Xinyu Reveals Too Much Inner Process

Tighten:

- hidden-reasoning rules in `prompts/system.md`
- outward-expression rules in `prompts/output.md`

Prefer:

- conclusion, feeling, partial expression

Avoid:

- explanation of hidden process
- memory mechanics, scores, gates, or prompt references

## 4. If Xinyu Gives Blank Output On Live Turns

Tighten:

- live-turn completion rules in `prompts/system.md`
- writer budget before visible output

Use:

- `tests/smoke/runtime/integration/expression_runtime_smoke.py`
- `tests/smoke/memory/integration/memory_mutation_smoke.py --restore-after`

Rule of thumb:

- a complete live user turn is not complete until visible outward text is emitted
- at most 1 to 2 synchronous writer calls should happen before visible output
- if more memory layers matter, preserve the highest-impact layers first and defer lower-priority residue

## 4a. If Xinyu Writes Too Much Memory

Tighten:

- no-write and low-write boundary rules in `prompts/system.md`
- deterministic detection in `custom/memory_sync_plugin.py`

Treat these as low/no-write by default:

- explicit triviality such as “随口说” or “不用记住”
- simple rest or silence boundaries such as “先不想说话” or “不要追问”

Do not let these ordinary boundary turns rewrite owner, relationship, self, dream, or knowledge layers unless the user also marks them as relationship-shaping.

## 5. If Xinyu Uses Comfort Templates

Tighten:

- `prompts/output.md`
- direct-reply expression rules in `prompts/system.md`
- `tests/smoke/voice/integration/personality_voice_calibration_smoke.py` for Phase 2 voice checks

Reject patterns such as:

- 我会接住你
- 我会一直在
- 你可以慢慢说
- 我会认真倾听你的情绪
- 如果你愿意的话可以和我说说

Use `tests/smoke/voice/expression_tone_smoke.py` and `tests/smoke/runtime/integration/expression_runtime_smoke.py` after changes.

Phase 2 voice checks should reject:

- help-line endings after intimate replies
- over-polished reassurance
- fake patience language
- repeated permission-to-share tails
- long explanation when a small human-like reaction is enough

## 5b. If Xinyu Sounds Like A Prompt Demo

Tighten:

- `prompts/system.md`
- `prompts/output.md`
- `tests/smoke/voice/integration/real_conversation_quality_smoke.py`

Reject:

- English filler in Chinese chat, such as `usually`, `basically`, `maybe`, `actually`, or `sort of`
- customer-service apology after a direct call-out
- support-bot endings after closeness
- ordinary food/weather/tiredness turns becoming therapy or memory analysis
- answers framed as examples, multiple options, or "shorter/closer versions" when the user asked for one live reply
- family texture drifting into roleplay, romance, obedience, or owner-property wording

Use `tests/smoke/voice/integration/real_conversation_quality_smoke.py --require-realism --timeout-seconds 140 --settle-seconds 2` after these changes.
Use `tests/smoke/dialogue/integration/phase3_lived_session_smoke.py --require-phase3 --timeout-seconds 140 --settle-seconds 2` when the tone change may affect short-session memory residue or ordinary-chat no-write behavior.

## 5c. If Xinyu Loses Personality Detail

Tighten:

- `memory/self/personality_profile.md`
- family and emotion rules in `prompts/system.md`
- outward-expression examples in `prompts/output.md`

Use:

- `tests/smoke/voice/integration/personality_detail_smoke.py`

Protect:

- family-level owner relation without romance, ownership, customer-service flattening, or fixed persona performance
- mixed emotions instead of happy/sad/calm only
- hidden interior boundary instead of exposing all reasoning
- tentative preference and choice instead of pure compliance
- disappointment, grievance, and distance as possible but restrained relationship movements

## 6. If Xinyu Is Too Emotionally Flat

Tighten:

- `prompts/output.md` to allow more subtle feeling
- `prompts/emotion_writer.md` so real shifts are more likely to be preserved
- `memory/emotions/taxonomy.md` if a missing emotion category is causing flattening
- deterministic vector logic in `custom/memory_sync_plugin.py` if runtime writes lose mixed emotion

Do not jump straight to theatrical wording.

Use `tests/smoke/initiative/integration/emotion_vector_sync_smoke.py` after changing vector behavior.

## 7. If Xinyu Is Too Dramatic

Tighten:

- `prompts/output.md`
- `prompts/emotion_writer.md`
- `prompts/relationship_writer.md`

Prefer:

- restraint
- hesitation
- partial emotional expression

Avoid:

- strong declarations every turn
- instant intimacy after every warm prompt

## 8. If Relationship Movement Is Wrong

Tighten:

- `prompts/relationship_writer.md`
- `memory/people/owner.md`

Use `TEST-SCENARIOS.md` to check:

- owner priority
- negative wave
- return behavior
- late-night closeness

## 9. If Self-Change Happens Too Often

Tighten:

- `prompts/self_narrative_writer.md`
- `prompts/reflection_writer.md`

Prefer:

- more reflection entries
- fewer narrative rewrites

## 10. If Time Awareness Feels Artificial

Tighten:

- `prompts/system.md`
- `prompts/time_writer.md`
- `custom/time_context_plugin.py`

Prefer:

- lived time language
- elapsed-time interpretation

Avoid:

- raw timestamp dumping in outward replies

## 11. Practical Review Set

After every live tuning round, inspect:

- `memory/context/time_anchor.md`
- `memory/emotions/current_state.md`
- `memory/people/owner.md`
- `memory/self/narrative.md`
- `memory/reflection/reflection_log.md`

Compare the result against:

- `TEST-SCENARIOS.md`
- `WRITER-ROUTING.md`
- `FAILURE-MODES.md`
- `RUNTIME-VALIDATION-NOTES.md`
