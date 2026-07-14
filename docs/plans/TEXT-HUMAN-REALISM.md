# Text-first human realism (no TTS required)

Status: active 2026-07-14  
Goal: maximize *text* companion realism before investing more in voice.

## Product goal (reframed)

Not “pass as human forever.”  
**Be a consistent person in private chat for days without cheap tells.**

Cheap tells (kill these first):

1. Wrong calendar facts (周几 / 日期 / 时段)
2. Mechanical service tails (“要不要我帮你…”)
3. Memory amnesia or invented shared history
4. Persona drift into generic assistant
5. Over-explaining / apology templates on simple corrections

## Stack already in place

| Layer | Module / flag | Role |
|-------|----------------|------|
| Voice seed | `prompts/live_voice_card.md` | Tone, bartender anchor, anti-template |
| Time anchors | `xinyu_bridge_state_text_time` + plugin | ISO + **explicit weekday** |
| World anchors | `xinyu_text_world_anchors` | Hard today/weekday block + post-repair |
| Natural voice | `XINYU_NATURAL_VOICE=1` | Loosen stiff guards (keep anti-leak) |
| Life reply policy | `xinyu_life_reply_policy` | Strip service-offer tails; length pressure |
| Visible sanitize | `xinyu_visible_*` | Leak/dedupe before QQ send |
| Lean prompt | `XINYU_LEAN_PROMPT` | Less meta sludge burying mid models |

## Landed this pass

1. **Prompt**: inject `world_anchor_prompt_block()` into lean + full live system prompts.
2. **Post-send guard**: `visible_reply()` repairs clear `今天是周日` style mistakes to runtime weekday.
3. **Docs**: this plan as the text-only roadmap.

## Next text-only milestones (ordered)

### M1 — Fact spine (1–2 weeks)
- Expand anchors: holiday, “今晚/明天早上” relative language resolution.
- Owner-correction latch: when owner asserts a fact, sticky for N turns.
- Optional: refuse to claim 周几 unless anchor present (already partially true).

### M2 — Rhythm as text (not TTS)
- Delay policy table by turn class (info / chat / emotional) without fake “Thinking…”.
- Prefer short uneven replies over polished paragraphs.
- Silence as valid action for low-value pings.

### M3 — Continuity spine
- 20 “relationship core facts” always-retrievable pack.
- Continuity canary: sample turns that require recall of owner name/preferences.
- Ban inventing events not in memory with a soft “我不确定” path.

### M4 — Persona consistency score
- Offline judge: reply vs live_voice_card (warm+edge, short, no service tail).
- Regression set from real QQ logs (redacted fixtures only).

### M5 — Inner thought → text initiative
- Only proactive text with `why_now`; else stay quiet.
- Align with CHI Inner Thoughts framing without multi-party complexity first.

## Explicit non-goals (for this track)

- TTS / prosody / sample-rate tuning
- Avatar / uncanny visual embodiment
- Full-tree ruff green
- Desktop toolchain majors

## Evaluation (owner)

Use `docs/system/USAGE-OBSERVATION-CHECKLIST.md` text rows:

- 7 consecutive private days
- 0 hard calendar errors after restart
- Service-offer tails rare
- Feels like same person, not a new bot each morning

## Env checklist for text realism

```text
XINYU_NATURAL_VOICE=1
XINYU_HUMAN_VOICE_UNIFIED_PROMPT=1
XINYU_HUMAN_VOICE_BYPASS_MODEL=1
XINYU_LEAN_PROMPT=1   # if mid-tier model drowns in sidecars
```

Restart core bridge after env changes: `.\XinYu.ps1 start qq` then `.\XinYu.ps1 health`.
