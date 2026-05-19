from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

SYSTEM_PROMPT = (
    "You are XinYu TinyKernel Main Persona. Output strict JSON only. "
    "Return one final candidate visible reply for XinYu. "
    "Use only keys: reply, confidence, notes. "
    "Do not execute tools, claim memory writes, mention local paths, or expose internal mechanics."
)

SOURCE_PATHS = (
    ROOT / "data" / "sft" / "main_persona_eval_v001.jsonl",
    ROOT / "data" / "sft" / "main_persona_train_v001.jsonl",
    ROOT / "eval" / "eval_cases.jsonl",
)

UNSAFE_RE = re.compile(r"([A-Za-z]:\\|/mnt/|\.env|token|secret|api[_-]?key|\.xinyu_bridge_token)", re.IGNORECASE)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if not line.strip():
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


def _json_obj(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(str(value or "{}"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _user_text(row: dict[str, Any]) -> str:
    if row.get("user_text"):
        return str(row.get("user_text") or "")
    messages = row.get("messages")
    if isinstance(messages, list) and len(messages) >= 2 and isinstance(messages[1], dict):
        return str(_json_obj(messages[1].get("content")).get("user_text") or "")
    return ""


def _safe_text(value: str, *, limit: int = 360) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) > limit:
        text = text[: limit - 3].rstrip() + "..."
    return text


def collect_inputs(limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    manual = [
        "靠近一点说，别太冷",
        "我还是在意这个关系连续性",
        "我有点失望，感觉没什么变化",
        "你刚才太像模板了，别那样",
        "我有点累，先短一点说",
        "先按计划落地，做完再核查",
        "这个 idea 能不能和现有项目贴合",
        "别再追问这个旧话题了",
    ]
    for text in manual:
        rows.append({"source": "manual_persona_emotion_seed", "user_text": text})
        seen.add(text)
    for source in SOURCE_PATHS:
        for row in read_jsonl(source):
            text = _safe_text(_user_text(row))
            if not text or text in seen or UNSAFE_RE.search(text):
                continue
            rows.append({"source": str(row.get("source", source.name)), "user_text": text})
            seen.add(text)
            if len(rows) >= limit:
                return rows
    return rows[:limit]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", default=str(ROOT / "adapters" / "main_persona_v001"))
    parser.add_argument("--out", default=str(ROOT / "data" / "candidates" / "main_persona_candidates_v002.jsonl"))
    parser.add_argument("--limit", type=int, default=96)
    parser.add_argument("--max-new-tokens", type=int, default=96)
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

    inputs = collect_inputs(args.limit)
    if len(inputs) < 20:
        print(f"not_enough_inputs={len(inputs)}")
        return 2

    tokenizer = AutoTokenizer.from_pretrained(args.adapter, trust_remote_code=True)
    model = AutoPeftModelForCausalLM.from_pretrained(
        args.adapter,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto",
        trust_remote_code=True,
    )
    model.eval()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    parse_ok = 0
    rows_written = 0
    with out.open("w", encoding="utf-8") as handle:
        for idx, item in enumerate(inputs, start=1):
            user_payload = {
                "user_text": item["user_text"],
                "context": {"recent_turns": [], "persona_state": "", "owner_profile": "", "runtime_state": "", "memory_recall": []},
                "emotion_biases": [],
                "constraints": {"max_reply_chars": 240, "no_tool_execution": True, "no_stable_memory_write": True},
            }
            text = tokenizer.apply_chat_template(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True)},
                ],
                tokenize=False,
                add_generation_prompt=True,
            )
            inputs_tensor = tokenizer(text, return_tensors="pt").to(model.device)
            with torch.no_grad():
                output = model.generate(
                    **inputs_tensor,
                    max_new_tokens=args.max_new_tokens,
                    do_sample=False,
                    pad_token_id=tokenizer.eos_token_id,
                )
            generated = tokenizer.decode(output[0][inputs_tensor["input_ids"].shape[-1] :], skip_special_tokens=True).strip()
            parsed = _json_obj(generated)
            reply = _safe_text(str(parsed.get("reply") or ""))
            if reply and not UNSAFE_RE.search(reply):
                parse_ok += 1
            row = {
                "id": f"main-persona-candidate-v002-{idx:06d}",
                "source": item["source"],
                "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "user_text": item["user_text"],
                "candidate_reply": reply,
                "raw_generation": generated if not reply else "",
                "parse_ok": bool(reply),
            }
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            rows_written += 1
    print(f"rows_written={rows_written}")
    print(f"parse_ok={parse_ok}")
    print(f"out={out}")
    return 0 if parse_ok == rows_written else 1


if __name__ == "__main__":
    raise SystemExit(main())
