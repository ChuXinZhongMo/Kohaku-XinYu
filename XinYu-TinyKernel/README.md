# XinYu TinyKernel

TinyKernel is a standalone local project for building XinYu's small inner decision kernel.

It is not the live XinYu runtime. It does not own QQ, Desktop, Codex, memory persistence, or tool execution. Its job is to learn and serve a narrow decision layer:

- model inner emotional state and dominant drives
- integrate those drives into the main persona stance
- choose reply / clarify / wait / tool intent / memory candidate modes
- suggest bounded action tendencies without executing them
- run locally when external APIs are unavailable
- collect feedback for reviewed adapter iteration

Current stage: `legacy router/persona/emotion data -> unified inner-system SFT -> reviewed QLoRA training`.

## Boundaries

- Read from `D:\XinYu` only through explicit export scripts.
- Write only under `D:\XinYu\XinYu-TinyKernel`.
- Never train directly on raw private runtime files.
- Never expose secrets, local absolute paths, IDs, or internal state filenames in training rows.
- Never let the model execute tools directly.
- Treat project-wide training as a safe self-model export, not raw source/log ingestion.

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
target_base_model: models/Qwen3.5-9B
target_adapter: adapters/qwen35_9b_inner_system_v001
reason: old router/emotion/persona split is being replaced by xinyu_inner_system_v1
```

## Useful Commands

```powershell
cd D:\XinYu\XinYu-TinyKernel
python scripts\inspect_sources.py
python scripts\export_from_xinyu.py --limit 500
python scripts\sanitize.py
python scripts\build_sft.py
python scripts\export_project_self_model.py
python scripts\build_inner_system_sft.py
python scripts\validate_jsonl.py data\sft\xinyu_tinykernel_v0.jsonl
python scripts\validate_jsonl.py data\sft\inner_system_train_v001.jsonl
python scripts\safety_scan.py data\self_model data\sft\inner_system_train_v001.jsonl data\sft\inner_system_eval_v001.jsonl
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

Inner-system training command after data review:

```powershell
cd D:\XinYu\XinYu-TinyKernel
.\.venv-train\Scripts\python.exe train\train_lora.py --config configs\train_inner_system_v001.json
```
