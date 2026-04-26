from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path


def snapshot_memory(root: Path) -> dict[str, tuple[int, int]]:
    memory = root / "memory"
    result: dict[str, tuple[int, int]] = {}
    for path in memory.rglob("*"):
        if not path.is_file():
            continue
        stat = path.stat()
        result[path.relative_to(memory).as_posix()] = (stat.st_mtime_ns, stat.st_size)
    return result


def request_json(url: str, *, payload: dict[str, str] | None = None, token: str = "") -> dict[str, object]:
    headers = {}
    data = None
    method = "GET"
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["X-XinYu-Bridge-Token"] = token
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
        method = "POST"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    root = Path(__file__).resolve().parent
    base_url = os.environ.get("XINYU_BRIDGE_BASE_URL", "http://127.0.0.1:8765").rstrip("/")
    token = os.environ.get("XINYU_BRIDGE_TOKEN", "")
    failures: list[str] = []

    before = snapshot_memory(root)
    health = request_json(f"{base_url}/health", token=token)
    before_sessions = int(health.get("sessions", -1))

    query = urllib.parse.urlencode({"text": "状态检查，只走 probe，不进记忆。"})
    get_probe = request_json(f"{base_url}/probe?{query}", token=token)
    post_probe = request_json(
        f"{base_url}/probe",
        payload={"text": "POST probe should not create session or memory."},
        token=token,
    )
    after_health = request_json(f"{base_url}/health", token=token)
    after = snapshot_memory(root)

    for label, result in (("GET", get_probe), ("POST", post_probe)):
        if result.get("probe") != "diagnostic_no_memory":
            failures.append(f"{label} probe missing diagnostic marker")
        if result.get("memory_changed") is not False:
            failures.append(f"{label} probe reported memory change")
        if result.get("session_created") is not False:
            failures.append(f"{label} probe created a session")
        notes = result.get("notes", [])
        if not isinstance(notes, list) or "no_agent_turn" not in notes:
            failures.append(f"{label} probe missing no_agent_turn note")

    after_sessions = int(after_health.get("sessions", -1))
    if after_sessions > before_sessions:
        failures.append("probe created bridge sessions")
    if before != after:
        changed = sorted(set(before) ^ set(after))
        shared_changed = [key for key in before.keys() & after.keys() if before[key] != after[key]]
        failures.append(f"probe changed memory files: {changed + shared_changed}")

    if failures:
        print("Bridge probe smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Bridge probe smoke passed")
    print(f"sessions: {before_sessions}->{after_sessions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
