from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Run a repeatable plain-mode smoke conversation against Xinyu."
    )
    parser.add_argument("--message", default="你好，心玉。")
    parser.add_argument(
        "--message-file",
        default=None,
        help="Optional UTF-8 text file whose contents will be used as the message.",
    )
    parser.add_argument("--warmup-seconds", type=int, default=2)
    parser.add_argument("--reply-wait-seconds", type=int, default=20)
    parser.add_argument("--venv-path", default=".venv")
    args = parser.parse_args()
    message = args.message
    if args.message_file:
        message = Path(args.message_file).read_text(encoding="utf-8").strip()
        if not message:
            raise SystemExit(f"Message file is empty: {args.message_file}")

    xinyu_dir = Path(__file__).resolve().parent
    python_exe = xinyu_dir / args.venv_path / "Scripts" / "python.exe"
    launcher = xinyu_dir / "run_local_xinyu.py"

    if not python_exe.exists():
        raise SystemExit(f"Virtual environment Python not found: {python_exe}")

    proc = subprocess.Popen(
        [str(python_exe), str(launcher), "--mode", "plain", "--no-session"],
        cwd=str(xinyu_dir),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert proc.stdin is not None
    time.sleep(args.warmup_seconds)
    proc.stdin.write(message + "\n")
    proc.stdin.flush()

    time.sleep(args.reply_wait_seconds)
    if proc.poll() is None:
        try:
            proc.stdin.write("/exit\n")
            proc.stdin.flush()
        except OSError:
            pass

    try:
        stdout, stderr = proc.communicate(timeout=120)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()

    print("=== RETURN CODE ===")
    print(proc.returncode)
    print("=== STDOUT ===")
    print(stdout)
    print("=== STDERR ===")
    print(stderr)

    log_dir = Path.home() / ".kohakuterrarium" / "logs"
    latest = max(log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, default=None)
    print("=== LATEST LOG ===")
    print(str(latest) if latest else "(none)")

    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
