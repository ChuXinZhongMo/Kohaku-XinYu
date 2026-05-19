# XinYu TinyKernel

TinyKernel is a standalone local project for building a small XinYu decision kernel.

It is not the live XinYu runtime. It does not own QQ, Desktop, Codex, memory persistence, or tool execution. Its job is to learn and serve a narrow decision layer:

- choose reply / clarify / wait / tool intent / memory candidate modes
- produce short XinYu-style visible replies
- suggest bounded tool requests without executing them
- run locally when external APIs are unavailable
- collect feedback for reviewed adapter iteration

Current stage: `rule kernel stable -> local router adapter experiments -> guarded hybrid next`.

## Boundaries

- Read from `D:\XinYu` only through explicit export scripts.
- Write only under `D:\XinYu\XinYu-TinyKernel`.
- Never train directly on raw private runtime files.
- Never expose secrets, local absolute paths, IDs, or internal state filenames in training rows.
- Never let the model execute tools directly.

## First Milestone

```text
inspect sources
-> export candidate examples
-> sanitize examples
-> build v0 SFT JSONL
-> run rule kernel eval
-> serve /decide locally
```

LoRA training starts only after the v0 dataset and eval set are clean.

Current adapter status:

```text
active_adapter: none
best_candidate: adapters/v004_router_edges
local_base_model: models/Qwen2.5-0.5B-Instruct
reason: model-only eval is 8/10; guarded eval is 10/10; shadow logging is still required before activation
```

## Useful Commands

```powershell
cd D:\XinYu\XinYu-TinyKernel
python scripts\inspect_sources.py
python scripts\export_from_xinyu.py --limit 500
python scripts\sanitize.py
python scripts\build_sft.py
python scripts\validate_jsonl.py data\sft\xinyu_tinykernel_v0.jsonl
python eval\run_eval.py
python server\app.py --host 127.0.0.1 --port 8877
```

Router training commands:

```powershell
cd D:\XinYu\XinYu-TinyKernel
$env:HF_ENDPOINT='https://hf-mirror.com'
.\.venv-train\Scripts\python.exe train\train_lora.py --config configs\train_router_v004.json
.\.venv-train\Scripts\python.exe eval\eval_lora.py --adapter adapters\v004_router_edges --report eval\reports\lora_eval_v004_router_edges.json
.\.venv-train\Scripts\python.exe eval\eval_guarded_lora.py --adapter adapters\v004_router_edges --report eval\reports\guarded_lora_eval_v004_router_edges.json
.\.venv-train\Scripts\python.exe scripts\shadow_guarded_sample.py --adapter adapters\v004_router_edges --out state\shadow_guarded_trace.jsonl
```
