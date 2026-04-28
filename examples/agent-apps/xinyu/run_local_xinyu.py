from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path

from xinyu_runtime_security import enforce_llm_http_guard


def _load_local_env(xinyu_dir: Path) -> None:
    env_path = xinyu_dir / "xinyu.local.env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _load_run_module(repo_root: Path):
    src_root = repo_root / "src"
    run_path = src_root / "kohakuterrarium" / "cli" / "run.py"
    if not run_path.exists():
        raise FileNotFoundError(f"CLI run entry not found: {run_path}")

    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))

    spec = importlib.util.spec_from_file_location("xinyu_local_cli_run", run_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to create import spec for: {run_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_local_xinyu.py",
        description="Run Xinyu from local KohakuTerrarium source without package install.",
    )
    parser.add_argument(
        "--mode",
        choices=["cli", "plain", "tui"],
        default="cli",
        help="Interactive mode passed to KohakuTerrarium run_agent_cli().",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
    )
    parser.add_argument(
        "--log-stderr",
        choices=["auto", "on", "off"],
        default="auto",
    )
    parser.add_argument(
        "--llm",
        default=None,
        help="Optional model/profile override.",
    )
    parser.add_argument(
        "--session",
        nargs="?",
        const="__auto__",
        default="__auto__",
        help="Session file path or auto session when omitted.",
    )
    parser.add_argument(
        "--no-session",
        action="store_true",
        help="Disable session persistence for this run.",
    )
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = _build_parser()
    args = parser.parse_args()

    xinyu_dir = Path(__file__).resolve().parent
    _load_local_env(xinyu_dir)
    enforce_llm_http_guard()
    os.chdir(xinyu_dir)
    repo_root = xinyu_dir.parents[2]
    run_mod = _load_run_module(repo_root)

    session = None if args.no_session else args.session
    return run_mod.run_agent_cli(
        str(xinyu_dir),
        log_level=args.log_level,
        session=session,
        io_mode=args.mode,
        llm_override=args.llm,
        log_stderr=args.log_stderr,
    )


if __name__ == "__main__":
    raise SystemExit(main())
