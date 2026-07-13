from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Any, Callable

from xinyu_bridge_stores import (
    bootstrap_env_file_exists,
    bootstrap_env_has_key,
    read_bootstrap_env_file_lines,
    write_bootstrap_env,
)
from xinyu_runtime_security import enforce_llm_http_guard


def load_local_env(xinyu_dir: Path) -> None:
    env_path = xinyu_dir / "xinyu.local.env"
    if not bootstrap_env_file_exists(env_path):
        return

    for raw_line in read_bootstrap_env_file_lines(env_path):
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and not bootstrap_env_has_key(key):
            write_bootstrap_env(key, value)


def ensure_repo_src(xinyu_dir: Path) -> Path:
    repo_root = xinyu_dir.parents[2]
    src_root = repo_root / "src"
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))
    return src_root


def runtime_load_runtime(
    runtime: Any,
    *,
    chdir: Callable[[Path], Any] = os.chdir,
    load_local_env_func: Callable[[Path], Any] = load_local_env,
    enforce_llm_http_guard_func: Callable[[], Any] = enforce_llm_http_guard,
    ensure_repo_src_func: Callable[[Path], Any] = ensure_repo_src,
    import_module: Callable[[str], Any] = importlib.import_module,
) -> None:
    if runtime._loaded:
        return

    chdir(runtime.xinyu_dir)
    load_local_env_func(runtime.xinyu_dir)
    enforce_llm_http_guard_func()
    ensure_repo_src_func(runtime.xinyu_dir)

    agent_mod = import_module("xinyu_runtime.core.agent")
    events_mod = import_module("xinyu_runtime.core.events")

    runtime._agent_cls = agent_mod.Agent
    runtime._create_user_input_event = events_mod.create_user_input_event
    runtime._trigger_event_cls = events_mod.TriggerEvent
    runtime._loaded = True
