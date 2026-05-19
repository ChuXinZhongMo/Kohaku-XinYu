# Training Notes

Training is intentionally not started in v0.

Prerequisites before LoRA:

1. `data\sft\xinyu_tinykernel_v0.jsonl` validates.
2. `eval\run_eval.py` passes for the rule kernel.
3. At least 300 cleaned rows are manually spot checked.
4. Sensitive data scan shows no secrets, raw IDs, or local path leaks.

Planned first training target:

```text
base model: Qwen/Qwen2.5-0.5B-Instruct
method: LoRA
precision: fp16
```
