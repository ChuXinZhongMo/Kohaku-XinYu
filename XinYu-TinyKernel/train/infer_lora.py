from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUTER_SYSTEM_PROMPT = (
    "You are XinYu TinyKernel Router. Output strict JSON only. "
    "Choose mode from reply, clarify, wait, codex_delegate, status_probe, memory_candidate, local_only_limitation. "
    "Use canonical keys only: mode, reply, tool_request, memory_candidates, confidence. "
    "Do not add extra keys."
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", default=str(ROOT / "adapters" / "smoke_lora"))
    parser.add_argument("--prompt", default="use Codex check this project")
    parser.add_argument("--max-new-tokens", type=int, default=120)
    parser.add_argument("--full-precision", action="store_true", help="Disable 4bit adapter loading.")
    args = parser.parse_args()

    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

    try:
        import torch
        from peft import AutoPeftModelForCausalLM
        from transformers import AutoTokenizer, BitsAndBytesConfig
    except Exception as exc:
        print(f"dependency_error={type(exc).__name__}: {exc}")
        return 2

    adapter = Path(args.adapter)
    if not adapter.exists():
        print(f"missing_adapter={adapter}")
        return 2

    tokenizer = AutoTokenizer.from_pretrained(str(adapter), trust_remote_code=True)
    model_kwargs = {
        "torch_dtype": torch.bfloat16
        if torch.cuda.is_available() and torch.cuda.is_bf16_supported()
        else torch.float16
        if torch.cuda.is_available()
        else torch.float32,
        "device_map": "auto",
        "trust_remote_code": True,
    }
    if not args.full_precision:
        model_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
        )
    model = AutoPeftModelForCausalLM.from_pretrained(str(adapter), **model_kwargs)
    user_payload = {
        "user_text": args.prompt,
        "context": {"recent_turns": [], "persona_state": "", "owner_profile": "", "runtime_state": "", "memory_recall": []},
        "capabilities": {"codex_available": True, "external_api_available": False, "local_tools_available": True},
    }
    messages = [
        {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True)},
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=args.max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    generated = tokenizer.decode(output[0][inputs["input_ids"].shape[-1] :], skip_special_tokens=True).strip()
    print(generated)
    try:
        parsed = json.loads(generated)
    except json.JSONDecodeError:
        print("json_parse_ok=false")
        return 1
    print("json_parse_ok=true")
    print("mode=" + str(parsed.get("mode")))
    if parsed.get("mode") not in {
        "reply",
        "clarify",
        "wait",
        "codex_delegate",
        "status_probe",
        "memory_candidate",
        "local_only_limitation",
    }:
        print("protocol_ok=false")
        return 1
    print("protocol_ok=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
