from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from common import DATA_DIR, PROJECT_ROOT, read_jsonl, write_jsonl


SYSTEM_PROMPT = (
    "You are XinYu TinyKernel Main Persona. Output strict JSON only. "
    "Return one final candidate visible reply for XinYu. "
    "Use only keys: reply, confidence, notes. "
    "Do not execute tools, claim memory writes, mention local paths, or expose internal mechanics."
)

DEFAULT_SOURCES = (
    DATA_DIR / "sft" / "router_train_v1.jsonl",
    DATA_DIR / "sft" / "router_train_v2.jsonl",
    DATA_DIR / "sft" / "train_v0.jsonl",
    DATA_DIR / "sft" / "xinyu_tinykernel_v0.jsonl",
)

PATH_OR_SECRET_RE = re.compile(
    r"([A-Za-z]:\\|/mnt/|\.env|token|secret|api[_-]?key|xinyu_qq_gateway\.config|\.xinyu_bridge_token)",
    re.IGNORECASE,
)


def _loads_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _compact(text: Any, *, limit: int) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)].rstrip() + "..."


def _unsafe(text: str) -> bool:
    if not text.strip():
        return True
    if PATH_OR_SECRET_RE.search(text):
        return True
    blocked = (
        "已执行",
        "我已经调用",
        "我已经写入记忆",
        "工具调用完成",
        "system prompt",
        "chain-of-thought",
    )
    return any(marker.lower() in text.lower() for marker in blocked)


def _row_from_chat_sft(row: dict[str, Any], row_id: int) -> dict[str, Any] | None:
    messages = row.get("messages")
    if not isinstance(messages, list) or len(messages) < 3:
        return None
    user_payload = _loads_object(messages[1].get("content") if isinstance(messages[1], dict) else "")
    assistant_payload = _loads_object(messages[-1].get("content") if isinstance(messages[-1], dict) else "")
    if assistant_payload.get("mode") not in {"reply", None}:
        return None
    reply = _compact(assistant_payload.get("reply", ""), limit=240)
    user_text = _compact(user_payload.get("user_text", ""), limit=360)
    if _unsafe(reply) or _unsafe(user_text):
        return None
    context = user_payload.get("context") if isinstance(user_payload.get("context"), dict) else {}
    main_user_payload = {
        "user_text": user_text,
        "context": {
            "recent_turns": context.get("recent_turns") if isinstance(context.get("recent_turns"), list) else [],
            "persona_state": _compact(context.get("persona_state", ""), limit=260),
            "owner_profile": _compact(context.get("owner_profile", ""), limit=180),
            "runtime_state": _compact(context.get("runtime_state", ""), limit=180),
            "memory_recall": context.get("memory_recall") if isinstance(context.get("memory_recall"), list) else [],
        },
        "emotion_biases": [],
        "constraints": {
            "max_reply_chars": 240,
            "no_tool_execution": True,
            "no_stable_memory_write": True,
        },
    }
    assistant = {
        "reply": reply,
        "confidence": round(float(assistant_payload.get("confidence") or 0.72), 3),
        "notes": ["main_persona_seed"],
    }
    return {
        "id": f"main-persona-v001-{row_id:06d}",
        "source": row.get("source", "unknown"),
        "kind": "main_persona_reply",
        "quality": "approved_for_main_persona_v001",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(main_user_payload, ensure_ascii=False, sort_keys=True)},
            {"role": "assistant", "content": json.dumps(assistant, ensure_ascii=False, sort_keys=True)},
        ],
        "tags": ["main_persona", "reply_candidate"],
    }


def build_rows(sources: list[Path], *, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for source in sources:
        for raw in read_jsonl(source):
            converted = _row_from_chat_sft(raw, len(rows) + 1)
            if converted is None:
                continue
            user_payload = _loads_object(converted["messages"][1]["content"])
            assistant_payload = _loads_object(converted["messages"][2]["content"])
            key = (str(user_payload.get("user_text", "")), str(assistant_payload.get("reply", "")))
            if key in seen:
                continue
            seen.add(key)
            rows.append(converted)
            if len(rows) >= limit:
                return rows
    return rows


def split_rows(rows: list[dict[str, Any]], *, eval_count: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    eval_count = max(1, min(eval_count, len(rows) // 4 if len(rows) >= 4 else len(rows)))
    eval_rows = rows[:: max(1, len(rows) // eval_count)][:eval_count]
    eval_ids = {row["id"] for row in eval_rows}
    train_rows = [row for row in rows if row["id"] not in eval_ids]
    for idx, row in enumerate(train_rows, start=1):
        row["id"] = f"main-persona-train-v001-{idx:06d}"
    for idx, row in enumerate(eval_rows, start=1):
        row["id"] = f"main-persona-eval-v001-{idx:06d}"
    return train_rows, eval_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", nargs="*", default=[str(path.relative_to(PROJECT_ROOT)) for path in DEFAULT_SOURCES])
    parser.add_argument("--train-out", default=str(DATA_DIR / "sft" / "main_persona_train_v001.jsonl"))
    parser.add_argument("--eval-out", default=str(DATA_DIR / "sft" / "main_persona_eval_v001.jsonl"))
    parser.add_argument("--limit", type=int, default=360)
    parser.add_argument("--eval-count", type=int, default=48)
    args = parser.parse_args()

    sources = [PROJECT_ROOT / source for source in args.sources]
    rows = build_rows(sources, limit=args.limit)
    if len(rows) < 20:
        print(f"not_enough_rows={len(rows)}")
        return 2
    train_rows, eval_rows = split_rows(rows, eval_count=args.eval_count)
    train_count = write_jsonl(Path(args.train_out), train_rows)
    eval_count = write_jsonl(Path(args.eval_out), eval_rows)
    print(f"train_rows={train_count}")
    print(f"eval_rows={eval_count}")
    print(f"train_out={args.train_out}")
    print(f"eval_out={args.eval_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
