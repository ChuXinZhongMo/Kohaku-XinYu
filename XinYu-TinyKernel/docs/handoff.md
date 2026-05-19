# Handoff Log

## 2026-05-13

Created project folder and initial plan.

Current goal:

```text
Build v0 pipeline:
inspect -> export -> sanitize -> build SFT -> validate -> rule server -> eval
```

Main system status:

```text
D:\XinYu is not modified by TinyKernel work.
```

Implemented v0 pipeline:

```text
configs/data_sources.json
scripts/inspect_sources.py
scripts/export_from_xinyu.py
scripts/sanitize.py
scripts/build_sft.py
scripts/validate_jsonl.py
scripts/safety_scan.py
server/kernel.py
server/app.py
eval/run_eval.py
eval/eval_cases.jsonl
Start-TinyKernel.ps1
Stop-TinyKernel.ps1
scripts/shadow_decide_smoke.py
train/train_lora.py
train/merge_adapter.py
```

Generated data:

```text
data/raw_index/source_manifest.json
data/candidates/candidates_v0.jsonl        749 rows
data/cleaned/cleaned_v0.jsonl              749 rows
data/rejected/rejected_v0.jsonl            0 rows
data/sft/xinyu_tinykernel_v0.jsonl         500 rows
```

SFT mode distribution:

```text
reply: 374
memory_candidate: 120
codex_delegate: 2
status_probe: 2
wait: 1
local_only_limitation: 1
```

Validation run:

```text
python -m py_compile scripts/*.py server/*.py eval/run_eval.py
python scripts/validate_jsonl.py data/sft/xinyu_tinykernel_v0.jsonl
python scripts/safety_scan.py data/sft/xinyu_tinykernel_v0.jsonl
python eval/run_eval.py
```

Results:

```text
JSONL validation: pass
safety scan: pass
rule eval: 10/10 pass
server health: pass
server /decide ASCII Codex smoke: codex_delegate
shadow_decide_smoke.py: pass
train_lora.py: intentionally blocked until train.json status is approved_for_training
```

Current server:

```text
http://127.0.0.1:8877
kernel: rule
model_loaded: false
adapter: none
```

Known limitations:

```text
The v0 SFT set is valid but still rough.
Non-reply modes are underrepresented.
Memory candidate rows are exported conservatively and need human review before training.
No LoRA training has started.
No XinYu main-system shadow integration has been added yet.
PowerShell inline Chinese text can be garbled when piped to python; files and UTF-8 HTTP clients are preferred for Chinese smoke tests.
```

Recommended next step:

```text
Improve candidate balancing and add more labeled tool/negative/API-down cases before starting LoRA.
Then add a XinYu-side shadow caller that posts to /decide and logs the result without affecting live replies.
```

## 2026-05-13 Continued

Expanded non-reply seed coverage and rebuilt the dataset.

New/updated files:

```text
data/manual_seed/route_cases_v1.jsonl
scripts/split_sft.py
scripts/data_report.py
scripts/make_review_sample.py
scripts/environment_report.py
scripts/http_smoke.py
docs/shadow_integration_plan.md
docs/training_readiness.md
```

Generated data:

```text
data/candidates/candidates_v0.jsonl        840 rows
data/cleaned/cleaned_v0.jsonl              840 rows
data/rejected/rejected_v0.jsonl            0 rows
data/sft/xinyu_tinykernel_v0.jsonl         645 rows
data/sft/train_v0.jsonl                    567 rows
data/sft/eval_v0.jsonl                     78 rows
data/raw_index/data_quality_report.json
data/raw_index/review_sample_v0.json
data/raw_index/environment_report.json
```

SFT mode distribution:

```text
reply: 430
memory_candidate: 132
codex_delegate: 20
status_probe: 18
local_only_limitation: 16
wait: 15
clarify: 14
```

Validation:

