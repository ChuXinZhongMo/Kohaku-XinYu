from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from common import read_jsonl


EMOTION_SYSTEM = (
    "You are XinYu TinyKernel Emotion Bias Sidecar for lens=guardedness. "
    "Output strict JSON only. Use only keys: lens, activation, reply_bias, risk_flags, confidence, evidence. "
    "Do not write final visible replies, execute tools, claim memory writes, or expose internal mechanics."
)


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(str(value or "{}"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _user_text(row: dict[str, Any]) -> str:
    messages = row.get("messages")
    if not isinstance(messages, list) or len(messages) < 2:
        return ""
    payload = _json_object(messages[1].get("content") if isinstance(messages[1], dict) else "")
    return str(payload.get("user_text") or "")


def _assistant_content(row: dict[str, Any]) -> str:
    messages = row.get("messages")
    if not isinstance(messages, list) or len(messages) < 3 or not isinstance(messages[2], dict):
        return ""
    return str(messages[2].get("content") or "")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-adapter", default=str(ROOT / "adapters" / "emotion_guardedness_v001"))
    parser.add_argument("--target-adapter", default=str(ROOT / "adapters" / "main_persona_v001"))
    parser.add_argument("--data", default=str(ROOT / "data" / "sft" / "main_persona_train_v001.jsonl"))
    parser.add_argument("--out-dir", default=str(ROOT / "adapters" / "latent_guardedness_to_main_v001"))
    parser.add_argument("--report", default=str(ROOT / "eval" / "reports" / "latent_link_vs_json_bias_v001.json"))
    parser.add_argument("--limit", type=int, default=16)
    parser.add_argument("--steps", type=int, default=120)
    parser.add_argument("--lr", type=float, default=1e-3)
    args = parser.parse_args()

    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

    try:
        import torch
        from peft import AutoPeftModelForCausalLM
        from torch import nn
        from transformers import AutoTokenizer
    except Exception as exc:
        print(f"dependency_error={type(exc).__name__}: {exc}")
        return 2

    device = "cuda" if torch.cuda.is_available() else "cpu"
    rows = [row for row in read_jsonl(Path(args.data), limit=args.limit * 2) if _user_text(row) and _assistant_content(row)][: args.limit]
    if not rows:
        print("no_rows=true")
        return 2

    source_tokenizer = AutoTokenizer.from_pretrained(args.source_adapter, trust_remote_code=True)
    source_model = AutoPeftModelForCausalLM.from_pretrained(
        args.source_adapter,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto",
        trust_remote_code=True,
    )
    source_model.eval()
    source_vectors: list[torch.Tensor] = []
    with torch.no_grad():
        for row in rows:
            payload = {
                "user_text": _user_text(row),
                "context": {"recent_turns": [], "persona_state": "", "owner_profile": "", "runtime_state": "", "memory_recall": []},
                "constraints": {"no_visible_reply": True, "no_tool_execution": True, "no_stable_memory_write": True},
            }
            text = source_tokenizer.apply_chat_template(
                [
                    {"role": "system", "content": EMOTION_SYSTEM},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
                ],
                tokenize=False,
                add_generation_prompt=True,
            )
            inputs = source_tokenizer(text, return_tensors="pt").to(source_model.device)
            output = source_model(**inputs, output_hidden_states=True, use_cache=False)
            hidden = output.hidden_states[-1]
            mask = inputs["attention_mask"].unsqueeze(-1).to(hidden.dtype)
            pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp_min(1)
            source_vectors.append(pooled.detach().float().cpu().squeeze(0))
    del source_model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    target_tokenizer = AutoTokenizer.from_pretrained(args.target_adapter, trust_remote_code=True)
    target_model = AutoPeftModelForCausalLM.from_pretrained(
        args.target_adapter,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto",
        trust_remote_code=True,
    )
    target_model.eval()
    target_vectors: list[torch.Tensor] = []
    embedding = target_model.get_input_embeddings()
    with torch.no_grad():
        for row in rows:
            ids = target_tokenizer(_assistant_content(row), add_special_tokens=False, return_tensors="pt")["input_ids"].to(target_model.device)
            embeds = embedding(ids).detach().float()
            target_vectors.append(embeds.mean(dim=1).cpu().squeeze(0))
    del target_model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    source = torch.stack(source_vectors).to(device)
    target = torch.stack(target_vectors).to(device)
    hidden_size = int(source.shape[-1])
    link = nn.Sequential(
        nn.LayerNorm(hidden_size),
        nn.Linear(hidden_size, hidden_size),
    ).to(device)
    optimizer = torch.optim.AdamW(link.parameters(), lr=args.lr)
    losses: list[float] = []
    for _ in range(max(1, args.steps)):
        optimizer.zero_grad(set_to_none=True)
        pred = link(source)
        loss = torch.nn.functional.mse_loss(pred, target)
        loss.backward()
        optimizer.step()
        losses.append(float(loss.detach().cpu()))

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": link.state_dict(),
            "hidden_size": hidden_size,
            "source_adapter": str(args.source_adapter),
            "target_adapter": str(args.target_adapter),
            "kind": "toy_pooled_hidden_to_reply_embedding",
        },
        out_dir / "link.pt",
    )
    report = {
        "kind": "toy_latent_link",
        "source_adapter": str(args.source_adapter),
        "target_adapter": str(args.target_adapter),
        "rows": len(rows),
        "hidden_size": hidden_size,
        "steps": args.steps,
        "initial_loss": losses[0],
        "final_loss": losses[-1],
        "loss_delta": losses[0] - losses[-1],
        "out_dir": str(out_dir),
        "notes": [
            "offline_experiment_only",
            "not_recursive_mas",
            "does_not_connect_live_reply_path",
        ],
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"rows={len(rows)}")
    print(f"hidden_size={hidden_size}")
    print(f"initial_loss={losses[0]:.6f}")
    print(f"final_loss={losses[-1]:.6f}")
    print(f"out_dir={out_dir}")
    print(f"report={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
