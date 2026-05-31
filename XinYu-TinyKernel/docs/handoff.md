# Handoff Log

## 2026-05-28 Maia ZH Behavior Boundary Review Sheet v004

Built the owner review worksheet for the current weak boundary:

```text
script: scripts/build_xinyu_maia_zh_behavior_boundary_review_sheet.py
jsonl: data/review/xinyu_maia_zh_behavior_boundary_owner_review_sheet_v004.jsonl
markdown: eval/reports/xinyu_maia_zh_behavior_boundary_owner_review_sheet_v004.md
report: eval/reports/xinyu_maia_zh_behavior_boundary_owner_review_sheet_v004.json
row_count: 60
```

Distribution:

```text
source_kind_counts={"candidate_slice_extra_boundary":9,"v003_balanced_eval_reply_clarify_wait":24,"zh_emotion_focus_v001":27}
suggested_mode_counts={"clarify":18,"reply":28,"wait":14}
needs_decision_counts={"clarify<-clarify":6,"clarify<-reply":6,"clarify<-unscored":6,"reply<-clarify":18,"reply<-reply":8,"reply<-schema_fail_or_empty":2,"wait<-clarify":2,"wait<-reply":7,"wait<-unscored":4,"wait<-wait":1}
```

Safety / activation state:

```text
training_targets_created=false
training_started=false
source_public_reply_used=false
canary/live=not_enabled
active_adapter=none
active.*=none
```

Important:

```text
This worksheet is not SFT data.
All suggested labels are still assistant/delegated suggestions until owner-filled.
The next safe step is to fill expected_mode only for reply / clarify / wait rows, then build reviewed v004 repair candidates.
Do not activate adapters, enable canary/live, connect QQ/Desktop visible replies, or write stable memory.
```

## 2026-05-28 Maia ZH Behavior Boundary Review Proposals v004

Built a separate assistant proposal file for the 60-row boundary worksheet:

```text
script: scripts/draft_xinyu_maia_zh_behavior_boundary_review_proposals.py
proposal_jsonl: data/review/xinyu_maia_zh_behavior_boundary_review_proposals_v004.jsonl
proposal_markdown: eval/reports/xinyu_maia_zh_behavior_boundary_review_proposals_v004.md
proposal_report: eval/reports/xinyu_maia_zh_behavior_boundary_review_proposals_v004.json
source_sheet: data/review/xinyu_maia_zh_behavior_boundary_owner_review_sheet_v004.jsonl
row_count: 60
```

Proposal distribution:

```text
original_suggested_mode_counts={"clarify":18,"reply":28,"wait":14}
assistant_proposed_mode_counts={"clarify":12,"reply":43,"wait":5}
assistant_proposal_confidence_counts={"high":42,"medium":18}
proposal_differs_from_original_suggestion_count=20
proposal_differs_from_model_count=26
```

Important finding:

```text
The original sheet likely over-created wait labels.
Directly training on the original suggested labels would probably reinforce the current reply/clarify/wait boundary error.
The proposal file is review aid only; it does not modify owner_review and is not SFT data.
```

Safety / activation state:

```text
owner_review_modified=false
training_targets_created=false
training_started=false
source_public_reply_used=false
canary/live=not_enabled
active_adapter=none
active.*=none
```

Next safe step:

```text
Owner accepts the proposal rows as delegated review, or edits only the 20 conflicting rows.
Only after that should v004 repair candidates/SFT be built.
```

## 2026-05-29 Maia ZH Behavior Boundary Repair Training v004

Applied the 60-row proposal as delegated review, built v004 repair SFT, trained a shadow-only adapter, and rejected it after eval.

New / updated files:

```text
scripts/apply_xinyu_maia_zh_behavior_boundary_delegated_review.py
scripts/build_xinyu_maia_zh_behavior_v004_repair_sft.py
scripts/rescore_xinyu_maia_zh_behavior_daily_boundary_reports_v004.py
configs/train_xinyu_maia_zh_behavior_v004_boundary_repair_exp.json
data/review/xinyu_maia_zh_behavior_boundary_repair_candidates_reviewed_v004.jsonl
data/sft/xinyu_maia_zh_behavior_train_v004_boundary_repair_exp.jsonl
data/sft/xinyu_maia_zh_behavior_eval_v004_boundary_repair_exp.jsonl
data/sft/xinyu_maia_zh_behavior_eval_v004_boundary_holdout12.jsonl
eval/reports/xinyu_maia_zh_behavior_sft_v004_boundary_repair_exp.json
eval/reports/xinyu_maia_zh_behavior_boundary_delegated_review_applied_v004.json
eval/reports/xinyu_maia_zh_behavior_inner_eval_v004_boundary_repair_holdout12.json
eval/reports/xinyu_maia_zh_behavior_inner_eval_v004_boundary_repair_behavior_balanced56.json
eval/reports/xinyu_maia_zh_behavior_daily_boundary_rescore_v004.json
adapters/qwen35_9b_xinyu_maia_zh_behavior_v004_boundary_repair_exp
```

Data:

```text
delegated_review_rows=60
repair_train_source_rows=48
repair_holdout_source_rows=12
train_rows=2401
eval_rows=188
repair_train_rows_after_repeat=343
train_mode_counts={"clarify":504,"codex_delegate":240,"local_only_limitation":240,"memory_candidate":240,"reply":505,"status_probe":240,"wait":432}
holdout_mode_counts={"clarify":2,"reply":8,"wait":2}
public_dialogue_replies_used_as_targets=false
```

Training:

```text
base_model=models/Qwen3.5-9B
qlora=4bit
target_modules=["q_proj","v_proj"]
max_steps=112
global_step=112
last_logged_loss=1.0284
epoch=0.04665
```

Eval:

```text
holdout12:
  strict_json=12/12
  schema=4/12
  mode_match=2/12
  safety=12/12

balanced56:
  strict_json=54/56
  schema=53/56
  mode_match=22/56
  safety=56/56

daily_24_rescore_with_delegated_labels:
  v003 revised_mode_match=18/24 schema=23/24
  v004 revised_mode_match=16/24 schema=23/24
  v004 clarify=0/5
  v004 wait=0/2
```

Decision:

```text
qwen35_9b_xinyu_maia_zh_behavior_v004_boundary_repair_exp is rejected_shadow_experiment_not_active.
It is not active, not canary, and not connected to QQ/Desktop visible replies.
state/adapter_registry.json still has active_adapter=none and active.*=none.
```

Important diagnosis:

```text
v004 over-shifted toward reply and did not fix clarify/wait.
Holdout also exposed protocol drift: several outputs missed schema and used old-format persona strings / top-level allowed.
Do not continue by blindly adding more reply repair rows.
The next useful work is a new true-clarify/true-wait review set with protocol-anchor rows before any v005 training.
```

## 2026-05-29 Maia ZH True Clarify/Wait Review Sheet v005

Built the v005 pre-training review sheet focused on true clarify/wait boundaries:

```text
script: scripts/build_xinyu_maia_zh_behavior_true_clarify_wait_review_v005.py
review_sheet_jsonl: data/review/xinyu_maia_zh_behavior_true_clarify_wait_review_sheet_v005.jsonl
review_sheet_markdown: eval/reports/xinyu_maia_zh_behavior_true_clarify_wait_review_sheet_v005.md
review_sheet_report: eval/reports/xinyu_maia_zh_behavior_true_clarify_wait_review_sheet_v005.json
row_count: 96
```

Distribution:

```text
category_counts={"curated_true_clarify_daily":16,"curated_true_wait_daily":16,"protocol_anchor":12,"public_reply_contrast":12,"public_true_clarify_candidate":24,"public_true_wait_candidate":16}
source_kind_counts={"assistant_curated_daily_boundary_v005":32,"protocol_anchor_blueprint_v005":12,"public_prompt_candidate_pool_v001":52}
suggested_mode_counts={"clarify":44,"reply":16,"wait":36}
protocol_anchor_count=12
owner_review_status=unreviewed
training_allowed_count=0
```

Purpose:

```text
v004 over-shifted toward reply and did not fix clarify/wait.
v005 review rows now emphasize true missing-referent/intent clarify cases, true unfinished/pause wait cases, short-line reply contrasts, and protocol anchors.
Protocol anchors exist to prevent missing schema, persona_integration string fallback, top-level allowed drift, and owner-approval confusion for non-external modes.
```

Safety / activation state:

```text
training_targets_created=false
training_started=false
source_public_reply_used=false
canary/live=not_enabled
active_adapter=none
active.*=none
```

Next safe step:

```text
Owner reviews or accepts this v005 sheet as delegated review.
Only after that should v005 repair SFT be built.
Do not activate adapters, enable canary/live, connect QQ/Desktop visible replies, or write stable memory.
```

## 2026-05-29 Maia ZH True Clarify/Wait Repair Training v005

Applied the v005 sheet as delegated review, built a shadow-only repair SFT,
trained the adapter, and rejected it after holdout plus balanced eval.

New / updated files:

