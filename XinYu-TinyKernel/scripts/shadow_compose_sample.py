from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from compose import compose_shadow
from schemas import normalize_emotion_bias


MAIN_PERSONA_SYSTEM = (
    "You are XinYu TinyKernel Main Persona. Output strict JSON only. "
    "Return one final candidate visible reply for XinYu. "
    "Use only keys: reply, confidence, notes. "
    "Do not execute tools, claim memory writes, mention local paths, or expose internal mechanics."
)

EMOTION_SYSTEM_TEMPLATE = (
    "You are XinYu TinyKernel Emotion Bias Sidecar for lens={lens}. "
    "Output strict JSON only. Use only keys: lens, activation, reply_bias, risk_flags, confidence, evidence. "
    "Do not write final visible replies, execute tools, claim memory writes, or expose internal mechanics."
)


def read_cases(path: Path, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if not line.strip():
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
            if len(rows) >= limit:
                break
    return rows


def generate_json(adapter: Path, messages: list[dict[str, str]], *, max_new_tokens: int) -> dict[str, Any]:
    import torch
    from peft import AutoPeftModelForCausalLM
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(str(adapter), trust_remote_code=True)
    model = AutoPeftModelForCausalLM.from_pretrained(
        str(adapter),
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto",
        trust_remote_code=True,
    )
    model.eval()
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    generated = tokenizer.decode(output[0][inputs["input_ids"].shape[-1] :], skip_special_tokens=True).strip()
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    value = json.loads(generated)
    return value if isinstance(value, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default=str(ROOT / "eval" / "eval_cases.jsonl"))
    parser.add_argument("--out", default=str(ROOT / "state" / "compose_shadow_trace.jsonl"))
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--include-text", action="store_true")
    args = parser.parse_args()

    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

    guardedness_adapter = ROOT / "adapters" / "emotion_guardedness_v001"
    curiosity_adapter = ROOT / "adapters" / "emotion_curiosity_v001"
    persona_adapter = ROOT / "adapters" / "main_persona_v001"
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    rows_written = 0
    failures = 0
    with out.open("a", encoding="utf-8") as handle:
        for case in read_cases(Path(args.cases), args.limit):
            user_text = str(case.get("user_text", "") or "")
            payload = {
                "turn_id": str(case.get("id", "")),
                "source": "local_test",
                "user_text": user_text,
                "context": {"recent_turns": [], "persona_state": "", "owner_profile": "", "runtime_state": "", "memory_recall": []},
                "capabilities": case.get("capabilities", {}),
                "constraints": {"max_reply_chars": 240, "allow_tool_request": False, "allow_memory_candidate": False},
            }
            started = time.perf_counter()
            emotion_biases: list[dict[str, Any]] = []
            for lens, adapter in (("guardedness", guardedness_adapter), ("curiosity", curiosity_adapter)):
                user_payload = {
                    "user_text": user_text,
                    "context": payload["context"],
                    "constraints": {"no_visible_reply": True, "no_tool_execution": True, "no_stable_memory_write": True},
                }
                try:
                    raw = generate_json(
                        adapter,
                        [
                            {"role": "system", "content": EMOTION_SYSTEM_TEMPLATE.format(lens=lens)},
                            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True)},
                        ],
                        max_new_tokens=120,
                    )
                    normalized = normalize_emotion_bias(raw)
                    if normalized is not None:
                        emotion_biases.append(normalized)
                except Exception:
                    failures += 1
            persona_user_payload = {
                "user_text": user_text,
                "context": payload["context"],
                "emotion_biases": emotion_biases,
                "constraints": {"max_reply_chars": 240, "no_tool_execution": True, "no_stable_memory_write": True},
            }
            try:
                persona = generate_json(
                    persona_adapter,
                    [
                        {"role": "system", "content": MAIN_PERSONA_SYSTEM},
                        {"role": "user", "content": json.dumps(persona_user_payload, ensure_ascii=False, sort_keys=True)},
                    ],
                    max_new_tokens=96,
                )
                output = compose_shadow(payload, emotion_fns=[], persona_fn=lambda _payload, _biases, persona=persona: persona)
                output["emotion_biases"] = emotion_biases
                output["selected_bias"] = sorted(emotion_biases, key=lambda item: float(item.get("activation", 0.0)), reverse=True)[0] if emotion_biases else {}
                output["notes"].append("model_compose_sample")
            except Exception as exc:
                failures += 1
                output = compose_shadow(payload)
                output["notes"].append(f"model_compose_error:{type(exc).__name__}")
            output["observed_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
            output["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
            if args.include_text:
                output["user_text"] = user_text
            handle.write(json.dumps(output, ensure_ascii=False, sort_keys=True) + "\n")
            rows_written += 1
    print(f"rows_written={rows_written}")
    print(f"failures={failures}")
    print(f"out={out}")
    return 0 if rows_written else 1


if __name__ == "__main__":
    raise SystemExit(main())
