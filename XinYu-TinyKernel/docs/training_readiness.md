# Training Readiness

Current status: adapter training is possible, but activation is blocked intentionally.

Training should not start until all gates are satisfied.

## Current Dataset

```text
main SFT rows: 712
main train rows: 625
main eval rows: 87
router SFT rows: 907
router train v0 rows: 797
router eval rows: 110
router train v2 rows: 522
```

Mode distribution:

```text
router_train_v2:
reply: 270
codex_delegate: 82
local_only_limitation: 37
wait: 36
memory_candidate: 33
status_probe: 33
clarify: 31
```

## Training Environment

The isolated training environment exists at:

```text
D:\XinYu\XinYu-TinyKernel\.venv-train
```

Verified:

```text
Python: D:\XinYu\Python312\python.exe
GPU: NVIDIA GeForce GTX 1660 Ti, 6GB VRAM
torch: 2.8.0+cu128
HF endpoint: https://hf-mirror.com
```

## Adapter Results

```text
v001_initial_voice: rejected, 1/10 fixed mode eval
v002_router: rejected, copied user payload, protocol failed
v003_router_masked: rejected, 6/10 fixed mode eval, protocol 10/10
v004_router_edges: guarded candidate, 8/10 model-only fixed mode eval, 10/10 guarded fixed mode eval, protocol 10/10
v005_router_edges: rejected, regressed to 6/10 fixed mode eval
```

See:

```text
docs/adapter_evaluation.md
state/adapter_registry.json
eval/reports/lora_eval_v004_router_edges.json
eval/reports/guarded_lora_eval_v004_router_edges.json
```

## Required Activation Gates

- JSONL validation passes.
- Safety scan passes.
- Rule eval passes 10/10.
- Model protocol eval passes 10/10.
- Guarded model eval passes 10/10. Current v004 guarded eval passes.
- HTTP smoke passes.
- Shadow-only logging passes.
- At least 100 rows are manually reviewed.
- `state/adapter_registry.json` is updated manually.

## Main Risk

The current small LoRA can obey the JSON protocol, but model-only mode selection is not stable enough for hard boundaries. API-down, wait, negative tool, and safety-critical tool routes should remain deterministic rule guards.

## Current Runtime Decision

Keep runtime active path as:

```text
server/kernel.py rule kernel
active_adapter: none
```

Next route is shadow-only logging through the guarded hybrid path, not another blind model-only training run.