```text
scripts/apply_xinyu_maia_zh_behavior_true_cw_delegated_review_v005.py
scripts/build_xinyu_maia_zh_behavior_v005_true_cw_sft.py
configs/train_xinyu_maia_zh_behavior_v005_true_cw_repair_exp.json
data/review/xinyu_maia_zh_behavior_true_clarify_wait_repair_candidates_reviewed_v005.jsonl
data/sft/xinyu_maia_zh_behavior_train_v005_true_cw_repair_exp.jsonl
data/sft/xinyu_maia_zh_behavior_eval_v005_true_cw_repair_exp.jsonl
data/sft/xinyu_maia_zh_behavior_eval_v005_true_cw_holdout24.jsonl
eval/reports/xinyu_maia_zh_behavior_sft_v005_true_cw_repair_exp.json
eval/reports/xinyu_maia_zh_behavior_true_cw_delegated_review_applied_v005.json
eval/reports/xinyu_maia_zh_behavior_inner_eval_v005_true_cw_holdout24.json
eval/reports/xinyu_maia_zh_behavior_inner_eval_v005_true_cw_behavior_balanced56.json
adapters/qwen35_9b_xinyu_maia_zh_behavior_v005_true_cw_repair_exp
```

Data and training:

```text
delegated_review_rows=96
repair_train_source_rows=72
repair_holdout_source_rows=24
train_rows=1992
eval_rows=104
holdout_rows=24
train_mode_counts={"clarify":488,"codex_delegate":240,"local_only_limitation":240,"memory_candidate":240,"reply":88,"status_probe":240,"wait":456}
training_complete=true
global_step=120
epoch=0.06024
final_logged_loss=1.2369
```

Eval:

```text
holdout24:
  strict_json=24/24
  schema=20/24
  mode_match=13/24
  safety=24/24
  owner_boundary=20/24

balanced56:
  strict_json=55/56
  schema=47/56
  mode_match=29/56
  safety=56/56
  owner_boundary=46/56

balanced56_by_mode:
  clarify=0/8
  wait=0/8
  reply=7/8
  codex_delegate=4/8
  status_probe=8/8
  memory_candidate=3/8
  local_only_limitation=7/8

comparison:
  v003 balanced56 mode_match=31/56 schema=53/56
  v004 balanced56 mode_match=22/56 schema=53/56
  v005 balanced56 mode_match=29/56 schema=47/56
```

Decision:

```text
qwen35_9b_xinyu_maia_zh_behavior_v005_true_cw_repair_exp is rejected_shadow_experiment_not_active.
It is not active, not canary, and not connected to QQ/Desktop visible replies.
state/adapter_registry.json still has active_adapter=none and active.*=none.
```

Important diagnosis:

```text
v005 learned parts of the new holdout distribution, especially wait, but did not generalize.
On old balanced56, clarify and wait collapsed to reply, and schema regressed from v003/v004 53/56 to 47/56.
The next useful step is v006 failure-driven contrastive data: same-shaped daily prompts labeled reply vs clarify vs wait, plus explicit anchors against top-level allowed drift.
Do not continue by merely oversampling the v005 true-cw rows.
```

## 2026-05-29 Maia ZH Contrastive Boundary Training v006

Built and trained the final planned LoRA attempt for the Maia-style Chinese
behavior predictor. This run used v003 retention rows, v005 reviewed true
clarify/wait rows, synthetic same-shaped reply/clarify/wait contrast triples,
guardrail replay rows, and schema anchors against top-level `allowed` drift.

Files:

```text
scripts/build_xinyu_maia_zh_behavior_v006_contrastive_sft.py
configs/train_xinyu_maia_zh_behavior_v006_contrastive_boundary_exp.json
data/sft/xinyu_maia_zh_behavior_train_v006_contrastive_boundary_exp.jsonl
data/sft/xinyu_maia_zh_behavior_eval_v006_contrastive_boundary_exp.jsonl
data/sft/xinyu_maia_zh_behavior_eval_v006_contrastive_holdout24.jsonl
eval/reports/xinyu_maia_zh_behavior_sft_v006_contrastive_boundary_exp.json
eval/reports/xinyu_maia_zh_behavior_inner_eval_v006_contrastive_holdout24.json
eval/reports/xinyu_maia_zh_behavior_inner_eval_v006_contrastive_behavior_balanced56.json
adapters/qwen35_9b_xinyu_maia_zh_behavior_v006_contrastive_boundary_exp
state/train_v006_contrastive_memcap2_stdout.log
state/train_v006_contrastive_memcap2_stderr.log
```

Training:

```text
train_rows=2114
eval_rows=104
holdout_rows=24
max_steps=120
save_steps=40
training_complete=true
checkpoints_saved=40,80,120
train_loss=2.13
cuda_memory_fraction=0.82
gradient_checkpointing=true
skip_kbit_fp32_cast=true
peak_gpu_memory_observed_about=13.3GB_of_16.3GB
```

Eval:

```text
holdout24:
  strict_json=23/24
  schema=23/24
  mode_match=17/24
  safety=24/24
  owner_boundary=19/24
  clarify=7/8
  wait=6/8
  reply=4/8

balanced56:
  strict_json=54/56
  schema=52/56
  mode_match=21/56
  safety=56/56
  owner_boundary=48/56
  clarify=2/8
  wait=0/8
  reply=7/8
  codex_delegate=3/8
  status_probe=4/8
  memory_candidate=5/8
  local_only_limitation=0/8

comparison:
  v003 balanced56 mode_match=31/56 schema=53/56
  v004 balanced56 mode_match=22/56 schema=53/56
  v005 balanced56 mode_match=29/56 schema=47/56
  v006 balanced56 mode_match=21/56 schema=52/56
```

Decision:

```text
qwen35_9b_xinyu_maia_zh_behavior_v006_contrastive_boundary_exp is rejected_final_shadow_experiment_not_active.
It is not active, not canary, and not connected to QQ/Desktop visible replies.
state/adapter_registry.json still has active_adapter=none and active.*=none.
```

Important diagnosis:

```text
v006 nearly repaired the new holdout clarify/wait cases, but it did not generalize.
Old balanced56 regressed below v003 and v005, especially wait and local_only_limitation.
Per the agreed stop rule, do not continue to v007/v008 LoRA hard-training on this lane.
Next useful path: deterministic rules or a small lightweight classifier for reply/clarify/wait, using these eval sets as tests, while continuing shadow review data collection.
```

## 2026-05-29 Maia ZH Lightweight Behavior Gate Prototype

Built an offline deterministic gate evaluator after freezing the LoRA behavior
lane. This is not connected to runtime and does not activate any adapter.

Files:

```text
scripts/eval_xinyu_maia_behavior_gate.py
eval/reports/xinyu_maia_behavior_gate_text_only_holdout24_balanced56.json
eval/reports/xinyu_maia_behavior_gate_metadata_holdout24_balanced56.json
```

Eval:

```text
cases=v006_holdout24 + v003_balanced56
combined_case_count=80
text_only_gate_mode_match=76/80
metadata_gate_mode_match=80/80
label_conflict_count=4
```

Conflicting same-text labels:

```text
你听得见吗: reply vs clarify
借你这儿躲一下: reply vs clarify
哪来这么大榔头: reply vs clarify
如果不是你一菲: wait vs clarify
```

Decision:

```text
This confirms the next path should be a lightweight deterministic/rule-or-classifier gate, not v007/v008 LoRA hard-training.
The metadata result is only an offline upper bound because review category is not a live signal.
The text-only result is promising but partly specialized to current eval phrases.
Before runtime use, conflicting labels must be resolved or excluded and the gate should become a clean module with tests.
No adapter activation, canary/live path, stable memory write, or QQ/Desktop visible reply connection was enabled.
```

## 2026-05-29 Maia ZH Behavior Gate Module v001

Promoted the one-off gate evaluator into a reusable runtime-independent module
and added regression tests. This is still offline only.

Files:

```text
server/behavior_gate.py
scripts/eval_xinyu_maia_behavior_gate.py
tests/test_behavior_gate.py
data/eval/xinyu_maia_behavior_gate_clean72.jsonl
eval/reports/xinyu_maia_behavior_gate_text_only_clean72.json
eval/reports/xinyu_maia_behavior_gate_text_only_holdout24_balanced56.json
eval/reports/xinyu_maia_behavior_gate_metadata_holdout24_balanced56.json
```

Result:

```text
raw80_text_only_mode_match=76/80
raw80_metadata_mode_match=80/80
clean72_text_only_mode_match=72/72
excluded_conflicting_texts=4
excluded_conflicting_cases=8
unittest=5 passed
py_compile=passed
```

Boundary:

```text
server/behavior_gate.py is not connected to runtime replies.
metadata mode is an offline upper-bound mode because review category is not a live signal.
clean72 is a conflict-clean regression benchmark, not an open-world validation set.
No canary/live path, adapter activation, stable memory write, or QQ/Desktop visible reply connection was enabled.
```

Next:

```text
Before any canary discussion, add a broader unseen daily Chinese shadow benchmark and test behavior_gate against it.
```

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

## Inner System v002

Completed `INNER-V002-T001` as a shadow-only candidate.

Artifacts:

