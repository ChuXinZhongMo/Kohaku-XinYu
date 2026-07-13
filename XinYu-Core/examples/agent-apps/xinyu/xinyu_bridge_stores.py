"""Consolidated thin persistence / environment accessors for the bridge.

Aggregates the former one-function ``xinyu_bridge_*_store`` shim modules.
Every function keeps its original public name and behavior; call sites only
change the module they import from. Grouped by domain below.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from state_service import append_jsonl, atomic_write_text
from state_service import read_text_safe as _read_text_safe


def _append_line(path: Path, line: str) -> bool:
    """Append a line to a file, creating parent dirs. False on any error."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)
    except Exception:
        return False
    return True


def read_text_safe(path: Path, default: str = "") -> str:
    return _read_text_safe(path, default=default)


# --- cli ---------------------------------------------------------------------
def read_bridge_cli_env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


# --- bootstrap ---------------------------------------------------------------
def bootstrap_env_file_exists(path: Path) -> bool:
    return Path(path).exists()


def read_bootstrap_env_file_lines(path: Path) -> list[str]:
    return Path(path).read_text(encoding="utf-8").splitlines()


def bootstrap_env_has_key(name: str) -> bool:
    return name in os.environ


def write_bootstrap_env(name: str, value: str) -> None:
    os.environ[name] = value


# --- prompt context ----------------------------------------------------------
@dataclass(frozen=True, slots=True)
class PromptContextFileSignature:
    mtime_ns: int
    size: int


def prompt_context_file_signature(path: Path) -> PromptContextFileSignature | None:
    try:
        stat = Path(path).stat()
    except OSError:
        return None
    return PromptContextFileSignature(mtime_ns=stat.st_mtime_ns, size=stat.st_size)


# --- desktop -----------------------------------------------------------------
def desktop_service_path_exists(path: Path) -> bool:
    return Path(path).exists()


def append_desktop_proactive_history_jsonl(path: Path, row: dict[str, Any]) -> None:
    append_jsonl(path, row)


def write_desktop_proactive_request_state_text(
    path: Path,
    text: str,
    *,
    final_newline: bool = True,
) -> None:
    atomic_write_text(path, text, final_newline=final_newline)


def read_desktop_self_action_json_dict(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def read_desktop_self_action_markdown_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return []


# --- private desktop ---------------------------------------------------------
def read_private_desktop_frame_bytes(path: Path) -> bytes:
    return Path(path).read_bytes()


def private_desktop_status_path_exists(path: Path) -> bool:
    return Path(path).exists()


def private_desktop_status_path_mtime(path: Path) -> float:
    return Path(path).stat().st_mtime


# --- promise -----------------------------------------------------------------
def write_promise_followup_state_text(path: Path, text: str) -> None:
    atomic_write_text(path, text)


def read_promise_owner_ids_env() -> str:
    return os.environ.get("XINYU_OWNER_USER_IDS", "")


def read_promise_owner_config_text(path: Path) -> str:
    return read_text_safe(path)


# --- renderer ----------------------------------------------------------------
def write_live_system_prompt_dump(root: Path, rel: Path, content: str) -> None:
    atomic_write_text(root / rel, content, final_newline=False)


# --- state text --------------------------------------------------------------
# (read_text_safe defined above is the shared accessor for this domain)


# --- external plugins --------------------------------------------------------
def append_external_plugin_trace(path: Path, row: dict[str, Any]) -> None:
    append_jsonl(path, row)


# --- learning ----------------------------------------------------------------
def read_learning_ingest_scope_env(name: str) -> str:
    return os.environ.get(name, "")


def resolve_learning_ingest_scope_root(text: str) -> Path:
    return Path(text).expanduser().resolve()


def append_codex_learning_followup_trace(path: Path, line: str) -> bool:
    return _append_line(path, line)


def codex_report_is_file(path: Path) -> bool:
    return path.is_file()


def codex_report_mtime(path: Path) -> float:
    return path.stat().st_mtime


def read_codex_report_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def read_codex_report_text_for_update(path: Path) -> tuple[bool, str]:
    try:
        return True, read_codex_report_text(path).rstrip()
    except OSError:
        return False, ""


def write_codex_report_text(path: Path, text: str) -> bool:
    try:
        path.write_text(text, encoding="utf-8")
    except OSError:
        return False
    return True


# --- proactive ---------------------------------------------------------------
def write_proactive_request_state_text(
    path: Path,
    text: str,
    *,
    final_newline: bool = True,
) -> None:
    atomic_write_text(path, text, final_newline=final_newline)


# --- autonomous --------------------------------------------------------------
def write_autonomous_state_text(path: Path, text: str) -> None:
    atomic_write_text(path, text)


def append_autonomous_trace_text(path: Path, line: str) -> bool:
    return _append_line(path, line)


# --- observation -------------------------------------------------------------
def observation_report_exists(path: Path) -> bool:
    return Path(path).exists()


def read_observation_report_text(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8-sig", errors="replace")


def read_observation_report_text_safe(path: Path, default: str = "") -> str:
    return read_text_safe(Path(path), default=default)


def write_observation_report_text(path: Path, text: str) -> None:
    atomic_write_text(Path(path), text)


# --- codex -------------------------------------------------------------------
def read_codex_presence_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def append_codex_background_trace(path: Path, line: str) -> bool:
    return _append_line(path, line)


# --- voice flags -------------------------------------------------------------
def read_voice_flag_env(name: str) -> str:
    return os.environ.get(name, "")


def write_voice_flag_env(name: str, value: str) -> None:
    os.environ[name] = value


def read_voice_flags_env_file_lines(path: Path) -> list[str]:
    path = Path(path)
    try:
        if not path.exists():
            return []
        return path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []


def write_voice_flags_env_file_lines(path: Path, lines: list[str]) -> None:
    atomic_write_text(Path(path), "\n".join(lines))
