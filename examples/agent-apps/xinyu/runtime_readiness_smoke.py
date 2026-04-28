from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class CommandResult:
    name: str
    command: list[str]
    exit_code: int
    log_path: str


SENSITIVE_PATTERNS = {
    "api_key_markers": re.compile(r"(?i)(sk-[a-z0-9_-]{12,}|api[_-]?key\s*=\s*[^\s#]+)"),
    "bridge_token_markers": re.compile(r"(?i)(xinyu[_-]?bridge[_-]?token\s*=\s*['\"]?[a-z0-9._~+/=-]{12,})"),
    "raw_long_numeric_ids": re.compile(r"\d{8,}"),
    "local_absolute_paths": re.compile(r"(?i)([a-z]:\\|/users/|/home/|\\\\)"),
}

SWEEP_RELS = [
    "DEPLOYMENT-STATUS-RUNBOOK.md",
    "RUNTIME-VALIDATION-NOTES.md",
    "VALIDATION-INDEX.md",
    "STATE-OF-XINYU.md",
    "IMPLEMENTATION-NEXT.md",
    "xinyu_status.py",
    "deployment_status_smoke.py",
    "xinyu_qq_gateway.py",
    "xinyu_qq_gateway.config.json",
]


def _python(root: Path) -> str:
    candidate = root / ".venv" / "Scripts" / "python.exe"
    return str(candidate if candidate.exists() else Path(sys.executable))


def _run(root: Path, log_dir: Path, name: str, command: list[str], timeout: int) -> CommandResult:
    completed = subprocess.run(
        command,
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    log_path = log_dir / f"{name}.log"
    log_path.write_text(
        "COMMAND: " + " ".join(command) + "\n"
        + f"EXIT_CODE: {completed.returncode}\n\n"
        + "=== STDOUT ===\n"
        + completed.stdout
        + "\n=== STDERR ===\n"
        + completed.stderr,
        encoding="utf-8",
    )
    return CommandResult(name=name, command=command, exit_code=completed.returncode, log_path=str(log_path))


def _sensitive_sweep(root: Path) -> dict[str, int]:
    repo_root = root.parents[2]
    counts = {name: 0 for name in SENSITIVE_PATTERNS}
    for rel in SWEEP_RELS:
        path = (repo_root / rel) if rel.startswith("integrations/") else (root / rel)
        if not path.exists() or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        for name, pattern in SENSITIVE_PATTERNS.items():
            counts[name] += len(pattern.findall(text))
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="One-command live XinYu runtime readiness gate.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--offline", action="store_true", help="Explicitly skip live QQ/NapCat/process checks.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=180)
    args = parser.parse_args()

    root = args.root.resolve()
    log_dir = root / "logs" / ("runtime_readiness_" + datetime.now().strftime("%Y%m%dT%H%M%S"))
    log_dir.mkdir(parents=True, exist_ok=True)
    py = _python(root)
    commands: list[tuple[str, list[str]]] = []
    if not args.offline:
        commands.extend(
            [
                ("deployment_status", [py, "deployment_status_smoke.py"]),
                ("bridge_probe", [py, "bridge_probe_smoke.py"]),
                ("session_cleanup", [py, "bridge_session_cleanup_smoke.py"]),
            ]
        )
    commands.extend(
        [
            ("mojibake_guard", [py, "mojibake_guard_smoke.py"]),
            ("long_run_status", [py, "long_run_status.py", "--require-no-residue"]),
        ]
    )

    results = [_run(root, log_dir, name, command, args.timeout_seconds) for name, command in commands]
    sweep_counts = _sensitive_sweep(root)
    failures = [item for item in results if item.exit_code != 0]
    if sweep_counts["api_key_markers"] or sweep_counts["bridge_token_markers"]:
        failures.append(
            CommandResult(
                name="sensitive_sweep",
                command=["redacted-sensitive-sweep"],
                exit_code=1,
                log_path=str(log_dir / "sensitive_sweep.log"),
            )
        )
    (log_dir / "sensitive_sweep.log").write_text(
        json.dumps({"counts": sweep_counts}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    output = {
        "ok": not failures,
        "offline": args.offline,
        "log_dir": str(log_dir),
        "commands": [item.__dict__ for item in results],
        "sensitive_sweep_counts": sweep_counts,
        "failures": [item.__dict__ for item in failures],
    }
    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print("runtime_readiness_smoke:", "ok" if not failures else "failed")
        print("offline:", args.offline)
        print("log_dir:", log_dir)
        print("sensitive_sweep_counts:", json.dumps(sweep_counts, ensure_ascii=False, sort_keys=True))
        for result in results:
            print(f"{'OK' if result.exit_code == 0 else 'FAIL'} {result.name}: exit={result.exit_code} log={result.log_path}")
        if failures:
            print("failures:")
            for failure in failures:
                print(
                    "- "
                    + failure.name
                    + " command="
                    + " ".join(failure.command)
                    + f" exit={failure.exit_code} log={failure.log_path}"
                )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