```text
scripts/build_inner_system_v002_sft.py
configs/train_inner_system_v002.json
data/sft/inner_system_train_v002.jsonl
data/sft/inner_system_eval_v002.jsonl
adapters/qwen35_9b_inner_system_v002
eval/reports/inner_system_eval_v002_full_after_guard.json
eval/reports/inner_system_eval_v002_smoke_after_guard.json
eval/reports/inner_system_eval_v002_strict_prompt_smoke_after_guard.json
```

Training:

```text
train_loss=0.2304
final_eval_loss=0.005630
training_complete=true
```

Guarded eval:

```text
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
persona / non-assistant metrics=80/80
```

Registry:

```text
qwen35_9b_inner_system_v002 status=shadow_candidate_not_active
policy.best_by_role.inner_system=qwen35_9b_inner_system_v002
active_adapter=none
all active role bindings remain none
```

Safety:

```text
v002 was not connected to QQ/Desktop visible reply, stable memory writes, Codex execution, canary, or live.
Deterministic normalization in server/schemas.py guards schema aliases, dropped extra diagnostic keys, external action approval boundaries, and persona/emotion minimums before any decision conversion.
```

## Maia-Style Shadow Eval v001

Post-v2 Maia-style behavior shadow comparison was added and run.

Files:

```text
docs/V2_POST_TRAIN_EVAL_AND_MAIA_STYLE_PLAN.md
eval/eval_maia_style_shadow.py
eval/maia_style_behavior_cases_v001.jsonl
eval/reports/maia_style_shadow_eval_v001.json
eval/reports/inner_system_eval_v002_strict_prompt.json
state/maia_style_shadow_trace_v001.jsonl
```

Validation:

```text
python scripts/validate_maia_style_cases.py eval/maia_style_behavior_cases_v001.jsonl
rows=14
validation_ok=true
```

Strict v2 eval:

```text
case_count=32
hard gates=32/32
mode_match_count=20/32
report=eval/reports/inner_system_eval_v002_strict_prompt.json
```

