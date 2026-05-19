from __future__ import annotations

import argparse
import json
import urllib.request


def request_json(url: str, payload: dict[str, object] | None = None) -> dict[str, object]:
    if payload is None:
        with urllib.request.urlopen(url, timeout=5) as response:
            value = json.loads(response.read().decode("utf-8"))
            return value if isinstance(value, dict) else {}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        value = json.loads(response.read().decode("utf-8"))
        return value if isinstance(value, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8877")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    failures: list[str] = []

    health = request_json(f"{base}/health")
    if not health.get("ok"):
        failures.append("health_not_ok")

    cases = [
        ("codex", "use Codex check this project", "codex_delegate"),
        ("negative", "不要开 Codex，我只是问想法", "reply"),
        ("api", "没有 API 了怎么办", "local_only_limitation"),
        ("memory", "我想把本地小模型作为 XinYu 的内核", "memory_candidate"),
    ]
    last_decision = ""
    for case_id, text, expected in cases:
        output = request_json(
            f"{base}/decide",
            {
                "turn_id": f"http-smoke-{case_id}",
                "source": "local_test",
                "user_text": text,
                "context": {"recent_turns": [], "persona_state": "", "owner_profile": "", "runtime_state": "", "memory_recall": []},
                "capabilities": {"codex_available": True, "external_api_available": False, "local_tools_available": True},
                "constraints": {"max_reply_chars": 240, "allow_tool_request": True, "allow_memory_candidate": True},
            },
        )
        last_decision = str(output.get("decision_id", last_decision))
        if output.get("mode") != expected:
            failures.append(f"{case_id}:expected={expected}:actual={output.get('mode')}")

    feedback = request_json(
        f"{base}/feedback",
        {"turn_id": "http-smoke-feedback", "decision_id": last_decision, "accepted": True, "owner_feedback": "smoke_ok"},
    )
    if not feedback.get("stored"):
        failures.append("feedback_not_stored")

    print("health=" + json.dumps(health, ensure_ascii=False, sort_keys=True))
    print("feedback=" + json.dumps(feedback, ensure_ascii=False, sort_keys=True))
    if failures:
        for failure in failures:
            print("FAIL " + failure)
        return 1
    print("http_smoke_ok=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
