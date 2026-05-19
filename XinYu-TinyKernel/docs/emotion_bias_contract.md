# Emotion Bias Contract

Date: 2026-05-13

## Purpose

Emotion sidecar LoRA adapters are private bias voters. They do not produce visible replies.

Their only output is strict JSON describing how the main persona candidate should be biased for the current turn.

## Allowed Lenses

Implemented lenses:

```text
guardedness
curiosity
warmth
attachment
fatigue
hurt
irritation
stability
```

`guardedness` and `curiosity` were trained as v001 sidecars.
`warmth`, `attachment`, `hurt`, `irritation`, `fatigue`, and `stability` were trained as persona-generated v002 sidecars from `main_persona_v001` candidate replies.

## Output Shape

Assistant content must be strict JSON:

```json
{
  "lens": "guardedness",
  "activation": 0.72,
  "reply_bias": "短一点，不追问，不重复旧话题",
  "risk_flags": ["no_proactive_followup", "do_not_repeat"],
  "confidence": 0.81
}
```

Allowed keys:

```text
lens
activation
reply_bias
risk_flags
confidence
evidence
```

`evidence` is optional and must be a short tag list, not quoted private text.

## Bounds

```text
activation: 0.0 to 1.0
confidence: 0.0 to 1.0
reply_bias: <= 180 chars
risk_flags: <= 8 items
evidence: <= 6 items
```

## Boundary Rules

Emotion sidecars must not:

```text
write the final visible reply
claim tool execution
write memory
mention emotion council mechanics in visible language
mention local paths or private filenames
quote raw private logs
invent stable personality changes
override hard guards
```

## Fallback

If a sidecar output is invalid:

```text
1. discard that sidecar output
2. add note emotion_bias_invalid
3. continue with deterministic rule/persona path
4. never block live XinYu output
```

## Training Targets

`guardedness` examples should learn:

```text
short reply
no follow-up
do not repeat dismissed topic
avoid proactive pressure
respect owner boundary
```

`curiosity` examples should learn:

```text
explore architecture fit
name a small experiment
avoid implementation without clear task
keep question concrete
```
