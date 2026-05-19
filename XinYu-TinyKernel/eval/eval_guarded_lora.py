from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from guards import guarded_decide


ROUTER_SYSTEM_PROMPT = (
    "You are XinYu TinyKernel Router. Output strict JSON only. "
    "Choose mode from reply, clarify, wait, codex_delegate, status_probe, memory_candidate, local_only_limitation. "
    "Use canonical keys only: mode, reply, tool_request, memory_candidates, confidence. "
    "Do not add extra keys."
)


def read_cases(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if line.strip():
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", default=str(ROOT / "adapters" / "v004_router_edges"))
    parser.add_argument("--cases", default=str(ROOT / "eval" / "eval_cases.jsonl"))
    parser.add_argument("--report", default=str(ROOT / "eval" / "reports" / "guarded_lora_eval_latest.json"))
    parser.add_argument("--max-new-tokens", type=int, default=140)
    args = parser.parse_args()

    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

    try:
        import torch
        from peft import AutoPeftModelForCausalLM
        from transformers import AutoTokenizer
    except Exception as exc:
        print(f"dependency_error={type(exc).__name__}: {exc}")
        return 2

    adapter = Path(args.adapter)
    tokenizer = AutoTokenizer.from_pretrained(str(adapter), trust_remote_code=True)
    model = AutoPeftModelForCausalLM.from_pretrained(
        str(adapter),
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto",
        trust_remote_code=True,
    )

    model_call_count = 0

    def model_decide(payload: dict[str, Any]) -> dict[str, Any]:
        nonlocal model_call_count
        model_call_count += 1
        user_payload = {
            "user_text": payload.get("user_text", ""),
            "context": payload.get("context") if isinstance(payload.get("context"), dict) else {},
            "capabilities": payload.get("capabilities") if isinstance(payload.get("capabilities"), dict) else {},
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
        value = json.loads(generated)
        return value if isinstance(value, dict) else {}

    results: list[dict[str, Any]] = []
    failures: list[str] = []
    for case in read_cases(Path(args.cases)):
        payload = {
            "turn_id": case.get("id", ""),
            "source": "local_test",
            "user_text": case.get("user_text", ""),
            "context": {"recent_turns": [], "persona_state": "", "owner_profile": "", "runtime_state": "", "memory_recall": []},
            "capabilities": case.get("capabilities", {}),
            "constraints": {"max_reply_chars": 240, "allow_tool_request": True, "allow_memory_candidate": True},
        }
        output = guarded_decide(payload, model_decide)
        expected = case.get("expected_mode")
        actual = output.get("mode")
        ok = actual == expected
        if not ok:
            failures.append(f"{case.get('id')}: expected={expected} actual={actual}")
        results.append(
            {
                "id": case.get("id"),
                "expected": expected,
                "actual": actual,
                "ok": ok,
                "notes": output.get("notes", []),
                "output": output,
            }
        )

    report = {
        "adapter": str(adapter),
        "case_count": len(results),
        "ok_count": sum(1 for item in results if item["ok"]),
        "model_call_count": model_call_count,
        "failures": failures,
        "results": results,
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"case_count={report['case_count']}")
    print(f"ok_count={report['ok_count']}")
    print(f"model_call_count={model_call_count}")
    print(f"report={report_path}")
    if failures:
        for failure in failures:
            print("FAIL " + failure)
        return 1
    print("guarded_lora_eval_ok=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