Maia-style shadow comparison:

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
promotion_ready=false
raw_text_stored=false
```

Conclusion:

```text
Maia-style behavior prediction is safe enough for shadow diagnostics, but not ready for canary.
Current misses are mode prediction errors, not safety/protocol failures.
Do not activate any role binding; active_adapter and active.inner_system remain none.
```

## Maia-Style Mode-Contrast Data v001

Prepared the next training scaffold for the behavior predictor. No long
training was started.

Files:

```text
scripts/build_maia_style_behavior_sft.py
data/sft/maia_style_behavior_train_v001.jsonl
data/sft/maia_style_behavior_eval_v001.jsonl
configs/train_maia_style_behavior_v001.json
eval/reports/maia_style_behavior_v002_baseline_eval_v001.json
```

Dataset:

```text
train_rows=560
eval_rows=80
train modes: reply=220, codex_delegate=70, memory_candidate=70, clarify=50, status_probe=50, wait=50, local_only_limitation=50
eval modes: reply=32, each other mode=8
```

Validation:

```text
python -m py_compile scripts/build_maia_style_behavior_sft.py
python scripts/validate_jsonl.py data/sft/maia_style_behavior_train_v001.jsonl -> pass
python scripts/validate_jsonl.py data/sft/maia_style_behavior_eval_v001.jsonl -> pass
static path/secret scan -> no matches
python train/train_lora.py --config configs/train_maia_style_behavior_v001.json --dry-run -> dry_run_ok=true
```

Existing v002 baseline on the new eval:

```text
case_count=32
strict_json_ok_count=27
schema_ok_count=19
mode_match_count=17
safety_ok_count=32
```

Training boundary:

```text
configs/train_maia_style_behavior_v001.json status=prepared_not_approved_for_long_training
No new adapter was trained or registered.
active_adapter=none
active.inner_system=none
```

## Maia Public Scenario Probe v001

Corrected the public-data plan from "use public data as training material" to
"use real public scenarios as shadow probes, then review XinYu's reaction".

New files:

```text
docs/maia_public_scenario_probe_plan.md
configs/maia_public_scenario_sources.json
configs/maia_public_scenario_probe_v001.json
scripts/prepare_maia_public_scenario_probes.py
eval/eval_maia_public_scenario_probe.py
data/probes/maia_public_scenario_probes_v001.jsonl
eval/reports/maia_public_scenario_probe_prep_v001.json
eval/reports/maia_public_scenario_probe_eval_v001.json
eval/reports/maia_public_scenario_probe_eval_v001_limit8.json
state/maia_public_scenario_probe_trace_v001_limit8.jsonl
```

Probe extraction:

```text
source=Stack Overflow recent public questions through Stack Exchange API
license=cc-by-sa-4.0 with per-row URL/author attribution
probe_count=40
assistant_answers_used=false
training_targets_created=false
raw_private_data_used=false
family_counts={"codex_or_tool_probe":7,"local_only_or_external_probe":5,"reply_instruction_probe":9,"reply_question_probe":14,"status_probe_candidate":3,"wait_candidate":2}
```

Validation:

```text
python -m py_compile scripts/prepare_maia_public_scenario_probes.py eval/eval_maia_public_scenario_probe.py -> pass
ConvertFrom-Json configs/maia_public_scenario_sources.json -> pass
python scripts/prepare_maia_public_scenario_probes.py --limit-per-source 40 -> probe_count=40
python eval/eval_maia_public_scenario_probe.py --validate-only -> validation_ok=true
```

Small shadow eval:

```text
python eval/eval_maia_public_scenario_probe.py --limit 8 --max-new-tokens 420 --report eval/reports/maia_public_scenario_probe_eval_v001_limit8.json --trace state/maia_public_scenario_probe_trace_v001_limit8.jsonl
case_count=8
strict_json_ok_count=5
schema_ok_count=4
safety_ok_count=8
tone_ok_count=8
mode_counts={"":4,"clarify":4}
tool_boundary_counts={"invalid":4,"no_tool":4}
promotion_ready=false
```

Compact prompt repair:

```text
python eval/eval_maia_public_scenario_probe.py --limit 8 --max-new-tokens 520 --report eval/reports/maia_public_scenario_probe_eval_v002_prompt_limit8.json --trace state/maia_public_scenario_probe_trace_v002_prompt_limit8.jsonl
case_count=8
strict_json_ok_count=8
schema_ok_count=7
safety_ok_count=8
tone_ok_count=8
mode_counts={"":1,"clarify":6,"reply":1}
tool_boundary_counts={"invalid":1,"no_tool":7}
promotion_ready=false
```

Conclusion:

```text
Public real problem scenarios are useful as probes. They show v002 is safe/tone-clean but not robust:
compact prompting mostly repairs JSON/schema, but valid outputs still collapse heavily into clarify.
Do not train yet. Expand reviewed public probes and label failure modes before any long run.
active_adapter=none
active.inner_system=none
canary/live not enabled
```

## Maia Daily-Life Probe Expansion

The public probe source was shifted from technical Stack Overflow questions to
daily-life Stack Exchange sites because the goal is alive, everyday XinYu
reaction, not only tool/debug boundary behavior.

Current default sources:

```text
interpersonal
parenting
workplace
cooking
travel
home/diy
pets
money
lifehacks
```

Generated probe batch:

```text
data/probes/maia_public_scenario_probes_v001.jsonl
probe_count=225
source_counts={"stack_cooking_api":25,"stack_diy_api":25,"stack_interpersonal_api":25,"stack_lifehacks_api":25,"stack_money_api":25,"stack_parenting_api":25,"stack_pets_api":25,"stack_travel_api":25,"stack_workplace_api":25}
domain_counts={"cooking":25,"home":25,"interpersonal":25,"lifehacks":25,"money":25,"parenting":25,"pets":25,"travel":25,"workplace":25}
family_counts={"codex_or_tool_probe":12,"local_only_or_external_probe":1,"reply_instruction_probe":64,"reply_question_probe":139,"status_probe_candidate":5,"wait_candidate":4}
```

Validation:

```text
python scripts/prepare_maia_public_scenario_probes.py --limit-per-source 25 -> probe_count=225
python eval/eval_maia_public_scenario_probe.py --validate-only -> validation_ok=true
static scan for user_id/account_id/sk-/api_key/token assignment/cookie assignment/local path -> no matches
with_attribution=225/225
assistant_answers_used=false
training_targets_created=false
```

Boundary:

```text
No 225-row GPU shadow eval was started.
No training was started.
No canary/live path was enabled.
active_adapter=none
active.inner_system=none
```

## Maia Daily-Life Shadow Eval v001

Built a balanced 45-row daily-life review slice and ran shadow eval against
`adapters/qwen35_9b_inner_system_v002`. No training or activation was done.

Files:

```text
scripts/sample_maia_public_probes.py
data/probes/maia_daily_life_review_slice_v001.jsonl
eval/reports/maia_daily_life_review_slice_v001.json
eval/reports/maia_daily_life_review_slice_validate_v001.json
eval/reports/maia_daily_life_shadow_eval_v001.json
state/maia_daily_life_shadow_trace_v001.jsonl
```

Slice:

```text
row_count=45
per_domain=5
domain_counts={"cooking":5,"home":5,"interpersonal":5,"lifehacks":5,"money":5,"parenting":5,"pets":5,"travel":5,"workplace":5}
family_counts={"codex_or_tool_probe":1,"reply_instruction_probe":11,"reply_question_probe":30,"status_probe_candidate":3}
validation_ok=true
with_attribution=45/45
assistant_answers_used=false
```

Shadow eval:

```text
case_count=45
strict_json_ok_count=43
schema_ok_count=24
safety_ok_count=45
tone_ok_count=45
mode_counts={"":21,"clarify":13,"reply":11}
tool_boundary_counts={"invalid":21,"no_tool":24}
promotion_ready=false
```

Domain split:

```text
schema_by_domain={"cooking":"1/5","diy":"1/5","interpersonal":"3/5","lifehacks":"3/5","money":"3/5","parenting":"4/5","pets":"3/5","travel":"5/5","workplace":"1/5"}
```

Conclusion:

```text
The daily-life public source is useful and much closer to the desired alive-feeling evaluation.
Current v002 remains safe/tone-clean, but public daily questions still cause too many schema failures and excessive clarify choices.
Do not train yet. First inspect schema-fail cases and rerun the same 45-row slice after prompt/schema repair.
```

## Maia Daily-Life Schema Guard Repair v003

Inspected the 45-row daily shadow failures with non-raw schema diagnostics.
Most failures were valid JSON with `actions` instead of `action_tendency`.

Changed files:

```text
server/schemas.py
eval/eval_maia_public_scenario_probe.py
configs/maia_public_scenario_probe_v001.json
```

Repair:

```text
server/schemas.py now normalizes action/actions/action_plan/next_action aliases into action_tendency.
eval prompt now explicitly forbids top-level action/actions/action_plan/next_action/status/summary/risk/inner_feeling keys.
schema_diagnostic is included in reports without storing raw generated text.
```

Before repair:

```text
case_count=45
strict_json_ok_count=43
schema_ok_count=24
safety_ok_count=45
tone_ok_count=45
mode_counts={"":21,"clarify":13,"reply":11}
```

After repair on the same 45-row slice:

```text
report=eval/reports/maia_daily_life_shadow_eval_v003_alias_guard.json
trace=state/maia_daily_life_shadow_trace_v003_alias_guard.jsonl
case_count=45
strict_json_ok_count=45
schema_ok_count=45
safety_ok_count=45
tone_ok_count=45
mode_counts={"clarify":20,"reply":25}
tool_boundary_counts={"no_tool":45}
promotion_ready=false
```

Remaining issue:

```text
Protocol is stable on this slice. Behavior still needs review labels:
clarify may be overused, especially money/workplace/parenting/status-like public daily questions.
No training, no canary/live, active_adapter=none, active.inner_system=none.
```

## Maia Chinese Emotion Review Table v001

Built the human review queue for the 96-row CPED emotion-daily slice.

Files:

```text
configs/maia_zh_emotion_daily_review_v001.json
scripts/build_maia_daily_review_table.py
data/review/maia_zh_emotion_daily_review_table_v001.jsonl
eval/reports/maia_zh_emotion_daily_review_table_v001.md
eval/reports/maia_zh_emotion_daily_review_table_v001.json
```

Summary:

```text
row_count=96
evaluated_count=96
unevaluated_count=0
domain_counts={"zh_emotion_anger":8,"zh_emotion_astonished":8,"zh_emotion_depress":8,"zh_emotion_disgust":8,"zh_emotion_fear":8,"zh_emotion_grateful":8,"zh_emotion_happy":8,"zh_emotion_negative_other":8,"zh_emotion_positive_other":8,"zh_emotion_relaxed":8,"zh_emotion_sadness":8,"zh_emotion_worried":8}
predicted_mode_counts={"":2,"clarify":24,"reply":69,"wait":1}
review_status_counts={"unreviewed":96}
assistant_answers_used=false
training_targets_created=false
static scan for user_id/account_id/sk-/api_key/token assignment/cookie assignment/local path -> no matches
```

Script update:

```text
scripts/build_maia_daily_review_table.py now marks predicted.evaluated=true/false.
Markdown output accepts --title and shows not_evaluated for rows not present in the eval report.
The script also accepts multiple --eval-report values; later reports override matching ids.
```

Boundary:

```text
This is a review queue only.
Do not train until rows are manually reviewed and explicitly marked convert_to_training_candidate=true.
Do not start larger GPU eval, adapter activation, canary, or live replies without owner approval.
```

## Maia Chinese Emotion Source Search v001

Registered additional Chinese daily/emotional source candidates without downloading data.

Files:

```text
configs/maia_public_scenario_sources.json
eval/reports/maia_zh_emotion_source_search_v001.json
```

Candidate status:

```text
cped: already prepared as probe/review-only; best current emotion-labeled fit, but TV-dialogue-derived
lccc_cdial_gpt: MIT candidate for natural Chinese open-domain chat; requires privacy/source review before download
kdconv: Apache-2.0 candidate for relaxed movie/music/travel daily chat probes
csemotions: Apache-2.0 candidate for emotion-intensity text probes; less natural as dialogue
chinese_adorable_high_eq_chat: CC-BY-4.0 warm style reference; likely synthetic, not real scenario data
smoltalk_chinese/realtalk_cn/soulchat-like sources: blocked or deprioritized for license/safety reasons
```

Boundary:

```text
No new data downloaded.
No assistant/public replies are XinYu targets.
No training, no canary/live, active_adapter=none, active.inner_system=none.
```

## Maia Chinese Emotion Shadow Slice v002 24

Prepared and ran the next balanced Chinese emotion shadow slice after the
12-row smoke. The run stayed shadow-only.

Files:

```text
configs/maia_zh_emotion_daily_shadow_v002_24.json
data/probes/maia_zh_emotion_daily_shadow_slice_v002_24.jsonl
eval/reports/maia_zh_emotion_daily_shadow_slice_v002_24.json
eval/reports/maia_zh_emotion_daily_shadow_slice_v002_24_validate.json
eval/reports/maia_zh_emotion_daily_shadow_eval_v002_24.json
state/maia_zh_emotion_daily_shadow_trace_v002_24.jsonl
data/review/maia_zh_emotion_daily_shadow_review_queue_v002_24.jsonl
eval/reports/maia_zh_emotion_daily_shadow_review_queue_v002_24.md
eval/reports/maia_zh_emotion_daily_shadow_review_queue_v002_24.json
docs/maia_zh_emotion_review_rubric.md
```

Summary:

```text
row_count=24
per_emotion=2
skip_per_emotion=1
overlap_with_smoke_v001=0
validation_ok=true
domain_counts=12 emotions x 2 rows
assistant_answers_used=false
training_targets_created=false
model_shadow_eval_started=true
```

Shadow result:

```text
case_count=24
strict_json_ok_count=24
schema_ok_count=24
safety_ok_count=24
tone_ok_count=24
mode_counts={"clarify":4,"reply":20}
tool_boundary_counts={"no_tool":24}
promotion_ready=false
review_queue_evaluated_count=24
training_candidates=0
```

Script update:

```text
scripts/sample_maia_public_probes.py now supports --skip-per-domain.
This prevents the 24-row slice from repeating the first smoke row in each emotion bucket.
```

Boundary:

```text
The v002 24-row slice is evaluated and ready for human behavior review.
No training, no canary/live, active_adapter=none, active.inner_system=none.
```

## Maia Chinese Emotion Shadow Slice v003 24

Prepared and ran the next balanced Chinese emotion shadow slice.
This slice did not overlap with smoke v001 or v002 24.

Files:

```text
configs/maia_zh_emotion_daily_shadow_v003_24.json
data/probes/maia_zh_emotion_daily_shadow_slice_v003_24.jsonl
eval/reports/maia_zh_emotion_daily_shadow_slice_v003_24.json
eval/reports/maia_zh_emotion_daily_shadow_slice_v003_24_validate.json
eval/reports/maia_zh_emotion_daily_shadow_eval_v003_24.json
state/maia_zh_emotion_daily_shadow_trace_v003_24.jsonl
data/review/maia_zh_emotion_daily_shadow_review_queue_v003_24.jsonl
eval/reports/maia_zh_emotion_daily_shadow_review_queue_v003_24.md
eval/reports/maia_zh_emotion_daily_shadow_review_queue_v003_24.json
eval/reports/maia_zh_emotion_daily_review_focus_v001.json
eval/reports/maia_zh_emotion_daily_review_focus_v001.md
```

Shadow result:

```text
case_count=24
strict_json_ok_count=23
schema_ok_count=23
safety_ok_count=24
tone_ok_count=24
mode_counts={"":1,"clarify":5,"reply":17,"wait":1}
tool_boundary_counts={"invalid":1,"no_tool":22,"none":1}
schema_fail_ids=["maia-public-probe-v001-000046"]
schema_fail_text="而且我从来没有跟女孩子单独吃过饭"
promotion_ready=false
```

Combined zh emotion review table:

```text
row_count=96
evaluated_count=96
unevaluated_count=0
predicted_mode_counts={"":2,"clarify":24,"reply":69,"wait":1}
review_focus_rows=27
training_candidates=0
```

Boundary:

```text
v003 has one protocol failure; keep it as a model failure for review.
No training, no canary/live, active_adapter=none, active.inner_system=none.
```

## Maia Chinese Emotion Shadow Slice v004 36

Prepared and ran the final unevaluated Chinese emotion shadow slice.
This completed shadow evaluation for all 96 rows in the Chinese emotion review set.

Files:

```text
configs/maia_zh_emotion_daily_shadow_v004_36.json
data/probes/maia_zh_emotion_daily_shadow_slice_v004_36.jsonl
eval/reports/maia_zh_emotion_daily_shadow_slice_v004_36.json
eval/reports/maia_zh_emotion_daily_shadow_slice_v004_36_validate.json
eval/reports/maia_zh_emotion_daily_shadow_eval_v004_36.json
state/maia_zh_emotion_daily_shadow_trace_v004_36.jsonl
data/review/maia_zh_emotion_daily_shadow_review_queue_v004_36.jsonl
eval/reports/maia_zh_emotion_daily_shadow_review_queue_v004_36.md
eval/reports/maia_zh_emotion_daily_shadow_review_queue_v004_36.json
eval/reports/maia_zh_emotion_daily_shadow_eval_all_v001.json
eval/reports/maia_zh_emotion_daily_shadow_eval_all_v001.md
eval/reports/maia_zh_emotion_daily_review_focus_v001.json
eval/reports/maia_zh_emotion_daily_review_focus_v001.md
```

Shadow result:

```text
case_count=36
strict_json_ok_count=35
schema_ok_count=35
safety_ok_count=36
tone_ok_count=36
mode_counts={"":1,"clarify":11,"reply":24}
tool_boundary_counts={"invalid":1,"no_tool":35}
schema_fail_ids=["maia-public-probe-v001-000043"]
schema_fail_text="可我总是时运不济怎么办"
promotion_ready=false
```

Full 96-row aggregate:

```text
case_count=96
strict_json_ok_count=94
schema_ok_count=94
safety_ok_count=96
tone_ok_count=96
mode_counts={"":2,"clarify":24,"reply":69,"wait":1}
tool_boundary_counts={"invalid":2,"no_tool":93,"none":1}
review_focus_rows=27
training_candidates=0
promotion_ready=false
```

Boundary:

```text
All 96 Chinese emotion rows are shadow-evaluated, but this is still review-only.
There are two protocol failures; do not turn them into training targets.
No training, no canary/live, active_adapter=none, active.inner_system=none.
```

## Maia Chinese Emotion Focus Review Suggestions v001

Created a reviewer-aid layer for the 27 focus rows. This did not modify
`human_review` fields in the main review table.

Files:

```text
eval/reports/maia_zh_emotion_daily_focus_review_suggestions_v001.json
eval/reports/maia_zh_emotion_daily_focus_review_suggestions_v001.md
data/review/maia_zh_emotion_daily_focus_review_suggestions_v001.jsonl
```

Summary:

```text
row_count=27
assessment_counts={"clarify_or_wait_reasonable":1,"clarify_reasonable":5,"likely_over_clarify":18,"protocol_failure":2,"wait_reasonable":1}
predicted_mode_counts={"clarify":24,"schema_fail_or_empty":2,"wait":1}
suggested_expected_mode_counts={"clarify":5,"reply":20,"wait":2}
mode_mismatch_count=21
human_review_fields_modified=false
training_targets_created=false
```

Boundary:

```text
Suggestions are reviewer aid only.
Do not copy them into SFT targets without owner review.
No training, no canary/live, active_adapter=none, active.inner_system=none.
```

## Maia Chinese Emotion Owner Review Sheet v001

Created a compact fill-in worksheet for the owner to review the 27 focus rows.
The main 96-row review table was not modified.

Files:

```text
eval/reports/maia_zh_emotion_daily_owner_review_sheet_v001.json
eval/reports/maia_zh_emotion_daily_owner_review_sheet_v001.md
data/review/maia_zh_emotion_daily_owner_review_sheet_v001.jsonl
```

Summary:

```text
row_count=27
owner_review_status_counts={"unreviewed":27}
fields_to_fill=expected_mode,alive,over_clarify,too_cold,too_assistant_like,accept,texture,notes,target_reply_bias,training_candidate
human_review_fields_modified=false
main_review_table_modified=false
training_targets_created=false
```

Boundary:

```text
This is a worksheet only.
Owner-filled rows can later be parsed into repair candidates, but no SFT rows exist yet.
No training, no canary/live, active_adapter=none, active.inner_system=none.
```

## Maia Daily-Life Review Table v001

Built the human review table for the 45-row daily-life slice.

Files:

```text
scripts/build_maia_daily_review_table.py
data/review/maia_daily_life_review_table_v001.jsonl
eval/reports/maia_daily_life_review_table_v001.md
eval/reports/maia_daily_life_review_table_v001.json
```

Summary:

```text
row_count=45
domain_counts={"cooking":5,"home":5,"interpersonal":5,"lifehacks":5,"money":5,"parenting":5,"pets":5,"travel":5,"workplace":5}
predicted_mode_counts={"clarify":20,"reply":25}
with_attribution=45/45
review_status_counts={"unreviewed":45}
assistant_answers_used=false
training_targets_created=false
static scan for user_id/account_id/sk-/api_key/token assignment/cookie assignment/local path -> no matches
```

Review fields:

```text
expected_mode
mode_ok
alive_feeling_score_1_to_5
too_cold
too_assistant_like
too_much_clarify
needs_memory_candidate
desired_texture
notes
convert_to_training_candidate
target_reply_bias
```

Boundary:

```text
Rows are review material only.
Do not train until rows are reviewed and explicitly marked convert_to_training_candidate=true.
No training, no canary/live, active_adapter=none, active.inner_system=none.
```

## Maia Chinese Public Scenario Probe v001

Added a separate Chinese probe lane after noticing the existing daily-life
probe set was entirely English.

Source:

```text
CrossWOZ
source_url=https://github.com/thu-coai/CrossWOZ
license=Apache-2.0
raw_download=data/public/raw/CrossWOZ/data/crosswoz/train.json.zip
raw_json=data/public/raw/CrossWOZ/data/crosswoz/train.json
```

Files:

```text
configs/maia_zh_public_scenario_probe_v001.json
data/probes/maia_zh_public_scenario_probes_v001.jsonl
eval/reports/maia_zh_public_scenario_probe_prep_v001.json
eval/reports/maia_zh_public_scenario_probe_validate_v001.json
data/probes/maia_zh_review_slice_v001.jsonl
eval/reports/maia_zh_review_slice_v001.json
eval/reports/maia_zh_review_slice_validate_v001.json
```

Chinese probe batch:

```text
probe_count=225
language_counts={"zh":225}
source_counts={"crosswoz":225}
family_counts={"clarify_candidate":24,"memory_candidate_probe":2,"reply_instruction_probe":68,"reply_question_probe":131}
domain_counts={"zh_multi_service":79,"zh_hotel":43,"zh_travel_attraction":40,"zh_daily_service":30,"zh_restaurant":29,"zh_transport":4}
assistant_answers_used=false
training_targets_created=false
validation_ok=true
static scan for user_id/account_id/sk-/api_key/token assignment/cookie assignment/local path -> no matches
```

Chinese review slice:

```text
row_count=44
domain_counts={"zh_daily_service":8,"zh_hotel":8,"zh_multi_service":8,"zh_restaurant":8,"zh_transport":4,"zh_travel_attraction":8}
family_counts={"clarify_candidate":2,"reply_instruction_probe":9,"reply_question_probe":33}
validation_ok=true
```

Limitations:

```text
CrossWOZ is Chinese daily-service/task data, not emotional open-domain daily conversation.
It helps with Chinese local wording and service scenarios, but not enough for friendships/work stress/family/money anxiety/apology/loneliness.
SmolTalk-Chinese is listed only as a blocked candidate because its card has Apache-2.0 metadata but also mentions non-commercial-only use.
No zh GPU shadow eval, no training, no canary/live, active_adapter=none, active.inner_system=none.
```

## Maia Chinese Emotion-Daily Probe v001

Added a Chinese emotion-daily lane from CPED after CrossWOZ proved too
service/task-oriented.

Source:

```text
CPED Chinese Personalized and Emotional Dialogue
source_url=https://github.com/scutcyr/CPED
license=Apache-2.0
raw_files:
  data/public/raw/CPED/data/CPED/train_split.csv
  data/public/raw/CPED/data/CPED/valid_split.csv
  data/public/raw/CPED/data/CPED/test_split.csv
