from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from schemas import INNER_SYSTEM_SCHEMA, VALID_EMOTION_LENSES, VALID_MODES, normalize_inner_system


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


def _validate_messages(row: dict[str, Any], line_no: int, failures: list[str]) -> list[dict[str, Any]] | None:
    messages = row.get("messages")
    if not isinstance(messages, list) or len(messages) != 3:
        failures.append(f"line {line_no}: expected 3 messages")
        return None
    for idx, message in enumerate(messages):
        if not isinstance(message, dict):
            failures.append(f"line {line_no}: message {idx} is not an object")
            return None
        if message.get("role") not in {"system", "user", "assistant"}:
            failures.append(f"line {line_no}: message {idx} has invalid role")
            return None
        if not isinstance(message.get("content"), str) or not str(message.get("content")).strip():
            failures.append(f"line {line_no}: message {idx} has empty content")
            return None
    return messages


def _validate_inner_system(assistant: dict[str, Any], line_no: int, failures: list[str]) -> tuple[str, str] | None:
    inner = normalize_inner_system(assistant)
    if inner is None:
        failures.append(f"line {line_no}: invalid {INNER_SYSTEM_SCHEMA}")
        return None
    mode = str(inner.get("action_tendency", {}).get("mode") or "")
    autonomy = inner.get("autonomy", {})
    external_action = mode in {"codex_delegate", "status_probe", "memory_candidate"} or bool(
        inner.get("action_tendency", {}).get("tool_request")
    )
    if external_action and not bool(autonomy.get("requires_owner_approval", True)):
        failures.append(f"line {line_no}: external action must require owner approval")
        return None
    return (INNER_SYSTEM_SCHEMA, mode)


def _validate_router_decision(assistant: dict[str, Any], line_no: int, failures: list[str]) -> tuple[str, str] | None:
    mode = assistant.get("mode")
    if mode not in VALID_MODES:
        failures.append(f"line {line_no}: invalid mode {mode!r}")
        return None
    required = {"mode", "reply", "tool_request", "memory_candidates", "confidence"}
    missing = required - set(assistant)
    if missing:
        failures.append(f"line {line_no}: missing router keys {sorted(missing)!r}")
        return None
    if not isinstance(assistant.get("memory_candidates"), list):
        failures.append(f"line {line_no}: memory_candidates must be a list")
        return None
    return ("router_decision", str(mode))


def _validate_main_persona(assistant: dict[str, Any], line_no: int, failures: list[str]) -> tuple[str, str] | None:
    reply = str(assistant.get("reply", "") or "").strip()
    if not reply:
        failures.append(f"line {line_no}: empty main persona reply")
        return None
    extra = set(assistant) - {"reply", "confidence", "notes"}
    if extra:
        failures.append(f"line {line_no}: unexpected main persona keys {sorted(extra)!r}")
        return None
    return ("main_persona_reply", "reply")


def _validate_emotion_bias(assistant: dict[str, Any], line_no: int, failures: list[str]) -> tuple[str, str] | None:
    lens = str(assistant.get("lens", "") or "").strip()
    reply_bias = str(assistant.get("reply_bias", "") or "").strip()
    if lens not in VALID_EMOTION_LENSES:
        failures.append(f"line {line_no}: invalid emotion lens {lens!r}")
        return None
    extra = set(assistant) - {"lens", "activation", "reply_bias", "risk_flags", "confidence", "evidence"}
    if extra:
        failures.append(f"line {line_no}: unexpected emotion bias keys {sorted(extra)!r}")
        return None
    if not reply_bias:
        failures.append(f"line {line_no}: empty emotion reply_bias")
        return None
    return (f"emotion_bias:{lens}", lens)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    args = parser.parse_args()
    path = Path(args.path)
    failures: list[str] = []
    count = 0
    modes: dict[str, int] = {}
    schemas: dict[str, int] = {}

    with path.open("r", encoding="utf-8-sig") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            count += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                failures.append(f"line {line_no}: invalid JSON: {exc}")
                continue
            messages = _validate_messages(row, line_no, failures)
            if messages is None:
                continue
            assistant = _loads_object(messages[2]["content"])
            if not assistant:
                failures.append(f"line {line_no}: assistant content not JSON object")
                continue

            result: tuple[str, str] | None
            if assistant.get("schema") == INNER_SYSTEM_SCHEMA:
                result = _validate_inner_system(assistant, line_no, failures)
            elif "mode" in assistant:
                result = _validate_router_decision(assistant, line_no, failures)
            elif "reply" in assistant:
                result = _validate_main_persona(assistant, line_no, failures)
            elif "lens" in assistant:
                result = _validate_emotion_bias(assistant, line_no, failures)
            else:
                failures.append(f"line {line_no}: assistant content has no known schema")
                continue

            if result is None:
                continue
            schema_name, mode_name = result
            schemas[schema_name] = schemas.get(schema_name, 0) + 1
            modes[mode_name] = modes.get(mode_name, 0) + 1

    print(f"rows={count}")
    print("schemas=" + json.dumps(schemas, ensure_ascii=False, sort_keys=True))
    print("modes=" + json.dumps(modes, ensure_ascii=False, sort_keys=True))
    if failures:
        for failure in failures[:30]:
            print("FAIL " + failure)
        print(f"failure_count={len(failures)}")
        return 1
    print("validation_ok=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
