"""F0 gate: does the coding model do native OpenAI tool-calling reliably?

The native coding capability assumes the coding model (mimo-v2.5-pro by default)
emits valid OpenAI `tool_calls`. This script checks that against the live
endpoint before you rely on it. Run it on the machine that has the real
XINYU_API_KEY / XINYU_BASE_URL:

    python f0_validate_tool_calling.py
    python f0_validate_tool_calling.py --model mimo-v2.5-pro --rounds 3

Exit code 0 = the model tool-called on every round (native mode is safe).
Non-zero = it did not; keep XINYU_NATIVE_CODING but expect the text-format
fallback to matter, or route coding to a different model via XINYU_CODING_MODEL.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_bash",
            "description": "Run a bash command on the host and return its stdout.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string", "description": "the command to run"}},
                "required": ["command"],
            },
        },
    }
]

PROMPT = "用 run_bash 工具执行 `echo hello` 并把输出告诉我。必须真正调用工具。"


def _coding_model() -> str:
    return os.environ.get("XINYU_CODING_MODEL", "").strip() or "mimo-v2.5-pro"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate native tool-calling for the coding model.")
    parser.add_argument("--model", default=_coding_model())
    parser.add_argument("--rounds", type=int, default=3)
    args = parser.parse_args(argv)

    base_url = os.environ.get("XINYU_BASE_URL", "").strip()
    api_key = os.environ.get("XINYU_API_KEY", "").strip()
    if not base_url or not api_key:
        print("FAIL: XINYU_BASE_URL / XINYU_API_KEY not set in environment.")
        return 2

    try:
        from openai import OpenAI
    except Exception as exc:
        print(f"FAIL: openai SDK not importable: {exc!r}")
        return 2

    client = OpenAI(base_url=base_url, api_key=api_key)
    tool_called = 0
    for i in range(1, args.rounds + 1):
        try:
            resp = client.chat.completions.create(
                model=args.model,
                messages=[{"role": "user", "content": PROMPT}],
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.2,
            )
            calls = resp.choices[0].message.tool_calls or []
            ok = bool(calls)
            args_ok = True
            for call in calls:
                try:
                    json.loads(call.function.arguments or "{}")
                except Exception:
                    args_ok = False
            print(f"round {i}: tool_calls={len(calls)} args_valid={args_ok}")
            if ok and args_ok:
                tool_called += 1
        except Exception as exc:
            print(f"round {i}: ERROR {exc!r}")

    print(f"\n{tool_called}/{args.rounds} rounds produced valid tool calls on model={args.model}")
    if tool_called == args.rounds:
        print("PASS: native tool-calling is reliable — XINYU_NATIVE_CODING native mode is safe.")
        return 0
    if tool_called == 0:
        print("FAIL: model never tool-called. Set XINYU_CODING_MODEL to a tool-capable model.")
        return 1
    print("PARTIAL: intermittent tool-calling. Consider a stronger XINYU_CODING_MODEL.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