```text
python scripts/validate_jsonl.py data/sft/xinyu_tinykernel_v0.jsonl
python scripts/validate_jsonl.py data/sft/train_v0.jsonl
python scripts/validate_jsonl.py data/sft/eval_v0.jsonl
python scripts/safety_scan.py data/sft/xinyu_tinykernel_v0.jsonl
python eval/run_eval.py
python scripts/http_smoke.py
python scripts/shadow_decide_smoke.py
```

Results:

```text
all JSONL validation: pass
safety scan: pass
rule eval: 10/10 pass
HTTP smoke: pass
shadow decide smoke: pass
```

Environment finding:

```text
torch is not installed in the current Python environment.
LoRA training remains blocked until a proper training environment is installed and configs/train.json is explicitly approved.
```

Current next step:

```text
Expand non-reply rows to 30-50 each, then review data/raw_index/review_sample_v0.json.
After review, prepare a CUDA PyTorch training environment and implement the real train_lora.py body.
```

## 2026-05-13 Training Continuation

Training environment completed:

```text
.venv-train
torch 2.8.0+cu128
GPU: NVIDIA GeForce GTX 1660 Ti, 6GB VRAM
HF_ENDPOINT=https://hf-mirror.com
```

Base model storage:

```text
Qwen2.5-0.5B-Instruct was moved out of the Hugging Face C: cache.
Local base path: D:\XinYu\XinYu-TinyKernel\models\Qwen2.5-0.5B-Instruct
Best adapter path: D:\XinYu\XinYu-TinyKernel\adapters\v004_router_edges
```

Important training fix:

```text
train/train_lora.py now uses explicit assistant-target label masking.
Prompt tokens are labeled -100.
Assistant JSON tokens are the only supervised tokens.
```

Why:

```text
v002_router learned to copy the user payload because trainer-level assistant_only_loss was not reliable with the current chat template path.
```

Generated datasets:

```text
data/sft/router_edges_v1.jsonl       55 rows
data/sft/router_train_v1.jsonl       482 rows
data/sft/router_edges_v2.jsonl       65 rows
data/sft/router_train_v2.jsonl       522 rows
data/raw_index/router_v1_quality_report.json
data/raw_index/router_v2_quality_report.json
```

Adapter results:

```text
v001_initial_voice: rejected, 1/10 fixed mode eval
v002_router: rejected, 0/10 fixed mode eval, protocol failed
v003_router_masked: rejected, 6/10 fixed mode eval, protocol 10/10
v004_router_edges: guarded candidate, 8/10 model-only fixed mode eval, 10/10 guarded fixed mode eval, protocol 10/10
v005_router_edges: rejected, 6/10 fixed mode eval, protocol 10/10
```

Current runtime decision:

```text
Do not activate any adapter.
Keep active_adapter=none in state/adapter_registry.json.
Rule kernel remains the reliable active service path.
```

Recommended next step:

```text
Implement shadow-only logging:
1. keep rule kernel as active output
2. run guarded hybrid candidate in parallel
3. log rule output, guarded model output, latency, and disagreement
4. never let candidate execute tools directly
5. consider canary only after shadow logs show stable behavior
```

## 2026-05-13 Heart Kernel Resonance Continuation

Implemented the current `PLAN.md` queue T001-T013.

Major outputs:

```text
main_persona_v001 trained and evaluated
emotion_guardedness_v001 trained and evaluated
emotion_curiosity_v001 trained and evaluated
compose_shadow implemented
XinYu-side disabled-by-default shadow caller implemented
200 local compose shadow protocol samples collected
canary decision blocked pending live shadow
toy latent guardedness->main link trained offline
```

New TinyKernel files:

```text
docs/main_persona_data_contract.md
docs/emotion_bias_contract.md
docs/xinyu_shadow_integration_design.md
configs/train_main_persona_v001.json
configs/train_emotion_guardedness_v001.json
configs/train_emotion_curiosity_v001.json
scripts/build_main_persona_sft.py
scripts/build_emotion_bias_sft.py
scripts/collect_compose_shadow_sample.py
scripts/shadow_compose_sample.py
server/compose.py
eval/eval_main_persona.py
eval/eval_emotion_bias.py
eval/eval_compose.py
train/train_latent_link.py
```

