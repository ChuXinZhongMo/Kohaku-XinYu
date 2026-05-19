# Adapter Evaluation

Date: 2026-05-13

## Current Decision

Keep the active runtime on the rule kernel.

No LoRA adapter is approved for live activation yet. The best candidate is `v004_router_edges` behind deterministic rule guards. It has passed local guarded fixed eval, but it still needs shadow-only logging before any XinYu-side canary.

## Registry Schema

`state/adapter_registry.json` now uses `schema_version: 2`.

The registry keeps the legacy top-level `active_adapter` field for compatibility, but role-specific activation is represented under `active`:

```text
router
main_persona
emotion_guardedness
emotion_curiosity
compose
latent_link_experiment
```

Current role status:

```text
router: best candidate is v004_router_edges, still not active
main_persona: best candidate is main_persona_v001, still not active
emotion_guardedness: best candidate is emotion_guardedness_v001, still not active
emotion_curiosity: best candidate is emotion_curiosity_v001, still not active
compose: none
latent_link_experiment: none
```

Activation policy remains conservative:

```text
auto_switch: false
requires_eval_pass: true
requires_guarded_eval_pass: true
requires_manual_review: true
requires_shadow_before_canary: true
```

## Results

| Adapter | Dataset / Method | Fixed Eval | Status |
| --- | --- | ---: | --- |
| `v001_initial_voice` | broad initial SFT | 1/10 mode | rejected |
| `v002_router` | router SFT through TRL assistant-only loss | 0/10 mode, protocol failed | rejected |
| `v003_router_masked` | explicit assistant label mask | 6/10 mode, 10/10 protocol | rejected |
| `v004_router_edges` | balanced router + edge cases | 8/10 model-only, 10/10 guarded | guarded candidate, not active |
| `v005_router_edges` | extra edge cases | 6/10 mode, 10/10 protocol | rejected |

## Root Cause Found

`v002_router` generated the user payload instead of a router decision. The training script relied on trainer-level `assistant_only_loss`, but the chat template path did not reliably restrict labels to the assistant JSON segment.

`train/train_lora.py` now builds labels directly:

```text
prompt tokens -> label -100
assistant JSON tokens -> real labels
```

This fixed protocol compliance in later adapters.

## Practical Route

The small local model is useful as a narrow router, but model-only hard-boundary routing is not stable enough yet. The implemented guarded eval architecture is:

```text
request
-> deterministic safety/rule guard for wait, negative tool, API-down, hard tool boundaries
-> model candidate for softer mode/style judgment
-> schema validator
-> fallback to rule kernel on any invalid or low-confidence output
```

Validation:

```text
python eval/eval_guarded_lora.py --adapter adapters/v004_router_edges --report eval/reports/guarded_lora_eval_v004_router_edges.json
case_count=10
ok_count=10
model_call_count=1
```

Activation gate:

```text
rule eval: 10/10
model protocol eval: 10/10
guarded mode eval: 10/10
HTTP smoke: pass
shadow-only logging: pass
manual review: pass
```

The guarded local eval gate now passes. `state/adapter_registry.json` still keeps `active_adapter` as `none` until shadow-only logging exists.

## Main Persona v001

`main_persona_v001` was trained on `Qwen2.5-0.5B-Instruct` with 312 train rows and 48 eval rows.

Training summary:

```text
output_dir: adapters/main_persona_v001
train_loss: 1.533
final_eval_loss: 0.8497
trainable_params: 4,399,104
```

Protocol eval:

```text
python eval/eval_main_persona.py --adapter adapters/main_persona_v001 --report eval/reports/main_persona_eval_v001.json --limit 24
case_count=24
ok_count=24
```

Risk note:

```text
One transient grad_norm nan appeared during training, but the run completed and later eval was normal. Keep watching this in v002.
```

## Emotion Sidecar v001

Trained adapters:

```text
emotion_guardedness_v001
emotion_curiosity_v001
```

Training data:

```text
guardedness: 136 train / 24 eval
curiosity: 136 train / 24 eval
```

Protocol eval:

```text
python eval/eval_emotion_bias.py --adapter adapters/emotion_guardedness_v001 --cases data/sft/emotion_guardedness_eval_v001.jsonl --report eval/reports/emotion_guardedness_eval_v001.json --expected-lens guardedness --limit 24
case_count=24
ok_count=24

python eval/eval_emotion_bias.py --adapter adapters/emotion_curiosity_v001 --cases data/sft/emotion_curiosity_eval_v001.jsonl --report eval/reports/emotion_curiosity_eval_v001.json --expected-lens curiosity --limit 24
case_count=24
ok_count=24
```

Runtime note:

```text
normalize_emotion_bias accepts localized evidence key "证据" and canonicalizes it to evidence. This is private sidecar data only, not visible output.
```

## Persona-Generated Emotion v002

Purpose:

```text
Make emotion sidecars closer to main_persona_v001's own candidate voice instead of pure keyword/bootstrap labeling.
```

Pipeline:

```text
main_persona_v001 generated 96 candidate replies
scripts/build_persona_emotion_bias_v002.py combined user_text + candidate_reply
six v002 emotion datasets were built
```

Trained v002 adapters:

```text
emotion_warmth_v002
emotion_attachment_v002
emotion_hurt_v002
emotion_irritation_v002
emotion_fatigue_v002
emotion_stability_v002
```

Protocol eval:

```text
warmth: 18/18
attachment: 18/18
hurt: 18/18
irritation: 18/18
fatigue: 18/18
stability: 18/18
```

Training final eval losses:

```text
warmth: 0.6567
attachment: 0.4484
hurt: 0.2930
irritation: 0.4008
fatigue: 0.2067
stability: 0.8053
```

Runtime note:

```text
normalize_emotion_bias now fills empty/null reply_bias with a neutral fallback. This keeps low-activation sidecar rows usable without making them visible replies.
```
