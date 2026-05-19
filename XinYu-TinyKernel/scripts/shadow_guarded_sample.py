from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from guards import guarded_decide
from kernel import decide


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


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", default=str(ROOT / "adapters" / "v004_router_edges"))
    parser.add_argument("--cases", default=str(ROOT / "eval" / "eval_cases.jsonl"))
    parser.add_argument("--out", default=str(ROOT / "state" / "shadow_guarded_trace.jsonl"))
    parser.add_argument("--include-text", action="store_true")
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

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    disagreement_count = 0
    rows_written = 0
    with out.open("a", encoding="utf-8") as handle:
        for case in read_cases(Path(args.cases)):
            user_text = str(case.get("user_text", "") or "")
            payload = {
                "turn_id": case.get("id", ""),
                "source": "local_test",
                "user_text": user_text,
                "context": {"recent_turns": [], "persona_state": "", "owner_profile": "", "runtime_state": "", "memory_recall": []},
                "capabilities": case.get("capabilities", {}),
                "constraints": {"max_reply_chars": 240, "allow_tool_request": True, "allow_memory_candidate": True},
            }
            started = time.perf_counter()
            rule_output = decide(payload)
            candidate_output = guarded_decide(payload, model_decide)
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            disagreement = rule_output.get("mode") != candidate_output.get("mode")
            disagreement_count += int(disagreement)
            row = {
                "event_kind": "tinykernel_guarded_shadow_sample",
                "observed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "turn_id": case.get("id", ""),
                "expected_mode": case.get("expected_mode"),
                "request_hash": text_hash(user_text),
                "request_chars": len(user_text),
                "rule_mode": rule_output.get("mode"),
                "candidate_mode": candidate_output.get("mode"),
                "candidate_notes": candidate_output.get("notes", []),
                "disagreement": disagreement,
                "elapsed_ms": elapsed_ms,
                "adapter": str(adapter),
            }
            if args.include_text:
                row["user_text"] = user_text
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            rows_written += 1

    print(f"rows_written={rows_written}")
    print(f"disagreement_count={disagreement_count}")
    print(f"model_call_count={model_call_count}")
    print(f"out={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