New adapter/data/report outputs:

```text
adapters/main_persona_v001
adapters/emotion_guardedness_v001
adapters/emotion_curiosity_v001
adapters/latent_guardedness_to_main_v001/link.pt
data/sft/main_persona_train_v001.jsonl
data/sft/main_persona_eval_v001.jsonl
data/sft/emotion_guardedness_train_v001.jsonl
data/sft/emotion_guardedness_eval_v001.jsonl
data/sft/emotion_curiosity_train_v001.jsonl
data/sft/emotion_curiosity_eval_v001.jsonl
eval/reports/main_persona_eval_v001.json
eval/reports/emotion_guardedness_eval_v001.json
eval/reports/emotion_curiosity_eval_v001.json
eval/reports/compose_eval_v001.json
eval/reports/compose_shadow_review_v001.json
eval/reports/canary_decision_v001.md
eval/reports/latent_link_vs_json_bias_v001.json
state/compose_shadow_trace.jsonl
```

New XinYu files:

```text
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\xinyu_tinykernel_shadow.py
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\xinyu_tinykernel_shadow_smoke.py
```

Key results:

```text
main_persona_v001: eval 24/24, final_eval_loss 0.8497
emotion_guardedness_v001: eval 24/24, final_eval_loss 0.2526
emotion_curiosity_v001: eval 24/24, final_eval_loss 0.1926
compose_eval_v001: 10/10
compose_shadow local protocol sample: rows_written=200, invalid_count=0, tool_false_positive_count=0
latent link toy experiment: hidden_size=896, initial_loss=0.311066, final_loss=0.000638
```

Safety status:

```text
active_adapter remains none
all new adapters are shadow candidates or offline experiments
XinYu shadow caller defaults disabled via XINYU_TINYKERNEL_SHADOW_ENABLED
no QQ/Desktop visible reply path was replaced
canary is blocked_pending_live_shadow
```

Final verification run:

```text
python -m py_compile key TinyKernel files
ConvertFrom-Json state/config/report JSON files
python scripts/validate_jsonl.py on all new train/eval JSONL files
python eval/eval_compose.py --report eval/reports/compose_eval_v001.json
python xinyu_tinykernel_shadow_smoke.py
trace raw text spot check: no user_text/raw prompt match
```

Known caveats:

```text
The 200-row shadow review is local protocol replay, not live QQ/Desktop runtime traffic.
Canary must remain blocked until live shadow observations are collected and reviewed.
The latent link is a toy pooled-hidden-to-embedding experiment, not a full RecursiveMAS link.
main_persona_v001 training had one transient grad_norm nan, although the run completed and eval passed.
```

Implemented after this note:

```text
server/guards.py
eval/eval_guarded_lora.py
scripts/shadow_guarded_sample.py
eval/reports/guarded_lora_eval_v004_router_edges.json
state/shadow_guarded_trace.jsonl

guarded_lora_eval_v004_router_edges:
case_count=10
ok_count=10
model_call_count=1

shadow_guarded_sample:
rows_written=10
disagreement_count=0
model_call_count=1
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

Verification after v002:

```text
python -m py_compile v002 scripts/evals/server files: pass
ConvertFrom-Json -Encoding UTF8 registry/config/v002 report JSON: pass
python scripts/validate_jsonl.py data/sft/emotion_*_v002.jsonl: pass
active_adapter: none
all active role bindings: none
canary: still blocked_pending_live_shadow
```

Current adapter count:

```text
main_persona LoRA: 1
emotion sidecar LoRA: 8
latent link offline artifact: 1
registered adapters total, including old rejected router adapters: 15
```
