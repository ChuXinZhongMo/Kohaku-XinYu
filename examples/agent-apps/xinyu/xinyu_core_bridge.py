from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from xinyu_async_exploration import (
    async_exploration_outbox_message,
    build_async_exploration_prompt_block,
    create_async_exploration_closure,
    parse_resume_instruction,
    update_async_exploration_from_codex,
)
from xinyu_bridge_http import XinYuBridgeHTTPServer, XinYuBridgeRequestHandler
from xinyu_bridge_learning import LearningBridgeError, ingest as learning_ingest_bridge, study as learning_study_bridge
from xinyu_bridge_observation import observe as learning_observe_bridge
from xinyu_bridge_proactive import acknowledge as proactive_ack_bridge, claim_or_preview as proactive_bridge
from xinyu_bridge_renderer import BridgeRenderer
from xinyu_codex_delegate import looks_like_codex_request, preview_codex_delegate_paths, run_codex_delegate
from xinyu_codex_dream_handoff import handoff_codex_to_dream
from xinyu_continuity_handoff import build_continuity_handoff_prompt_block, refresh_continuity_handoff
from xinyu_context_retrieval import log_recalled_context, retrieve_recalled_context
from xinyu_dialogue_curiosity import evaluate_previous_reaction, record_reply_prediction
from xinyu_dialogue_archive import archive_dialogue_turn, archive_message
from xinyu_dialogue_working_memory import (
    compact_tail_for_prompt,
    load_dialogue_tail,
    persisted_tail_entries,
    prompt_tail_entries,
    save_dialogue_tail,
    session_tail_entries,
)
from xinyu_expression_self_learning import record_expression_self_learning_event
from xinyu_interaction_journal import record_interaction_turn
from xinyu_learning_closed_loop import (
    build_learning_closed_loop_prompt_block,
    record_learning_closed_loop_self_thought,
    record_learning_closed_loop_turn,
)
from xinyu_life_posture import build_life_posture
from xinyu_life_month_slots import refresh_current_life_month_context  # noqa: F401 - compatibility for older tests/hooks
from xinyu_memory_candidate_extractor import extract_memory_candidates
from xinyu_memory_event_sourcing import record_chat_event
from xinyu_memory_self_review import run_memory_self_review
from xinyu_package_installer import install_python_packages
from xinyu_memory_weights import refresh_memory_weight_state  # noqa: F401 - compatibility for older tests/hooks
from xinyu_persona_state import observe_persona_turn
from xinyu_persona_runtime import build_persona_runtime_state
from xinyu_private_thought_events import record_private_thought_outcome, record_private_thought_reply_link
from xinyu_proactive_presence import acknowledge_proactive_qq_message, claim_proactive_qq_message
from xinyu_proactive_request_loop import run_proactive_request_loop
from xinyu_qq_outbox import ack_qq_outbox_message, claim_next_qq_outbox_message, enqueue_qq_outbox_message
from xinyu_recent_attachment_context import load_recent_attachment_context, record_recent_attachment_context
from xinyu_runtime_presence import (
    build_runtime_presence_prompt_block,
    record_bridge_heartbeat,
    record_codex_presence,
    record_turn_finished,
    record_turn_started,
    read_runtime_presence_summary,
)
from xinyu_runtime_security import enforce_bridge_token_guard, enforce_llm_http_guard
from xinyu_self_code_approval import (
    consume_self_code_approval,
    create_direct_self_code_approval,
    mark_self_code_execution_scheduled,
)
from xinyu_self_thought_loop import run_self_thought_loop
from xinyu_speech_controller import XinyuSpeechController
from xinyu_text_variants import readable_markers
from xinyu_turn_residue import read_turn_residue, write_turn_residue
from xinyu_turn_classifier import classify_visible_turn
from xinyu_uncertainty_pause import (
    build_uncertainty_pause_prompt_block,
    is_waiting_reply,
    mark_uncertainty_pause_replied,
    record_uncertainty_pause,
)
from xinyu_voice_learning import record_voice_correction
from xinyu_watched_sources import run_watched_source_check


BRIDGE_VERSION = "0.8.50"
CODEX_DEFAULT_TIMEOUT_SECONDS = 3600
CODEX_VISIBLE_WINDOW_TITLE = "Xinyu codex"

CODEX_DELEGATE_OPEN = "[[XINYU_CODEX_DELEGATE]]"
CODEX_DELEGATE_CLOSE = "[[/XINYU_CODEX_DELEGATE]]"
CODEX_DELEGATE_PATTERNS = (
    re.compile(
        r"\[\[XINYU_CODEX_DELEGATE\]\]\s*(?P<task>.*?)\s*\[\[/XINYU_CODEX_DELEGATE\]\]",
        re.S,
    ),
    re.compile(
        r"\[/codex\]\s*(?:@@task\s*=\s*)?(?P<task>.*?)\s*\[codex/\]",
        re.I | re.S,
    ),
)
WAIT_TO_THINK_PATTERNS = (
    re.compile(r"\[WAIT_TO_THINK(?::\s*(?P<task>[^\]]+))?\]", re.I),
    re.compile(
        r"\[\[XINYU_WAIT_TO_THINK\]\]\s*(?P<task>.*?)\s*\[\[/XINYU_WAIT_TO_THINK\]\]",
        re.I | re.S,
    ),
)

PROMISE_FOLLOWUP_STATE_REL = Path("memory/context/promise_followup_state.md")
PROMISE_FOLLOWUP_USER_MARKERS = (
    "自己查看",
    "自己看看",
    "自己看一下",
    "你得自己查看",
    "检查一下",
    "核查一下",
    "复查一下",
    "确认一下",
    "看完告诉我",
    "看完跟我说",
    "主动告诉我",
    "主动跟我说",
    "怎么知道你看没看",
    "怎么知道她看没看",
    "看没看",
    "怎么样了",
    "现在呢",
    "看了吗",
    "查了吗",
    "卡住",
    "还没回",
    "没回",
)
PROMISE_FOLLOWUP_REPLY_MARKERS = (
    "我再看看",
    "我再看",
    "我看看",
    "我看一下",
    "我去看看",
    "我去看",
    "我查一下",
    "我再查",
    "我去查",
    "我确认一下",
    "我再确认",
    "我回头看",
    "我想想",
)
PROMISE_FOLLOWUP_DONE_MARKERS = (
    "我看完了",
    "看完了",
    "我查完了",
    "查完了",
    "确认完了",
    "我确认了",
    "已经看",
    "已经查",
)
OWNER_DIRECT_CODEX_DELEGATE_MARKERS = (
    "用codex",
    "调用codex",
    "让codex",
    "交给codex",
    "找codex",
    "codex搜索",
    "codex查",
    "codex浏览",
    "codex联网",
    "codex学习",
    "codex研究",
)
OWNER_DIRECT_CODEX_SUPPORT_MARKERS = (
    "联网",
    "浏览网络",
    "搜索",
    "查一下",
    "查资料",
    "找资料",
    "学习",
    "研究",
    "想不通",
    "没办法",
    "自己想办法",
)
OWNER_DIRECT_CODEX_NEGATIVE_MARKERS = (
    "别用codex",
    "不要用codex",
    "不用codex",
    "先别用codex",
    "别调用codex",
    "不要调用codex",
)
OWNER_SELF_CODE_EDIT_GRANT_MARKERS = (
    "改你的代码",
    "更改你的代码",
    "修改你的代码",
    "改动你的代码",
    "改自己的代码",
    "修改自己的代码",
    "主动改代码",
    "主动尝试更改你的代码",
    "对你的代码进行改动",
    "改项目代码",
    "自我代码迭代",
    "自己动代码",
    "自己改项目",
    "主动修改代码",
    "主动更改代码",
)
OWNER_SELF_CODE_START_MARKERS = (
    "现在开始",
    "现在就开始",
    "可以现在开始",
    "可以现在就开始",
    "可以开始",
    "开始吧",
    "开始动手",
    "开始改",
    "直接开始",
    "那就开始",
    "权限给",
    "权限低",
)
OWNER_SELF_CODE_NEGATIVE_MARKERS = (
    "别改代码",
    "不要改代码",
    "先别改代码",
    "先别改",
    "别动代码",
    "不要动代码",
)
OWNER_SELF_CODE_GRANT_CUES = (
    "允许",
    "可以",
    "授权",
    "同意",
    "准许",
    "支持",
    "试试",
    "动手",
    "开始",
    "直接",
    "去",
    "给你",
    "都可以",
    "吧",
)

OWNER_SELF_CODE_EDIT_GRANT_MARKERS = (
    *OWNER_SELF_CODE_EDIT_GRANT_MARKERS,
    *readable_markers(
        "改你的代码",
        "修改你的代码",
        "更改你的代码",
        "改自己的代码",
        "修改自己的代码",
        "修改自身代码",
        "主动修改代码",
        "主动改代码",
        "自改代码",
        "自我代码修改",
        "自身代码",
        "所有代码",
        "modify your code",
        "edit your code",
        "change your own code",
        "self-code",
    ),
)
OWNER_SELF_CODE_START_MARKERS = (
    *OWNER_SELF_CODE_START_MARKERS,
    *readable_markers(
        "现在开始",
        "现在就开始",
        "开始吧",
        "开始改",
        "直接开始",
        "进行修改",
        "现在修改",
        "现在主动修改",
        "start now",
        "go ahead",
        "proceed",
    ),
)
OWNER_SELF_CODE_NEGATIVE_MARKERS = (
    *OWNER_SELF_CODE_NEGATIVE_MARKERS,
    *readable_markers(
        "别改代码",
        "不要改代码",
        "先别改代码",
        "别动代码",
        "不要动代码",
        "不要修改",
        "先别修改",
        "do not edit",
        "don't edit",
        "no code changes",
    ),
)
OWNER_SELF_CODE_GRANT_CUES = (
    *OWNER_SELF_CODE_GRANT_CUES,
    *readable_markers(
        "允许",
        "授权",
        "同意",
        "可以",
        "要求",
        "请",
        "希望",
        "现在",
        "开始",
        "直接",
        "进行",
        "动手",
        "go ahead",
        "approved",
        "approve",
        "authorized",
        "please",
    ),
)

PROMPT_CONTEXT_SIGNATURE_FILES: tuple[str, ...] = (
    "config.yaml",
    "prompts/system.md",
    "prompts/output.md",
    "prompts/live_voice_card.md",
    "memory/context/memory_weight_state.md",
    "memory/context/persona_surface_state.md",
    "memory/self/system_prompt_memory.md",
    "memory/self/core.md",
    "memory/self/personality_profile.md",
    "memory/context/persona_life_anchors.md",
    "memory/context/life_month_slots.md",
    "memory/context/current_life_month_context.md",
    "memory/self/mind_loop_policy.md",
    "memory/self/mind_loop_state.md",
    "memory/self/voice_profile_zh.md",
    "memory/self/voice_calibration_log.md",
    "memory/self/narrative.md",
    "memory/emotions/taxonomy.md",
    "memory/emotions/current_state.md",
    "memory/relationships/vector_model.md",
    "memory/relationships/index.md",
    "memory/people/index.md",
    "memory/people/owner.md",
    "memory/context/time_anchor.md",
    "memory/context/real_world_anchor_policy.md",
    "memory/context/real_life_input_adapter_policy.md",
    "memory/context/recent_context.md",
    "memory/context/watch_sources.md",
    "memory/context/watched_source_state.md",
    "memory/context/memory_self_review_state.md",
    "memory/context/continuity_handoff_state.md",
    "memory/context/uncertainty_pause_state.md",
    "memory/context/self_code_approval_state.md",
    "memory/context/initiative_policy.md",
    "memory/context/initiative_state.md",
    "memory/context/owner_permission_grants.md",
    "memory/context/codex_delegation_policy.md",
    "memory/context/runtime_bridge_state.md",
    "memory/context/maintenance_recommendations.md",
    "memory/context/maintenance_dispatch_state.md",
    "memory/context/inner_cycle_state.md",
    "memory/context/maintenance_schedule_state.md",
    "memory/dreams/dream_weight_state.md",
    "memory/archive/long_term_memory_gate_state.md",
    "memory/self/personality_change_state.md",
    "memory/self/personality_self_review_state.md",
    "memory/self/ai_self_iteration_state.md",
    "memory/self/ai_self_iteration_review_state.md",
    "memory/self/expression_self_learning_state.md",
    "memory/self/learning_closed_loop_state.md",
    "memory/self/learning_closed_loop_cases.md",
    "memory/knowledge/ai_domain.md",
    "memory/knowledge/social_inquiry_policy.md",
)

AUTONOMOUS_MAINTENANCE_PROMPT = (
    "Maintenance-only pass. This is a low-frequency maintenance pass from "
    "XinYu Core, not a human speaking turn. Refresh time anchor, runtime "
    "bridge state, inner cycle, desktop thoughts, continuity, slow reflection, "
    "memory consolidation, learning gates, and archive gates only when each "
    "subsystem is due. Do not initiate visible chat. If any outward text is "
    "unavoidable, output exactly [WAITING]."
)


