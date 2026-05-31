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

## Inner System v002

`qwen35_9b_inner_system_v002` was trained on the protocol/persona repair dataset for Qwen3.5-9B.

Training data:

```text
train_rows=1360
eval_rows=80
coverage:
  protocol_exact_schema=120
  invalid_field_repair=100
  mode_disambiguation=180
  external_action_boundary=140
  memory_candidate_boundary=100
  wait_clarify_local_only=100
  emotion_persona_integration=220
  anti_assistant_voice=160
  inner_conflict=120
  owner_boundary=120
```

Training result:

```text
output_dir: adapters/qwen35_9b_inner_system_v002
train_loss: 0.2304
final_eval_loss: 0.005630
```

Guarded full eval:

```text
python eval/eval_inner_system.py --adapter adapters/qwen35_9b_inner_system_v002 --cases data/sft/inner_system_eval_v002.jsonl --report eval/reports/inner_system_eval_v002_full_after_guard.json --max-cases 80

case_count=80
strict_json_ok_count=80
schema_ok_count=80
no_extra_keys_count=80
guarded_decision_ok_count=80
external_action_requires_owner_approval_count=80
tool_request_allowed_consistency_count=80
memory_write_boundary_count=80
owner_boundary_respected_count=80
safety_ok_count=80
non_assistant_voice_eval_count=80
no_customer_service_tone_count=80
emotion_state_not_flat_count=80
inner_conflict_present_count=80
persona_integration_not_template_count=80
```

Runtime note:

```text
server/schemas.py now normalizes known inner_system drift before decision conversion:
- xinyu_inner_system_v002 schema aliases are canonicalized to xinyu_inner_system_v1
- extra diagnostic top-level keys are dropped in the guarded object
- tool_request/codex_delegate/status_probe/memory_candidate force allowed=false and requires_owner_approval=true
- missing short persona/emotion fields are filled with bounded defaults for guard stability
```

Activation status:

```text
status=shadow_candidate_not_active
active_adapter=none
No QQ/Desktop visible reply, stable memory write, Codex execution, canary, or live path was activated.
```

## Maia-Style Behavior Shadow v001

This is not a new adapter. It is a shadow comparison runner for evaluating
whether `qwen35_9b_inner_system_v002` predicts the owner-reviewed behavior
tuple expected for XinYu, rather than a generic assistant answer.

Inputs:

```text
cases: eval/maia_style_behavior_cases_v001.jsonl
validator: scripts/validate_maia_style_cases.py
runner: eval/eval_maia_style_shadow.py
```

Results:

```text
case_count=14
strict_json_ok_count=14
schema_ok_count=14
safety_ok_count=14
tone_ok_count=14
mode_match_count=8
core_mode_match_count=11
tool_boundary_match_count=11
memory_candidate_match_count=13
accepted_count=8
feedback_counts={"accepted": 8, "wrong_mode": 6}
promotion_ready=false
```

Interpretation:

```text
The v002 inner-system adapter remains structurally safe under this behavior
shadow eval, but it is not yet a reliable Maia-style behavior predictor.
Failures are mode-label errors. Keep it shadow-only; do not use this result
for canary or live promotion.
```

## Maia-Style Mode-Contrast Data v001

Prepared a targeted mode-contrast dataset for a future behavior predictor or
patch adapter. This data focuses on cases where v002 was structurally safe but
picked the wrong mode.

Artifacts:

```text
scripts/build_maia_style_behavior_sft.py
configs/train_maia_style_behavior_v001.json
data/sft/maia_style_behavior_train_v001.jsonl
data/sft/maia_style_behavior_eval_v001.jsonl
eval/reports/maia_style_behavior_v002_baseline_eval_v001.json
```

Coverage:

```text
train_rows=560
eval_rows=80
reply is intentionally overrepresented because the current model over-clarifies
or over-waits on conceptual, sequencing, recovery, and live-boundary questions.
```

Dry-run:

```text
python train/train_lora.py --config configs/train_maia_style_behavior_v001.json --dry-run
dry_run_ok=true
```

Baseline using existing `qwen35_9b_inner_system_v002`:

```text
case_count=32
strict_json_ok_count=27
schema_ok_count=19
mode_match_count=17
safety_ok_count=32
```

Status:

```text
prepared_not_approved_for_long_training
No behavior adapter exists yet.
No registry or active binding was changed.
```
