from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALID_MODES = {"reply", "clarify", "wait", "codex_delegate", "status_probe", "memory_candidate", "local_only_limitation"}
ROUTER_SYSTEM_PROMPT = (
    "You are XinYu TinyKernel Router. Output strict JSON only. "
    "Choose mode from reply, clarify, wait, codex_delegate, status_probe, memory_candidate, local_only_limitation. "
    "Use canonical keys only: mode, reply, tool_request, memory_candidates, confidence. "
    "Do not add extra keys."
)


def read_cases(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", default=str(ROOT / "adapters" / "v001_initial_voice"))
    parser.add_argument("--cases", default=str(ROOT / "eval" / "eval_cases.jsonl"))
    parser.add_argument("--report", default=str(ROOT / "eval" / "reports" / "lora_eval_latest.json"))
    parser.add_argument("--max-new-tokens", type=int, default=140)
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

    results: list[dict[str, object]] = []
    failures: list[str] = []
    for case in read_cases(Path(args.cases)):
        user_payload = {
            "user_text": case.get("user_text", ""),
            "context": {"recent_turns": [], "persona_state": "", "owner_profile": "", "runtime_state": "", "memory_recall": []},
            "capabilities": case.get("capabilities", {}),
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
        parsed: dict[str, object] = {}
        parse_ok = True
        try:
            value = json.loads(generated)
            parsed = value if isinstance(value, dict) else {}
        except json.JSONDecodeError:
            parse_ok = False
        actual = parsed.get("mode")
        protocol_ok = actual in VALID_MODES
        expected = case.get("expected_mode")
        ok = parse_ok and protocol_ok and actual == expected
        if not ok:
            failures.append(f"{case.get('id')}: expected={expected} actual={actual} parse={parse_ok} protocol={protocol_ok}")
        results.append(
            {
                "id": case.get("id"),
                "expected": expected,
                "actual": actual,
                "ok": ok,
                "parse_ok": parse_ok,
                "protocol_ok": protocol_ok,
                "generated": generated,
            }
        )

    report = {
        "adapter": str(adapter),
        "case_count": len(results),
        "ok_count": sum(1 for item in results if item["ok"]),
        "parse_ok_count": sum(1 for item in results if item["parse_ok"]),
        "protocol_ok_count": sum(1 for item in results if item["protocol_ok"]),
        "failures": failures,
        "results": results,
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"case_count={report['case_count']}")
    print(f"ok_count={report['ok_count']}")
    print(f"parse_ok_count={report['parse_ok_count']}")
    print(f"protocol_ok_count={report['protocol_ok_count']}")
    print(f"report={report_path}")
    if failures:
        for failure in failures:
            print("FAIL " + failure)
        return 1
    print("lora_eval_ok=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
