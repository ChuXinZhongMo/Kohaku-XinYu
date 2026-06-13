from __future__ import annotations

import asyncio
import threading
from typing import Any

from xinyu_bridge_desktop_surface_state_store import LegacyRuntimeDesktopSurfaceStateStore


def reset_runtime_mutable_state(runtime: Any) -> None:
    runtime._codex_delegate_lock = asyncio.Lock()
    runtime._review_admin_lock = asyncio.Lock()
    runtime._desktop_event_stream_service = None
    runtime.desktop_event_bus = None
    runtime.desktop_ws_server = None
    runtime._desktop_recent_turns = []
    runtime._desktop_recent_memory_events = []
    runtime._desktop_surface_state_store = LegacyRuntimeDesktopSurfaceStateStore(runtime)
    runtime._desktop_proactive_inbox = {}
    runtime._desktop_proactive_history = []
    runtime._desktop_proactive_lock = threading.Lock()
    runtime._loaded = False
    runtime._closed = False
    runtime._agent_cls = None
    runtime._create_user_input_event = None
    runtime._trigger_event_cls = None
    runtime._autonomous_task = None
    runtime._metabolism_task = None
    runtime._metabolism_wakeup_event = None
    runtime._metabolism_in_progress = False
    runtime._metabolism_run_count = 0
    runtime._metabolism_last_started_at = ""
    runtime._metabolism_last_success_at = ""
    runtime._metabolism_last_error = ""
    runtime._metabolism_last_result = {}
    runtime._autonomous_in_progress = False
    runtime._autonomous_run_count = 0
    runtime._autonomous_failure_count = 0
    runtime._autonomous_last_started_at = ""
    runtime._autonomous_last_success_at = ""
    runtime._autonomous_last_error = ""
    runtime._autonomous_last_memory_changed = "unknown"
    runtime._autonomous_last_notes = []
    runtime._autonomous_next_run_at = ""
    runtime._v1_app = None
    runtime._v1_last_trace_id = ""
    runtime._v1_last_route = ""
    runtime._v1_last_error = ""
