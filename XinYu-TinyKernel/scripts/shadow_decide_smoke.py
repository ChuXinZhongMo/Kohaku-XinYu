from __future__ import annotations

import json
import urllib.request


def main() -> int:
    payload = {
        "turn_id": "shadow-smoke",
        "source": "local_test",
        "user_text": "use Codex check this project",
        "context": {"recent_turns": [], "persona_state": "", "owner_profile": "", "runtime_state": "", "memory_recall": []},
        "capabilities": {"codex_available": True, "external_api_available": False, "local_tools_available": True},
        "constraints": {"max_reply_chars": 240, "allow_tool_request": True, "allow_memory_candidate": True},
    }
    req = urllib.request.Request(
        "http://127.0.0.1:8877/decide",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        body = json.loads(response.read().decode("utf-8"))
    print(json.dumps(body, ensure_ascii=False, sort_keys=True))
    return 0 if body.get("mode") == "codex_delegate" else 1


if __name__ == "__main__":
    raise SystemExit(main())
