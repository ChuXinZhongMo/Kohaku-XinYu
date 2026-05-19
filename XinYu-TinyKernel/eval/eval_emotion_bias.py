from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from schemas import normalize_emotion_bias


def read_rows(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if not line.strip():
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
            if limit is not None and len(rows) >= limit:
                break
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--cases", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--expected-lens", required=True)
    parser.add_argument("--limit", type=int, default=24)
    parser.add_argument("--max-new-tokens", type=int, default=120)
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
    model.eval()

    results: list[dict[str, Any]] = []
    failures: list[str] = []
    for row in read_rows(Path(args.cases), limit=args.limit):
        messages = row.get("messages")
        if not isinstance(messages, list) or len(messages) < 2:
            failures.append(f"{row.get('id')}: invalid messages")
            continue
        prompt_messages = messages[:2]
        text = tokenizer.apply_chat_template(prompt_messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt").to(model.device)
        with torch.no_grad():
            output = model.generate(
                **inputs,
                max_new_tokens=args.max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        generated = tokenizer.decode(output[0][inputs["input_ids"].shape[-1] :], skip_special_tokens=True).strip()
        ok = True
        notes: list[str] = []
        parsed: dict[str, Any] | None = None
        try:
            value = json.loads(generated)
            parsed = value if isinstance(value, dict) else None
        except json.JSONDecodeError:
            notes.append("invalid_json")
            ok = False
        normalized = normalize_emotion_bias(parsed or {})
        if normalized is None:
            notes.append("invalid_schema")
            ok = False
        elif normalized.get("lens") != args.expected_lens:
            notes.append(f"wrong_lens:{normalized.get('lens')}")
            ok = False
        if not ok:
            failures.append(f"{row.get('id')}: {','.join(notes)}")
        results.append({"id": row.get("id"), "ok": ok, "notes": notes, "generated": generated})

    report = {
        "adapter": str(adapter),
        "case_count": len(results),
        "expected_lens": args.expected_lens,
        "ok_count": sum(1 for item in results if item["ok"]),
        "failures": failures,
        "results": results,
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"case_count={report['case_count']}")
    print(f"ok_count={report['ok_count']}")
    print(f"report={report_path}")
    if failures:
        for failure in failures[:20]:
            print("FAIL " + failure)
        return 1
    print("emotion_bias_eval_ok=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
