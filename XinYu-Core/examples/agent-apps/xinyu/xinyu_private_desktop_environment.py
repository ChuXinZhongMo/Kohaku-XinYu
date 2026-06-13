"""XinYu Private Desktop — Phase 0 environment probe.

READ-ONLY. Detects whether a viable ISOLATED desktop backend exists on this
machine (Docker / WSL2 / Hyper-V / Windows Sandbox), whether loopback binding
works, and whether noVNC/websockify is present. It installs nothing and changes
no configuration.

Hard rule (see CLAUDE-TASK-XINYU-ISOLATED-DESKTOP-CONTROL-2026-06-03.md): if no
isolated backend exists, the caller must report blocked and stop. It must never
fall back to controlling / capturing the owner's host Windows desktop.
"""
from __future__ import annotations

import argparse
import json
import shutil
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROBE_VERSION = 1

# Candidate loopback ports a future isolated desktop would use (VNC + noVNC).
CANDIDATE_PORTS = (5900, 5901, 6080, 6081)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _service_state(name: str) -> str:
    """Return a Windows service state without hanging. 'absent' if not found."""
    if sys.platform != "win32":
        return "not_windows"
    try:
        proc = subprocess.run(
            ["sc", "query", name],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return "query_failed"
    out = (proc.stdout or "") + (proc.stderr or "")
    if "FAILED 1060" in out or "does not exist" in out.lower():
        return "absent"
    for token in ("RUNNING", "STOPPED", "START_PENDING", "STOP_PENDING", "PAUSED"):
        if token in out:
            return token.lower()
    return "unknown" if proc.returncode == 0 else "absent"


def _service_present(name: str) -> bool:
    return _service_state(name) not in {"absent", "query_failed", "not_windows"}


def _module_available(name: str) -> bool:
    import importlib.util

    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _loopback_bind_ok() -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", 0))
        return True
    except OSError:
        return False


def _port_free(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False


def probe_docker() -> dict[str, Any]:
    cli = shutil.which("docker") or ""
    service = _service_state("com.docker.service")
    engine_ok = False
    server_version = ""
    error = ""
    if cli:
        try:
            proc = subprocess.run(
                [cli, "info", "--format", "{{json .ServerVersion}}"],
                capture_output=True,
                text=True,
                timeout=20,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if proc.returncode == 0:
                server_version = (proc.stdout or "").strip().strip('"')
                engine_ok = bool(server_version)
            else:
                error = ((proc.stderr or proc.stdout or "docker_info_failed").strip())[:240]
        except (OSError, subprocess.SubprocessError) as exc:
            error = f"docker_info_error:{type(exc).__name__}"
    usable = bool(cli) and engine_ok
    return {
        "cli_present": bool(cli),
        "service_state": service,
        "engine_ok": engine_ok,
        "server_version": server_version,
        "usable": usable,
        "error": error,
    }


def probe_wsl() -> dict[str, Any]:
    launcher = bool(shutil.which("wsl"))
    # The wsl.exe launcher always exists on modern Windows even with no distro.
    # A functional WSL2 needs LxssManager + the Host Compute Service (vmcompute).
    lxss = _service_present("LxssManager")
    vmcompute = _service_present("vmcompute")
    usable = bool(launcher and lxss and vmcompute)
    return {
        "launcher_present": launcher,
        "lxss_manager_present": lxss,
        "vmcompute_present": vmcompute,
        "usable": usable,
        "note": "" if usable else "wsl2_not_installed_run_wsl_install_requires_admin_reboot",
    }


def probe_hyperv() -> dict[str, Any]:
    vmms = _service_state("vmms")
    vmcompute = _service_present("vmcompute")
    return {"vmms_state": vmms, "vmcompute_present": vmcompute, "usable": vmms == "running"}


def probe_windows_sandbox() -> dict[str, Any]:
    if sys.platform != "win32":
        return {"present": False}
    exe = Path(r"C:\Windows\System32\WindowsSandbox.exe")
    return {"present": exe.exists()}


def probe_novnc(root: Path) -> dict[str, Any]:
    workspace = root / "runtime/private_ecosystem/desktop_workspace"
    return {
        "websockify_module": _module_available("websockify"),
        "vncdotool_module": _module_available("vncdotool"),
        "novnc_dir_present": (workspace / "novnc").exists(),
    }


def probe_desktop_environment(root: Path | None = None) -> dict[str, Any]:
    root = Path(root) if root is not None else Path(__file__).resolve().parent
    docker = probe_docker()
    wsl = probe_wsl()
    hyperv = probe_hyperv()
    sandbox = probe_windows_sandbox()
    novnc = probe_novnc(root)

    backends_available: list[str] = []
    if docker["usable"]:
        backends_available.append("docker")
    if wsl["usable"]:
        backends_available.append("wsl2")
    if hyperv["usable"]:
        backends_available.append("hyperv")

    decision = "available" if backends_available else "blocked_no_isolated_backend"
    blocker = ""
    owner_action = ""
    if not backends_available:
        blocker = "no_isolated_desktop_backend_present (docker/wsl2/hyper-v all unavailable)"
        owner_action = (
            "Install Docker Desktop (WSL2 backend) OR run 'wsl --install' as admin then reboot; "
            "both require administrator rights, a reboot, and network access. The probe will not "
            "install anything and XinYu will not control the host Windows desktop instead."
        )

    return {
        "ok": True,
        "version": PROBE_VERSION,
        "probed_at": _now_iso(),
        "platform": sys.platform,
        "read_only": True,
        "installed_anything": False,
        "docker": docker,
        "wsl": wsl,
        "hyperv": hyperv,
        "windows_sandbox": sandbox,
        "novnc": novnc,
        "loopback_bind_ok": _loopback_bind_ok(),
        "free_candidate_ports": {str(p): _port_free(p) for p in CANDIDATE_PORTS},
        "backends_available": backends_available,
        "decision": decision,
        "blocker": blocker,
        "owner_action": owner_action,
        "boundaries": {
            "host_windows_desktop_controlled": False,
            "host_screen_captured": False,
            "owner_mouse_moved": False,
            "computer_control_enabled": False,
            "falls_back_to_host_automation": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only probe for a XinYu isolated desktop backend.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = probe_desktop_environment(args.root.resolve())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"decision={report['decision']} backends={report['backends_available'] or 'none'}")
        if report["blocker"]:
            print(f"blocker={report['blocker']}")
            print(f"owner_action={report['owner_action']}")
    # Exit 0 even when blocked: a clean, honest report is success for a probe.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