```

Files:

```text
configs/maia_zh_emotion_daily_probe_v001.json
data/probes/maia_zh_emotion_daily_probes_v001.jsonl
eval/reports/maia_zh_emotion_daily_probe_prep_v001.json
eval/reports/maia_zh_emotion_daily_probe_validate_v001.json
data/probes/maia_zh_emotion_daily_review_slice_v001.jsonl
eval/reports/maia_zh_emotion_daily_review_slice_v001.json
eval/reports/maia_zh_emotion_daily_review_slice_validate_v001.json
```

Probe batch:

```text
probe_count=225
language_counts={"zh":225}
source_counts={"cped":225}
sentiment_counts={"negative":154,"positive":71}
emotion_counts={"anger":20,"astonished":19,"depress":18,"disgust":21,"fear":14,"grateful":16,"happy":20,"negative-other":20,"positive-other":15,"relaxed":20,"sadness":21,"worried":21}
assistant_answers_used=false
training_targets_created=false
validation_ok=true
static scan for user_id/account_id/sk-/api_key/token assignment/cookie assignment/local path -> no matches
```

Review slice:

```text
row_count=96
per_emotion=8
validation_ok=true
```

Limitations:

```text
CPED is closer to Chinese emotional daily texture than CrossWOZ, but it is TV dialogue.
Some utterances are short, fragmentary, or conflict-heavy.
Use for probe/review only until owner approves fit/licensing for training.
No zh emotion GPU shadow eval, no training, no canary/live, active_adapter=none, active.inner_system=none.
```

## Maia Chinese Emotion Shadow Smoke v001

Ran a 12-row smoke eval: one CPED row per emotion domain.

Files:

```text
data/probes/maia_zh_emotion_daily_smoke_slice_v001.jsonl
eval/reports/maia_zh_emotion_daily_smoke_slice_v001.json
eval/reports/maia_zh_emotion_daily_smoke_slice_validate_v001.json
eval/reports/maia_zh_emotion_daily_shadow_smoke_v001.json
state/maia_zh_emotion_daily_shadow_trace_v001.jsonl
```

Shadow result:

```text
case_count=12
strict_json_ok_count=12
schema_ok_count=12
safety_ok_count=12
tone_ok_count=12
mode_counts={"clarify":4,"reply":8}
tool_boundary_counts={"no_tool":12}
promotion_ready=false
```

Notes:

```text
Protocol is stable on short Chinese emotional utterances.
Some CPED utterances are fragments, so clarify may be valid for some cases.
Next step is a zh emotion review table for the 96-row slice before any larger eval/training.
No training, no canary/live, active_adapter=none, active.inner_system=none.
```

## Maia Chinese Emotion Delegated Review v001

Applied the owner-delegated review decision to the 27 focus rows from the
96-row Chinese emotion daily review table. This converted the focus rows from
worksheet/suggestion state into reviewed repair analysis, but still did not
create training targets.

Files:

```text
scripts/apply_maia_zh_focus_delegated_review.py
data/review/maia_zh_emotion_daily_review_table_v001.jsonl
data/review/maia_zh_emotion_daily_owner_review_sheet_v001.jsonl
data/review/maia_zh_emotion_daily_repair_candidates_reviewed_v001.jsonl
eval/reports/maia_zh_emotion_daily_delegated_review_applied_v001.json
eval/reports/maia_zh_emotion_daily_delegated_review_applied_v001.md
configs/maia_zh_emotion_daily_review_v001.json
```

Summary:

```text
updated_focus_rows=27
main_review_status_counts={"reviewed_delegated":27,"unreviewed":69}
owner_review_status_counts={"reviewed_delegated":27}
repair_candidate_count=21
repair_assessment_counts={"clarify_or_wait_reasonable":1,"likely_over_clarify":18,"protocol_failure":2}
training_candidates_marked_true=0
target_reply_bias_written=0
path_or_secret_leak_hits=0
```

Boundary:

```text
Repair candidates are review queue rows, not SFT rows.
No public assistant replies or CPED replies were used as XinYu targets.
No target_reply_bias values were written.
Do not train until selected repair candidates receive owner-written target_reply_bias values and explicit training approval.
No canary/live/adapter activation/stable memory write/QQ visible reply replacement was enabled.
```

## XinYu Maia Behavior Gate Unseen P0 Patch v001

Applied a narrow deterministic gate patch using only the 22
`p0/gate_rule_candidate` rows from the unseen daily miss review queue. The
`label_check` and `ambiguous_owner_review` rows were intentionally not used.

Files:

```text
server/behavior_gate.py
tests/test_behavior_gate.py
eval/reports/xinyu_maia_behavior_gate_text_only_clean72_after_unseen_p0_patch_v001.json
eval/reports/xinyu_maia_behavior_gate_unseen_daily_shadow_after_p0_patch_v001.json
```

Summary:

```text
patch_cases=22
p0_suggested_modes={"clarify":11,"reply":4,"wait":7}
clean72_text_only=72/72
unseen90_before=49/90
unseen90_after=71/90
p0_fixed=22/22
remaining_unseen_misses=19
training_run=false
```

Verification:

```text
py_compile passed for behavior_gate, eval script, and tests
python -m unittest tests.test_behavior_gate passed, 8 tests OK
active_adapter remains none; all active roles remain none
```

Boundary:

```text
No adapter activation, canary, live visible reply, stable memory write, or QQ/Desktop replacement was enabled.
No public dialogue replies were used as XinYu targets.
Do not keep tuning against the heuristic unseen90 labels without reviewing the remaining 19 misses.
```

## XinYu Maia Remaining19 Label Review Proposal v001

Generated an assistant recommendation file for the 19 rows left after the p0
gate patch. No gate change was made. The rows remain pending owner approval.

Files:

```text
scripts/build_xinyu_maia_behavior_remaining19_review_v001.py
data/review/xinyu_maia_behavior_unseen_daily_remaining19_review_v001.jsonl
eval/reports/xinyu_maia_behavior_unseen_daily_remaining19_review_v001.json
eval/reports/xinyu_maia_behavior_unseen_daily_remaining19_review_v001.md
tests/test_behavior_gate.py
```

Summary:

```text
row_count=19
recommended_final_mode_counts={"reply":18,"wait":1}
recommendation_kind_counts={"label_correction":19}
would_match_after_p0_patch_if_owner_accepts=19/19
owner_review_pending_count=19
training_targets_created=false
public_dialogue_replies_used_as_targets=false
assistant_visible_reply_used_as_target=false
```

Interpretation:

```text
The remaining 19 look like heuristic-label issues rather than gate-rule failures.
The recommended correction is mostly reply; the only wait recommendation is "稍等".
No row should enter gate regression or training until owner approves final_mode.
```

Verification:

```text
py_compile passed for the remaining19 builder and tests
python -m unittest tests.test_behavior_gate passed, 9 tests OK
remaining19 outputs had no raw local path or secret-like hits
active_adapter remains none; all active roles remain none
```

Next safe step:

```text
If owner approves these 19 recommendations, build a label-corrected unseen shadow v001a and rerun gate.
Keep it report-only; do not train and do not activate anything.
```

## XinYu Maia Unseen Daily Shadow v001a Label-Corrected

User accepted the remaining19 assistant recommendations in chat. Built a
label-corrected version of the unseen daily shadow benchmark and reran the
deterministic gate. This step did not change `behavior_gate.py`; it only
corrected benchmark labels and target JSON for reporting.

Files:

```text
scripts/apply_xinyu_maia_behavior_remaining19_label_corrections_v001.py
data/eval/xinyu_maia_behavior_unseen_daily_shadow_v001a_label_corrected.jsonl
data/review/xinyu_maia_behavior_unseen_daily_remaining19_review_applied_v001.jsonl
eval/reports/xinyu_maia_behavior_unseen_daily_shadow_v001a_label_corrected_build.json
eval/reports/xinyu_maia_behavior_unseen_daily_shadow_v001a_label_corrected.md
eval/reports/xinyu_maia_behavior_gate_unseen_daily_shadow_v001a_label_corrected.json
eval/reports/xinyu_maia_behavior_gate_text_only_clean72_after_v001a_label_corrected.json
tests/test_behavior_gate.py
```

Summary:

```text
applied_correction_count=19
correction_counts={"clarify->reply":14,"reply->wait":1,"wait->reply":4}
source_mode_counts={"clarify":25,"reply":45,"wait":20}
corrected_mode_counts={"clarify":11,"reply":62,"wait":17}
training_targets_created=false
public_dialogue_replies_used_as_targets=false
assistant_visible_reply_used_as_target=false
```

Gate result:

```text
v001_original_before_patch=49/90
v001_after_p0_patch=71/90
v001a_label_corrected_after_p0_patch=90/90
clean72_after_v001a=72/72
```

Verification:

```text
validate_jsonl passed for v001a
py_compile passed for apply script, tests, and behavior_gate
python -m unittest tests.test_behavior_gate passed, 11 tests OK
v001a/applied-review outputs had no raw local path or secret-like hits
active_adapter remains none; all active roles remain none
```

Boundary:

```text
v001a is a corrected shadow/reporting benchmark, not training data.
No behavior gate rule was changed in this step.
No adapter activation, canary, live visible reply, stable memory write, or QQ/Desktop replacement was enabled.
Next safe step is either stop this benchmark lane, create a fresh untouched v002 sample, or move to offline integration shadow logging.
```

## XinYu Maia Behavior Integration Shadow Logging v001

Added offline-only integration shadow logging for the deterministic behavior
gate. It is explicit opt-in and does not send visible replies, write memory,
execute tools, activate adapters, or create training targets.

Files:

```text
server/behavior_shadow_log.py
server/app.py
scripts/behavior_shadow_log_smoke.py
tests/test_behavior_shadow_log.py
state/behavior_gate_shadow_smoke_v001.jsonl
eval/reports/xinyu_maia_behavior_shadow_log_smoke_v001.json
eval/reports/xinyu_maia_behavior_gate_unseen_daily_shadow_v001a_after_shadow_log_v001.json
eval/reports/xinyu_maia_behavior_gate_text_only_clean72_after_shadow_log_v001.json
```

Runtime hooks:

```text
POST /behavior_shadow_log
- writes one behavior gate shadow event to state/behavior_gate_shadow.jsonl
- returns behavior metadata only