class BridgeRequestError(RuntimeError):
    def __init__(self, status: HTTPStatus, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


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


def _ensure_repo_src(xinyu_dir: Path) -> Path:
    repo_root = xinyu_dir.parents[2]
    src_root = repo_root / "src"
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))
    return src_root


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _dedupe(values: list[str] | tuple[str, ...]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = _safe_str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _memory_snapshot(memory_root: Path) -> dict[str, tuple[int, int]]:
    if not memory_root.exists():
        return {}

    snapshot: dict[str, tuple[int, int]] = {}
    for path in memory_root.rglob("*"):
        if not path.is_file():
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        snapshot[path.relative_to(memory_root).as_posix()] = (
            stat.st_mtime_ns,
            stat.st_size,
        )
    return snapshot


def _normalize_reply(text: str) -> str:
    lines = [line.strip() for line in text.replace("\r\n", "\n").split("\n")]
    compact_lines: list[str] = []

    for line in lines:
        if not line.strip():
            continue
        compact_lines.append(line)

    if not compact_lines:
        return ""

    # QQ already wraps long bubbles. Model-authored line breaks make normal chat
    # look like formatted prose, so collapse visible replies into one paragraph.
    reply = compact_lines[0]
    for line in compact_lines[1:]:
        if reply and reply[-1].isascii() and line and line[0].isascii():
            reply += " " + line
        else:
            reply += line
    return reply.strip()


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    if value is None:
        return default
    return bool(value)


def _as_int(value: Any, default: int) -> int:
    if value is None:
        return default
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _as_str_set(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, (list, tuple, set)):
        raw_items = value
    else:
        raw_items = str(value).replace(";", ",").split(",")
    return {str(item).strip() for item in raw_items if str(item).strip()}


def _read_text_safe(path: Path) -> str:
    try:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def _state_field(text: str, field: str, default: str = "") -> str:
    match = re.search(rf"(?m)^-\s+{re.escape(field)}:\s*(.*)$", text or "")
    if not match:
        return default
    return re.sub(r"\s+", " ", match.group(1).strip()) or default


def _parse_iso(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _seconds_since_iso(value: str, *, default: float = 999999.0) -> float:
    parsed = _parse_iso(value)
    if parsed is None:
        return default
    return max(0.0, (datetime.now().astimezone() - parsed).total_seconds())


def _payload_path(value: str) -> Path:
    text = value.strip()
    if text.lower().startswith("file://"):
        parsed = urlparse(text)
        path_text = parsed.path
        if os.name == "nt" and len(path_text) > 2 and path_text[0] == "/" and path_text[2] == ":":
            path_text = path_text[1:]
        return Path(unquote(path_text))
    return Path(text)


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _run_learning_study_chain(root: Path, mode: str) -> dict[str, object]:
    custom_dir = Path(__file__).resolve().parent / "custom"
    if str(custom_dir) not in sys.path:
        sys.path.insert(0, str(custom_dir))

    from learner_integration_engine import run_learner_integration
    from learning_quality_engine import run_learning_quality
    from source_integration_gate_engine import run_source_integration_gate

    gate = run_source_integration_gate(root, mode=f"{mode}_source_gate")
    learner = run_learner_integration(root, mode=f"{mode}_learner")
    quality = run_learning_quality(root, mode=f"{mode}_quality")
    return {
        "source_integration_gate": gate,
        "learner_integration": learner,
        "learning_quality": quality,
    }


def _int_result(mapping: dict[str, object], key: str) -> int:
    try:
        return int(mapping.get(key, 0))
    except (TypeError, ValueError):
        return 0


def _should_run_learning_after_codex(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "学习",
            "学一下",
            "读一下",
            "阅读",
            "消化",
            "论文",
            "资料",
            "源码",
            "仓库",
        )
    )


class _NullInputModule:
    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def get_input(self) -> Any:
        await asyncio.sleep(3600)
        return None

    def set_user_commands(self, commands: dict[str, Any], context: Any) -> None:
        self._user_commands = commands
        self._user_command_context = context


@dataclass
class AgentSession:
    key: str
    agent: Any
    prompt_signature: str
    chunks: list[str] = field(default_factory=list)
    dialogue_tail: list[dict[str, str]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)


class XinYuBridgeRuntime:
    def __init__(
        self,
        *,
        xinyu_dir: Path,
        turn_timeout_seconds: int,
        max_text_chars: int,
        settle_seconds: float,
        outward_renderer: bool,
        renderer_mode: str = "off",
        render_timeout_seconds: int = 60,
        session_idle_ttl_seconds: int = 86400,
        max_sessions: int = 8,
        proactive_min_interval_seconds: int = 21600,
        autonomous_maintenance_enabled: bool = True,
        autonomous_maintenance_initial_delay_seconds: int = 60,
        autonomous_maintenance_interval_seconds: int = 1800,
        autonomous_maintenance_session_key: str = "xinyu:autonomous:maintenance",
    ) -> None:
        self.xinyu_dir = xinyu_dir
        self.memory_root = xinyu_dir / "memory"
        self.turn_timeout_seconds = turn_timeout_seconds
        self.max_text_chars = max_text_chars
        self.settle_seconds = settle_seconds
        self.outward_renderer = outward_renderer
        self.renderer_mode = self._normalize_renderer_mode(renderer_mode)
        self.render_timeout_seconds = render_timeout_seconds
        self.session_idle_ttl_seconds = session_idle_ttl_seconds
        self.dialogue_prompt_tail_entries = prompt_tail_entries()
        self.dialogue_session_tail_entries = session_tail_entries()
        self.dialogue_persisted_tail_entries = persisted_tail_entries()
        self.max_sessions = max_sessions
        self.proactive_min_interval_seconds = proactive_min_interval_seconds
        self.autonomous_maintenance_enabled = autonomous_maintenance_enabled
        self.autonomous_maintenance_initial_delay_seconds = max(0, autonomous_maintenance_initial_delay_seconds)
        self.autonomous_maintenance_interval_seconds = max(60, autonomous_maintenance_interval_seconds)
        self.autonomous_maintenance_session_key = autonomous_maintenance_session_key.strip() or "xinyu:autonomous:maintenance"
        self.v1_enabled = _as_bool(os.environ.get("XINYU_V1_ENABLED"), default=False)
        self.v1_shadow_mode = _as_bool(os.environ.get("XINYU_V1_SHADOW_MODE"), default=False)
        self.v1_shadow_timeout_seconds = max(1, _as_int(os.environ.get("XINYU_V1_SHADOW_TIMEOUT_SECONDS"), 3))
        self.v1_owner_user_ids = _as_str_set(os.environ.get("XINYU_OWNER_USER_IDS"))
        self.speech_controller = XinyuSpeechController(xinyu_dir)
        self.renderer = BridgeRenderer(
            xinyu_dir=xinyu_dir,
            speech_controller=self.speech_controller,
            renderer_mode=self.renderer_mode,
            render_timeout_seconds=self.render_timeout_seconds,
        )
        self._sessions: dict[str, AgentSession] = {}
        self._sessions_lock = asyncio.Lock()
        self._global_turn_lock = asyncio.Lock()
        self._codex_delegate_lock = asyncio.Lock()
        self._loaded = False
        self._closed = False
        self._agent_cls: Any = None
        self._create_user_input_event: Any = None
        self._trigger_event_cls: Any = None
        self._autonomous_task: asyncio.Task | None = None
        self._autonomous_in_progress = False
        self._autonomous_run_count = 0
        self._autonomous_failure_count = 0
        self._autonomous_last_started_at = ""
        self._autonomous_last_success_at = ""
        self._autonomous_last_error = ""
        self._autonomous_last_memory_changed = "unknown"
        self._autonomous_last_notes: list[str] = []
        self._autonomous_next_run_at = ""
        self._v1_app: Any = None
        self._v1_last_trace_id = ""
        self._v1_last_route = ""
        self._v1_last_error = ""
        record_bridge_heartbeat(
            self.xinyu_dir,
            reason="bridge_init",
            bridge_snapshot={
                "active_sessions": len(self._sessions),
                "autonomous_maintenance": "idle" if self.autonomous_maintenance_enabled else "disabled",
                "qq_outbox": "unknown",
            },
        )

    def _load_runtime(self) -> None:
        if self._loaded:
            return

        os.chdir(self.xinyu_dir)
        _load_local_env(self.xinyu_dir)
        enforce_llm_http_guard()
        _ensure_repo_src(self.xinyu_dir)

        from kohakuterrarium.core.agent import Agent
        from kohakuterrarium.core.events import TriggerEvent, create_user_input_event

        self._agent_cls = Agent
        self._create_user_input_event = create_user_input_event
        self._trigger_event_cls = TriggerEvent
        self._loaded = True

    def health_snapshot(self) -> dict[str, Any]:
        runtime_presence = read_runtime_presence_summary(self.xinyu_dir)
        return {
            "ok": True,
            "bridge": "xinyu_core_bridge",
            "version": BRIDGE_VERSION,
            "xinyu_dir": str(self.xinyu_dir),
            "memory_root": str(self.memory_root),
            "sessions": len(self._sessions),
            "turn_timeout_seconds": self.turn_timeout_seconds,
            "outward_renderer": self.outward_renderer,
            "renderer_mode": self.renderer_mode,
            "render_timeout_seconds": self.render_timeout_seconds,
            "session_idle_ttl_seconds": self.session_idle_ttl_seconds,
            "max_sessions": self.max_sessions,
            "dialogue_memory": {
                "prompt_tail_entries": self.dialogue_prompt_tail_entries,
                "session_tail_entries": self.dialogue_session_tail_entries,
                "persisted_tail_entries": self.dialogue_persisted_tail_entries,
            },
            "proactive_min_interval_seconds": self.proactive_min_interval_seconds,
            "autonomous_maintenance": self._autonomous_maintenance_health(),
            "runtime_presence": runtime_presence,
            "program_awareness": runtime_presence.get("program_awareness", {}),
            "v1": self._v1_health(),
            "closed": self._closed,
        }

    async def health(self) -> dict[str, Any]:
        return self.health_snapshot()

    def _v1_health(self) -> dict[str, Any]:
        return {
            "enabled": self.v1_enabled,
            "shadow_mode": self.v1_shadow_mode,
            "shadow_timeout_seconds": self.v1_shadow_timeout_seconds,
            "owner_user_ids_configured": len(self.v1_owner_user_ids),
            "loaded": self._v1_app is not None,
            "last_trace_id": self._v1_last_trace_id,
            "last_route": self._v1_last_route,
            "last_error": self._v1_last_error,
        }

    def _ensure_v1_app(self) -> Any:
        if self._v1_app is not None:
            return self._v1_app
        from xinyu_v1.app import XinYuV1App
        from xinyu_v1.config import XinYuV1Config

        self._v1_app = XinYuV1App(XinYuV1Config.load(self.xinyu_dir))
        return self._v1_app

    async def _run_v1_shadow(self, payload: dict[str, Any], *, text: str) -> dict[str, Any]:
        if not self.v1_shadow_mode:
            return {"notes": []}
        started = time.monotonic()
        try:
            app = self._ensure_v1_app()
            shadow_payload = dict(payload)
            shadow_payload.setdefault("text", text)
            metadata = shadow_payload.get("metadata")
            shadow_payload["metadata"] = dict(metadata) if isinstance(metadata, dict) else {}
            shadow_payload["metadata"]["v1_shadow_source"] = "xinyu_core_bridge"
            user_id = _safe_str(shadow_payload.get("user_id")).strip()
            if user_id and user_id in self.v1_owner_user_ids:
                shadow_payload["metadata"]["is_owner_user"] = True
            reply = await asyncio.wait_for(
                app.shadow_payload(shadow_payload),
                timeout=self.v1_shadow_timeout_seconds,
            )
            elapsed_ms = int((time.monotonic() - started) * 1000)
            self._v1_last_error = ""
            self._v1_last_trace_id = reply.trace_id
            self._v1_last_route = reply.route
            return {
                "accepted": reply.accepted,
                "route": reply.route,
                "trace_id": reply.trace_id,
                "elapsed_ms": elapsed_ms,
                "notes": [
                    f"v1_shadow_route:{reply.route or 'unknown'}",
                    f"v1_shadow_elapsed_ms:{elapsed_ms}",
                ],
            }
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - started) * 1000)
            self._v1_last_error = f"{type(exc).__name__}: {exc}"
            print(f"[xinyu_core_bridge] v1 shadow failed: {self._v1_last_error}", flush=True)
            return {
                "accepted": False,
                "route": "",
                "trace_id": "",
                "elapsed_ms": elapsed_ms,
                "notes": [f"v1_shadow_error:{type(exc).__name__}"],
            }

    async def start_background_tasks(self) -> None:
        if self._closed or not self.autonomous_maintenance_enabled:
            self._trace_autonomous("background disabled")
            self._write_autonomous_state("disabled")
            return
        if self._autonomous_task is not None and not self._autonomous_task.done():
            return
        self._autonomous_task = asyncio.create_task(
            self._autonomous_maintenance_loop(),
            name="xinyu-autonomous-maintenance",
        )
        self._trace_autonomous("background task started")
        self._write_autonomous_state("starting")

    def _autonomous_maintenance_health(self) -> dict[str, Any]:
        task = self._autonomous_task
        task_running = bool(task is not None and not task.done())
        task_done = bool(task is not None and task.done())
        return {
            "enabled": self.autonomous_maintenance_enabled,
            "task_running": task_running,
            "task_done": task_done,
            "in_progress": self._autonomous_in_progress,
            "session_key": self.autonomous_maintenance_session_key,
            "initial_delay_seconds": self.autonomous_maintenance_initial_delay_seconds,
            "interval_seconds": self.autonomous_maintenance_interval_seconds,
            "run_count": self._autonomous_run_count,
            "failure_count": self._autonomous_failure_count,
            "last_started_at": self._autonomous_last_started_at,
            "last_success_at": self._autonomous_last_success_at,
            "last_error": self._autonomous_last_error,
            "last_memory_changed": self._autonomous_last_memory_changed,
            "next_run_at": self._autonomous_next_run_at,
        }

    async def _autonomous_maintenance_loop(self) -> None:
        try:
            try:
                await self._ensure_autonomous_session()
            except Exception as exc:
                self._record_autonomous_failure(f"startup_session_error:{exc!r}")

            delay = self.autonomous_maintenance_initial_delay_seconds
            if delay > 0:
                self._autonomous_next_run_at = self._iso_from_timestamp(time.time() + delay)
                self._write_autonomous_state("waiting_initial_delay")
                await asyncio.sleep(delay)

            while not self._closed and self.autonomous_maintenance_enabled:
                try:
                    await self._run_autonomous_maintenance_once()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    self._record_autonomous_failure(f"run_error:{exc!r}")

                self._autonomous_next_run_at = self._iso_from_timestamp(
                    time.time() + self.autonomous_maintenance_interval_seconds
                )
                self._write_autonomous_state("sleeping")
                await asyncio.sleep(self.autonomous_maintenance_interval_seconds)
        except asyncio.CancelledError:
            self._trace_autonomous("background task cancelled")
            self._write_autonomous_state("cancelled")
            raise
        finally:
            self._autonomous_in_progress = False
            if self._closed:
                self._write_autonomous_state("closed")

    async def _ensure_autonomous_session(self) -> AgentSession:
        async with self._global_turn_lock:
            await self._cleanup_idle_sessions(preserve_keys={self.autonomous_maintenance_session_key})
            session = await self._get_session(self.autonomous_maintenance_session_key)
            session.last_used_at = time.time()
            self._trace_autonomous(f"session ready key={session.key}")
            self._write_autonomous_state("session_ready")
            return session

    async def _run_autonomous_maintenance_once(self) -> dict[str, Any]:
        if self._closed or not self.autonomous_maintenance_enabled:
            return {"accepted": False, "notes": ["disabled_or_closed"]}

        async with self._global_turn_lock:
            cleanup = await self._cleanup_idle_sessions(preserve_keys={self.autonomous_maintenance_session_key})
            session = await self._get_session(self.autonomous_maintenance_session_key)
            before_memory = _memory_snapshot(self.memory_root)
            session.chunks.clear()
            event = self._create_autonomous_maintenance_event()
            self._autonomous_in_progress = True
            self._autonomous_last_started_at = datetime.now().astimezone().isoformat()
            self._autonomous_last_error = ""
            self._trace_autonomous("run started")
            self._write_autonomous_state("running")

            try:
                await asyncio.wait_for(
                    session.agent.inject_event(event),
                    timeout=self.turn_timeout_seconds,
                )
            except TimeoutError:
                try:
                    session.agent.interrupt()
                except Exception:
                    pass
                raise
            finally:
                self._autonomous_in_progress = False

            session.last_used_at = time.time()
            reply_preview = _normalize_reply("".join(session.chunks))[:200]
            sidecar_notes = self._run_autonomous_self_thought_sidecars(
                checked_at=datetime.now().astimezone().isoformat()
            )
            after_memory = _memory_snapshot(self.memory_root)
            memory_changed = before_memory != after_memory
            self._autonomous_run_count += 1
            self._autonomous_last_success_at = datetime.now().astimezone().isoformat()
            notes = ["autonomous_maintenance_turn", "no_visible_reply"]
            notes.extend(sidecar_notes)
            if cleanup["cleaned_sessions"]:
                notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")
            self._trace_autonomous(
                f"run finished memory_changed={memory_changed} reply_preview={reply_preview!r}"
            )
            self._write_autonomous_state("last_run_ok", memory_changed=memory_changed, notes=notes)
            return {
                "accepted": True,
                "memory_changed": memory_changed,
                "reply_preview": reply_preview,
                "sessions": len(self._sessions),
                "notes": notes,
            }

    def _run_autonomous_self_thought_sidecars(self, *, checked_at: str) -> list[str]:
        notes: list[str] = []
        try:
            watched = run_watched_source_check(
                self.xinyu_dir,
                checked_at=checked_at,
                min_interval_seconds=self.autonomous_maintenance_interval_seconds,
            )
            if _safe_str(watched.get("status")) != "no_sources":
                notes.append(
                    "watched_source:"
                    f"{_safe_str(watched.get('status'), 'unknown')}/"
                    f"{_safe_str(watched.get('fetched_items'), '0')}/"
                    f"{_safe_str(watched.get('new_items'), '0')}"
                )
        except Exception as exc:
            notes.append(f"watched_source_error:{type(exc).__name__}")
            self._trace_autonomous(f"watched_source_error={exc!r}")
        try:
            thought = run_self_thought_loop(
                self.xinyu_dir,
                checked_at=checked_at,
                trigger="autonomous_maintenance",
                min_interval_seconds=self.autonomous_maintenance_interval_seconds,
            )
            notes.append(
                "self_thought:"
                f"{_safe_str(thought.get('status'), 'unknown')}/"
                f"{_safe_str(thought.get('outcome'), 'unknown')}/"
                f"{_safe_str(thought.get('focus_kind'), 'unknown')}/"
                f"{_safe_str(thought.get('intention'), 'unknown')}"
            )
        except Exception as exc:
            notes.append(f"self_thought_error:{type(exc).__name__}")
            self._trace_autonomous(f"self_thought_error={exc!r}")
            return notes

        if not _as_bool(thought.get("candidate_enabled"), default=False):
            if _as_bool(thought.get("research_needed"), default=False):
                notes.append(f"self_thought_research:{_safe_str(thought.get('research_route'), 'unknown')}")
            try:
                closed_loop = record_learning_closed_loop_self_thought(
                    self.xinyu_dir,
                    thought=thought,
                    observed_at=checked_at,
                )
                notes.extend(_safe_str(note) for note in closed_loop.get("notes", [])[:2])
            except Exception as exc:
                notes.append(f"learning_closed_loop_self_thought_error:{type(exc).__name__}")
            return notes

        request: dict[str, Any] = {}
        try:
            request = run_proactive_request_loop(
                self.xinyu_dir,
                evaluated_at=checked_at,
                delivery_level="queue_owner_private",
            )
            notes.append(
                "proactive_request:"
                f"{_safe_str(request.get('status'), 'unknown')}/"
                f"{_safe_str(request.get('kind'), 'unknown')}/"
                f"{_safe_str(request.get('delivery_level'), 'unknown')}"
            )
        except Exception as exc:
            notes.append(f"proactive_request_error:{type(exc).__name__}")
            self._trace_autonomous(f"proactive_request_error={exc!r}")
        try:
            closed_loop = record_learning_closed_loop_self_thought(
                self.xinyu_dir,
                thought=thought,
                request=request,
                observed_at=checked_at,
            )
            notes.extend(_safe_str(note) for note in closed_loop.get("notes", [])[:2])
        except Exception as exc:
            notes.append(f"learning_closed_loop_self_thought_error:{type(exc).__name__}")
        return notes

    def _create_autonomous_maintenance_event(self) -> Any:
        self._load_runtime()
        event_cls = self._trigger_event_cls
        if event_cls is None:
            raise RuntimeError("TriggerEvent class is unavailable")
        now = datetime.now().astimezone().isoformat()
        return event_cls(
            type="timer",
            content=AUTONOMOUS_MAINTENANCE_PROMPT,
            context={
                "trigger": "scheduler",
                "source": "xinyu_core_bridge",
                "time": now,
                "session_id": self.autonomous_maintenance_session_key,
                "autonomous": True,
            },
            stackable=False,
        )

    def _record_autonomous_failure(self, message: str) -> None:
        self._autonomous_failure_count += 1
        self._autonomous_last_error = message
        self._trace_autonomous(message)
        self._write_autonomous_state("error")

    def _trace_autonomous(self, line: str) -> None:
        trace_path = self.memory_root / "context/autonomous_mind_loop_trace.log"
        try:
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().astimezone().isoformat()
            with trace_path.open("a", encoding="utf-8") as fh:
                fh.write(f"{stamp} {line}\n")
        except Exception:
            pass

    def _write_autonomous_state(
        self,
        status: str,
        *,
        memory_changed: bool | None = None,
        notes: list[str] | None = None,
    ) -> None:
        state_path = self.memory_root / "context/autonomous_mind_loop_state.md"
        updated_at = datetime.now().astimezone().isoformat()
        if notes is not None:
            self._autonomous_last_notes = notes
        if memory_changed is not None:
            self._autonomous_last_memory_changed = str(memory_changed).lower()
        note_lines = "\n".join(f"- {note}" for note in self._autonomous_last_notes) or "- none"
        text = f"""---
title: Autonomous Mind Loop State
memory_type: autonomous_mind_loop_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: xinyu_core_bridge
updated_at: {updated_at}
status: active
tags: [autonomy, maintenance, runtime]
---

# Autonomous Mind Loop State

## Runtime
- status: {status}
- enabled: {str(self.autonomous_maintenance_enabled).lower()}
- in_progress: {str(self._autonomous_in_progress).lower()}
- session_key: {self.autonomous_maintenance_session_key}
- initial_delay_seconds: {self.autonomous_maintenance_initial_delay_seconds}
- interval_seconds: {self.autonomous_maintenance_interval_seconds}
- next_run_at: {self._autonomous_next_run_at or "unknown"}

## Last Run
- run_count: {self._autonomous_run_count}
- failure_count: {self._autonomous_failure_count}
- last_started_at: {self._autonomous_last_started_at or "never"}
- last_success_at: {self._autonomous_last_success_at or "never"}
- memory_changed: {self._autonomous_last_memory_changed}
- last_error: {self._autonomous_last_error or "none"}

## Notes
{note_lines}
"""
        try:
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(text, encoding="utf-8")
        except Exception:
            pass

    def _iso_from_timestamp(self, value: float) -> str:
        return datetime.fromtimestamp(value).astimezone().isoformat()

    async def probe(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """No-memory diagnostic endpoint.

        This intentionally does not start an Agent, create a session, render a
        reply, or inject a turn. It is for startup/status checks that should not
        become lived context.
        """
        payload = payload or {}
        text = self._payload_text(payload) if isinstance(payload, dict) else ""
        cleanup = await self._cleanup_idle_sessions()
        return {
            "ok": True,
            "bridge": "xinyu_core_bridge",
            "version": BRIDGE_VERSION,
            "probe": "diagnostic_no_memory",
            "accepted": True,
            "reply": "probe_ok",
            "received_text_chars": len(text),
            "memory_changed": False,
            "session_created": False,
            "sessions": len(self._sessions),
            "cleaned_sessions": cleanup["cleaned_sessions"],
            "notes": ["no_agent_turn", "no_memory_write", "no_session_created"],
        }

    async def proactive(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._closed:
            raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")
        if payload is not None and not isinstance(payload, dict):
            raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
        try:
            return await proactive_bridge(
                xinyu_dir=self.xinyu_dir,
                memory_root=self.memory_root,
                payload=payload or {},
                proactive_min_interval_seconds=self.proactive_min_interval_seconds,
                cleanup_idle_sessions=self._cleanup_idle_sessions,
                session_count=lambda: len(self._sessions),
                lock=self._global_turn_lock,
            )
        except ValueError as exc:
            raise BridgeRequestError(HTTPStatus.BAD_REQUEST, str(exc)) from exc

    async def proactive_ack(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._closed:
            raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")
        if payload is not None and not isinstance(payload, dict):
            raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
        return await proactive_ack_bridge(
            xinyu_dir=self.xinyu_dir,
            memory_root=self.memory_root,
            payload=payload or {},
            cleanup_idle_sessions=self._cleanup_idle_sessions,
            session_count=lambda: len(self._sessions),
            lock=self._global_turn_lock,
        )

    async def qq_outbox_claim(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._closed:
            raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")
        if payload is not None and not isinstance(payload, dict):
            raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
        payload = payload or {}
        claim = await asyncio.to_thread(claim_next_qq_outbox_message, self.xinyu_dir, payload)
        if claim.get("message_claimed"):
            return claim

        proactive_claim = await self._claim_proactive_for_qq_outbox(payload)
        if proactive_claim is None:
            return claim
        return proactive_claim

    def qq_outbox_claim_fast(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._closed:
            raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")
        if payload is not None and not isinstance(payload, dict):
            raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
        payload = payload or {}
        claim = claim_next_qq_outbox_message(self.xinyu_dir, payload)
        if claim.get("message_claimed"):
            return claim
        proactive_claim = self._claim_proactive_for_qq_outbox_sync(payload)
        if proactive_claim is None:
            return claim
        return proactive_claim

    async def qq_outbox_ack(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._closed:
            raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")
        if payload is not None and not isinstance(payload, dict):
            raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
        payload = payload or {}
        message_id = _safe_str(payload.get("message_id")).strip()
        if message_id.startswith("proactive:"):
            result = await proactive_ack_bridge(
                xinyu_dir=self.xinyu_dir,
                memory_root=self.memory_root,
                payload=payload,
                cleanup_idle_sessions=self._cleanup_idle_sessions,
                session_count=lambda: len(self._sessions),
                lock=self._global_turn_lock,
            )
            if result.get("ack_recorded") and result.get("ack_status") == "sent":
                self._record_proactive_outbound_dialogue(payload)
            return result
        return await asyncio.to_thread(ack_qq_outbox_message, self.xinyu_dir, payload or {})

    def qq_outbox_ack_fast(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._closed:
            raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")
        if payload is not None and not isinstance(payload, dict):
            raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
        payload = payload or {}
        message_id = _safe_str(payload.get("message_id")).strip()
        if message_id.startswith("proactive:"):
            result = acknowledge_proactive_qq_message(
                self.xinyu_dir,
                claim_id=_safe_str(payload.get("claim_id")).strip(),
                ack_status=_safe_str(payload.get("ack_status") or payload.get("status"), "sent").strip(),
                adapter_message_id=_safe_str(payload.get("adapter_message_id") or payload.get("message_id")).strip(),
                adapter_error=_safe_str(payload.get("adapter_error") or payload.get("error")).strip(),
            )
            result = {**result, "session_created": False, "sessions": len(self._sessions)}
            if result.get("ack_recorded") and result.get("ack_status") == "sent":
                self._record_proactive_outbound_dialogue(payload)
            return result
        return ack_qq_outbox_message(self.xinyu_dir, payload)

    async def _claim_proactive_for_qq_outbox(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        candidate = self._ready_proactive_outbox_candidate()
        if not candidate:
            return None

        owner_user_id = self._owner_private_user_id()
        if not owner_user_id:
            return None

        claim_id = _safe_str(payload.get("claim_id")).strip() or f"proactive-{int(time.time())}"
        proactive = await proactive_bridge(
            xinyu_dir=self.xinyu_dir,
            memory_root=self.memory_root,
            payload={
                "claim": True,
                "claim_id": claim_id,
                "min_interval_seconds": payload.get("min_interval_seconds", self.proactive_min_interval_seconds),
            },
            proactive_min_interval_seconds=self.proactive_min_interval_seconds,
            cleanup_idle_sessions=self._cleanup_idle_sessions,
            session_count=lambda: len(self._sessions),
            lock=self._global_turn_lock,
        )
        if not proactive.get("candidate_claimed"):
            return None

        message = _safe_str(proactive.get("reply") or proactive.get("preview_reply")).strip()
        if not message:
            return None
        request_id = _safe_str(proactive.get("proactive_request_id") or proactive.get("request_id")).strip()
        if not request_id:
            request_id = _safe_str(proactive.get("evaluated_at")).strip() or claim_id
        return {
            "accepted": True,
            "message_claimed": True,
            "message_id": f"proactive:{request_id}",
            "claim_id": claim_id,
            "target": {"message_kind": "private", "user_id": owner_user_id, "group_id": ""},
            "message": message,
            "attempts": 1,
            "source": "proactive_request",
            "notes": ["claimed", "proactive_request_claimed_via_outbox"] + list(proactive.get("notes", [])),
        }

    def _claim_proactive_for_qq_outbox_sync(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        candidate = self._ready_proactive_outbox_candidate()
        if not candidate:
            return None

        owner_user_id = self._owner_private_user_id()
        if not owner_user_id:
            return None

        claim_id = _safe_str(payload.get("claim_id")).strip() or f"proactive-{int(time.time())}"
        min_interval_seconds = _as_int(payload.get("min_interval_seconds"), self.proactive_min_interval_seconds)
        proactive = claim_proactive_qq_message(
            self.xinyu_dir,
            mode="bridge_proactive_qq_claim_fast",
            claim=True,
            claim_id=claim_id,
            min_interval_seconds=min_interval_seconds,
        )
        if not proactive.get("candidate_claimed"):
            return None

        message = _safe_str(proactive.get("reply") or proactive.get("preview_reply")).strip()
        if not message:
            return None
        request_id = _safe_str(proactive.get("proactive_request_id") or proactive.get("request_id")).strip()
        if not request_id or request_id in {"none", "unknown"}:
            request_id = _safe_str(proactive.get("evaluated_at")).strip() or claim_id
        return {
            "accepted": True,
            "message_claimed": True,
            "message_id": f"proactive:{request_id}",
            "claim_id": claim_id,
            "target": {"message_kind": "private", "user_id": owner_user_id, "group_id": ""},
            "message": message,
            "attempts": 1,
            "source": "proactive_request",
            "notes": ["claimed", "proactive_request_claimed_via_outbox_fast"] + list(proactive.get("notes", [])),
        }

    def _ready_proactive_outbox_candidate(self) -> str:
        state = _read_text_safe(self.xinyu_dir / "memory/context/proactive_request_state.md")
        if _state_field(state, "status") != "ready":
            return ""
        if _state_field(state, "delivery_level") not in {"queue_owner_private", "claim_ack"}:
            return ""
        candidate = _state_field(state, "concrete_question")
        return candidate if candidate not in {"", "none", "unknown"} else ""

    def _proactive_candidate_already_handled(self, candidate: str) -> bool:
        state = _read_text_safe(self.xinyu_dir / "memory/context/proactive_qq_dispatch_state.md")
        status = _state_field(state, "last_claim_status")
        if status not in {"claimed", "sent"}:
            return False
        return _state_field(state, "last_claimed_message") == candidate

    def _record_proactive_outbound_dialogue(self, ack_payload: dict[str, Any]) -> None:
        dispatch = _read_text_safe(self.xinyu_dir / "memory/context/proactive_qq_dispatch_state.md")
        if _state_field(dispatch, "last_ack_status") != "sent":
            return
        message = _state_field(dispatch, "last_claimed_message")
        if not message or message in {"none", "unknown"}:
            return
        claimed_at = _state_field(dispatch, "last_claimed_at") or datetime.now().astimezone().isoformat()
        payload = self._owner_private_payload(
            source="proactive_request_outbox",
            message_id=_safe_str(ack_payload.get("message_id")),
        )
        appended = self._append_assistant_to_dialogue_tail(
            payload["session_id"],
            message,
            recorded_at=claimed_at,
        )
        if not appended:
            return
        try:
            archive_message(
                self.xinyu_dir,
                payload,
                role="assistant",
                text=message,
                created_at=claimed_at,
                message_type="private_proactive",
                metadata={"source": "proactive_request_outbox"},
            )
        except Exception as exc:
            print(f"[xinyu_core_bridge] proactive outbound archive failed: {exc}", flush=True)

    def _owner_private_payload(self, *, source: str, message_id: str = "") -> dict[str, Any]:
        owner_user_id = self._owner_private_user_id()
        session_id = f"qq:private:{owner_user_id}" if owner_user_id else "qq:private:owner"
        return {
            "platform": "qq",
            "adapter": "xinyu_core_bridge",
            "message_type": "private_proactive",
            "session_id": session_id,
            "user_id": owner_user_id,
            "message_id": message_id,
            "metadata": {
                "source": source,
                "is_owner_user": True,
                "proactive_outbound": True,
            },
        }

    def _append_assistant_to_dialogue_tail(self, session_key: str, message: str, *, recorded_at: str = "") -> bool:
        clean = _safe_str(message).strip()
        if not clean:
            return False
        tail = load_dialogue_tail(
            self.xinyu_dir,
            session_key,
            max_entries=self.dialogue_persisted_tail_entries,
            include_timestamps=True,
        )
        for item in tail[-8:]:
            if item.get("role") == "assistant" and _safe_str(item.get("content")).strip() == clean:
                return False
        tail.append(
            {
                "role": "assistant",
                "content": clean,
                "recorded_at": recorded_at or datetime.now().astimezone().isoformat(),
            }
        )
        tail.sort(key=lambda item: _safe_str(item.get("recorded_at")))
        return save_dialogue_tail(
            self.xinyu_dir,
            session_key,
            tail,
            max_entries=self.dialogue_persisted_tail_entries,
        )

    def _owner_direct_codex_task(
        self,
        payload: dict[str, Any],
        *,
        user_text: str,
        reply: str,
        session_key: str,
    ) -> str:
        if not self._can_model_delegate_codex(payload):
            return ""
        compact_user = self._compact_promise_text(user_text)
        if any(marker in compact_user for marker in OWNER_DIRECT_CODEX_NEGATIVE_MARKERS):
            return ""
        if not looks_like_codex_request(user_text):
            return ""
        has_direct_codex = any(marker in compact_user for marker in OWNER_DIRECT_CODEX_DELEGATE_MARKERS)
        has_support_context = any(marker in compact_user for marker in OWNER_DIRECT_CODEX_SUPPORT_MARKERS)
        if not (has_direct_codex or ("codex" in compact_user and has_support_context)):
            return ""
        compact_reply = self._compact_promise_text(reply)
        if "要现在开始吗" in compact_reply or "要现在开始" in compact_reply:
            pass
        elif any(marker in compact_reply for marker in ("开了", "让codex", "交给codex", "xinyucodex", "codex在新窗口")):
            return ""
        return _normalize_reply(
            "\n".join(
                [
                    "Owner explicitly asked XinYu to use Codex instead of stalling or asking for more permission.",
                    f"Owner message: {user_text}",
                    f"XinYu draft that failed to act: {reply}",
                    f"Session: {session_key}",
                    (
                        "Task: use web/repository research to find concrete ways to reduce XinYu's mechanical voice "
                        "and shallow context continuity, then report actionable project changes. Do not change files; "
                        "produce a concise report with sources or code pointers."
                    ),
                ]
            )
        )

    def _owner_self_code_grant_in_text(self, compact_text: str) -> bool:
        if any(marker in compact_text for marker in OWNER_SELF_CODE_NEGATIVE_MARKERS):
            return False
        if not any(marker in compact_text for marker in OWNER_SELF_CODE_EDIT_GRANT_MARKERS):
            return False
        if any(marker in compact_text for marker in OWNER_SELF_CODE_GRANT_CUES):
            return True
        return any(
            marker in compact_text
            for marker in (
                "主动改代码",
                "主动修改代码",
                "主动更改代码",
                "开始改代码",
                "直接改代码",
            )
        )

    def _recent_owner_self_code_grant(self, session_key: str) -> bool:
        tail = load_dialogue_tail(self.xinyu_dir, session_key, max_entries=8)
        for item in reversed(tail):
            if item.get("role") != "user":
                continue
            compact = self._compact_promise_text(item.get("content", ""))
            if any(marker in compact for marker in OWNER_SELF_CODE_NEGATIVE_MARKERS):
                return False
            if self._owner_self_code_grant_in_text(compact):
                return True
        return False

    def _owner_self_code_direct_grant_requested(self, user_text: str, *, session_key: str) -> bool:
        compact_user = self._compact_promise_text(user_text)
        if any(marker in compact_user for marker in OWNER_SELF_CODE_NEGATIVE_MARKERS):
            return False
        if self._owner_self_code_grant_in_text(compact_user):
            return True
        has_start_marker = any(marker in compact_user for marker in OWNER_SELF_CODE_START_MARKERS)
        return has_start_marker and self._recent_owner_self_code_grant(session_key)

    def _owner_self_code_iteration_task(
        self,
        payload: dict[str, Any],
        *,
        user_text: str,
        reply: str,
        session_key: str,
    ) -> str:
        if not self._can_model_delegate_codex(payload):
            return ""
        approval = consume_self_code_approval(
            self.xinyu_dir,
            payload,
            owner_text=user_text,
            session_key=session_key,
            reply=reply,
        )
        if not approval.get("approved"):
            if not self._owner_self_code_direct_grant_requested(user_text, session_key=session_key):
                return ""
            approval = create_direct_self_code_approval(
                self.xinyu_dir,
                payload,
                owner_text=user_text,
                session_key=session_key,
                reply=reply,
            )
            if not approval.get("approved"):
                return ""
            approval_reason = (
                "The approval exists because the owner directly requested or authorized self-code modification "
                "in QQ private chat."
            )
        else:
            approval_reason = "The approval exists because XinYu first sent a QQ self-code application and owner approved that pending request."
        return _normalize_reply(
            "\n".join(
                [
                    f"Self-code approval id: {_safe_str(approval.get('approval_id'), 'unknown')}",
                    approval_reason,
                    _safe_str(approval.get("task_text")),
                ]
            )
        )

    def _codex_delegate_running(self) -> dict[str, Any]:
        if self._codex_delegate_lock.locked():
            return {"running": True, "status": "running", "source": "lock", "visible_window_title": CODEX_VISIBLE_WINDOW_TITLE}
        path = self.xinyu_dir / "runtime/codex_presence_state.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return {"running": False, "status": "unknown"}
        if not isinstance(data, dict):
            return {"running": False, "status": "unknown"}
        status = _safe_str(data.get("status")).strip().lower()
        updated_at = _safe_str(data.get("updated_at")).strip()
        stale = bool(updated_at) and _seconds_since_iso(updated_at, default=0.0) > CODEX_DEFAULT_TIMEOUT_SECONDS + 900
        running = status in {"running", "starting", "queued"} and not stale
        return {
            "running": running,
            "status": status or "unknown",
            "job_id": _safe_str(data.get("job_id")).strip(),
            "visible_window_title": _safe_str(data.get("visible_window_title"), CODEX_VISIBLE_WINDOW_TITLE).strip()
            or CODEX_VISIBLE_WINDOW_TITLE,
            "report_label": _safe_str(data.get("report_label")).strip(),
            "stale": stale,
        }

    def _codex_busy_reply(self, state: dict[str, Any]) -> str:
        job_id = _safe_str(state.get("job_id")).strip()
        window = _safe_str(state.get("visible_window_title"), CODEX_VISIBLE_WINDOW_TITLE).strip() or CODEX_VISIBLE_WINDOW_TITLE
        job_part = f" {job_id}" if job_id else ""
        return (
            f"权限不是低，是执行位现在被 Codex{job_part} 占着，还在 {window} 窗口里跑。"
            "等它出结果，我再接代码改动；这次不会只停在“我想想”。"
        )

    def _promised_followup_candidate(
        self,
        payload: dict[str, Any],
        *,
        user_text: str,
        reply: str,
        session_key: str,
        model_codex_task: str = "",
    ) -> dict[str, str]:
        if model_codex_task:
            return {}
        if not self._owner_private_payload_matches(payload):
            return {}
        user_id = _safe_str(payload.get("user_id")).strip() or self._owner_private_user_id()
        if not user_id:
            return {}
        compact_user = self._compact_promise_text(user_text)
        compact_reply = self._compact_promise_text(reply)
        if not any(marker in compact_user for marker in PROMISE_FOLLOWUP_USER_MARKERS):
            return {}
        if not any(marker in compact_reply for marker in PROMISE_FOLLOWUP_REPLY_MARKERS):
            return {}
        if any(marker in compact_reply for marker in PROMISE_FOLLOWUP_DONE_MARKERS):
            return {}
        digest = hashlib.sha1(f"{session_key}\n{user_text}\n{reply}".encode("utf-8", errors="replace")).hexdigest()[:16]
        return {
            "user_id": user_id,
            "session_key": session_key,
            "user_text": _safe_str(user_text).strip(),
            "reply": _safe_str(reply).strip(),
            "dedupe_key": f"promise_followup:{digest}",
        }

    @staticmethod
    def _compact_promise_text(text: str) -> str:
        return re.sub(r"[\s，。！？、；：,.!?;:<>《》\"'`]+", "", _safe_str(text).lower())

    def _schedule_promised_followup_if_needed(
        self,
        payload: dict[str, Any],
        *,
        user_text: str,
        reply: str,
        session_key: str,
        model_codex_task: str = "",
    ) -> dict[str, Any]:
        candidate = self._promised_followup_candidate(
            payload,
            user_text=user_text,
            reply=reply,
            session_key=session_key,
            model_codex_task=model_codex_task,
        )
        if not candidate:
            return {"scheduled": False, "notes": []}
        self._write_promised_followup_state(candidate, status="scheduled", message_id="none", notes=["scheduled"])
        asyncio.create_task(
            asyncio.to_thread(self._run_promised_followup_review, candidate),
            name=f"xinyu-promised-followup-{candidate['dedupe_key'].split(':')[-1]}",
        )
        return {"scheduled": True, "notes": ["promised_followup_scheduled"]}

    def _run_promised_followup_review(self, candidate: dict[str, str]) -> dict[str, Any]:
        notes = ["reviewed_runtime_followup_contract"]
        message = self._promised_followup_message(candidate)
        queued = enqueue_qq_outbox_message(
            self.xinyu_dir,
            user_id=candidate["user_id"],
            message=message,
            source="promise_followup",
            dedupe_key=candidate["dedupe_key"],
            metadata={
                "session_key": candidate.get("session_key", ""),
                "origin_user_text": candidate.get("user_text", "")[:240],
                "origin_reply": candidate.get("reply", "")[:120],
                "followup_kind": "promised_review_completion",
            },
        )
        notes.extend(_safe_str(note) for note in queued.get("notes", []))
        status = "queued" if queued.get("queued") or queued.get("accepted") else "failed"
        self._write_promised_followup_state(
            candidate,
            status=status,
            message_id=_safe_str(queued.get("message_id")),
            notes=notes,
        )
        return {"scheduled": True, "queued": bool(queued.get("queued")), "message_id": queued.get("message_id", ""), "notes": notes}

    def _promised_followup_message(self, candidate: dict[str, str]) -> str:
        user_text = candidate.get("user_text", "")
        if "看没看" in user_text or "主动" in user_text or "告诉我" in user_text or "跟我说" in user_text:
            return "我看完了。刚才那种“好，我再看看”不该停在那里；以后我只要说要去看/查，就会挂一个待回报，查完主动发给你。"
        return "我看完了。刚才我说要再看看，这件事没有放后台不管；后面如果还需要继续查，我会直接接着告诉你。"

    def _write_promised_followup_state(
        self,
        candidate: dict[str, str],
        *,
        status: str,
        message_id: str,
        notes: list[str],
    ) -> None:
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        note_lines = "\n".join(f"- {note}" for note in _dedupe(notes)) or "- none"
        text = f"""---
title: Promise Followup State
memory_type: promise_followup_state
time_scope: short_term
subject_ids: [xinyu, owner]
protected: true
source: xinyu_core_bridge
updated_at: {now}
status: active
tags: [promise, followup, qq-outbox, continuity]
---

# Promise Followup State

## Latest Promise
- status: {_safe_str(status, "unknown")}
- checked_at: {now}
- session_key: {_safe_str(candidate.get("session_key"), "unknown")}
- user_id: {_safe_str(candidate.get("user_id"), "unknown")}
- dedupe_key: {_safe_str(candidate.get("dedupe_key"), "unknown")}
- queued_message_id: {_safe_str(message_id, "none") or "none"}
- owner_request: {_normalize_reply(candidate.get("user_text", ""))[:240] or "none"}
- promised_reply: {_normalize_reply(candidate.get("reply", ""))[:160] or "none"}

## Notes
{note_lines}
"""
        path = self.xinyu_dir / PROMISE_FOLLOWUP_STATE_REL
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _owner_private_user_id(self) -> str:
        if self.v1_owner_user_ids:
            return sorted(self.v1_owner_user_ids)[0]

        env_owner_ids = _as_str_set(os.environ.get("XINYU_OWNER_USER_IDS"))
        if env_owner_ids:
            return sorted(env_owner_ids)[0]

        config_path = self.xinyu_dir / "xinyu_qq_gateway.config.json"
        try:
            data = json.loads(config_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return ""
        owner_ids = _as_str_set(data.get("owner_user_ids") if isinstance(data, dict) else None)
        return sorted(owner_ids)[0] if owner_ids else ""

    def _sync_recent_proactive_to_dialogue_tail(self, session: AgentSession, payload: dict[str, Any]) -> bool:
        if not self._owner_private_payload_matches(payload):
            return False
        dispatch = _read_text_safe(self.xinyu_dir / "memory/context/proactive_qq_dispatch_state.md")
        if _state_field(dispatch, "last_claim_status") not in {"claimed", "sent"}:
            return False
        message = _state_field(dispatch, "last_claimed_message")
        if not message or message in {"none", "unknown"}:
            return False
        if _seconds_since_iso(_state_field(dispatch, "last_claimed_at"), default=999999.0) > 6 * 3600:
            return False
        for item in session.dialogue_tail[-8:]:
            if item.get("role") == "assistant" and _safe_str(item.get("content")).strip() == message:
                return False
        session.dialogue_tail.append(
            {
                "role": "assistant",
                "content": message,
                "recorded_at": _state_field(dispatch, "last_claimed_at") or datetime.now().astimezone().isoformat(),
            }
        )
        session.dialogue_tail.sort(key=lambda item: _safe_str(item.get("recorded_at")))
        if len(session.dialogue_tail) > self.dialogue_session_tail_entries:
            del session.dialogue_tail[:-self.dialogue_session_tail_entries]
        try:
            save_dialogue_tail(self.xinyu_dir, session.key, session.dialogue_tail, max_entries=self.dialogue_persisted_tail_entries)
        except Exception:
            pass
        return True

    def _owner_private_payload_matches(self, payload: dict[str, Any]) -> bool:
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        if not _as_bool(metadata.get("is_owner_user"), default=False):
            return False
        message_type = _safe_str(payload.get("message_type")).lower()
        return message_type.startswith("private") or not _safe_str(payload.get("group_id")).strip()

    def _proactive_thread_context(self, payload: dict[str, Any], current_text: str) -> str:
        if not self._owner_private_payload_matches(payload):
            return ""
        dispatch = _read_text_safe(self.xinyu_dir / "memory/context/proactive_qq_dispatch_state.md")
        if _state_field(dispatch, "last_claim_status") not in {"claimed", "sent"}:
            return ""
        message = _state_field(dispatch, "last_claimed_message")
        if not message or message in {"none", "unknown"}:
            return ""
        age_seconds = _seconds_since_iso(_state_field(dispatch, "last_claimed_at"), default=999999.0)
        if age_seconds > 6 * 3600:
            return ""
        request = _read_text_safe(self.xinyu_dir / "memory/context/proactive_request_state.md")
        kind = _state_field(request, "kind", "proactive")
        answer_state = _state_field(request, "request_answer_state", "pending")
        extra_rules: list[str] = []
        evidence_label = _state_field(request, "evidence_label", "")
        if kind == "reflection_share" and "Codex" in evidence_label:
            runtime_presence = _read_text_safe(self.xinyu_dir / "memory/context/runtime_self_presence.md")
            codex_status = _state_field(runtime_presence, "codex_status", "unknown").lower()
            codex_timed_out = _state_field(runtime_presence, "codex_timed_out", "false").lower() == "true"
            if codex_status in {"", "unknown", "none"} and not codex_timed_out:
                extra_rules.append(
                    "- reflection_share_rule: this proactive line came from an old reflection queue item, "
                    "not from a currently running or currently timed-out Codex job. If the owner is confused, "
                    "say that directly and do not repeat the decision request."
                )
        return "\n".join(
            [
                "proactive thread sidecar:",
                f"- last_xinyu_proactive_message: {message}",
                f"- proactive_kind: {kind}",
                f"- request_answer_state_before_this_turn: {answer_state}",
                f"- current_owner_message: {_safe_str(current_text).strip()}",
                (
                    "- continuity_rule: treat the owner message as a likely reply to XinYu's proactive message. "
                    "Continue from that concrete thread; do not ask what to talk about when the owner is already "
                    "commenting on the proactive message."
                ),
                (
                    "- dream_share_rule: if proactive_kind is dream_share and the owner says dreams are illogical, "
                    "strange, or asks what XinYu means, answer from XinYu's own dream context instead of asking the "
                    "owner to explain the dream."
                ),
                *extra_rules,
            ]
        )

    def _mark_proactive_owner_reply(self, payload: dict[str, Any], *, text: str, reply: str) -> bool:
        if not self._owner_private_payload_matches(payload):
            return False
        request_path = self.xinyu_dir / "memory/context/proactive_request_state.md"
        request = _read_text_safe(request_path)
        if _state_field(request, "status") not in {"ready", "candidate_only", "claimed", "sent"}:
            return False
        if _state_field(request, "request_answer_state", "pending") not in {"pending", "", "unknown"}:
            return False
        dispatch = _read_text_safe(self.xinyu_dir / "memory/context/proactive_qq_dispatch_state.md")
        if _state_field(dispatch, "last_claim_status") != "sent":
            return False
        answered_at = datetime.now().astimezone().isoformat()
        updated = re.sub(
            r"(?m)^-\s+request_answer_state:\s*.*$",
            "- request_answer_state: owner_replied",
            request,
            count=1,
        )
        if updated == request:
            updated = request.rstrip() + "\n- request_answer_state: owner_replied\n"
        updated = re.sub(
            r"(?m)^-\s+status:\s*.*$",
            "- status: answered",
            updated,
            count=1,
        )
        updated = re.sub(
            r"(?m)^updated_at:\s*.*$",
            f"updated_at: {answered_at}",
            updated,
            count=1,
        )
        extra = (
            "\n## Last Owner Reply To Proactive\n"
            f"- owner_replied_at: {answered_at}\n"
            f"- owner_reply_preview: {_safe_str(text).strip()[:240] or 'none'}\n"
            f"- xinyu_reply_preview: {_safe_str(reply).strip()[:240] or 'none'}\n"
        )
        try:
            request_path.write_text(updated.rstrip() + extra, encoding="utf-8")
        except OSError:
            return False
        return True

    async def package_install(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._closed:
            raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")
        if payload is not None and not isinstance(payload, dict):
            raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
        async with self._global_turn_lock:
            return await asyncio.to_thread(install_python_packages, self.xinyu_dir, payload or {})

    async def learning_ingest(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._closed:
            raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")
        if payload is not None and not isinstance(payload, dict):
            raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
        payload = payload or {}
        try:
            result = await learning_ingest_bridge(
                xinyu_dir=self.xinyu_dir,
                memory_root=self.memory_root,
                payload=payload,
                cleanup_idle_sessions=self._cleanup_idle_sessions,
                session_count=lambda: len(self._sessions),
                lock=self._global_turn_lock,
                load_local_env=_load_local_env,
            )
        except LearningBridgeError as exc:
            raise BridgeRequestError(exc.status, exc.message) from exc

        try:
            if record_recent_attachment_context(self.xinyu_dir, payload, result):
                notes = result.get("notes")
                if not isinstance(notes, list):
                    notes = []
                    result["notes"] = notes
                notes.append("recent_attachment_context_recorded")
        except Exception as exc:
            notes = result.get("notes")
            if not isinstance(notes, list):
                notes = []
                result["notes"] = notes
            notes.append(f"recent_attachment_context_error:{type(exc).__name__}")
        return result

        payload = payload or {}
        file_path = _safe_str(payload.get("file_path") or payload.get("path")).strip()
        file_url = _safe_str(payload.get("file_url") or payload.get("url")).strip()
        file_name = _safe_str(payload.get("file_name") or payload.get("name")).strip()
        if not file_path and not file_url:
            raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "file_path or file_url is required")

        origin = _safe_str(payload.get("origin"), "owner_supplied").strip() or "owner_supplied"
        reason = _safe_str(payload.get("reason"), "owner supplied QQ file").strip() or "owner supplied QQ file"
        question_id = _safe_str(payload.get("question_id"), "qq-file-learning").strip() or "qq-file-learning"
        title = _safe_str(payload.get("title") or file_name).strip()
        label = _safe_str(payload.get("label") or file_name).strip()
        stage = _as_bool(payload.get("stage"), default=True)
        curated = _as_bool(payload.get("curated"), default=(origin == "owner_supplied"))
        max_bytes = _as_int(payload.get("max_bytes"), DEFAULT_MAX_BYTES)
        if max_bytes <= 0:
            raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "max_bytes must be > 0")

        async with self._global_turn_lock:
            _load_local_env(self.xinyu_dir)
            cleanup = await self._cleanup_idle_sessions()
            before_memory = _memory_snapshot(self.memory_root)
            if file_path:
                source = _payload_path(file_path)
                metadata = await asyncio.to_thread(
                    add_local_material,
                    root=self.xinyu_dir,
                    path=source,
                    origin=origin,
                    reason=reason,
                    question_id=question_id,
                    title=title,
                    label=label,
                    max_bytes=max_bytes,
                )
            else:
                metadata = await asyncio.to_thread(
                    add_url_material,
                    root=self.xinyu_dir,
                    url=file_url,
                    origin=origin,
                    reason=reason,
                    question_id=question_id,
                    title=title,
                    label=label,
                    max_bytes=max_bytes,
                )
            material_id = ""
            if stage:
                material_id = await asyncio.to_thread(
                    stage_manifest_record,
                    self.xinyu_dir,
                    metadata,
                    curated,
                )
            after_memory = _memory_snapshot(self.memory_root)

        notes = ["learning_ingest", "no_agent_turn", "session_not_created"]
        if cleanup["cleaned_sessions"]:
            notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")
        if stage:
            notes.append(f"stage:{material_id}")
        else:
            notes.append("stage:skipped")

        title_for_reply = _safe_str(metadata.get("title") or file_name or metadata.get("id")).strip()
        extracted_text_path = _safe_str(metadata.get("extracted_text_path")).strip()
        staged_text = "，并登记到学习管道" if stage else ""
        extracted_text = "，已提取可阅读文本" if extracted_text_path else "，但暂时没有提取到可阅读文本"
        return {
            "accepted": True,
            "reply": f"收到了：{title_for_reply}。已经放进学习资料库{staged_text}{extracted_text}。",
            "memory_changed": before_memory != after_memory,
            "library_changed": True,
            "session_created": False,
            "sessions": len(self._sessions),
            "learning_item_id": metadata.get("id", ""),
            "material_id": material_id,
            "origin": metadata.get("origin", origin),
            "item_dir": metadata.get("item_dir", ""),
            "stored_paths": metadata.get("stored_paths", []),
            "extracted_text": bool(extracted_text_path),
            "extracted_text_path": extracted_text_path,
            "stage_status": material_id or "not_staged",
            "notes": notes,
        }

    async def learning_study(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._closed:
            raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")
        if payload is not None and not isinstance(payload, dict):
            raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
        return await learning_study_bridge(
            xinyu_dir=self.xinyu_dir,
            memory_root=self.memory_root,
            payload=payload or {},
            cleanup_idle_sessions=self._cleanup_idle_sessions,
            session_count=lambda: len(self._sessions),
            lock=self._global_turn_lock,
            load_local_env=_load_local_env,
        )

    async def learning_observe(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._closed:
            raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")
        if payload is not None and not isinstance(payload, dict):
            raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
        return await learning_observe_bridge(
            xinyu_dir=self.xinyu_dir,
            memory_root=self.memory_root,
            payload=payload or {},
            cleanup_idle_sessions=self._cleanup_idle_sessions,
            session_count=lambda: len(self._sessions),
            lock=self._global_turn_lock,
        )

    async def codex_execute(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._closed:
            raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")
        if payload is not None and not isinstance(payload, dict):
            raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
        payload = dict(payload or {})
        text = self._payload_text(payload)
        if not looks_like_codex_request(text):
            raise BridgeRequestError(
                HTTPStatus.BAD_REQUEST,
                "codex_execute requires an explicit Codex request or a learning/download/read request with URL",
            )
        text = self._augment_codex_payload_with_dialogue_context(payload, text)
        payload["visible_window"] = True
        payload["window_title"] = _safe_str(payload.get("window_title"), CODEX_VISIBLE_WINDOW_TITLE).strip() or CODEX_VISIBLE_WINDOW_TITLE

        auto_study = _as_bool(
            payload.get("auto_study"),
            default=_should_run_learning_after_codex(text),
        )

        background = _as_bool(
            payload.get("background"),
            default=_safe_str(payload.get("source")) == "qq_gateway_codex_execute_message",
        )
        if background:
            payload.setdefault("job_id", f"codex-qq-{datetime.now().astimezone().strftime('%Y%m%dT%H%M%S')}")
            payload.setdefault("timeout_seconds", CODEX_DEFAULT_TIMEOUT_SECONDS)
            payload.setdefault("network_access", True)
            paths = preview_codex_delegate_paths(self.xinyu_dir, payload)
            record_codex_presence(
                self.xinyu_dir,
                job_id=paths["job_id"],
                status="running",
                request_path=paths["request_path"],
                report_path=paths["report_path"],
                visible_window_title=_safe_str(payload.get("window_title"), CODEX_VISIBLE_WINDOW_TITLE),
            )
            cleanup = await self._cleanup_idle_sessions()
            asyncio.create_task(
                self._codex_delegate_background(payload, text=text, auto_study=auto_study),
                name=f"xinyu-codex-delegate-{paths['job_id']}",
            )
            notes = [
                "codex_delegate",
                "codex_delegate_background:scheduled",
                "dream_handoff_on_timeout:armed",
                f"job_id:{paths['job_id']}",
                "learning_after_codex:" + ("scheduled_after_finish" if auto_study else "skipped"),
            ]
            if cleanup["cleaned_sessions"]:
                notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")
            return {
                "accepted": True,
                "reply": self._codex_status_reply("started", paths=paths, auto_study=auto_study),
                "memory_changed": False,
                "library_changed": False,
                "session_created": False,
                "sessions": len(self._sessions),
                "request_path": paths["request_path"],
                "workspace_path": paths["workspace_path"],
                "report_path": paths["report_path"],
                "last_message_path": paths["last_message_path"],
                "codex_exit_code": None,
                "codex_timed_out": False,
                "stdout_tail": "",
                "stderr_tail": "",
                "source_integration_gate": {},
                "learner_integration": {},
                "learning_quality": {},
                "integrated_materials": 0,
                "ready_materials": 0,
                "blocked_unreadable_materials": 0,
                "quality_grade": "background",
                "notes": notes,
            }

        cleanup = await self._cleanup_idle_sessions()
        presence_paths = preview_codex_delegate_paths(self.xinyu_dir, payload)
        record_codex_presence(
            self.xinyu_dir,
            job_id=presence_paths["job_id"],
            status="running",
            request_path=presence_paths["request_path"],
            report_path=presence_paths["report_path"],
            visible_window_title=_safe_str(payload.get("window_title"), CODEX_VISIBLE_WINDOW_TITLE),
        )
        async with self._codex_delegate_lock:
            before_memory = _memory_snapshot(self.memory_root)
            try:
                result = await asyncio.to_thread(run_codex_delegate, self.xinyu_dir, payload)
            except Exception:
                record_codex_presence(
                    self.xinyu_dir,
                    job_id=presence_paths["job_id"],
                    status="failed",
                    request_path=presence_paths["request_path"],
                    report_path=presence_paths["report_path"],
                    visible_window_title=_safe_str(payload.get("window_title"), CODEX_VISIBLE_WINDOW_TITLE),
                )
                raise
            after_memory = _memory_snapshot(self.memory_root)

        learner: dict[str, object] = {}
        quality: dict[str, object] = {}
        gate: dict[str, object] = {}
        integrated = 0
        ready = 0
        blocked_unreadable = 0
        quality_grade = "scheduled" if result.accepted and auto_study else "not_run"

        paths = {
            "request_path": result.request_path,
            "workspace_path": result.workspace_path,
            "report_path": result.report_path,
            "last_message_path": result.last_message_path,
        }
        if result.timed_out:
            status = "timeout_staged" if result.accepted else "timeout"
        elif result.accepted:
            status = "done"
        else:
            status = "failed"
        record_codex_presence(
            self.xinyu_dir,
            job_id=presence_paths["job_id"],
            status="timed_out" if result.timed_out else ("finished" if result.accepted else "failed"),
            request_path=result.request_path or presence_paths["request_path"],
            report_path=result.report_path or presence_paths["report_path"],
            exit_code=result.exit_code,
            timed_out=result.timed_out,
            visible_window_title=_safe_str(payload.get("window_title"), CODEX_VISIBLE_WINDOW_TITLE),
        )
        reply = self._codex_status_reply(status, paths=paths, auto_study=auto_study, exit_code=result.exit_code)
        if result.accepted and auto_study:
            asyncio.create_task(self._codex_learning_followup("codex_delegate_async"))

        notes = list(result.notes)
        if result.timed_out or not result.accepted:
            try:
                async with self._global_turn_lock:
                    handoff = await asyncio.to_thread(
                        handoff_codex_to_dream,
                        self.xinyu_dir,
                        task_text=text,
                        report_path=result.report_path,
                        request_path=result.request_path,
                        workspace_path=result.workspace_path,
                        timed_out=result.timed_out,
                        exit_code=result.exit_code,
                    )
                notes.extend(handoff.notes)
            except Exception as exc:
                notes.append(f"codex_dream_handoff_failed:{type(exc).__name__}")
        notes.append("learning_after_codex:" + ("scheduled" if result.accepted and auto_study else "skipped"))
        if cleanup["cleaned_sessions"]:
            notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")

        return {
            "accepted": result.accepted,
            "reply": reply,
            "memory_changed": before_memory != after_memory,
            "library_changed": True,
            "session_created": False,
            "sessions": len(self._sessions),
            "request_path": result.request_path,
            "workspace_path": result.workspace_path,
            "report_path": result.report_path,
            "last_message_path": result.last_message_path,
            "codex_exit_code": result.exit_code,
            "codex_timed_out": result.timed_out,
            "stdout_tail": result.stdout_tail,
            "stderr_tail": result.stderr_tail,
            "source_integration_gate": gate,
            "learner_integration": learner,
            "learning_quality": quality,
            "integrated_materials": integrated,
            "ready_materials": ready,
            "blocked_unreadable_materials": blocked_unreadable,
            "quality_grade": quality_grade,
            "notes": notes,
        }

    def _extract_model_codex_delegate(self, reply: str) -> str:
        for pattern in CODEX_DELEGATE_PATTERNS:
            match = pattern.search(reply or "")
            if not match:
                continue
            task = re.sub(r"\s+", " ", match.group("task")).strip()
            task = re.sub(r"(?i)^@@task\s*=\s*", "", task).strip()
            return task[:4000]
        return ""

    def _extract_wait_to_think_task(self, reply: str, *, user_text: str, session_key: str) -> str:
        for pattern in WAIT_TO_THINK_PATTERNS:
            match = pattern.search(reply or "")
            if not match:
                continue
            raw_task = re.sub(r"\s+", " ", _safe_str(match.groupdict().get("task"))).strip()
            if not raw_task:
                raw_task = "verify the uncertain owner request before answering"
            return _normalize_reply(
                "\n".join(
                    [
                        "XinYu paused instead of faking certainty. Use Codex as asynchronous exploration.",
                        f"Owner message: {user_text}",
                        f"XinYu pause marker: {reply}",
                        f"Session: {session_key}",
                        (
                            "Task: investigate the concrete uncertainty, using web search, local repository inspection, "
                            "or small non-destructive validation commands only when relevant. Write a concise report with "
                            "what was checked, what is still uncertain, and the exact next answer XinYu can safely give. "
                            "Do not change files unless the owner has separately approved a self-code modification."
                        ),
                        f"Specific uncertainty: {raw_task}",
                    ]
                )
            )[:4000]
        return ""

    def _wait_to_think_execution_plan(self, wait_task: str, *, user_text: str) -> str:
        text = f"{wait_task}\n{user_text}".lower()
        write_risk = any(
            marker in text
            for marker in (
                " edit ",
                "write ",
                "delete",
                "move ",
                "install",
                "download",
                "modify",
                "patch",
                "apply",
                "修改",
                "写入",
                "删除",
                "移动",
                "安装",
                "下载",
                "改代码",
            )
        )
        if write_risk:
            risk = "high"
            plan_shape = "precise command/script draft required; Codex may only adjust paths/quoting and must not expand scope"
        else:
            risk = "read_only"
            plan_shape = "semi-structured read-only plan is acceptable; Codex translates final local commands"
        return _normalize_reply(
            "\n".join(
                [
                    f"risk_level: {risk}",
                    f"plan_shape: {plan_shape}",
                    "steps:",
                    "1. Restate the concrete uncertainty and expected evidence before running anything.",
                    "2. Execute only the smallest read-only checks needed unless a separate owner-approved ticket permits writes.",
                    "3. If a step fails, record the failure kind and stop or choose the listed fallback; do not invent success.",
                    "4. Return a sanitized summary, verified scope, unknowns, and whether owner narrowing is needed.",
                    "forbidden:",
                    "- no credential/cookie/token reading",
                    "- no destructive file operations",
                    "- no dependency install or code modification unless an explicit approval ticket is present",
                    "- no raw stdout/stderr injection into the final answer",
                ]
            )
        )

    def _extract_self_code_approval_id(self, task_text: str) -> str:
        match = re.search(r"(?im)^\s*Self-code approval id:\s*([A-Za-z0-9_-]+)\s*$", task_text or "")
        return match.group(1).strip() if match else "unknown"

    async def _transition_wait_to_think_reply(
        self,
        payload: dict[str, Any],
        *,
        user_text: str,
        draft_reply: str,
        wait_task: str,
        session_key: str,
    ) -> tuple[str, dict[str, Any]]:
        closure = create_async_exploration_closure(
            self.xinyu_dir,
            payload,
            session_key=session_key,
            user_text=user_text,
            draft_reply=draft_reply,
            task_text=wait_task,
            delegation_reason="model_wait_to_think",
            execution_plan=self._wait_to_think_execution_plan(wait_task, user_text=user_text),
        )
        transition = _safe_str(closure.get("transition_message")).strip() or "我去后台验证一下，等结果出来再接着说。"
        resume_id = _safe_str(closure.get("resume_id")).strip()
        if resume_id:
            wait_task = f"{wait_task}\n\nSuspension resume_id: {resume_id}"
        plan = self._wait_to_think_execution_plan(wait_task, user_text=user_text)
        wait_task = f"{wait_task}\n\nStructured execution plan:\n{plan}"
        codex_payload = self._build_model_codex_payload(
            payload,
            session_key=session_key,
            task_text=wait_task,
        )
        codex_payload["metadata"]["delegated_by_wait_to_think"] = True
        codex_payload["metadata"]["async_resume_id"] = resume_id
        codex_payload["auto_study"] = False
        try:
            await self.codex_execute(codex_payload)
            note = "wait_to_think_codex_scheduled"
        except Exception as exc:
            update = update_async_exploration_from_codex(
                self.xinyu_dir,
                resume_id=resume_id or "wait-unknown",
                result=None,
                error=f"{type(exc).__name__}: {exc}",
            )
            note = "wait_to_think_schedule_error"
            user_id = _safe_str(payload.get("user_id")).strip() or self._owner_private_user_id()
            if user_id:
                enqueue_qq_outbox_message(
                    self.xinyu_dir,
                    user_id=user_id,
                    message=async_exploration_outbox_message(update),
                    source="async_exploration_failure",
                    dedupe_key=f"async_exploration_failure:{resume_id or user_text[:80]}",
                    metadata={"resume_id": resume_id, "has_error": True},
                )
        return transition, {
            "notes": [
                _safe_str(note),
                *[_safe_str(item) for item in closure.get("notes", [])],
            ],
            "resume_id": resume_id,
        }

    def _can_model_delegate_codex(self, payload: dict[str, Any]) -> bool:
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        if not _as_bool(metadata.get("is_owner_user"), default=False):
            return False
        message_type = _safe_str(payload.get("message_type")).lower()
        if message_type and not message_type.startswith("private"):
            return False
        group_id = _safe_str(payload.get("group_id")).strip()
        return group_id in {"", "0", "none", "None"}

    def _build_model_codex_payload(
        self,
        payload: dict[str, Any],
        *,
        session_key: str,
        task_text: str,
    ) -> dict[str, Any]:
        metadata = {
            "gateway": _safe_str(payload.get("adapter"), "xinyu_core_bridge"),
            "source": "qq_gateway_codex_execute_message",
            "is_owner_user": True,
            "codex_auxiliary_brain": True,
            "direct_cli_execution": False,
            "delegated_by_model": True,
        }
        return {
            "platform": _safe_str(payload.get("platform"), "qq"),
            "adapter": _safe_str(payload.get("adapter"), "xinyu_core_bridge"),
            "message_type": "private_codex_model_delegate",
            "session_id": session_key,
            "user_id": _safe_str(payload.get("user_id")),
            "sender_name": _safe_str(payload.get("sender_name")),
            "group_id": None,
            "bot_id": _safe_str(payload.get("bot_id")),
            "message_id": _safe_str(payload.get("message_id")),
            "text": f"Use Codex auxiliary brain for this owner-approved task:\n{task_text}",
            "raw_owner_task": task_text,
            "source": "qq_gateway_codex_execute_message",
            "background": True,
            "auto_study": True,
            "timeout_seconds": CODEX_DEFAULT_TIMEOUT_SECONDS,
            "visible_window": True,
            "window_title": CODEX_VISIBLE_WINDOW_TITLE,
            "network_access": True,
            "include_dialogue_context": True,
            "timestamp": _as_int(payload.get("timestamp"), int(time.time())),
            "metadata": metadata,
        }

    def _augment_codex_payload_with_dialogue_context(self, payload: dict[str, Any], text: str) -> str:
        if _safe_str(payload.get("source")) != "qq_gateway_codex_execute_message":
            return text
        if not _as_bool(payload.get("include_dialogue_context"), default=True):
            return text
        session_key = _safe_str(payload.get("session_id")).strip()
        if not session_key:
            return text
        tail = load_dialogue_tail(self.xinyu_dir, session_key, max_entries=8)
        if not tail:
            return text
        raw_task = _safe_str(payload.get("raw_owner_task")).strip() or text
        tail_block = self._format_dialogue_tail(tail)
        augmented = "\n\n".join(
            [
                text,
                "Recent QQ context before this Codex request:",
                tail_block,
                "Use the recent context only to resolve references in the owner task.",
                f"Current owner Codex task: {raw_task}",
            ]
        )
        payload["text"] = augmented
        payload["codex_context_included"] = True
        metadata = payload.get("metadata")
        if isinstance(metadata, dict):
            metadata["dialogue_context_included"] = True
        return augmented

    def _codex_status_reply(
        self,
        status: str,
        *,
        paths: dict[str, str],
        auto_study: bool,
        exit_code: int | None = None,
    ) -> str:
        report_path = _safe_str(paths.get("report_path")).strip()
        request_path = _safe_str(paths.get("request_path")).strip()
        report_label = Path(report_path).name if report_path else "Codex Outbox"
        request_label = Path(request_path).name if request_path else "Codex Requests"
        if status == "started":
            return f"开了，我让 Codex 在新窗口里跑，你能直接看它动。窗口标题是 {CODEX_VISIBLE_WINDOW_TITLE}，报告会落到本地 Codex Outbox：{report_label}。"
        if status == "done":
            return f"跑完了。报告在本地 Codex Outbox：{report_label}。"
        if status == "timeout_staged":
            return f"它超时了，这次不能算完整跑完；链接我先收进学习暂存。报告目标还是本地 Codex Outbox：{report_label}。"
        if status == "timeout":
            return f"它超时了，不算完成。请求留在本地 Codex Requests：{request_label}。"
        if exit_code is not None:
            return f"这次没跑顺，退出码 {exit_code}。报告目标是本地 Codex Outbox：{report_label}。"
        return f"这次没正常跑起来。报告目标是本地 Codex Outbox：{report_label}。"

    def _codex_completion_summary(self, result: Any, *, limit: int = 220) -> str:
        candidates: list[str] = []
        for path_text in (_safe_str(getattr(result, "last_message_path", "")), _safe_str(getattr(result, "report_path", ""))):
            if not path_text:
                continue
            path = Path(path_text)
            if not path.is_absolute():
                path = self.xinyu_dir / path
            try:
                text = path.read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            for raw_line in text.splitlines():
                line = raw_line.strip()
                if not line or line in {"---", "```", "```text"}:
                    continue
                if line.startswith(("#", "title:", "status:", "generated_at:", "## Stdout", "## Stderr")):
                    continue
                if re.search(r"(?i)([a-z]:\\|/users/|/home/|\\\\|token|api[_-]?key|stderr|stdout)", line):
                    continue
                line = re.sub(r"(?i)([a-z]:\\[^\\s]+|/users/\\S+|/home/\\S+|\\\\\\S+)", "<local_path>", line)
                line = re.sub(r"\s+", " ", line).strip("- ").strip()
                if line and line.lower() not in {"none", "unknown"}:
                    candidates.append(line)
                if len(candidates) >= 3:
                    break
            if candidates:
                break

        summary = "；".join(candidates[:3]).strip()
        if len(summary) > limit:
            summary = summary[: limit - 3].rstrip() + "..."
        return summary

    def _codex_completion_outbox_message(
        self,
        result: Any,
        *,
        text: str,
        auto_study: bool,
        handoff_notes: list[str],
    ) -> str:
        report_path = _safe_str(getattr(result, "report_path", ""))
        report_label = Path(report_path).name if report_path else "Codex Outbox"
        report_file = Path(report_path) if report_path else None
        if report_file is not None and not report_file.is_absolute():
            report_file = self.xinyu_dir / report_file
        report_exists = bool(report_file and report_file.exists())
        exit_code = getattr(result, "exit_code", None)
        timed_out = bool(getattr(result, "timed_out", False))
        accepted = bool(getattr(result, "accepted", False))
        summary = self._codex_completion_summary(result)

        if timed_out:
            head = "Codex 超时了，这次不能算完成。"
        elif accepted:
            head = "Codex 跑完了。"
        elif exit_code is not None:
            head = f"Codex 没跑顺，退出码 {exit_code}。"
        else:
            head = "Codex 这次没有正常完成。"

        parts = [head]
        if summary:
            parts.append(summary)
        if timed_out or handoff_notes:
            parts.append("我先把这件事留住，后面继续查。")
        elif accepted and auto_study:
            parts.append("后面的学习整合我放后台。")
        if report_exists:
            parts.append(f"报告在本地 Codex Outbox：{report_label}。")
        else:
            parts.append("这次没有写出报告，trace 留在本地 Codex Outbox。")
        return re.sub(r"\s+", " ", "".join(parts)).strip()

    def _enqueue_codex_completion_if_needed(
        self,
        payload: dict[str, Any],
        *,
        result: Any | None,
        text: str,
        auto_study: bool,
        handoff_notes: list[str],
        error: str = "",
    ) -> None:
        if _safe_str(payload.get("source")) != "qq_gateway_codex_execute_message":
            return
        metadata = payload.get("metadata")
        if isinstance(metadata, dict) and _safe_str(metadata.get("async_resume_id")).strip():
            return
        user_id = _safe_str(payload.get("user_id")).strip()
        if not user_id:
            return
        job_id = _safe_str(payload.get("job_id")).strip()
        if not job_id and result is not None:
            job_id = Path(_safe_str(getattr(result, "report_path", ""))).stem or "codex-qq"

        if error:
            message = f"Codex 辅助脑这次在后台报错了：{error}。我没有把它当成完成，会留在本地日志里继续查。"
        elif result is not None:
            message = self._codex_completion_outbox_message(
                result,
                text=text,
                auto_study=auto_study,
                handoff_notes=handoff_notes,
            )
        else:
            return

        enqueue_qq_outbox_message(
            self.xinyu_dir,
            user_id=user_id,
            message=message,
            source="codex_completion",
            dedupe_key=f"codex_completion:{job_id or text[:80]}",
            metadata={
                "job_id": job_id,
                "task_preview": text[:240],
                "auto_study": auto_study,
                "has_error": bool(error),
            },
        )

    async def _codex_delegate_background(self, payload: dict[str, Any], *, text: str, auto_study: bool) -> None:
        trace_path = self.memory_root / "knowledge/codex_delegate_background_trace.log"
        started_at = datetime.now().astimezone().isoformat()
        presence_paths = preview_codex_delegate_paths(self.xinyu_dir, payload)
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        async_resume_id = _safe_str(metadata.get("async_resume_id")).strip()
        owner_intervention = _safe_str(metadata.get("owner_intervention")).strip()
        try:
            async with self._codex_delegate_lock:
                result = await asyncio.to_thread(run_codex_delegate, self.xinyu_dir, payload)
            handoff_notes: list[str] = []
            if result.timed_out or not result.accepted:
                handoff = await asyncio.to_thread(
                    handoff_codex_to_dream,
                    self.xinyu_dir,
                    task_text=text,
                    report_path=result.report_path,
                    request_path=result.request_path,
                    workspace_path=result.workspace_path,
                    timed_out=result.timed_out,
                    exit_code=result.exit_code,
                )
                handoff_notes = handoff.notes
            if result.accepted and auto_study:
                asyncio.create_task(
                    self._codex_learning_followup("codex_delegate_async"),
                    name="xinyu-codex-learning-followup",
                )
            record_codex_presence(
                self.xinyu_dir,
                job_id=presence_paths["job_id"],
                status="timed_out" if result.timed_out else ("finished" if result.accepted else "failed"),
                request_path=result.request_path or presence_paths["request_path"],
                report_path=result.report_path or presence_paths["report_path"],
                exit_code=result.exit_code,
                timed_out=result.timed_out,
                visible_window_title=_safe_str(payload.get("window_title"), CODEX_VISIBLE_WINDOW_TITLE),
            )
            self._enqueue_codex_completion_if_needed(
                payload,
                result=result,
                text=text,
                auto_study=auto_study,
                handoff_notes=handoff_notes,
            )
            if async_resume_id:
                update = update_async_exploration_from_codex(
                    self.xinyu_dir,
                    resume_id=async_resume_id,
                    result=result,
                    owner_intervention=owner_intervention,
                )
                user_id = _safe_str(payload.get("user_id")).strip() or self._owner_private_user_id()
                if user_id:
                    enqueue_qq_outbox_message(
                        self.xinyu_dir,
                        user_id=user_id,
                        message=async_exploration_outbox_message(update),
                        source="async_exploration_result",
                        dedupe_key=f"async_exploration_result:{async_resume_id}",
                        metadata={
                            "resume_id": async_resume_id,
                            "result_quality": update.get("result_quality", "unknown"),
                            "owner_intervention": owner_intervention,
                        },
                    )
            line = (
                f"{datetime.now().astimezone().isoformat()} ok "
                f"started_at={started_at} accepted={result.accepted} timed_out={result.timed_out} "
                f"exit={result.exit_code if result.exit_code is not None else 'timeout'} "
                f"report={result.report_path} dream_handoff={';'.join(handoff_notes) or 'none'} "
                f"text={text[:120]!r}\n"
            )
        except Exception as exc:
            record_codex_presence(
                self.xinyu_dir,
                job_id=presence_paths["job_id"],
                status="failed",
                request_path=presence_paths["request_path"],
                report_path=presence_paths["report_path"],
                visible_window_title=_safe_str(payload.get("window_title"), CODEX_VISIBLE_WINDOW_TITLE),
            )
            self._enqueue_codex_completion_if_needed(
                payload,
                result=None,
                text=text,
                auto_study=auto_study,
                handoff_notes=[],
                error=f"{type(exc).__name__}: {exc}",
            )
            if async_resume_id:
                update = update_async_exploration_from_codex(
                    self.xinyu_dir,
                    resume_id=async_resume_id,
                    result=None,
                    error=f"{type(exc).__name__}: {exc}",
                    owner_intervention=owner_intervention,
                )
                user_id = _safe_str(payload.get("user_id")).strip() or self._owner_private_user_id()
                if user_id:
                    enqueue_qq_outbox_message(
                        self.xinyu_dir,
                        user_id=user_id,
                        message=async_exploration_outbox_message(update),
                        source="async_exploration_result",
                        dedupe_key=f"async_exploration_result:{async_resume_id}",
                        metadata={"resume_id": async_resume_id, "has_error": True},
                    )
            line = (
                f"{datetime.now().astimezone().isoformat()} error "
                f"started_at={started_at} {type(exc).__name__}: {exc} text={text[:120]!r}\n"
            )
        try:
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            with trace_path.open("a", encoding="utf-8") as fh:
                fh.write(line)
        except Exception:
            pass

    async def _codex_learning_followup(self, mode: str) -> None:
        trace_path = self.memory_root / "knowledge/codex_learning_followup_trace.log"
        started_at = datetime.now().astimezone().isoformat()
        try:
            async with self._global_turn_lock:
                result = await asyncio.to_thread(_run_learning_study_chain, self.xinyu_dir, mode)
            learner = result.get("learner_integration", {}) if isinstance(result, dict) else {}
            quality = result.get("learning_quality", {}) if isinstance(result, dict) else {}
            integrated = _int_result(learner if isinstance(learner, dict) else {}, "newly_integrated_materials")
            quality_grade = _safe_str(quality.get("quality_grade"), "unknown") if isinstance(quality, dict) else "unknown"
            line = (
                f"{datetime.now().astimezone().isoformat()} ok "
                f"started_at={started_at} integrated={integrated} quality={quality_grade}\n"
            )
        except Exception as exc:
            line = (
                f"{datetime.now().astimezone().isoformat()} error "
                f"started_at={started_at} {type(exc).__name__}: {exc}\n"
            )
        try:
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            with trace_path.open("a", encoding="utf-8") as fh:
                fh.write(line)
        except Exception:
            pass

    async def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._closed:
            raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")
        if not isinstance(payload, dict):
            raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")

        text = self._payload_text(payload)
        if not text:
            return {
                "accepted": True,
                "reply": "",
                "memory_changed": False,
                "notes": ["empty_text"],
            }
        if len(text) > self.max_text_chars:
            raise BridgeRequestError(
                HTTPStatus.PAYLOAD_TOO_LARGE,
                f"text is too long: {len(text)} chars > {self.max_text_chars}",
            )

        session_key = self._session_key(payload)
        turn_started_at = time.perf_counter()
        presence_start: dict[str, Any] = {"turn_id": ""}
        async with self._global_turn_lock:
            cleanup = await self._cleanup_idle_sessions()
            presence_start = record_turn_started(
                self.xinyu_dir,
                payload=payload,
                text=text,
                session_key=session_key,
                active_sessions=len(self._sessions),
            )
            before_memory = _memory_snapshot(self.memory_root)
            curiosity_eval: dict[str, Any] = {"notes": []}
            try:
                curiosity_eval = evaluate_previous_reaction(
                    self.xinyu_dir,
                    payload,
                    text=text,
                    session_key=session_key,
                )
            except Exception as exc:
                print(f"[xinyu_core_bridge] dialogue curiosity evaluation failed: {exc}", flush=True)
                curiosity_eval = {"notes": [f"dialogue_curiosity_eval_error:{type(exc).__name__}"]}
            private_thought_outcome: dict[str, Any] = {"notes": []}
            try:
                private_thought_outcome = record_private_thought_outcome(
                    self.xinyu_dir,
                    payload,
                    text=text,
                    session_key=session_key,
                    evaluation=curiosity_eval,
                )
            except Exception as exc:
                print(f"[xinyu_core_bridge] private thought outcome failed: {exc}", flush=True)
                private_thought_outcome = {"notes": [f"private_thought_outcome_error:{type(exc).__name__}"]}
            uncertainty_pause_reply: dict[str, Any] = {"notes": []}
            try:
                uncertainty_pause_reply = mark_uncertainty_pause_replied(
                    self.xinyu_dir,
                    text=text,
                    observed_at=datetime.now().astimezone().isoformat(),
                )
            except Exception as exc:
                print(f"[xinyu_core_bridge] uncertainty pause reply mark failed: {exc}", flush=True)
                uncertainty_pause_reply = {"notes": [f"uncertainty_pause_reply_error:{type(exc).__name__}"]}
            event_sidecar: dict[str, Any] = {"notes": ["event_sourcing_not_run"]}
            v1_shadow: dict[str, Any] = {"notes": []}
            try:
                event_sidecar = record_chat_event(self.xinyu_dir, payload, text=text)
            except Exception as exc:
                print(f"[xinyu_core_bridge] event sourcing sidecar failed: {exc}", flush=True)
                event_sidecar = {"notes": [f"event_sourcing_error:{type(exc).__name__}"]}
            v1_shadow = await self._run_v1_shadow(payload, text=text)
            session = await self._get_session(session_key)
            proactive_tail_synced = self._sync_recent_proactive_to_dialogue_tail(session, payload)
            persona_sidecar: dict[str, Any] = {"notes": ["persona_state_not_run"], "prompt_block": ""}
            try:
                persona_sidecar = observe_persona_turn(self.xinyu_dir, payload, text=text)
            except Exception as exc:
                print(f"[xinyu_core_bridge] persona state sidecar failed: {exc}", flush=True)
                persona_sidecar = {
                    "notes": [f"persona_state_error:{type(exc).__name__}"],
                    "prompt_block": "",
                }
            session.chunks.clear()
            event = self._create_user_input_event(
                text,
                source="qq_gateway",
                bridge_payload=payload,
                platform=_safe_str(payload.get("platform"), "qq"),
                message_type=_safe_str(payload.get("message_type")),
                session_id=session_key,
                user_id=_safe_str(payload.get("user_id")),
                sender_name=_safe_str(payload.get("sender_name")),
                received_at=int(time.time()),
            )
            visible_turn = classify_visible_turn(self.xinyu_dir, payload=payload, user_text=text)
            recalled_context = None
            recalled_context_notes: list[str] = []
            try:
                recalled_context = retrieve_recalled_context(
                    self.xinyu_dir,
                    payload,
                    user_text=text,
                    dialogue_tail=session.dialogue_tail,
                    visible_turn=visible_turn,
                )
                recalled_context_notes.extend(_safe_str(note) for note in recalled_context.notes[:3])
            except Exception as exc:
                print(f"[xinyu_core_bridge] context retrieval failed: {exc}", flush=True)
                recalled_context_notes.append(f"context_retrieval_error:{type(exc).__name__}")

            continuity_handoff: dict[str, Any] = {"notes": []}
            try:
                continuity_handoff = refresh_continuity_handoff(
                    self.xinyu_dir,
                    user_text=text,
                    observed_at=datetime.now().astimezone().isoformat(),
                )
            except Exception as exc:
                print(f"[xinyu_core_bridge] continuity handoff failed: {exc}", flush=True)
                continuity_handoff = {"notes": [f"continuity_handoff_error:{type(exc).__name__}"]}
            runtime_presence_context = build_runtime_presence_prompt_block(self.xinyu_dir, limit=2200)
            try:
                self._inject_live_turn_context(
                    session.agent,
                    payload=payload,
                    text=text,
                    dialogue_tail=session.dialogue_tail,
                    persona_context=_safe_str(persona_sidecar.get("prompt_block")),
                    curiosity_context=_safe_str(curiosity_eval.get("prompt_block")),
                    visible_turn=visible_turn,
                    recalled_context=_safe_str(getattr(recalled_context, "prompt_block", "")),
                    runtime_presence_context=runtime_presence_context,
                    continuity_context=build_continuity_handoff_prompt_block(self.xinyu_dir, user_text=text),
                    uncertainty_pause_context=build_uncertainty_pause_prompt_block(self.xinyu_dir),
                )
                await asyncio.wait_for(
                    session.agent.inject_event(event),
                    timeout=self.turn_timeout_seconds,
                )
            except TimeoutError as exc:
                try:
                    session.agent.interrupt()
                except Exception:
                    pass
                record_turn_finished(
                    self.xinyu_dir,
                    turn_id=_safe_str(presence_start.get("turn_id")),
                    reply="",
                    elapsed_ms=int((time.perf_counter() - turn_started_at) * 1000),
                    status="timeout",
                    notes=["turn_timeout"],
                )
                raise BridgeRequestError(
                    HTTPStatus.GATEWAY_TIMEOUT,
                    f"XinYu turn timed out after {self.turn_timeout_seconds} seconds",
                ) from exc
            except Exception as exc:
                record_turn_finished(
                    self.xinyu_dir,
                    turn_id=_safe_str(presence_start.get("turn_id")),
                    reply="",
                    elapsed_ms=int((time.perf_counter() - turn_started_at) * 1000),
                    status="error",
                    notes=[f"turn_error:{type(exc).__name__}"],
                )
                raise

            if self.settle_seconds > 0:
                await asyncio.sleep(self.settle_seconds)

            session.last_used_at = time.time()
            draft_reply = _normalize_reply("".join(session.chunks))
            reply = draft_reply
            rendered = False
            renderer_reason = ""
            model_codex_delegate_note = ""
            model_codex_task = self._extract_model_codex_delegate(draft_reply)
            wait_to_think_task = self._extract_wait_to_think_task(
                draft_reply,
                user_text=text,
                session_key=session_key,
            )
            direct_codex_task = ""
            wait_to_think_sidecar: dict[str, Any] = {"notes": []}
            self_code_task = self._owner_self_code_iteration_task(
                payload,
                user_text=text,
                reply=draft_reply,
                session_key=session_key,
            )
            if wait_to_think_task and not self_code_task and not model_codex_task:
                reply, wait_to_think_sidecar = await self._transition_wait_to_think_reply(
                    payload,
                    user_text=text,
                    draft_reply=draft_reply,
                    wait_task=wait_to_think_task,
                    session_key=session_key,
                )
                model_codex_delegate_note = "wait_to_think:scheduled"
                self._replace_last_assistant_message(session.agent, reply)
            elif self_code_task:
                codex_state = self._codex_delegate_running()
                if codex_state.get("running"):
                    reply = self._codex_busy_reply(codex_state)
                    model_codex_delegate_note = "owner_self_code_iteration:codex_busy"
                else:
                    codex_payload = self._build_model_codex_payload(
                        payload,
                        session_key=session_key,
                        task_text=self_code_task,
                    )
                    codex_payload["auto_study"] = False
                    codex_payload["metadata"]["delegated_by_model"] = False
                    codex_payload["metadata"]["delegated_by_owner_self_code_iteration"] = True
                    codex_payload["metadata"]["self_code_iteration"] = True
                    approval_id = self._extract_self_code_approval_id(self_code_task)
                    codex_payload["metadata"]["approval_id"] = approval_id
                    codex_payload["metadata"]["owner_intervention"] = (
                        "owner private direct self-code request"
                        if approval_id.startswith("selfcode-direct-")
                        else "owner approved one-time self-code ticket through QQ"
                    )
                    try:
                        codex_response = await self.codex_execute(codex_payload)
                        mark_self_code_execution_scheduled(
                            self.xinyu_dir,
                            approval_id=approval_id,
                            job_id=_safe_str(codex_response.get("request_path") or codex_response.get("report_path") or ""),
                        )
                        reply = _normalize_reply(_safe_str(codex_response.get("reply")))
                        if not reply:
                            reply = "开了，我让 Codex 在专门窗口里做一个小范围代码改动。"
                        model_codex_delegate_note = "owner_self_code_iteration:scheduled"
                    except BridgeRequestError as exc:
                        reply = exc.message
                        model_codex_delegate_note = f"owner_self_code_iteration_error:{exc.status.value}"
                self._replace_last_assistant_message(session.agent, reply)
            elif model_codex_task:
                if self._can_model_delegate_codex(payload):
                    codex_payload = self._build_model_codex_payload(
                        payload,
                        session_key=session_key,
                        task_text=model_codex_task,
                    )
                    try:
                        codex_response = await self.codex_execute(codex_payload)
                        reply = _normalize_reply(_safe_str(codex_response.get("reply")))
                        if not reply:
                            reply = "我已经把这个任务交给 Codex 辅助脑了。"
                        model_codex_delegate_note = "model_codex_delegate:scheduled"
                    except BridgeRequestError as exc:
                        reply = exc.message
                        model_codex_delegate_note = f"model_codex_delegate_error:{exc.status.value}"
                    self._replace_last_assistant_message(session.agent, reply)
                else:
                    reply = "这类 Codex 本机委托只接受 owner 私聊。"
                    model_codex_delegate_note = "model_codex_delegate_rejected:not_owner_private"
                    self._replace_last_assistant_message(session.agent, reply)
            if not self_code_task and not model_codex_task and not wait_to_think_task:
                direct_codex_task = self._owner_direct_codex_task(
                    payload,
                    user_text=text,
                    reply=draft_reply,
                    session_key=session_key,
                )
                if direct_codex_task:
                    codex_payload = self._build_model_codex_payload(
                        payload,
                        session_key=session_key,
                        task_text=direct_codex_task,
                    )
                    codex_payload["metadata"]["delegated_by_owner_directive"] = True
                    try:
                        codex_response = await self.codex_execute(codex_payload)
                        reply = _normalize_reply(_safe_str(codex_response.get("reply")))
                        if not reply:
                            reply = "开了，我让 Codex 在专门窗口里查。"
                        model_codex_delegate_note = "owner_direct_codex_delegate:scheduled"
                    except BridgeRequestError as exc:
                        reply = exc.message
                        model_codex_delegate_note = f"owner_direct_codex_delegate_error:{exc.status.value}"
                    self._replace_last_assistant_message(session.agent, reply)
            if self.outward_renderer and not self_code_task and not model_codex_task and not direct_codex_task and not wait_to_think_task:
                renderer_reason = self._renderer_reason(
                    payload=payload,
                    user_text=text,
                    draft_reply=draft_reply,
                )
                if renderer_reason:
                    rendered_reply = await self._render_outward_reply(
                        session.agent,
                        payload=payload,
                        user_text=text,
                        draft_reply=draft_reply,
                    )
                    if rendered_reply:
                        reply = rendered_reply
                        rendered = True
                        self._replace_last_assistant_message(session.agent, rendered_reply)
            guarded_reply, final_guard_flags = self.speech_controller.final_reply_guard(
                payload=payload,
                user_text=text,
                reply=reply,
            )
            expression_learning: dict[str, Any] = {"notes": []}
            critical_guard_flags = self._critical_final_guard_flags(final_guard_flags)
            if critical_guard_flags and not self_code_task and not model_codex_task and not direct_codex_task:
                bad_reply = reply
                repaired_reply = await self._render_outward_reply(
                    session.agent,
                    payload=payload,
                    user_text=text,
                    draft_reply=bad_reply,
                )
                repaired_guarded, repaired_flags = self.speech_controller.final_reply_guard(
                    payload=payload,
                    user_text=text,
                    reply=repaired_reply,
                )
                if repaired_guarded and not self._critical_final_guard_flags(repaired_flags):
                    guarded_reply = repaired_guarded
                    final_guard_flags = _dedupe(final_guard_flags + ["final_guard_repair_rendered"] + repaired_flags)
                    self._replace_last_assistant_message(session.agent, repaired_guarded)
                else:
                    guarded_reply = ""
                    final_guard_flags = _dedupe(final_guard_flags + ["final_guard_blocked_unsendable_reply"] + repaired_flags)
                    self._replace_last_assistant_message(session.agent, "")
                try:
                    expression_learning = record_expression_self_learning_event(
                        self.xinyu_dir,
                        user_text=text,
                        bad_reply=bad_reply,
                        repaired_reply=guarded_reply,
                        flags=critical_guard_flags,
                        failure_kind="visible_mechanism_or_template_leak",
                    )
                except Exception as exc:
                    print(f"[xinyu_core_bridge] expression self-learning failed: {exc}", flush=True)
                    expression_learning = {"notes": [f"expression_self_learning_error:{type(exc).__name__}"]}
            final_guard_applied = guarded_reply != reply
            if final_guard_applied:
                reply = guarded_reply
                self._replace_last_assistant_message(session.agent, guarded_reply)
            uncertainty_pause: dict[str, Any] = {"notes": []}
            if is_waiting_reply(reply):
                try:
                    uncertainty_pause = record_uncertainty_pause(
                        self.xinyu_dir,
                        payload,
                        user_text=text,
                        draft_reply=draft_reply,
                        final_reply=reply,
                        reason="waiting_marker",
                        final_guard_flags=final_guard_flags,
                        session_key=session_key,
                        visible_turn_kind=_safe_str(getattr(visible_turn, "turn_kind", "")),
                    )
                except Exception as exc:
                    print(f"[xinyu_core_bridge] uncertainty pause failed: {exc}", flush=True)
                    uncertainty_pause = {"notes": [f"uncertainty_pause_error:{type(exc).__name__}"]}
            elif "final_guard_blocked_unsendable_reply" in final_guard_flags:
                try:
                    uncertainty_pause = record_uncertainty_pause(
                        self.xinyu_dir,
                        payload,
                        user_text=text,
                        draft_reply=draft_reply,
                        final_reply=reply,
                        reason="final_guard_blocked_unsendable_reply",
                        final_guard_flags=final_guard_flags,
                        session_key=session_key,
                        visible_turn_kind=_safe_str(getattr(visible_turn, "turn_kind", "")),
                    )
                except Exception as exc:
                    print(f"[xinyu_core_bridge] uncertainty pause failed: {exc}", flush=True)
                    uncertainty_pause = {"notes": [f"uncertainty_pause_error:{type(exc).__name__}"]}
            learning_closed_loop: dict[str, Any] = {"notes": []}
            try:
                closed_loop_quality_flags = (
                    self.speech_controller.reply_quality_flags(
                        payload=payload,
                        user_text=text,
                        reply=reply,
                    )
                    if reply
                    else []
                )
                learning_closed_loop = record_learning_closed_loop_turn(
                    self.xinyu_dir,
                    payload,
                    user_text=text,
                    reply=reply,
                    session_key=session_key,
                    visible_turn_kind=_safe_str(getattr(visible_turn, "turn_kind", "")),
                    final_guard_flags=final_guard_flags,
                    quality_flags=closed_loop_quality_flags,
                    expression_notes=[_safe_str(note) for note in expression_learning.get("notes", [])],
                )
            except Exception as exc:
                print(f"[xinyu_core_bridge] learning closed loop failed: {exc}", flush=True)
                learning_closed_loop = {"notes": [f"learning_closed_loop_error:{type(exc).__name__}"]}
            residue_written = write_turn_residue(
                self.xinyu_dir,
                scene=self.speech_controller.classify(payload=payload, user_text=text),
                user_text=text,
                reply=reply,
                source="qq_gateway",
            )
            metadata = payload.get("metadata")
            if not isinstance(metadata, dict):
                metadata = {}
            is_owner = _as_bool(metadata.get("is_owner_user"), default=False)
            voice_calibrated = False
            if is_owner:
                voice_calibrated = record_voice_correction(
                    self.xinyu_dir,
                    user_text=text,
                    reply=reply,
                    source="qq_gateway",
                )
            curiosity_prediction: dict[str, Any] = {"notes": []}
            try:
                curiosity_prediction = record_reply_prediction(
                    self.xinyu_dir,
                    payload,
                    user_text=text,
                    reply=reply,
                    session_key=session_key,
                )
            except Exception as exc:
                print(f"[xinyu_core_bridge] dialogue curiosity prediction failed: {exc}", flush=True)
                curiosity_prediction = {"notes": [f"dialogue_curiosity_prediction_error:{type(exc).__name__}"]}
            private_thought_link: dict[str, Any] = {"notes": []}
            try:
                private_thought_link = record_private_thought_reply_link(
                    self.xinyu_dir,
                    payload,
                    user_text=text,
                    reply=reply,
                    session_key=session_key,
                )
            except Exception as exc:
                print(f"[xinyu_core_bridge] private thought reply link failed: {exc}", flush=True)
                private_thought_link = {"notes": [f"private_thought_link_error:{type(exc).__name__}"]}
            archive_result: dict[str, Any] = {"notes": [], "message_ids": []}
            try:
                archive_result = archive_dialogue_turn(
                    self.xinyu_dir,
                    payload,
                    user_text=text,
                    assistant_reply=reply,
                    message_type=_safe_str(getattr(visible_turn, "turn_kind", "")),
                    quality_flags=final_guard_flags,
                )
            except Exception as exc:
                print(f"[xinyu_core_bridge] dialogue archive failed: {exc}", flush=True)
                archive_result = {"notes": [f"dialogue_archive_error:{type(exc).__name__}"], "message_ids": []}
            if recalled_context is not None and getattr(recalled_context, "items", ()):
                try:
                    if log_recalled_context(self.xinyu_dir, recalled_context):
                        recalled_context_notes.append("recalled_context_logged")
                except Exception as exc:
                    print(f"[xinyu_core_bridge] recalled context log failed: {exc}", flush=True)
                    recalled_context_notes.append(f"recalled_context_log_error:{type(exc).__name__}")
            candidate_result: dict[str, Any] = {"notes": []}
            try:
                candidate_result = extract_memory_candidates(
                    self.xinyu_dir,
                    payload,
                    user_text=text,
                    assistant_reply=reply,
                    source_message_ids=list(archive_result.get("message_ids", [])),
                    dialogue_tail=session.dialogue_tail,
                    visible_turn=visible_turn,
                    quality_flags=final_guard_flags,
                )
            except Exception as exc:
                print(f"[xinyu_core_bridge] memory candidate extraction failed: {exc}", flush=True)
                candidate_result = {"notes": [f"memory_candidate_error:{type(exc).__name__}"]}
            memory_self_review: dict[str, Any] = {"notes": []}
            try:
                memory_self_review = run_memory_self_review(self.xinyu_dir)
                if int(memory_self_review.get("reviewed_candidates") or 0) > 0:
                    memory_self_review.setdefault("notes", []).append(
                        "memory_self_review:"
                        f"{_safe_str(memory_self_review.get('reviewed_candidates'), '0')}/"
                        f"{_safe_str(memory_self_review.get('self_approved'), '0')}/"
                        f"{_safe_str(memory_self_review.get('observe_more'), '0')}/"
                        f"{_safe_str(memory_self_review.get('owner_review_required'), '0')}/"
                        f"{_safe_str(memory_self_review.get('blocked'), '0')}"
                    )
            except Exception as exc:
                print(f"[xinyu_core_bridge] memory self-review failed: {exc}", flush=True)
                memory_self_review = {"notes": [f"memory_self_review_error:{type(exc).__name__}"]}
            interaction_journal: dict[str, Any] = {"notes": []}
            try:
                interaction_journal = record_interaction_turn(
                    self.xinyu_dir,
                    payload,
                    user_text=text,
                    reply=reply,
                    session_key=session_key,
                    source="qq_gateway",
                    turn_kind=_safe_str(getattr(visible_turn, "turn_kind", "")),
                    turn_id=_safe_str(presence_start.get("turn_id")),
                    elapsed_ms=int((time.perf_counter() - turn_started_at) * 1000),
                )
            except Exception as exc:
                print(f"[xinyu_core_bridge] interaction journal failed: {exc}", flush=True)
                interaction_journal = {"notes": [f"interaction_journal_error:{type(exc).__name__}"]}
            self._append_dialogue_tail(session, user_text=text, reply=reply)
            proactive_owner_reply_marked = self._mark_proactive_owner_reply(payload, text=text, reply=reply)
            promised_followup: dict[str, Any] = {"notes": []}
            try:
                promised_followup = self._schedule_promised_followup_if_needed(
                    payload,
                    user_text=text,
                    reply=reply,
                    session_key=session_key,
                    model_codex_task=self_code_task or model_codex_task or direct_codex_task,
                )
            except Exception as exc:
                print(f"[xinyu_core_bridge] promised followup scheduling failed: {exc}", flush=True)
                promised_followup = {"notes": [f"promised_followup_error:{type(exc).__name__}"]}
            after_memory = _memory_snapshot(self.memory_root)
            notes: list[str] = []
            if not reply:
                notes.append("empty_reply")
            if rendered:
                notes.append(f"outward_renderer_applied:{renderer_reason or 'unknown'}")
            elif self.outward_renderer:
                notes.append(f"outward_renderer_skipped:{self.renderer_mode}")
            if final_guard_flags:
                notes.append("final_reply_guard_flags:" + ",".join(final_guard_flags[:3]))
            if final_guard_applied:
                notes.append("final_reply_guard_applied")
            if residue_written:
                notes.append("persona_surface_residue_updated")
            if voice_calibrated:
                notes.append("voice_calibration_recorded")
            if persona_sidecar.get("state_changed"):
                notes.append("persona_state_updated")
            if persona_sidecar.get("event_recorded"):
                notes.append("owner_relationship_event_recorded")
            if proactive_tail_synced:
                notes.append("proactive_outbound_tail_synced")
            if proactive_owner_reply_marked:
                notes.append("proactive_request_owner_replied")
            if model_codex_delegate_note:
                notes.append(model_codex_delegate_note)
            if wait_to_think_task:
                notes.append("wait_to_think_marker_intercepted")
            notes.extend(_safe_str(note) for note in curiosity_eval.get("notes", [])[:4])
            notes.extend(_safe_str(note) for note in curiosity_prediction.get("notes", [])[:4])
            notes.extend(_safe_str(note) for note in private_thought_outcome.get("notes", [])[:3])
            notes.extend(_safe_str(note) for note in uncertainty_pause_reply.get("notes", [])[:2])
            notes.extend(_safe_str(note) for note in continuity_handoff.get("notes", [])[:2])
            notes.extend(_safe_str(note) for note in private_thought_link.get("notes", [])[:3])
            notes.extend(_safe_str(note) for note in persona_sidecar.get("notes", [])[:4])
            notes.extend(_safe_str(note) for note in event_sidecar.get("notes", [])[:4])
            notes.extend(_safe_str(note) for note in v1_shadow.get("notes", [])[:4])
            notes.extend(_safe_str(note) for note in recalled_context_notes[:4])
            notes.extend(_safe_str(note) for note in archive_result.get("notes", [])[:3])
            notes.extend(_safe_str(note) for note in candidate_result.get("notes", [])[:3])
            notes.extend(_safe_str(note) for note in memory_self_review.get("notes", [])[:3])
            notes.extend(_safe_str(note) for note in interaction_journal.get("notes", [])[:3])
            notes.extend(_safe_str(note) for note in expression_learning.get("notes", [])[:3])
            notes.extend(_safe_str(note) for note in learning_closed_loop.get("notes", [])[:3])
            notes.extend(_safe_str(note) for note in uncertainty_pause.get("notes", [])[:3])
            notes.extend(_safe_str(note) for note in wait_to_think_sidecar.get("notes", [])[:3])
            notes.extend(_safe_str(note) for note in promised_followup.get("notes", [])[:3])
            if cleanup["cleaned_sessions"]:
                notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")
            if session.dialogue_tail:
                notes.append("dialogue_working_memory_active")
            post_cleanup = await self._cleanup_idle_sessions(preserve_keys={session_key})
            if post_cleanup["cleaned_sessions"]:
                notes.append(f"cleaned_extra_sessions:{post_cleanup['cleaned_sessions']}")
            memory_changed = before_memory != after_memory
            record_turn_finished(
                self.xinyu_dir,
                turn_id=_safe_str(presence_start.get("turn_id")),
                reply=reply,
                elapsed_ms=int((time.perf_counter() - turn_started_at) * 1000),
                status="ok",
                notes=notes,
                memory_changed=memory_changed,
            )

            return {
                "accepted": True,
                "reply": reply,
                "memory_changed": memory_changed,
                "notes": notes,
            }

    async def shutdown(self) -> None:
        self._closed = True
        autonomous_task = self._autonomous_task
        self._autonomous_task = None
        if autonomous_task is not None and not autonomous_task.done():
            autonomous_task.cancel()
            try:
                await autonomous_task
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                print(f"[xinyu_core_bridge] autonomous task shutdown warning: {exc}", flush=True)

        async with self._sessions_lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()

        for session in sessions:
            try:
                await asyncio.wait_for(session.agent.stop(), timeout=30)
            except Exception as exc:
                print(f"[xinyu_core_bridge] failed to stop session {session.key}: {exc}", flush=True)

    async def _get_session(self, session_key: str) -> AgentSession:
        self._load_runtime()
        prompt_signature = self._session_prompt_signature()
        old_session: AgentSession | None = None
        async with self._sessions_lock:
            session = self._sessions.get(session_key)
            if session is not None and session.prompt_signature == prompt_signature:
                return session
            if session is not None:
                old_session = self._sessions.pop(session_key)

        if old_session is not None:
            try:
                await asyncio.wait_for(old_session.agent.stop(), timeout=30)
                print(
                    f"[xinyu_core_bridge] restarted session {session_key} after prompt/memory context change",
                    flush=True,
                )
            except Exception as exc:
                print(f"[xinyu_core_bridge] failed to stop stale session {session_key}: {exc}", flush=True)

        if self.dialogue_session_tail_entries <= 0:
            dialogue_tail = []
        elif old_session is not None and old_session.dialogue_tail:
            dialogue_tail = list(old_session.dialogue_tail[-self.dialogue_session_tail_entries :])
        else:
            dialogue_tail = load_dialogue_tail(
                self.xinyu_dir,
                session_key,
                max_entries=self.dialogue_session_tail_entries,
                include_timestamps=True,
            )
        chunks: list[str] = []
        agent = self._agent_cls.from_path(
            str(self.xinyu_dir),
            input_module=_NullInputModule(),
            pwd=str(self.xinyu_dir),
        )
        agent.set_output_handler(
            lambda text, buffer=chunks: buffer.append(text),
            replace_default=True,
        )
        await agent.start()
        session = AgentSession(
            key=session_key,
            agent=agent,
            prompt_signature=prompt_signature,
            chunks=chunks,
            dialogue_tail=dialogue_tail,
        )
        async with self._sessions_lock:
            self._sessions[session_key] = session
        print(f"[xinyu_core_bridge] started session {session_key}", flush=True)
        return session

    def _session_prompt_signature(self) -> str:
        parts: list[str] = []
        for rel in PROMPT_CONTEXT_SIGNATURE_FILES:
            path = self.xinyu_dir / rel
            try:
                stat = path.stat()
            except OSError:
                parts.append(f"{rel}:missing")
                continue
            parts.append(f"{rel}:{stat.st_mtime_ns}:{stat.st_size}")
        return "|".join(parts)

    async def _cleanup_idle_sessions(self, *, preserve_keys: set[str] | None = None) -> dict[str, int]:
        preserve_keys = set(preserve_keys or set())
        if self.autonomous_maintenance_enabled and self.autonomous_maintenance_session_key:
            preserve_keys.add(self.autonomous_maintenance_session_key)
        if self.session_idle_ttl_seconds <= 0 and self.max_sessions <= 0:
            return {"cleaned_sessions": 0, "remaining_sessions": len(self._sessions)}

        now = time.time()
        to_stop: list[AgentSession] = []
        async with self._sessions_lock:
            expire_keys: set[str] = set()
            if self.session_idle_ttl_seconds > 0:
                for key, session in self._sessions.items():
                    if key in preserve_keys:
                        continue
                    if now - session.last_used_at > self.session_idle_ttl_seconds:
                        expire_keys.add(key)

            remaining = [
                (key, session)
                for key, session in self._sessions.items()
                if key not in expire_keys and key not in preserve_keys
            ]
            if self.max_sessions > 0 and len(self._sessions) - len(expire_keys) > self.max_sessions:
                overflow = len(self._sessions) - len(expire_keys) - self.max_sessions
                oldest = sorted(remaining, key=lambda item: item[1].last_used_at)[:overflow]
                expire_keys.update(key for key, _session in oldest)

            for key in expire_keys:
                session = self._sessions.pop(key, None)
                if session is not None:
                    to_stop.append(session)
            remaining_count = len(self._sessions)

        for session in to_stop:
            try:
                await asyncio.wait_for(session.agent.stop(), timeout=30)
                print(f"[xinyu_core_bridge] cleaned idle session {session.key}", flush=True)
            except Exception as exc:
                print(f"[xinyu_core_bridge] failed to clean session {session.key}: {exc}", flush=True)

        return {"cleaned_sessions": len(to_stop), "remaining_sessions": remaining_count}

    def _payload_text(self, payload: dict[str, Any]) -> str:
        text = _safe_str(payload.get("text")).strip()
        if text:
            return text
        return _safe_str(payload.get("raw_message")).strip()

    def _session_key(self, payload: dict[str, Any]) -> str:
        for key in ("session_id", "user_id"):
            value = _safe_str(payload.get(key)).strip()
            if value:
                return value
        return "qq:default"

    def _looks_like_time_fact_correction(self, text: str) -> bool:
        compact = re.sub(r"\s+", "", _safe_str(text))
        if not compact:
            return False
        correction_cues = (
            "不是",
            "不对",
            "错了",
            "算错",
            "何意味",
            "什么意思",
            "哪来的",
            "怎么就",
            "怎么会",
            "怎么是",
            "不应该",
        )
        time_fact_cues = (
            "今天",
            "日期",
            "时间",
            "星期",
            "周几",
            "假期",
            "五一",
            "劳动节",
            "5.5",
            "5月",
            "五月",
            "最后一天",
            "结束",
            "收尾",
            "明天",
            "昨天",
        )
        return any(cue in compact for cue in correction_cues) and any(
            cue in compact for cue in time_fact_cues
        )

    def _inject_live_turn_context(
        self,
        agent: Any,
        *,
        payload: dict[str, Any],
        text: str,
        dialogue_tail: list[dict[str, str]] | None = None,
        persona_context: str = "",
        curiosity_context: str = "",
        visible_turn: Any | None = None,
        recalled_context: str = "",
        runtime_presence_context: str = "",
        continuity_context: str = "",
        uncertainty_pause_context: str = "",
    ) -> None:
        controller = getattr(agent, "controller", None)
        pending = getattr(controller, "_pending_injections", None)
        if not isinstance(pending, list):
            return

        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        is_owner = _as_bool(metadata.get("is_owner_user"), default=False)
        message_type = _safe_str(payload.get("message_type"))
        sender_name = _safe_str(payload.get("sender_name")) or _safe_str(payload.get("user_id"))
        source_line = "QQ group chat" if message_type.startswith("group_") else "QQ private chat"
        relationship_line = (
            "owner"
            if is_owner
            else "external contact"
        )
        if visible_turn is None:
            visible_turn = classify_visible_turn(self.xinyu_dir, payload=payload, user_text=text)
        life_posture = build_life_posture(self.xinyu_dir, payload=payload, user_text=text, visible_turn=visible_turn)
        persona_runtime = build_persona_runtime_state(
            self.xinyu_dir,
            payload=payload,
            user_text=text,
            draft_reply="",
        )
        previous_residue = read_turn_residue(self.xinyu_dir)

        pressure_line = "style pressure: answer through the next line, not through a report." if visible_turn.owner_style_pressure and is_owner else "ordinary live turn."
        residue_line = (
            f"previous residue: {previous_residue.tone}, {previous_residue.felt_residue}, strength={previous_residue.decayed_strength}"
            if previous_residue.active
            else "previous residue: none"
        )
        tail_block = self._format_dialogue_tail(dialogue_tail or [])
        sidecar_lines: list[str] = []
        persona_block = _safe_str(persona_context).strip()
        if persona_block:
            sidecar_lines.extend(["persona sidecar:", persona_block[:1200]])
        curiosity_block = _safe_str(curiosity_context).strip()
        if curiosity_block:
            sidecar_lines.extend(["curiosity sidecar:", curiosity_block[:1200]])
        recalled_block = _safe_str(recalled_context).strip()
        if recalled_block:
            sidecar_lines.extend(["recalled context sidecar:", recalled_block])
        learning_loop_block = build_learning_closed_loop_prompt_block(self.xinyu_dir, user_text=text)
        if learning_loop_block:
            sidecar_lines.extend([learning_loop_block])
        proactive_block = self._proactive_thread_context(payload, text)
        if proactive_block:
            sidecar_lines.extend([proactive_block])
        attachment_block = load_recent_attachment_context(self.xinyu_dir, self._session_key(payload), text)
        if attachment_block:
            sidecar_lines.extend(["recent attachment sidecar:", attachment_block])
        runtime_presence_block = _safe_str(runtime_presence_context).strip()
        if runtime_presence_block:
            sidecar_lines.extend(["runtime presence sidecar:", runtime_presence_block[:2200]])
        continuity_block = _safe_str(continuity_context).strip()
        if continuity_block:
            sidecar_lines.extend([continuity_block])
        uncertainty_block = _safe_str(uncertainty_pause_context).strip()
        if uncertainty_block:
            sidecar_lines.extend([uncertainty_block])
        if is_owner and self._looks_like_time_fact_correction(text):
            today = datetime.now().astimezone().date().isoformat()
            sidecar_lines.extend(
                [
                    "factual/time correction sidecar:",
                    (
                        f"current_runtime_date: {today}. The owner is correcting a concrete "
                        "time/date/holiday fact from XinYu's previous reply. Treat the owner "
                        "correction and current runtime date as authoritative over stale memory, "
                        "mood residue, or old time-anchor wording. Continue the chat from the "
                        "corrected fact in one ordinary line; do not use apology/report wording "
                        "such as 我算错了 / 刚才那句说岔了 / 别理 / 抱歉 / 不好意思 / 我会改."
                    ),
                ]
            )
        if _as_bool(metadata.get("attachment_followup_after_ingest"), default=False):
            sidecar_lines.extend(
                [
                    "attachment followup:",
                    (
                        "The owner just sent a readable attachment. Read the attachment context now. "
                        "Respond from your own reading of it in this turn when something is worth saying; "
                        "do not use a fixed acknowledgement or report template."
                    ),
                ]
            )

        codex_delegate_contract = ""
        if self._owner_private_payload_matches(payload):
            codex_delegate_contract = (
                "codex_delegation_contract: in owner-private chat, an explicit Codex request, search/code "
                "investigation request, or owner instruction to use Codex can be delegated through the hidden "
                f"marker {CODEX_DELEGATE_OPEN}<concrete task>{CODEX_DELEGATE_CLOSE}. If you use it, output only "
                "that marker and no visible prose; the bridge will intercept it and open XinYu's dedicated Codex "
                "window. If the owner explicitly grants XinYu permission to change her own code or says to start "
                "after such a grant, do not turn it into 我可以试试 / 要现在开始吗; hand it to the bridge as an "
                "actionable bounded self-code iteration. A direct owner-private request to modify XinYu code is "
                "already a one-time approval; do not require a prior application first. Do not tell the owner manual "
                "/codex is required unless a real bridge rejection just happened."
            )

        live_context_lines = [
            visible_turn.to_prompt_block(),
            "",
            life_posture.to_prompt_block(),
            "",
            persona_runtime.to_prompt_block(),
            "",
            "Live turn context, restored continuity version.",
            "sidecar_visibility_contract: private_observation_only.",
            (
                "Never print sidecar names, state labels, file paths, hashes, XML/tool syntax, gates, scores, "
                "or 'I read this file' mechanics in ordinary chat. Convert useful facts into the next natural line; "
                "only discuss mechanics when owner explicitly asks about the system."
            ),
            (
                "promise_followup_contract: do not make a bare promise like 我再看看 / 我查一下 and then stop. "
                "If you say you will look, check, think, or verify something for the owner, either delegate the "
                "real work now or expect the bridge to create an owner-private follow-up through QQ outbox after review."
            ),
            codex_delegate_contract,
            f"scene: {visible_turn.turn_kind}",
            f"source: {source_line}",
            f"speaker_relation: {relationship_line}",
            f"sender_display: {sender_name or 'unknown'}",
            residue_line,
            tail_block,
            *sidecar_lines,
            pressure_line,
            "Let the current sentence matter more than old templates.",
            "Use the session tail for callbacks, corrections, and direct references to the previous reply.",
            "Recent attachment context is available when the owner asks about a file, attachment, screenshot, document, or its contents.",
            "If this is technical work, do the technical work directly.",
        ]

        pending.append(
            {
                "role": "system",
                "content": "\n".join(live_context_lines),
            }
        )

    def _format_dialogue_tail(self, dialogue_tail: list[dict[str, str]]) -> str:
        if not dialogue_tail:
            return "current session tail: none"
        lines = ["current session tail:"]
        for item in compact_tail_for_prompt(
            dialogue_tail,
            max_entries=self.dialogue_prompt_tail_entries,
            include_timestamps=True,
        ):
            role = _safe_str(item.get("role")).strip()
            content = _safe_str(item.get("content")).strip()
            if not role or not content:
                continue
            recorded_at = _safe_str(item.get("recorded_at")).strip()
            time_suffix = f" ({recorded_at})" if recorded_at else ""
            lines.append(f"- {role}{time_suffix}: {content}")
        return "\n".join(lines) if len(lines) > 1 else "current session tail: none"

    def _append_dialogue_tail(self, session: AgentSession, *, user_text: str, reply: str) -> None:
        if user_text.strip():
            session.dialogue_tail.append({"role": "user", "content": user_text.strip()})
        if reply.strip():
            session.dialogue_tail.append({"role": "assistant", "content": reply.strip()})
        if self.dialogue_session_tail_entries <= 0:
            session.dialogue_tail.clear()
        elif len(session.dialogue_tail) > self.dialogue_session_tail_entries:
            del session.dialogue_tail[:-self.dialogue_session_tail_entries]
        try:
            save_dialogue_tail(self.xinyu_dir, session.key, session.dialogue_tail, max_entries=self.dialogue_persisted_tail_entries)
        except Exception:
            pass

    async def _render_outward_reply(
        self,
        agent: Any,
        *,
        payload: dict[str, Any],
        user_text: str,
        draft_reply: str,
    ) -> str:
        return await self.renderer.render_outward_reply(
            agent,
            payload=payload,
            user_text=user_text,
            draft_reply=draft_reply,
        )

    def _renderer_reason(self, *, payload: dict[str, Any], user_text: str, draft_reply: str) -> str:
        return self.renderer.renderer_reason(payload=payload, user_text=user_text, draft_reply=draft_reply)

    def _normalize_renderer_mode(self, value: str) -> str:
        return BridgeRenderer.normalize_renderer_mode(value)

    def _build_renderer_messages(
        self,
        agent: Any,
        *,
        payload: dict[str, Any],
        user_text: str,
        draft_reply: str,
        failed_reply: str = "",
        quality_flags: list[str] | None = None,
    ) -> list[dict[str, str]]:
        return self.renderer.build_renderer_messages(
            agent,
            payload=payload,
            user_text=user_text,
            draft_reply=draft_reply,
            failed_reply=failed_reply,
            quality_flags=quality_flags,
        )

    def _is_live_style_pressure(self, text: str) -> bool:
        return self.speech_controller.is_live_style_pressure(text)

    def _is_owner_relationship_pressure(self, text: str) -> bool:
        return self.speech_controller.is_owner_relationship_pressure(text)

    def _is_explicit_technical_request(self, text: str) -> bool:
        return self.speech_controller.is_explicit_technical_request(text)

    def _reply_quality_flags(self, *, user_text: str, reply: str) -> list[str]:
        return self.speech_controller.reply_quality_flags(user_text=user_text, reply=reply)

    @staticmethod
    def _critical_final_guard_flags(flags: list[str] | tuple[str, ...]) -> list[str]:
        critical = {
            "pseudo_tool_call_naturalized",
            "machine_introspection_naturalized",
            "visible_memory_mechanics_naturalized",
            "false_codex_unavailable_claim_blocked",
        }
        return [flag for flag in flags if flag in critical]

    def _renderer_memory_context(self) -> str:
        return self.renderer.renderer_memory_context()

    def _read_text(self, rel: str, *, limit: int) -> str:
        return self.renderer.read_text(rel, limit=limit)

    def _conversation_tail(self, agent: Any, *, max_messages: int) -> str:
        return self.renderer.conversation_tail(agent, max_messages=max_messages)

    def _replace_last_assistant_message(self, agent: Any, rendered_reply: str) -> None:
        controller = getattr(agent, "controller", None)
        conversation = getattr(controller, "conversation", None)
        if conversation is None or not hasattr(conversation, "get_last_assistant_message"):
            return
        try:
            message = conversation.get_last_assistant_message()
        except Exception:
            return
        if message is None:
            return
        try:
            message.content = rendered_reply
            message.tool_calls = None
        except Exception:
            pass

    def _strip_renderer_wrappers(self, text: str) -> str:
        return self.renderer.strip_renderer_wrappers(text)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HTTP bridge from QQ gateway to XinYu core.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--turn-timeout-seconds", type=int, default=165)
    parser.add_argument("--settle-seconds", type=float, default=0.0)
    parser.add_argument("--max-body-bytes", type=int, default=1024 * 1024)
    parser.add_argument("--max-text-chars", type=int, default=8000)
    parser.add_argument("--disable-outward-renderer", action="store_true")
    parser.add_argument(
        "--renderer-mode",
        choices=("always", "quality", "pressure", "off"),
        default=os.environ.get("XINYU_RENDERER_MODE", "off"),
        help=(
            "Outward renderer policy. always=second LLM call every reply; "
            "quality=only pressure or failed quality gate; pressure=only pressure turns; off=disabled by default."
        ),
    )
    parser.add_argument("--render-timeout-seconds", type=int, default=60)
    parser.add_argument(
        "--session-idle-ttl-seconds",
        type=int,
        default=_as_int(os.environ.get("XINYU_DIALOGUE_SESSION_IDLE_TTL_SECONDS"), 86400),
    )
    parser.add_argument("--max-sessions", type=int, default=8)
    parser.add_argument("--proactive-min-interval-seconds", type=int, default=1800)
    parser.add_argument("--disable-autonomous-maintenance", action="store_true")
    parser.add_argument("--autonomous-maintenance-initial-delay-seconds", type=int, default=60)
    parser.add_argument("--autonomous-maintenance-interval-seconds", type=int, default=1800)
    parser.add_argument(
        "--autonomous-maintenance-session-key",
        default="xinyu:autonomous:maintenance",
    )
    parser.add_argument(
        "--bridge-token",
        default=os.environ.get("XINYU_BRIDGE_TOKEN", ""),
        help="Shared token. Optional only for loopback hosts; required for non-loopback hosts.",
    )
    return parser


def _start_loop_thread() -> tuple[asyncio.AbstractEventLoop, threading.Thread]:
    ready = threading.Event()
    holder: dict[str, asyncio.AbstractEventLoop] = {}

    def run_loop() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        holder["loop"] = loop
        ready.set()
        loop.run_forever()
        pending = [task for task in asyncio.all_tasks(loop) if not task.done()]
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()

    thread = threading.Thread(target=run_loop, name="xinyu-core-bridge-loop", daemon=True)
    thread.start()
    ready.wait(timeout=10)
    loop = holder.get("loop")
    if loop is None:
        raise RuntimeError("failed to start asyncio loop")
    return loop, thread


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    args = _build_parser().parse_args()
    xinyu_dir = Path(__file__).resolve().parent
    _load_local_env(xinyu_dir)
    enforce_llm_http_guard()
    enforce_bridge_token_guard(args.host, args.bridge_token.strip())
    runtime = XinYuBridgeRuntime(
        xinyu_dir=xinyu_dir,
        turn_timeout_seconds=args.turn_timeout_seconds,
        max_text_chars=args.max_text_chars,
        settle_seconds=args.settle_seconds,
        outward_renderer=not args.disable_outward_renderer and args.renderer_mode != "off",
        renderer_mode=args.renderer_mode,
        render_timeout_seconds=args.render_timeout_seconds,
        session_idle_ttl_seconds=args.session_idle_ttl_seconds,
        max_sessions=args.max_sessions,
        proactive_min_interval_seconds=args.proactive_min_interval_seconds,
        autonomous_maintenance_enabled=not args.disable_autonomous_maintenance,
        autonomous_maintenance_initial_delay_seconds=args.autonomous_maintenance_initial_delay_seconds,
        autonomous_maintenance_interval_seconds=args.autonomous_maintenance_interval_seconds,
        autonomous_maintenance_session_key=args.autonomous_maintenance_session_key,
    )
    loop, loop_thread = _start_loop_thread()
    server = XinYuBridgeHTTPServer(
        (args.host, args.port),
        XinYuBridgeRequestHandler,
        runtime=runtime,
        loop=loop,
        bridge_token=args.bridge_token.strip(),
        max_body_bytes=args.max_body_bytes,
        request_timeout_seconds=args.turn_timeout_seconds + 15,
    )
    try:
        future = asyncio.run_coroutine_threadsafe(runtime.start_background_tasks(), loop)
        future.result(timeout=10)
    except Exception as exc:
        print(f"[xinyu_core_bridge] background startup warning: {exc}", flush=True)

    print(
        f"[xinyu_core_bridge] listening on http://{args.host}:{args.port} "
        f"(turn_timeout={args.turn_timeout_seconds}s, "
        f"session_ttl={args.session_idle_ttl_seconds}s, max_sessions={args.max_sessions}, "
        f"renderer_mode={args.renderer_mode}, autonomous_maintenance={not args.disable_autonomous_maintenance})",
        flush=True,
    )

    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        print("[xinyu_core_bridge] interrupted", flush=True)
    finally:
        server.shutdown()
        server.server_close()
        try:
            future = asyncio.run_coroutine_threadsafe(runtime.shutdown(), loop)
            future.result(timeout=60)
        except Exception as exc:
            print(f"[xinyu_core_bridge] shutdown warning: {exc}", flush=True)
        loop.call_soon_threadsafe(loop.stop)
        loop_thread.join(timeout=10)
        print("[xinyu_core_bridge] stopped", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
