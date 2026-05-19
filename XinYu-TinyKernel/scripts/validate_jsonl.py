from __future__ import annotations

import argparse
import json
from pathlib import Path


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
            messages = row.get("messages")
            if not isinstance(messages, list) or len(messages) != 3:
                failures.append(f"line {line_no}: expected 3 messages")
                continue
            try:
                assistant = json.loads(messages[2]["content"])
            except (KeyError, TypeError, json.JSONDecodeError) as exc:
                failures.append(f"line {line_no}: assistant content not JSON: {exc}")
                continue
            if "mode" in assistant:
                mode = assistant.get("mode")
                if mode not in {"reply", "clarify", "wait", "codex_delegate", "status_probe", "memory_candidate", "local_only_limitation"}:
                    failures.append(f"line {line_no}: invalid mode {mode!r}")
                else:
                    modes[mode] = modes.get(mode, 0) + 1
                    schemas["router_decision"] = schemas.get("router_decision", 0) + 1
                continue
            if "reply" in assistant:
                reply = str(assistant.get("reply", "") or "").strip()
                if not reply:
                    failures.append(f"line {line_no}: empty main persona reply")
                    continue
                extra = set(assistant) - {"reply", "confidence", "notes"}
                if extra:
                    failures.append(f"line {line_no}: unexpected main persona keys {sorted(extra)!r}")
                    continue
                schemas["main_persona_reply"] = schemas.get("main_persona_reply", 0) + 1
                continue
            if "lens" in assistant:
                lens = str(assistant.get("lens", "") or "").strip()
                reply_bias = str(assistant.get("reply_bias", "") or "").strip()
                if lens not in {"attachment", "curiosity", "fatigue", "guardedness", "hurt", "irritation", "stability", "warmth"}:
                    failures.append(f"line {line_no}: invalid emotion lens {lens!r}")
                    continue
                extra = set(assistant) - {"lens", "activation", "reply_bias", "risk_flags", "confidence", "evidence"}
                if extra:
                    failures.append(f"line {line_no}: unexpected emotion bias keys {sorted(extra)!r}")
                    continue
                if not reply_bias:
                    failures.append(f"line {line_no}: empty emotion reply_bias")
                    continue
                schemas[f"emotion_bias:{lens}"] = schemas.get(f"emotion_bias:{lens}", 0) + 1
                continue
            failures.append(f"line {line_no}: assistant content has neither mode nor reply")
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