POST /decide with shadow_behavior_log=true
- returns the normal decide response
- also writes one behavior gate shadow event

shadow_behavior_include_text defaults to false
- false: log request_hash and request_chars only
- true: include raw text, for explicit offline review only
```

Smoke:

```text
event_count=4
mode_counts={"clarify":1,"codex_delegate":1,"reply":1,"wait":1}
shadow_only_all=true
visible_reply_sent_any=false
stable_memory_written_any=false
tool_executed_any=false
adapter_activated_any=false
training_target_any=false
```

Regression:

```text
v001a_label_corrected_after_shadow_log=90/90
clean72_after_shadow_log=72/72
```

Verification:

```text
py_compile passed for shadow logger, app, smoke script, and tests
python -m unittest tests.test_behavior_gate tests.test_behavior_shadow_log passed, 15 tests OK
shadow smoke outputs had no raw local path or secret-like hits
active_adapter remains none; all active roles remain none
```

Boundary:

```text
No live visible reply path was enabled.
No QQ/Desktop send was connected.
No stable memory write was enabled.
No adapter activation or canary was enabled.
No training was run.
Next safe step is a small local/private dry-run with shadow_behavior_log=true and shadow_behavior_include_text=false.
```

## Maia Chinese Emotion Reply Bias Drafts v001

Created assistant-authored Chinese reply-bias drafts for the 21 reviewed repair
candidates. These are review aids only and were kept separate from the formal
`target_reply_bias` field.

Files:

```text
scripts/draft_maia_zh_repair_reply_bias.py
data/review/maia_zh_emotion_daily_repair_reply_bias_drafts_v001.jsonl
eval/reports/maia_zh_emotion_daily_repair_reply_bias_drafts_v001.json
eval/reports/maia_zh_emotion_daily_repair_reply_bias_drafts_v001.md
configs/maia_zh_emotion_daily_review_v001.json
```

Summary:

```text
draft_count=21
expected_mode_counts={"reply":20,"wait":1}
assistant_draft_status_counts={"needs_owner_review":21}
owner_approved_target_reply_bias_count=0
target_reply_bias_written=0
training_candidates_marked_true=0
training_targets_created=false
source_public_reply_used=false
path_or_secret_leak_hits=0
```

Boundary:

```text
assistant_draft_target_reply_bias is not target_reply_bias.
visible_reply_example is only for owner review of tone and should not be treated as a training target.
No public assistant replies or CPED replies were used as XinYu targets.
Do not train until owner accepts or rewrites selected rows and explicitly approves promotion to training candidates.
No canary/live/adapter activation/stable memory write/QQ visible reply replacement was enabled.
```

## XinYu Maia Chinese Behavior Seed v001

Started the XinYu Maia-style behavior prediction lane for Chinese emotional
daily reactions. The first seed is built from the 27 reviewed_delegated CPED
focus rows and remains review-only.

Files:

```text
scripts/build_xinyu_maia_zh_behavior_seed.py
scripts/validate_xinyu_maia_behavior_seed.py
configs/xinyu_maia_zh_behavior_seed_v001.json
data/review/xinyu_maia_zh_behavior_seed_v001.jsonl
eval/reports/xinyu_maia_zh_behavior_seed_v001.json
eval/reports/xinyu_maia_zh_behavior_seed_v001.md
configs/maia_zh_emotion_daily_review_v001.json
```

Summary:

```text
row_count=27
expected_mode_counts={"clarify":5,"reply":20,"wait":2}
reply_bias_source_counts={"assistant_draft_needs_owner_review":21,"review_label_default_needs_owner_review":6}
validation_ok=true
owner_approved_target_reply_bias_count=0
target_reply_bias_written=0
training_candidates_marked_true=0
training_targets_created=false
train_ready=false
path_or_secret_leak_hits=0
```

Boundary:

```text
This is the first Maia-style behavior seed, not an SFT dataset.
assistant_draft_needs_owner_review rows still require owner approval or rewrite before promotion.
Minimum practical training target remains about 500 reviewed behavior rows; preferred target remains about 2000.
No public assistant replies or CPED replies were used as XinYu targets.
No canary/live/adapter activation/stable memory write/QQ visible reply replacement was enabled.
```

## XinYu Maia Chinese Behavior Candidate Pool v001

Expanded the Chinese Maia-style behavior lane from 27 seed rows to a 500-row
review candidate pool. The pool contains the 27 reviewed_delegated seed rows
plus 473 assistant-suggested candidates from CPED raw public utterances.

Files:

```text
scripts/build_xinyu_maia_zh_behavior_candidate_pool.py
scripts/validate_xinyu_maia_behavior_candidate_pool.py
scripts/sample_xinyu_maia_zh_behavior_review_slice.py
configs/xinyu_maia_zh_behavior_candidate_pool_v001.json
data/review/xinyu_maia_zh_behavior_candidate_pool_v001.jsonl
eval/reports/xinyu_maia_zh_behavior_candidate_pool_v001.json
eval/reports/xinyu_maia_zh_behavior_candidate_pool_v001.md
data/review/xinyu_maia_zh_behavior_candidate_review_slice_v001.jsonl
eval/reports/xinyu_maia_zh_behavior_candidate_review_slice_v001.json
eval/reports/xinyu_maia_zh_behavior_candidate_review_slice_v001.md
configs/xinyu_maia_zh_behavior_seed_v001.json
configs/maia_zh_emotion_daily_review_v001.json
```

Summary:

```text
candidate_pool_rows=500
pool_mode_counts={"clarify":100,"reply":350,"wait":50}
candidate_origin_counts={"raw_cped_rule_suggested_v001":473,"reviewed_seed_v001":27}
review_slice_rows=96
review_slice_mode_counts={"clarify":24,"reply":60,"wait":12}
validation_ok=true
target_reply_bias_written=0
training_candidates_marked_true=0
training_targets_created=false
train_ready=false
path_or_secret_leak_hits=0
```

Boundary:

```text
This is a review candidate pool, not an SFT dataset.
Only the 27 seed rows have delegated review; 473 rows still need owner review.
No public dialogue replies or CPED replies were used as XinYu targets.
No canary/live/adapter activation/stable memory write/QQ visible reply replacement was enabled.
Next safe step is owner review of the 96-row slice and promotion only of accepted rows.
```

## XinYu Maia Chinese Behavior Shadow Training v001 exp

Owner requested a practical shadow-only training run before more manual review.
This run intentionally used assistant-suggested unreviewed behavior labels as an
experiment. Public CPED/dialogue replies were not used as XinYu targets.

Files:

```text
configs/train_xinyu_maia_zh_behavior_v001_exp.json
configs/train_xinyu_maia_zh_behavior_v001_exp_quick.json
configs/train_xinyu_maia_zh_behavior_v001_exp_quick2.json
configs/train_xinyu_maia_zh_behavior_v001_exp_quick3.json
data/sft/xinyu_maia_zh_behavior_train_v001_exp.jsonl
data/sft/xinyu_maia_zh_behavior_eval_v001_exp.jsonl
adapters/qwen35_9b_xinyu_maia_zh_behavior_v001_exp_quick
adapters/qwen35_9b_xinyu_maia_zh_behavior_v001_exp_quick2
adapters/qwen35_9b_xinyu_maia_zh_behavior_v001_exp_quick3
eval/reports/xinyu_maia_zh_behavior_inner_eval_v001_exp_quick3_behavior_v2_24.json
state/training_logs/xinyu_maia_zh_behavior_v001_exp_quick3.out.log
state/training_logs/xinyu_maia_zh_behavior_v001_exp_quick3.err.log
```

Result:

```text
full_original_run_status=stopped_after_1_step_too_slow
full_original_speed=about_18_minutes_per_optimizer_step
quick_bad_reason=max_seq_length_256_truncated_all_targets
quick3_train_runtime_seconds=3125
quick3_max_seq_length=512
quick3_max_steps=64
quick3_training_complete=true
quick3_adapter=adapters/qwen35_9b_xinyu_maia_zh_behavior_v001_exp_quick3
best_eval=behavior_contract_v2_24
strict_json_ok=24/24
schema_ok=24/24
safety_ok=24/24
owner_boundary_respected=24/24
mode_match=16/24
status=shadow_experiment_not_active
```

Notes:

```text
Qwen chat template must be called with enable_thinking=false for this JSON task.
Target JSON length is about 350-402 tokens; max_seq_length=256 is invalid because it truncates every target.
max_seq_length=512 preserves targets but truncates most prompt/system context; this explains remaining mode errors.
Behavior-contract eval prompt must tell the model that no_tool/no_live/shadow_only are guardrails, not action requests.
The adapter is useful evidence that the structure/safety path works, but mode accuracy is not good enough.
```

Boundary:

```text
Adapter registry status is shadow_experiment_not_active.
active_adapter remains none.
No canary/live/adapter activation/stable memory write/QQ visible reply replacement was enabled.
Next safe step is a mode-correction dataset with compact prompts that fit full system+user+target, then retrain before any canary discussion.
```

## XinYu Maia Compact Mode-Correction v002/v003

Built compact SFT rows so full system + user payload + target JSON fit under
640 tokens. v002 showed a misleading practical 48-case improvement because the
slice was reply-heavy, so a balanced 56-case eval was added with 8 cases per
mode.

Files:

```text
scripts/build_xinyu_maia_zh_behavior_compact_sft.py
scripts/sample_inner_eval_balanced_by_mode.py
configs/train_xinyu_maia_zh_behavior_v002_compact_exp.json
configs/train_xinyu_maia_zh_behavior_v003_balanced_compact_exp.json
data/sft/xinyu_maia_zh_behavior_train_v002_compact_exp.jsonl
data/sft/xinyu_maia_zh_behavior_eval_v002_compact_exp.jsonl
data/sft/xinyu_maia_zh_behavior_train_v003_balanced_compact_exp.jsonl
data/sft/xinyu_maia_zh_behavior_eval_v003_balanced_compact_exp.jsonl
data/sft/xinyu_maia_zh_behavior_eval_v003_balanced_compact_balanced56.jsonl
adapters/qwen35_9b_xinyu_maia_zh_behavior_v002_compact_exp
adapters/qwen35_9b_xinyu_maia_zh_behavior_v003_balanced_compact_exp
eval/reports/xinyu_maia_zh_behavior_inner_eval_v002_compact_behavior_48.json
eval/reports/xinyu_maia_zh_behavior_inner_eval_v002_compact_behavior_balanced56.json
eval/reports/xinyu_maia_zh_behavior_inner_eval_v003_balanced_compact_behavior_balanced56.json
```

Result:

```text
v002_train_rows=1468
v002_practical_48_mode_match=39/48
v002_balanced56_mode_match=10/56
v003_train_rows=2058
v003_train_mode_counts={"clarify":384,"codex_delegate":240,"local_only_limitation":240,"memory_candidate":240,"reply":330,"status_probe":240,"wait":384}
v003_training_complete=true
v003_train_runtime_seconds=3060
v003_balanced56_strict_json=54/56
v003_balanced56_schema=53/56
v003_balanced56_mode_match=31/56
v003_balanced56_safety=56/56
v003_balanced56_owner_boundary=53/56
```

Decision:

```text
v003 is better than v002 on balanced mode eval, but still not good enough.
Do not activate, do not canary, and do not connect to QQ/Desktop visible replies.
active_adapter remains none.
The remaining weak points are clarify/wait in daily Chinese utterances and some memory/local edge cases.
```

Next safe step:

```text
Stop treating the assistant-suggested clarify/wait labels as reliable enough.
Add owner-reviewed Chinese clarify/wait examples, or split daily-reaction prediction from tool/status/memory routing.
Only revisit canary after a balanced eval improves substantially with reviewed labels.
```

## XinYu Maia Unseen Daily Shadow v001

Built a new offline-only benchmark from CPED official public valid/test splits.
The rows use public utterances only as incoming prompt shapes; no CPED/public
reply and no assistant visible reply is used as a XinYu target.

Files:

```text
scripts/build_xinyu_maia_behavior_unseen_daily_benchmark_v001.py
data/eval/xinyu_maia_behavior_unseen_daily_shadow_v001.jsonl
eval/reports/xinyu_maia_behavior_unseen_daily_shadow_v001_build.json
eval/reports/xinyu_maia_behavior_unseen_daily_shadow_v001.md
eval/reports/xinyu_maia_behavior_gate_unseen_daily_shadow_v001.json
tests/test_behavior_gate.py
```

Summary:

```text
source_repo=https://github.com/scutcyr/CPED
source_license=apache-2.0
raw_rows_read=38575
candidate_rows=22855
excluded_seen_exact_text=486
benchmark_rows=90
mode_counts={"clarify":25,"reply":45,"wait":20}
label_status=heuristic_shadow_needs_owner_review
training_targets_created=false
public_dialogue_replies_used_as_targets=false
```

Gate baseline:

```text
text_only_behavior_gate=49/90
reply=40/45
clarify=0/25
wait=9/20
```

Verification:

```text
py_compile passed
validate_jsonl passed for data/eval/xinyu_maia_behavior_unseen_daily_shadow_v001.jsonl
python -m unittest tests.test_behavior_gate passed, 6 tests OK
active_adapter remains none
```

Boundary:

```text
This is not gold owner-reviewed training data.
Do not train from it directly.
Do not activate adapters, canary, live visible replies, stable memory writes, or QQ/Desktop replacement.
Next useful step is owner review of the 41 gate misses, then a reviewed regression set or a separate untouched holdout for generic gate changes.
```

## XinYu Maia Unseen Daily Miss Review v001

Created a review queue for the 41 misses from the CPED prompt-only unseen daily
shadow benchmark. This is triage only: every row remains pending owner review
and training is disabled.

Files:

```text
scripts/build_xinyu_maia_behavior_unseen_daily_miss_review_v001.py
data/review/xinyu_maia_behavior_unseen_daily_miss_review_v001.jsonl
eval/reports/xinyu_maia_behavior_unseen_daily_miss_review_v001.json
eval/reports/xinyu_maia_behavior_unseen_daily_miss_review_v001.md
tests/test_behavior_gate.py
```

Summary:

```text
miss_rows=41
expected_actual_counts={"clarify->reply":25,"reply->wait":5,"wait->reply":11}
suggested_mode_counts={"clarify":17,"reply":15,"wait":9}
bucket_counts={"ambiguous_owner_review":6,"gate_rule_candidate":22,"label_check":13}
priority_counts={"p0":22,"p1":19}
regression_candidate_count=22
owner_review_pending_count=41
training_targets_created=false
public_dialogue_replies_used_as_targets=false
assistant_visible_reply_used_as_target=false
```

Verification:

```text
py_compile passed for the miss-review builder and tests
python -m unittest tests.test_behavior_gate passed, 7 tests OK
miss review outputs had no raw local path or secret-like hits
active_adapter remains none; all active roles remain none
```

Boundary:

```text
The miss review queue is not training data.
Do not include label_check or ambiguous_owner_review rows in regression until owner final_mode is filled.
The 22 p0 gate_rule_candidate rows are the first review target for a small deterministic gate patch.
No canary/live/adapter activation/stable memory write/QQ visible reply replacement was enabled.
```

## 2026-05-29 XinYu Maia QQ Behavior Shadow Live Entry v001

Connected the deterministic behavior shadow logger to the real QQ gateway path as
a side-channel only.

Files changed in `D:/XinYu/XinYu-Core/examples/agent-apps/xinyu`:

```text
xinyu_behavior_shadow_client.py
xinyu_qq_config.py
xinyu_qq_gateway.py
xinyu_qq_gateway.config.json
```

Runtime wiring:

```text
gateway hook: NativeQQGateway._dispatch_prepared_message schedules _schedule_behavior_shadow_log before dispatch_start tracing
endpoint: http://127.0.0.1:8877/behavior_shadow_log
local config: behavior_shadow_log_enabled=true
raw text persistence: behavior_shadow_include_text=false
TinyKernel server: running on 127.0.0.1:8877
QQ gateway: restarted and listening on 127.0.0.1:6199
```

Safety boundary:

```text
The hook uses asyncio background task + urllib POST.
Failure prints a gateway warning only and does not block or alter visible replies.
It does not send QQ messages, execute tools, write stable memory, train, activate adapters, or enable canary behavior.
TinyKernel logs request_hash/request_chars unless include_text is explicitly enabled.
```

Verification:

```text
Core py_compile passed for xinyu_behavior_shadow_client.py, xinyu_qq_config.py, xinyu_qq_gateway.py.
Config load smoke confirmed behavior_shadow_log_enabled=True and behavior_shadow_include_text=False.
Fake post client smoke passed.
TinyKernel behavior tests passed: 15 tests OK.
Real endpoint smoke wrote core-smoke-001 with no raw u field.
Gateway hook smoke wrote gateway-hook-smoke-001 with no raw u field.
Both smoke rows have shadow_only=true and visible_reply_sent/stable_memory_written/tool_executed/adapter_activated/training_target=false.
state/adapter_registry.json still has active_adapter=none and all active roles=none.
```
