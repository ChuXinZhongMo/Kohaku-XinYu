from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path


AUTONOMOUS_VOLATILE_MEMORY_PATTERNS = (
    "context/autonomous_mind_loop_",
    "context/desktop_thoughts_",
    "context/thought_seeds.md",
    "context/initiative_state.md",
    "knowledge/outward_source_",
    "knowledge/source_materials.md",
    "knowledge/source_notes.md",
    "knowledge/source_reliability_state.md",
)

ALWAYS_VOLATILE_MEMORY_PATTERNS = (
    "context/qq_outbox_",
)


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


def bridge_token(root: Path, *, base_url: str = "http://127.0.0.1:8765") -> str:
    token = os.environ.get("XINYU_BRIDGE_TOKEN", "").strip()
    if token:
        return token
    port = urllib.parse.urlparse(base_url).port or 8765
    token = _running_bridge_token(port)
    if token:
        return token
    for token_path in (root / ".xinyu_bridge_token", root.parents[3] / ".xinyu_bridge_token"):
        if not token_path.exists():
            continue
        token = token_path.read_text(encoding="ascii", errors="ignore").strip()
        if token:
            return token
    return ""


def _running_bridge_token(port: int = 8765) -> str:
    if os.name != "nt":
        return ""
    command = (
        f"$listen = Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue | "
        "Select-Object -First 1; "
        "$listenPid = if ($listen) { $listen.OwningProcess } else { $null }; "
        "$p = if ($listenPid) { "
        "Get-CimInstance Win32_Process -Filter \"ProcessId = $listenPid\" "
        "} else { "
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'xinyu_core_bridge\\.py' } | "
        "Select-Object -First 1 "
        "}; "
        "$p = $p | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'xinyu_core_bridge\\.py' } | "
        "Select-Object -First 1 -ExpandProperty CommandLine; "
        "if ($p) { $p }"
    )
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if completed.returncode != 0:
        return ""
    match = re.search(r"--bridge-token\s+(\S+)", completed.stdout)
    return match.group(1).strip() if match else ""


def changed_memory_files(
    before: dict[str, tuple[int, int]],
    after: dict[str, tuple[int, int]],
) -> list[str]:
    changed = sorted(set(before) ^ set(after))
    changed.extend(sorted(key for key in before.keys() & after.keys() if before[key] != after[key]))
    return changed


def autonomous_run_changed(before_health: dict[str, object], after_health: dict[str, object]) -> bool:
    before = before_health.get("autonomous_maintenance")
    after = after_health.get("autonomous_maintenance")
    if not isinstance(before, dict) or not isinstance(after, dict):
        return False
    return (
        before.get("run_count") != after.get("run_count")
        or before.get("last_success_at") != after.get("last_success_at")
        or before.get("last_started_at") != after.get("last_started_at")
    )


def is_autonomous_volatile(rel_path: str) -> bool:
    return any(rel_path.startswith(pattern) or rel_path == pattern for pattern in AUTONOMOUS_VOLATILE_MEMORY_PATTERNS)


def is_always_volatile(rel_path: str) -> bool:
    return any(rel_path.startswith(pattern) or rel_path == pattern for pattern in ALWAYS_VOLATILE_MEMORY_PATTERNS)


def main() -> int:
    root = Path(__file__).resolve().parent
    base_url = os.environ.get("XINYU_BRIDGE_BASE_URL", "http://127.0.0.1:8765").rstrip("/")
    token = bridge_token(root, base_url=base_url)
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
    changed_files = changed_memory_files(before, after)
    if changed_files:
        changed_files = [path for path in changed_files if not is_always_volatile(path)]
        if autonomous_run_changed(health, after_health):
            changed_files = [path for path in changed_files if not is_autonomous_volatile(path)]
        if changed_files:
            failures.append(f"probe changed memory files: {changed_files}")

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
