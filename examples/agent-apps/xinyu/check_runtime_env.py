from __future__ import annotations

import importlib
import os
import shutil
import sys
from pathlib import Path


def check_command(name: str) -> tuple[bool, str]:
    path = shutil.which(name)
    return (path is not None, path or "")


def check_module(name: str) -> tuple[bool, str]:
    try:
        mod = importlib.import_module(name)
        return True, getattr(mod, "__file__", "<built-in>")
    except Exception as e:
        return False, str(e)


def check_file(path: Path) -> tuple[bool, str]:
    return path.exists(), str(path)



def read_local_env_flags(path: Path) -> tuple[bool, bool]:
    """Return whether local env file contains key/base URL without revealing values."""
    if not path.exists():
        return False, False
    has_key = False
    has_base_url = False
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key == "XINYU_API_KEY" and value:
            has_key = True
        elif key == "XINYU_BASE_URL" and value:
            has_base_url = True
    return has_key, has_base_url
def main() -> int:
    print("Xinyu runtime environment check")
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version.split()[0]}")

    overall_ok = True

    cmd_ok, cmd_info = check_command("kt")
    print(f"kt available: {cmd_ok} {cmd_info}")

    xinyu_dir = Path(__file__).resolve().parent
    repo_root = xinyu_dir.parents[2]
    src_root = repo_root / "src"
    run_launcher = xinyu_dir / "run_local_xinyu.py"
    local_env = xinyu_dir / "xinyu.local.env"
    local_env_example = xinyu_dir / "xinyu.local.env.example"
    reqs = xinyu_dir / "requirements-minimal.txt"
    bootstrap = xinyu_dir / "bootstrap_minimal_env.ps1"
    package_markers = [
        repo_root / "pyproject.toml",
        repo_root / "setup.py",
        repo_root / "setup.cfg",
    ]
    marker = next((p for p in package_markers if p.exists()), None)
    marker_ok = marker is not None
    print(f"Packaging metadata present: {marker_ok} {marker if marker_ok else ''}")

    src_ok, src_info = check_file(src_root)
    print(f"Local src tree present: {src_ok} {src_info}")
    overall_ok = overall_ok and src_ok

    launcher_ok, launcher_info = check_file(run_launcher)
    print(f"Local launcher present: {launcher_ok} {launcher_info}")
    overall_ok = overall_ok and launcher_ok

    reqs_ok, reqs_info = check_file(reqs)
    print(f"Minimal requirements file present: {reqs_ok} {reqs_info}")
    overall_ok = overall_ok and reqs_ok

    bootstrap_ok, bootstrap_info = check_file(bootstrap)
    print(f"Bootstrap script present: {bootstrap_ok} {bootstrap_info}")
    overall_ok = overall_ok and bootstrap_ok

    env_example_ok, env_example_info = check_file(local_env_example)
    print(f"Local env example present: {env_example_ok} {env_example_info}")
    overall_ok = overall_ok and env_example_ok

    dependency_modules = [
        "yaml",
        "jinja2",
        "aiofiles",
        "html2text",
        "openai",
        "httpx",
        "prompt_toolkit",
        "rich",
        "textual",
        "kohakuvault",
    ]
    deps_ok = True
    for mod_name in dependency_modules:
        mod_ok, mod_info = check_module(mod_name)
        print(f"Dependency {mod_name}: {mod_ok} {mod_info}")
        deps_ok = deps_ok and mod_ok

    xinyu_key = bool(os.environ.get("XINYU_API_KEY"))
    xinyu_base_url = os.environ.get("XINYU_BASE_URL", "")
    local_env_present = local_env.exists()
    local_env_has_key, local_env_has_base_url = read_local_env_flags(local_env)
    print(f"XINYU_API_KEY set in process: {xinyu_key}")
    print(f"XINYU_BASE_URL set in process: {bool(xinyu_base_url)}")
    print(f"xinyu.local.env present: {local_env_present}")
    print(f"xinyu.local.env has XINYU_API_KEY: {local_env_has_key}")
    print(f"xinyu.local.env has XINYU_BASE_URL: {local_env_has_base_url}")

    direct_runtime_ready = overall_ok and deps_ok
    if direct_runtime_ready:
        print("Runtime environment looks ready for local-source Xinyu execution.")
        if not xinyu_key and not local_env_has_key:
            print(
                "Runtime can start, but the first real conversation still needs "
                "XINYU_API_KEY, either from the process environment or "
                "from xinyu.local.env."
            )
        return 0

    print("Runtime environment is not fully ready yet.")
    if not marker_ok:
        print(
            "Note: repo packaging metadata is missing, so the supported path is "
            "local-source launch via run_local_xinyu.py rather than `kt` install."
        )
    if not deps_ok:
        print(
            "Next step: create a virtual environment and install "
            "requirements-minimal.txt."
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
