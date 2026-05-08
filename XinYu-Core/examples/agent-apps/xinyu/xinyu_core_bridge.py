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
from datetime import datetime
from http import HTTPStatus
from pathlib import Path
from typing import Any

from xinyu_async_exploration import (
    async_exploration_outbox_message,
    create_async_exploration_closure,
    update_async_exploration_from_codex,
)
from xinyu_action_layer import XinyuActionLayer, codex_response_to_outcome
from xinyu_action_reply_composer import compose_action_reply
from state_service import atomic_write_text
from xinyu_bridge_http import XinYuBridgeHTTPServer, XinYuBridgeRequestHandler
from xinyu_bridge_bootstrap import ensure_repo_src as _ensure_repo_src
from xinyu_bridge_bootstrap import load_local_env as _load_local_env
from xinyu_bridge_learning import (
    LearningBridgeError,
    stage_codex_report_material,
)
from xinyu_bridge_context import prompt_context_signature
from xinyu_bridge_desktop_actions import desktop_action_pressure_label as _desktop_action_pressure_label
from xinyu_bridge_desktop_actions import desktop_action_result_label as _desktop_action_result_label
from xinyu_bridge_desktop_actions import desktop_action_theme_label as _desktop_action_theme_label
from xinyu_bridge_desktop_actions import desktop_scrub_action_markers as _desktop_scrub_action_markers
from xinyu_bridge_memory_snapshot import memory_snapshot as _memory_snapshot
from xinyu_bridge_proactive import acknowledge as proactive_ack_bridge, claim_or_preview as proactive_bridge
from xinyu_bridge_reply_text import normalize_bridge_reply as _normalize_reply
from xinyu_bridge_renderer import BridgeRenderer
from xinyu_bridge_session import AgentSession, session_key_from_payload, session_keys_to_expire
from xinyu_bridge_state_text import parse_iso as _parse_iso
from xinyu_bridge_state_text import payload_path as _payload_path
from xinyu_bridge_state_text import read_text_safe as _read_text_safe
from xinyu_bridge_state_text import seconds_since_iso as _seconds_since_iso
from xinyu_bridge_state_text import state_field as _state_field
from xinyu_bridge_values import as_bool as _as_bool
from xinyu_bridge_values import as_int as _as_int
from xinyu_bridge_values import as_str_set as _as_str_set
from xinyu_bridge_values import compact_text as _compact_text
from xinyu_bridge_values import contains_any as _contains_any
from xinyu_bridge_values import dedupe as _dedupe
from xinyu_bridge_values import optional_int as _optional_int
from xinyu_bridge_values import safe_str as _safe_str
import xinyu_bridge_action_routes
from xinyu_bridge_turn_pipeline import run_pre_model_routes
import xinyu_bridge_v1_routes
from v1_canary_gate import payload_has_attachment_signal as _payload_has_attachment_signal
from xinyu_chat_service import ChatServiceError, build_chat_service
from xinyu_codex_delegate import (
    looks_like_codex_request,
    looks_like_owner_local_write_request,
    preview_codex_delegate_paths,
    run_codex_delegate,
)
from xinyu_codex_dream_handoff import handoff_codex_to_dream
from xinyu_codex_service import (
    codex_completion_outbox_message,
    codex_completion_summary,
    codex_generated_image_artifacts,
    codex_owner_task_text,
    codex_reply_variant,
    codex_started_reply,
    codex_status_reply,
    codex_task_subject,
    enqueue_codex_completion_if_needed,
    looks_like_codex_image_generation_task,
)
from xinyu_continuity_handoff import build_continuity_handoff_prompt_block, refresh_continuity_handoff
from xinyu_context_retrieval import log_recalled_context, retrieve_recalled_context
from xinyu_dialogue_curiosity import evaluate_previous_reaction, record_reply_prediction
from xinyu_dialogue_archive import archive_dialogue_turn, archive_message
from xinyu_dialogue_rule_trial_overlay import build_dialogue_rule_trial_overlay_prompt_block
from xinyu_dialogue_working_memory import (
    compact_tail_for_prompt,
    load_dialogue_tail,
    persisted_tail_entries,
    prompt_tail_entries,
    save_dialogue_tail,
    session_tail_entries,
)
from xinyu_desktop_service import (
    build_desktop_service,
    desktop_event_state as desktop_service_event_state,
    desktop_events_recent as desktop_service_events_recent,
    desktop_limit as desktop_service_limit,
    desktop_recent_items as desktop_service_recent_items,
    desktop_services as desktop_service_services,
)
from xinyu_environment_sensor import sample_environment
from xinyu_life_kernel import build_entropy_state, evaluate_life_kernel
from xinyu_life_reply_policy import (
    apply_life_reply_policy,
    build_life_reply_policy,
    build_life_reply_prompt_block,
)
from xinyu_learning_service import build_learning_service
from xinyu_daily_digest import build_daily_digest_prompt_block, run_daily_digest_maintenance
from xinyu_expression_self_learning import record_expression_self_learning_event
from xinyu_goldmark import mark_goldmark_request as mark_goldmark_request_bridge
from xinyu_goldmark_dehydrate import run_goldmark_dehydration_maintenance
from xinyu_interaction_journal import record_interaction_turn
from xinyu_impulse_soup import run_impulse_soup
from xinyu_learning_closed_loop import (
    build_learning_closed_loop_prompt_block,
    record_learning_closed_loop_self_thought,
    record_learning_closed_loop_turn,
)
from xinyu_life_posture import build_life_posture
from xinyu_life_month_slots import refresh_current_life_month_context  # noqa: F401 - compatibility for older tests/hooks
from xinyu_memory_candidate_extractor import extract_memory_candidates
from xinyu_experience_frame import (
    build_experience_frame,
    compose_recent_action_followup,
    read_recent_action_context,
    write_action_experience_residue,
    write_recent_action_experience,
)
from xinyu_action_experience_digest import (
    compose_action_digest_followup,
    digest_action_experience_residue,
    read_recent_action_digest_context,
    read_recent_action_digest_snapshot,
)
from xinyu_memory_event_sourcing import record_action_experience_event, record_chat_event
from xinyu_memory_self_review import run_memory_self_review
from xinyu_metabolism_contract import (
    approve_ticket as approve_metabolism_ticket,
    cancel_ticket as cancel_metabolism_ticket,
    create_ticket as create_metabolism_ticket,
    get_ticket as get_metabolism_ticket,
    list_tickets as list_metabolism_tickets,
    reject_ticket as reject_metabolism_ticket,
    run_due_metabolism_tickets,
)
from xinyu_self_choice_store import SelfChoiceStore
from xinyu_package_installer import install_python_packages
from xinyu_memory_weights import refresh_memory_weight_state  # noqa: F401 - compatibility for older tests/hooks
from xinyu_persona_state import observe_persona_turn
from xinyu_persona_runtime import build_persona_runtime_state
from xinyu_private_thought_events import record_private_thought_outcome, record_private_thought_reply_link
from xinyu_proactive_presence import (
    acknowledge_proactive_qq_message,
    claim_proactive_qq_message,
    _write_dispatch_state as write_proactive_qq_dispatch_state,
)
from xinyu_proactive_request_loop import run_proactive_request_loop
from xinyu_proactivity_scorer import run_proactivity_scorer_shadow
from xinyu_qq_outbox import (
    ack_qq_outbox_message,
    claim_next_qq_outbox_message,
    enqueue_qq_outbox_file,
    enqueue_qq_outbox_image,
    enqueue_qq_outbox_message,
)
from xinyu_recent_attachment_context import load_recent_attachment_context
from xinyu_runtime_presence import (
    build_runtime_presence_prompt_block,
    record_bridge_heartbeat,
    record_codex_presence,
    record_turn_finished,
    record_turn_started,
    read_runtime_presence_summary,
)
from xinyu_runtime_context import build_goldmark_auth_prompt_block
from xinyu_runtime_security import enforce_bridge_token_guard, enforce_llm_http_guard
from xinyu_review_inbox import handle_review_inbox_command, run_review_inbox_maintenance
from xinyu_self_code_approval import (
    consume_self_code_approval,
    create_direct_self_code_approval,
    mark_self_code_execution_scheduled,
)
from xinyu_self_code_watchdog import create_self_code_snapshot
from xinyu_self_thought_loop import run_self_thought_loop
from xinyu_sent_reply_index import register_sent_reply_ack, visible_text_hash
from xinyu_sticker_ingest import import_sticker_from_payload
from xinyu_speech_controller import XinyuSpeechController
from xinyu_sticker_pack import maybe_enqueue_sticker_reply, sticker_mood_label
from xinyu_text_variants import readable_markers
from xinyu_tool_protocol import ActionOutcome, DELEGATED_LOCAL_RISK, ToolRequest
from xinyu_v1_canary_readiness import record_v1_shadow_observation
from xinyu_turn_residue import read_turn_residue, write_turn_residue
from xinyu_turn_classifier import classify_visible_turn
from xinyu_uncertainty_pause import (
    build_uncertainty_pause_prompt_block,
    is_waiting_reply,
    mark_uncertainty_pause_replied,
    record_uncertainty_pause,
)
from xinyu_visible_reply_guard import dedupe_visible_reply
from xinyu_visible_state_hygiene import sanitize_visible_state_files
from xinyu_voice_learning import record_voice_correction
from xinyu_voice_trial_overlay import build_voice_trial_overlay_prompt_block, record_voice_trial_overlay
from xinyu_watched_sources import run_watched_source_check


BRIDGE_VERSION = "0.8.96"
CODEX_DEFAULT_TIMEOUT_SECONDS = 3600
CODEX_VISIBLE_WINDOW_TITLE = "Xinyu codex"
CODEX_GENERATED_IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp"})
DESKTOP_RECENT_TURNS_MAX = 200
DESKTOP_RECENT_MEMORY_EVENTS_MAX = 200
DESKTOP_PROACTIVE_INBOX_MAX = 50
DESKTOP_PROACTIVE_INBOX_STATUSES = {"ready", "candidate_only", "claimed"}
DESKTOP_PROACTIVE_FINAL_STATUSES = {
    "sent",
    "answered",
    "failed",
    "expired",
    "blocked",
    "none",
    "read_locally",
    "replied",
    "dismissed",
    "queued_qq",
}
DESKTOP_PROACTIVE_ACK_ACTIONS = {"read_locally", "approve_qq", "dismiss", "reply"}
DEBUG_PROMPT_DUMP_ENV = "XINYU_DEBUG_PROMPT_DUMP"
DEBUG_LIVE_SYSTEM_PROMPT_REL = Path("runtime/debug/last_live_system_prompt.txt")
V1_OWNER_SIMPLE_CANARY_ENV = "XINYU_V1_OWNER_SIMPLE_CANARY"
V1_CANARY_GREETING_TEXTS = frozenset({"hi", "hello", "hey", "早", "早安", "晚上好", "你好", "在吗"})
V1_CANARY_ACK_TEXTS = frozenset({"嗯", "嗯嗯", "哦", "好", "好的", "好哦", "行", "知道了", "ok"})

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
TRUSTED_CODEX_PUBLIC_SEARCH_MARKERS = readable_markers(
    "搜索",
    "搜一下",
    "搜下",
    "搜东西",
    "联网",
    "查一下",
    "查下",
    "查资料",
    "核对",
    "验证",
    "找资料",
    "公开资料",
    "网页",
    "新闻",
    "资料来源",
    "source",
    "search",
    "web",
    "verify",
)
TRUSTED_CODEX_LOCAL_BLOCK_MARKERS = readable_markers(
    "本机",
    "本地",
    "电脑",
    "文件",
    "目录",
    "路径",
    "代码",
    "项目",
    "仓库",
    "安装",
    "pip",
    "包",
    "修改",
    "改代码",
    "删除",
    "移动",
    "上传",
    "token",
    "密钥",
    "密码",
    "cookie",
    "日志",
    "配置",
    "权限配置",
)
TRUSTED_CODEX_LOCAL_PATH_RE = re.compile(
    r"(?i)(?:[a-z]:[\\/]|\\\\|file://|(?:^|[\s`'\"“”‘’])\.{1,2}[\\/])"
)
TRUSTED_CODEX_LOCAL_ENGLISH_BLOCK_MARKERS = (
    "local",
    "localhost",
    "127.0.0.1",
    "file://",
    "localfile",
    "localpath",
    "localconfig",
    "config.yaml",
    ".env",
    "code",
    "repo",
    "repository",
    "project",
    "install",
    "package",
    "admin",
    "permission",
    "delete",
    "modify",
    "write",
    "readfile",
    "openfile",
    "log",
    "secret",
    "api_key",
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
    "没让你用codex",
    "没有让你用codex",
    "不是让你用codex",
    "不是叫你用codex",
    "不是提到codex",
    "不是说codex",
    "一提codex",
    "提到codex就",
    "自动开codex",
    "自动启动codex",
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
        "code modification ability",
        "self-modification ability",
        "self editing ability",
        "your own code modification ability",
        "代码修改能力",
        "自改能力",
        "自我修改能力",
        "自己的代码修改能力",
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
        "make it stronger",
        "strengthen it",
        "improve it",
        "加强一下",
        "增强一下",
        "提升一下",
        "补强一下",
        "修一下",
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
        "weak",
        "stronger",
        "improve",
        "strengthen",
        "弱",
        "不够强",
        "不太行",
        "加强",
        "增强",
        "提升",
        "补强",
    ),
)

PROMPT_CONTEXT_SIGNATURE_FILES: tuple[str, ...] = (
    "config.yaml",
    "prompts/system.md",
    "prompts/output.md",
    "prompts/live_voice_card.md",
    "memory/self/system_prompt_memory.md",
    "memory/self/core.md",
    "memory/self/personality_profile.md",
    "memory/context/life_month_slots.md",
    "memory/context/current_life_month_context.md",
    "memory/self/mind_loop_policy.md",
    "memory/self/mind_loop_state.md",
    "memory/self/voice_profile_zh.md",
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
        metabolism_runner_interval_seconds: int = 30,
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
        self.metabolism_runner_interval_seconds = max(5, metabolism_runner_interval_seconds)
        self.v1_enabled = _as_bool(os.environ.get("XINYU_V1_ENABLED"), default=False)
        self.v1_shadow_mode = _as_bool(os.environ.get("XINYU_V1_SHADOW_MODE"), default=False)
        self.v1_shadow_timeout_seconds = max(1, _as_int(os.environ.get("XINYU_V1_SHADOW_TIMEOUT_SECONDS"), 3))
        self.v1_owner_simple_canary = _as_bool(os.environ.get(V1_OWNER_SIMPLE_CANARY_ENV), default=False)
        self.v1_canary_timeout_seconds = max(
            1,
            _as_int(os.environ.get("XINYU_V1_CANARY_TIMEOUT_SECONDS"), self.v1_shadow_timeout_seconds),
        )
        self.v1_owner_user_ids = _as_str_set(os.environ.get("XINYU_OWNER_USER_IDS"))
        self.self_choice_store = SelfChoiceStore(xinyu_dir)
        self.action_layer = XinyuActionLayer(xinyu_dir)
        self._self_choice_boot_logged = False
        self.speech_controller = XinyuSpeechController(xinyu_dir)
        self.renderer = BridgeRenderer(
            xinyu_dir=xinyu_dir,
            speech_controller=self.speech_controller,
            renderer_mode=self.renderer_mode,
            render_timeout_seconds=self.render_timeout_seconds,
        )
        self.chat_service = build_chat_service()
        self._sessions: dict[str, AgentSession] = {}
        self._sessions_lock = asyncio.Lock()
        self._global_turn_lock = asyncio.Lock()
        self.learning_service = build_learning_service(
            xinyu_dir=self.xinyu_dir,
            memory_root=self.memory_root,
            cleanup_idle_sessions=self._cleanup_idle_sessions,
            session_count=lambda: len(self._sessions),
            lock=self._global_turn_lock,
            load_local_env=_load_local_env,
        )
        self._codex_delegate_lock = asyncio.Lock()
        self._review_admin_lock = asyncio.Lock()
        self.desktop_event_bus: Any | None = None
        self.desktop_ws_server: Any | None = None
        self._desktop_recent_turns: list[dict[str, Any]] = []
        self._desktop_recent_memory_events: list[dict[str, Any]] = []
        self._desktop_proactive_inbox: dict[str, dict[str, Any]] = {}
        self._desktop_proactive_lock = threading.Lock()
        self._loaded = False
        self._closed = False
        self._agent_cls: Any = None
        self._create_user_input_event: Any = None
        self._trigger_event_cls: Any = None
        self._autonomous_task: asyncio.Task | None = None
        self._metabolism_task: asyncio.Task | None = None
        self._metabolism_wakeup_event: asyncio.Event | None = None
        self._metabolism_in_progress = False
        self._metabolism_run_count = 0
        self._metabolism_last_started_at = ""
        self._metabolism_last_success_at = ""
        self._metabolism_last_error = ""
        self._metabolism_last_result: dict[str, Any] = {}
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

        from xinyu_runtime.core.agent import Agent
        from xinyu_runtime.core.events import TriggerEvent, create_user_input_event

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
            "metabolism": self._metabolism_health(),
            "self_choice": self.self_choice_store.health_snapshot(),
            "action_experience_digest": read_recent_action_digest_snapshot(self.xinyu_dir, limit=3),
            "closed": self._closed,
        }

    async def health(self) -> dict[str, Any]:
        return self.health_snapshot()

    async def _ensure_self_choice_ready(self) -> None:
        await self.self_choice_store.load_or_recover()

    async def desktop_snapshot(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        await self._ensure_self_choice_ready()
        await self.self_choice_store.apply_time_decay()
        self_choice_private = await self.self_choice_store.snapshot_private()
        event_state = await self._desktop_event_state()
        proactive_items = (await self.desktop_proactive_inbox(payload)).get("items", [])
        recent_turns = (await self.desktop_chat_recent(payload)).get("items", [])
        recent_memory_events = (await self.desktop_memory_recent(payload)).get("items", [])
        environment = sample_environment(self.xinyu_dir)
        entropy = build_entropy_state(
            environment=environment,
            proactive_items=proactive_items,
            recent_turns=recent_turns,
            recent_memory_events=recent_memory_events,
        )
        entropy_state = entropy.model_dump(mode="json")
        active_desires = await self._desktop_active_desires(
            environment=environment,
            entropy_state=entropy,
            proactive_items=proactive_items,
            recent_turns=recent_turns,
            recent_memory_events=recent_memory_events,
            self_choice_state=self_choice_private,
        )
        self_choice_public = await self.self_choice_store.snapshot_public()
        action_digest = read_recent_action_digest_snapshot(self.xinyu_dir, limit=5)
        return {
            "version": 1,
            "snapshotAt": datetime.now().astimezone().isoformat(),
            "lastEventId": event_state.get("latest_event_id", ""),
            "services": self._desktop_services(),
            "health": self.health_snapshot(),
            "environment": environment,
            "entropyState": entropy_state,
            "selfChoiceState": self_choice_public,
            "activeDesires": active_desires,
            "xinyuState": self._desktop_xinyu_state(
                environment=environment,
                entropy_state=entropy_state,
                active_desires=active_desires,
                proactive_items=proactive_items,
                recent_turns=recent_turns,
                recent_memory_events=recent_memory_events,
                action_digest=action_digest,
            ),
            "eventBus": event_state,
            "proactiveInbox": proactive_items,
            "recentTurns": recent_turns,
            "recentMemoryEvents": recent_memory_events,
            "actionDigestState": action_digest,
            "notes": ["desktop_snapshot_v1_life_state"],
        }

    async def _desktop_active_desires(
        self,
        *,
        environment: dict[str, Any],
        entropy_state: Any,
        proactive_items: list[Any],
        recent_turns: list[Any],
        recent_memory_events: list[Any],
        self_choice_state: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        desire = evaluate_life_kernel(
            environment=environment,
            proactive_items=proactive_items,
            recent_turns=recent_turns,
            recent_memory_events=recent_memory_events,
            entropy_state=entropy_state,
            self_choice_state=self_choice_state,
        )
        if desire is None:
            return []
        desire_data = desire.model_dump(mode="json")
        await self.self_choice_store.record_life_choice(desire.chosen_action)
        if desire.chosen_action == "request_metabolism_window":
            ticket = await asyncio.to_thread(self._desktop_open_metabolism_ticket)
            if not ticket:
                self_choice_dream_bias = await self.self_choice_store.dream_bias_snapshot()
                ticket_result = await asyncio.to_thread(
                    create_metabolism_ticket,
                    self.xinyu_dir,
                    entropy_state=entropy_state.model_dump(mode="json") if hasattr(entropy_state, "model_dump") else {},
                    resource_request=desire_data.get("entropy", {}).get("resource_request")
                    if isinstance(desire_data.get("entropy"), dict)
                    else None,
                    active_desire=desire_data,
                    input_window=self._metabolism_input_window(
                        proactive_items=proactive_items,
                        recent_turns=recent_turns,
                        recent_memory_events=recent_memory_events,
                        self_choice_dream_bias=self_choice_dream_bias,
                    ),
                )
                ticket = ticket_result.get("ticket") if isinstance(ticket_result.get("ticket"), dict) else {}
            desire_data["metabolism_ticket_id"] = _safe_str(ticket.get("ticket_id"))
            desire_data["metabolism_ticket_status"] = _safe_str(ticket.get("status"), "requested")
            desire_data["metabolism_ticket"] = ticket
        return [desire_data]

    def _desktop_open_metabolism_ticket(self) -> dict[str, Any]:
        tickets = list_metabolism_tickets(self.xinyu_dir, statuses={"requested", "approved", "running"})
        if not tickets:
            return {}
        rank = {"running": 3, "approved": 2, "requested": 1}
        return dict(
            sorted(
                tickets,
                key=lambda ticket: (
                    rank.get(_safe_str(ticket.get("status")), 0),
                    _safe_str(ticket.get("created_at")),
                    _safe_str(ticket.get("ticket_id")),
                ),
                reverse=True,
            )[0]
        )

    def _metabolism_input_window(
        self,
        *,
        proactive_items: list[Any],
        recent_turns: list[Any],
        recent_memory_events: list[Any],
        self_choice_dream_bias: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        window: dict[str, Any] = {
            "suppressed_residue_count": self._desktop_marker_count(
                recent_memory_events,
                ("suppress", "suppressed", "忍住", "压下", "没有发出去"),
            ),
            "memory_event_count": len([item for item in recent_memory_events if isinstance(item, dict)]),
            "proactive_item_count": len([item for item in proactive_items if isinstance(item, dict)]),
            "recent_turn_count": len([item for item in recent_turns if isinstance(item, dict)]),
        }
        if isinstance(self_choice_dream_bias, dict):
            window["self_choice"] = self_choice_dream_bias
        return window

    @staticmethod
    def _desktop_marker_count(items: list[Any], markers: tuple[str, ...]) -> int:
        lowered_markers = tuple(marker.lower() for marker in markers)
        count = 0
        for item in items:
            text = _safe_str(item).lower()
            if any(marker in text for marker in lowered_markers):
                count += 1
        return count

    def _desktop_xinyu_state(
        self,
        *,
        environment: dict[str, Any],
        entropy_state: dict[str, Any],
        active_desires: list[dict[str, Any]],
        proactive_items: list[Any],
        recent_turns: list[Any],
        recent_memory_events: list[Any],
        action_digest: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        latest_intent = proactive_items[0] if proactive_items and isinstance(proactive_items[0], dict) else {}
        latest_turn = recent_turns[-1] if recent_turns and isinstance(recent_turns[-1], dict) else {}
        sensation = environment.get("physicalSensation") if isinstance(environment.get("physicalSensation"), dict) else {}
        physical_sensation = _safe_str(sensation.get("phrase"), "体感未校准")
        pressure = _safe_str(sensation.get("pressure"), "unknown")
        active_desire = active_desires[0] if active_desires else {}
        resource_request = (
            entropy_state.get("resource_request") if isinstance(entropy_state.get("resource_request"), dict) else None
        )
        action_digest = action_digest if isinstance(action_digest, dict) else {}
        action_recent = action_digest.get("recent") if isinstance(action_digest.get("recent"), list) else []
        latest_action = action_recent[-1] if action_recent and isinstance(action_recent[-1], dict) else {}
        seed_detail = latest_action.get("seed_detail") if isinstance(latest_action.get("seed_detail"), dict) else {}
        seed_id = _safe_str(latest_action.get("seed_id"))
        reflection_item_id = _safe_str(latest_action.get("reflection_item_id"))
        consumed_at = _safe_str(seed_detail.get("consumed_at"))
        action_theme = _compact_text(_safe_str(seed_detail.get("theme")) or "行动经验正在沉淀", 96)
        action_theme_label = _desktop_action_theme_label(action_theme)
        action_residue = _compact_text(_safe_str(seed_detail.get("residue")) or action_theme, 140)
        action_result = _safe_str(latest_action.get("result"), "unknown") or "unknown"
        action_pressure = _safe_str(latest_action.get("pressure"), "unknown") or "unknown"
        digested_count = int(action_digest.get("digested_count") or 0) if str(action_digest.get("digested_count") or "0").isdigit() else 0
        action_route = ""
        if seed_id:
            if consumed_at and consumed_at != "none" and reflection_item_id:
                action_route = "已进梦境和反思"
            elif consumed_at and consumed_at != "none":
                action_route = "已被梦境消费"
            elif reflection_item_id:
                action_route = "已排入反思"
            else:
                action_route = "等待梦境处理"
        action_attention = _compact_text(f"行动残留：{action_theme_label}", 96) if seed_id else ""
        action_concern = _compact_text(
            f"{action_route or '行动沉淀'}；{_desktop_action_result_label(action_result)}，{_desktop_action_pressure_label(action_pressure)}",
            72,
        ) if seed_id else ""
        action_residue_label = _compact_text(
            f"{action_route or '行动沉淀'} · {_desktop_action_result_label(action_result)} · {_desktop_action_pressure_label(action_pressure)}",
            72,
        ) if seed_id else ""
        if seed_id and action_pressure in {"medium", "high"}:
            suffix = "行动余温偏重" if action_pressure == "high" else "行动余温未散"
            physical_sensation = _compact_text(f"{physical_sensation}；{suffix}", 64)
        attention = _compact_text(
            _safe_str(active_desire.get("visible_trace"))
            or _safe_str(latest_intent.get("focusLabel"))
            or _safe_str(latest_intent.get("kind"))
            or action_attention
            or _safe_str(entropy_state.get("visible_artifact"))
            or _safe_str(latest_turn.get("textPreview"))
            or _safe_str(latest_turn.get("replyPreview"))
            or "等待新的生活信号",
            96,
        )
        concern = _compact_text(
            _safe_str(active_desire.get("possible_action"))
            or _safe_str(resource_request.get("reason") if resource_request else "")
            or _safe_str(latest_intent.get("candidatePreview"))
            or _safe_str(latest_intent.get("whyNowPreview"))
            or action_concern
            or _safe_str(latest_turn.get("replyPreview"))
            or _safe_str(latest_turn.get("textPreview"))
            or "还没有新的牵挂浮上来",
            140,
        )
        waiting = bool(proactive_items)
        chosen_action = _safe_str(active_desire.get("chosen_action"))
        mood_tag = "想靠近" if waiting else "安静在场"
        if chosen_action == "suppress_and_wait":
            mood_tag = "想靠近但忍住了"
        elif chosen_action == "leave_note_on_desk":
            mood_tag = "把话留在桌面边缘"
        elif chosen_action == "request_metabolism_window":
            mood_tag = "在索求一次整理窗口"
        elif not waiting and _safe_str(entropy_state.get("entropy_band")) in {"fracture", "terminal"}:
            mood_tag = "熵噪堆积"
        if pressure == "high" and not chosen_action:
            mood_tag = "被热压住" if not waiting else mood_tag
        elif pressure == "low" and not waiting and not chosen_action:
            mood_tag = "失重安静"
        if seed_id and not waiting and not chosen_action and action_pressure in {"medium", "high"}:
            mood_tag = "行动残留未散"
        return {
            "version": 1,
            "mood_tag": mood_tag,
            "current_attention": attention,
            "recent_concerns": [concern],
            "is_waiting_for_reply": waiting,
            "physical_sensation": physical_sensation,
            "physical_sensation_tag": _safe_str(sensation.get("tag"), "unfelt"),
            "physical_pressure": pressure,
            "environment_sensor_quality": _safe_str(environment.get("sensorQuality"), "unknown"),
            "recent_memory_echoes": len(recent_memory_events),
            "entropy_level": entropy_state.get("entropy_level", 0.0),
            "entropy_band": _safe_str(entropy_state.get("entropy_band"), "clear"),
            "scar_level": entropy_state.get("scar_level", 0.0),
            "memory_decay_risk": entropy_state.get("memory_decay_risk", 0.0),
            "metabolism_needed": bool(entropy_state.get("metabolism_needed")),
            "entropy_visible_artifact": _safe_str(entropy_state.get("visible_artifact"), ""),
            "resource_request": resource_request,
            "metabolism_ticket_id": _safe_str(active_desire.get("metabolism_ticket_id")),
            "metabolism_ticket_status": _safe_str(active_desire.get("metabolism_ticket_status")),
            "action_experience_count": digested_count,
            "action_residue_label": action_residue_label,
            "action_residue_route": action_route,
            "action_residue_pressure": action_pressure if seed_id else "",
            "action_residue_result": action_result if seed_id else "",
            "action_residue_seed_id": seed_id,
            "action_residue_reflection_item_id": reflection_item_id,
        }

    async def desktop_events_recent(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await desktop_service_events_recent(self.desktop_event_bus, payload)

    async def desktop_proactive_inbox(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        _ = payload
        state_item = self._desktop_proactive_item_from_state()
        if state_item:
            self._desktop_upsert_proactive_inbox(state_item)
        else:
            self._desktop_clear_proactive_inbox()
        with self._desktop_proactive_lock:
            items = sorted(
                (dict(item) for item in self._desktop_proactive_inbox.values()),
                key=lambda item: _safe_str(item.get("createdAt")),
                reverse=True,
            )[:DESKTOP_PROACTIVE_INBOX_MAX]
        return {
            "version": 1,
            "items": items,
            "notes": ["desktop_proactive_inbox_v0_runtime_buffer"],
        }

    async def desktop_chat_recent(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return desktop_service_recent_items(
            self._desktop_recent_turns,
            payload,
            default=50,
            maximum=200,
            notes=["desktop_chat_recent_v0_runtime_buffer"],
        )

    async def desktop_memory_recent(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return desktop_service_recent_items(
            self._desktop_recent_memory_events,
            payload,
            default=100,
            maximum=500,
            notes=["desktop_memory_recent_v0_runtime_buffer"],
        )

    async def life_metabolism_ticket_get(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        ticket_id = _safe_str(payload.get("ticket_id") or payload.get("id")).strip()
        if not ticket_id:
            return {"accepted": False, "ticket": {}, "notes": ["missing_ticket_id"]}
        ticket = await asyncio.to_thread(get_metabolism_ticket, self.xinyu_dir, ticket_id)
        return {
            "accepted": bool(ticket),
            "ticket": ticket,
            "notes": ["ticket_found"] if ticket else ["ticket_not_found"],
        }

    async def life_metabolism_ticket_list(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        raw_status = _safe_str(payload.get("status") or payload.get("statuses")).strip()
        statuses = {part.strip() for part in raw_status.split(",") if part.strip()} if raw_status else None
        tickets = await asyncio.to_thread(list_metabolism_tickets, self.xinyu_dir, statuses=statuses)
        return {"accepted": True, "tickets": tickets, "notes": ["tickets_listed"]}

    async def life_metabolism_ticket_approve(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        ticket_id = _safe_str(payload.get("ticket_id") or payload.get("id")).strip()
        result = await asyncio.to_thread(
            approve_metabolism_ticket,
            self.xinyu_dir,
            ticket_id,
            owner_decision_id=_safe_str(payload.get("owner_decision_id") or payload.get("decision_id")).strip(),
            approved_seconds=_optional_int(payload.get("approved_seconds")),
            note=_safe_str(payload.get("note")),
        )
        await self._apply_self_choice_metabolism_decision("ticket_approved", result)
        await self._publish_metabolism_decision("approved", result)
        if result.get("accepted"):
            self._wake_metabolism_runner()
        return result

    async def life_metabolism_ticket_reject(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        ticket_id = _safe_str(payload.get("ticket_id") or payload.get("id")).strip()
        result = await asyncio.to_thread(
            reject_metabolism_ticket,
            self.xinyu_dir,
            ticket_id,
            owner_decision_id=_safe_str(payload.get("owner_decision_id") or payload.get("decision_id")).strip(),
            note=_safe_str(payload.get("note")),
        )
        await self._apply_self_choice_metabolism_decision("ticket_rejected", result)
        await self._publish_metabolism_decision("rejected", result)
        return result

    async def life_metabolism_ticket_cancel(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        ticket_id = _safe_str(payload.get("ticket_id") or payload.get("id")).strip()
        result = await asyncio.to_thread(
            cancel_metabolism_ticket,
            self.xinyu_dir,
            ticket_id,
            reason=_safe_str(payload.get("reason"), "owner_cancelled"),
        )
        await self._publish_metabolism_decision("cancelled", result)
        return result

    async def _apply_self_choice_metabolism_decision(self, event: str, result: dict[str, Any]) -> None:
        if not result.get("accepted") or result.get("idempotent"):
            return
        result["selfChoiceState"] = await self.self_choice_store.apply_event_impulse(event)

    async def _publish_metabolism_decision(self, decision: str, result: dict[str, Any]) -> None:
        ticket = result.get("ticket") if isinstance(result.get("ticket"), dict) else {}
        await self._desktop_publish_event(
            "metabolism_ticket_updated",
            {
                "decision": decision,
                "accepted": bool(result.get("accepted")),
                "ticket": ticket,
                "selfChoiceState": result.get("selfChoiceState") if isinstance(result.get("selfChoiceState"), dict) else {},
                "notes": result.get("notes", []),
            },
            severity="info" if result.get("accepted") else "warn",
        )

    async def _desktop_event_state(self) -> dict[str, Any]:
        return await desktop_service_event_state(self.desktop_event_bus)

    def _desktop_services(self) -> list[dict[str, Any]]:
        return desktop_service_services(
            ws_server=self.desktop_ws_server,
            closed=self._closed,
            memory_root_exists=self.memory_root.exists(),
        )

    @staticmethod
    def _desktop_limit(value: Any, *, default: int, maximum: int) -> int:
        return desktop_service_limit(value, default=default, maximum=maximum)

    async def _desktop_publish_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        privacy: str = "internal_summary",
        severity: str | None = None,
    ) -> dict[str, Any]:
        if self.desktop_event_bus is None:
            return {}
        try:
            return await self.desktop_event_bus.publish(
                event_type,
                payload,
                source="xinyu_core_bridge",
                privacy=privacy,
                severity=severity,
            )
        except Exception as exc:
            print(f"[xinyu_core_bridge] desktop event publish failed: {event_type}: {exc}", flush=True)
            return {}

    def _desktop_publish_event_threadsafe(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        privacy: str = "internal_summary",
        severity: str | None = None,
    ) -> None:
        if self.desktop_event_bus is None:
            return
        try:
            future = self.desktop_event_bus.publish_threadsafe(
                event_type,
                payload,
                source="xinyu_core_bridge",
                privacy=privacy,
                severity=severity,
            )

            def _log_failure(done: Any) -> None:
                try:
                    done.result()
                except Exception as exc:
                    print(
                        f"[xinyu_core_bridge] desktop event publish failed: {event_type}: {exc}",
                        flush=True,
                    )

            future.add_done_callback(_log_failure)
        except Exception as exc:
            print(f"[xinyu_core_bridge] desktop event publish scheduling failed: {event_type}: {exc}", flush=True)

    async def _desktop_publish_chat_started(
        self,
        payload: dict[str, Any],
        *,
        text: str,
        session_key: str,
        turn_id: str,
        started_at: str,
        active_sessions: int,
    ) -> None:
        await self._desktop_publish_event(
            "chat.turn.started",
            {
                **self._desktop_turn_base(payload, session_key=session_key, turn_id=turn_id),
                "startedAt": started_at,
                "textPreview": self._desktop_text_preview(text, limit=180),
                "textChars": len(text),
                "activeSessions": active_sessions,
            },
            privacy=self._desktop_privacy_for_payload(payload),
        )

    async def _desktop_publish_chat_finished(
        self,
        payload: dict[str, Any],
        *,
        text: str,
        reply: str,
        session_key: str,
        turn_id: str,
        started_at: str,
        elapsed_ms: int,
        status: str,
        notes: list[str] | tuple[str, ...] | None = None,
        memory_changed: bool = False,
        archive_message_ids: list[Any] | tuple[Any, ...] | None = None,
        reply_hash: str = "",
        recall_event_id: str = "",
        recall_count: int = 0,
        top_recall_sources: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        safe_notes = [_safe_str(note) for note in list(notes or []) if _safe_str(note)][:12]
        item = {
            **self._desktop_turn_base(payload, session_key=session_key, turn_id=turn_id),
            "startedAt": started_at,
            "finishedAt": datetime.now().astimezone().isoformat(),
            "status": _safe_str(status, "unknown") or "unknown",
            "latencyMs": max(0, int(elapsed_ms)),
            "textPreview": self._desktop_text_preview(text, limit=180),
            "replyPreview": self._desktop_text_preview(reply, limit=220),
            "textChars": len(text),
            "replyChars": len(reply),
            "memoryChanged": bool(memory_changed),
            "replyHash": reply_hash or (visible_text_hash(reply) if reply else ""),
            "archiveMessageIds": [_safe_str(value) for value in list(archive_message_ids or [])[:8]],
            "recallEventId": _safe_str(recall_event_id),
            "recallCount": max(0, int(recall_count)),
            "topRecallSources": [_safe_str(source) for source in list(top_recall_sources or [])[:6]],
            "notes": safe_notes,
        }
        self._desktop_remember_turn(item)
        severity = "error" if item["status"] == "error" else ("warn" if item["status"] == "timeout" else None)
        await self._desktop_publish_event(
            "chat.turn.finished",
            item,
            privacy=self._desktop_privacy_for_payload(payload),
            severity=severity,
        )

    async def _desktop_publish_memory_recall(
        self,
        payload: dict[str, Any],
        result: Any,
        *,
        session_key: str,
        turn_id: str,
    ) -> dict[str, Any]:
        notes = [_safe_str(note) for note in tuple(getattr(result, "notes", ()) or ()) if _safe_str(note)]
        if any(note in {"retrieval_disabled", "retrieval_not_needed"} for note in notes):
            return {}
        raw_items = list(getattr(result, "items", ()) or ())
        items = [self._desktop_recall_item(item) for item in raw_items[:8]]
        status = "used" if items else "empty"
        top_sources = _dedupe([_safe_str(item.get("source")) for item in items if _safe_str(item.get("source"))])[:6]
        query_text = _safe_str(getattr(result, "query_text", ""))
        event_payload = {
            **self._desktop_turn_base(payload, session_key=session_key, turn_id=turn_id),
            "status": status,
            "recallTurnId": _safe_str(getattr(result, "turn_id", "")),
            "queryHash": self._desktop_hash(query_text),
            "queryChars": len(query_text),
            "itemCount": len(raw_items),
            "topSources": top_sources,
            "items": items,
            "notes": notes[:8],
        }
        event = await self._desktop_publish_event(
            "memory.recall.used",
            event_payload,
            privacy=self._desktop_privacy_for_payload(payload),
        )
        if event:
            self._desktop_remember_memory_event(
                {
                    "eventId": _safe_str(event.get("id")),
                    "ts": _safe_str(event.get("ts")),
                    **event_payload,
                }
            )
        return event

    def _desktop_recall_item(self, item: Any) -> dict[str, Any]:
        memory_ref = _safe_str(getattr(item, "memory_ref", ""))
        message_id = getattr(item, "message_id", None)
        return {
            "recallId": _safe_str(getattr(item, "recall_id", "")),
            "source": _safe_str(getattr(item, "source", "")),
            "scope": _safe_str(getattr(item, "scope", "")),
            "time": _safe_str(getattr(item, "time", "")),
            "speaker": _safe_str(getattr(item, "speaker", "")),
            "summaryPreview": self._desktop_text_preview(_safe_str(getattr(item, "summary", "")), limit=220),
            "relevancePreview": self._desktop_text_preview(_safe_str(getattr(item, "relevance", "")), limit=180),
            "confidence": _safe_str(getattr(item, "confidence", "")),
            "score": round(float(getattr(item, "score", 0.0) or 0.0), 3),
            "messageId": int(message_id) if isinstance(message_id, int) else None,
            "memoryRef": memory_ref[:240],
            "memoryRefHash": self._desktop_hash(memory_ref),
        }

    @staticmethod
    def _desktop_recall_count(result: Any) -> int:
        if result is None:
            return 0
        return len(list(getattr(result, "items", ()) or ()))

    @staticmethod
    def _desktop_top_recall_sources(result: Any) -> list[str]:
        if result is None:
            return []
        sources = [_safe_str(getattr(item, "source", "")) for item in list(getattr(result, "items", ()) or ())]
        return _dedupe([source for source in sources if source])[:6]

    async def _desktop_publish_proactive_candidate_ready_from_state(
        self,
        *,
        notes: list[str] | tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        item = self._desktop_proactive_item_from_state(include_final=False)
        if not item:
            return {}
        existing = self._desktop_proactive_existing(item["candidateId"])
        self._desktop_upsert_proactive_inbox(item)
        if existing.get("readyEventId") and existing.get("candidatePreview") == item.get("candidatePreview"):
            return {"id": existing.get("readyEventId", "")}
        event_payload = {
            **item,
            "notes": _dedupe(list(item.get("notes", [])) + list(notes or []))[:10],
        }
        event = await self._desktop_publish_event(
            "proactive.candidate.ready",
            event_payload,
            privacy="owner_private",
        )
        if event:
            item["readyEventId"] = _safe_str(event.get("id"))
            self._desktop_upsert_proactive_inbox(item)
        return event

    def _desktop_schedule_proactive_candidate_ready_from_state(
        self,
        *,
        notes: list[str] | tuple[str, ...] | None = None,
    ) -> bool:
        if self.desktop_event_bus is None:
            return False
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return False
        loop.create_task(
            self._desktop_publish_proactive_candidate_ready_from_state(notes=notes),
            name="xinyu-desktop-proactive-candidate-ready",
        )
        return True

    async def _desktop_publish_proactive_delivery_from_state(
        self,
        *,
        status_override: str = "",
        notes: list[str] | tuple[str, ...] | None = None,
        severity: str | None = None,
    ) -> dict[str, Any]:
        item = self._desktop_proactive_item_from_state(include_final=True)
        if not item:
            return {}
        return await self._desktop_publish_proactive_delivery_item(
            item,
            status_override=status_override,
            notes=notes,
            severity=severity,
        )

    async def _desktop_publish_proactive_delivery_item(
        self,
        item: dict[str, Any],
        *,
        status_override: str = "",
        notes: list[str] | tuple[str, ...] | None = None,
        severity: str | None = None,
    ) -> dict[str, Any]:
        payload = self._desktop_proactive_delivery_payload(item, status_override=status_override, notes=notes)
        self._desktop_apply_proactive_delivery(payload)
        return await self._desktop_publish_event(
            "proactive.delivery.updated",
            payload,
            privacy="owner_private",
            severity=severity or ("error" if payload.get("status") == "failed" else None),
        )

    def _desktop_publish_proactive_delivery_from_state_threadsafe(
        self,
        *,
        status_override: str = "",
        notes: list[str] | tuple[str, ...] | None = None,
        severity: str | None = None,
    ) -> None:
        item = self._desktop_proactive_item_from_state(include_final=True)
        if not item:
            return
        payload = self._desktop_proactive_delivery_payload(item, status_override=status_override, notes=notes)
        self._desktop_apply_proactive_delivery(payload)
        self._desktop_publish_event_threadsafe(
            "proactive.delivery.updated",
            payload,
            privacy="owner_private",
            severity=severity or ("error" if payload.get("status") == "failed" else None),
        )

    def _desktop_proactive_delivery_payload(
        self,
        item: dict[str, Any],
        *,
        status_override: str = "",
        notes: list[str] | tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        status = _safe_str(status_override or item.get("status"), "unknown") or "unknown"
        return {
            **item,
            "status": status,
            "updatedAt": datetime.now().astimezone().isoformat(),
            "claimId": _safe_str(item.get("claimId")),
            "ackStatus": _safe_str(item.get("ackStatus")),
            "adapterMessageHash": self._desktop_hash(item.get("adapterMessageId")),
            "adapterErrorPreview": self._desktop_text_preview(_safe_str(item.get("adapterError")), limit=180),
            "notes": _dedupe(list(item.get("notes", [])) + list(notes or []))[:10],
        }

    def _desktop_apply_proactive_delivery(self, payload: dict[str, Any]) -> None:
        status = _safe_str(payload.get("status"))
        candidate_id = _safe_str(payload.get("candidateId"))
        if not candidate_id:
            return
        if status in DESKTOP_PROACTIVE_FINAL_STATUSES:
            self._desktop_remove_proactive_inbox(candidate_id)
            return
        self._desktop_upsert_proactive_inbox(payload)

    def _desktop_proactive_item_from_state(self, *, include_final: bool = False) -> dict[str, Any]:
        state = _read_text_safe(self.xinyu_dir / "memory/context/proactive_request_state.md")
        if not state:
            return {}
        status = _state_field(state, "status", "unknown")
        expires_at = _state_field(state, "expires_at", "")
        if self._desktop_proactive_expired(expires_at) and status in DESKTOP_PROACTIVE_INBOX_STATUSES:
            status = "expired"
        if not include_final and status not in DESKTOP_PROACTIVE_INBOX_STATUSES:
            return {}
        if include_final and status in {"", "unknown"}:
            return {}

        request_id = _state_field(state, "request_id", "")
        question = _state_field(state, "concrete_question", "")
        candidate_id = request_id if request_id not in {"", "none", "unknown"} else self._desktop_hash(question)
        if not candidate_id:
            return {}
        delivery_level = _state_field(state, "delivery_level", "none")
        claim_id = _state_field(state, "last_claim_id", "")
        ack_status = _state_field(state, "last_ack_status", "")
        adapter_message_id = _state_field(state, "adapter_message_id", "")
        adapter_error = _state_field(state, "adapter_error", "")
        return {
            "candidateId": candidate_id,
            "requestId": request_id,
            "status": status,
            "deliveryLevel": delivery_level,
            "requiresOwnerAck": status == "candidate_only" or delivery_level in {"state_only", "preview_only"},
            "claimable": status == "ready" and delivery_level in {"queue_owner_private", "claim_ack"},
            "createdAt": _state_field(state, "created_at", ""),
            "expiresAt": expires_at,
            "kind": _state_field(state, "kind", ""),
            "source": _state_field(state, "source", ""),
            "focusKind": _state_field(state, "focus_kind", ""),
            "focusLabel": self._desktop_text_preview(_state_field(state, "focus_label", ""), limit=120),
            "priority": _state_field(state, "priority", ""),
            "requestFamily": _state_field(state, "request_family", ""),
            "threadId": _state_field(state, "thread_id", ""),
            "requestedAction": _state_field(state, "requested_action", ""),
            "evidenceHash": _state_field(state, "evidence_hash", ""),
            "dedupeHash": self._desktop_hash(_state_field(state, "dedupe_key", "")),
            "candidatePreview": self._desktop_text_preview(question, limit=240),
            "whyNowPreview": self._desktop_text_preview(_state_field(state, "why_now", ""), limit=220),
            "answerState": _state_field(state, "request_answer_state", "pending"),
            "claimId": claim_id,
            "ackStatus": ack_status,
            "adapterMessageId": adapter_message_id,
            "adapterError": adapter_error,
            "notes": [],
        }

    def _desktop_proactive_existing(self, candidate_id: str) -> dict[str, Any]:
        with self._desktop_proactive_lock:
            return dict(self._desktop_proactive_inbox.get(candidate_id, {}))

    def _desktop_upsert_proactive_inbox(self, item: dict[str, Any]) -> None:
        candidate_id = _safe_str(item.get("candidateId"))
        if not candidate_id:
            return
        with self._desktop_proactive_lock:
            existing = self._desktop_proactive_inbox.get(candidate_id, {})
            merged = {**existing, **dict(item)}
            self._desktop_proactive_inbox.clear()
            self._desktop_proactive_inbox[candidate_id] = merged

    def _desktop_remove_proactive_inbox(self, candidate_id: str) -> None:
        with self._desktop_proactive_lock:
            self._desktop_proactive_inbox.pop(candidate_id, None)

    def _desktop_clear_proactive_inbox(self) -> None:
        with self._desktop_proactive_lock:
            self._desktop_proactive_inbox.clear()

    def _desktop_prune_proactive_inbox(self) -> None:
        with self._desktop_proactive_lock:
            stale = [
                candidate_id
                for candidate_id, item in self._desktop_proactive_inbox.items()
                if _safe_str(item.get("status")) in DESKTOP_PROACTIVE_FINAL_STATUSES
                or self._desktop_proactive_expired(_safe_str(item.get("expiresAt")))
            ]
            for candidate_id in stale:
                self._desktop_proactive_inbox.pop(candidate_id, None)

    @staticmethod
    def _desktop_proactive_expired(expires_at: str) -> bool:
        if expires_at in {"", "none", "unknown"}:
            return False
        parsed = _parse_iso(expires_at)
        if parsed is None:
            return False
        return datetime.now().astimezone() >= parsed

    def _desktop_remember_turn(self, item: dict[str, Any]) -> None:
        self._desktop_recent_turns.append(dict(item))
        if len(self._desktop_recent_turns) > DESKTOP_RECENT_TURNS_MAX:
            del self._desktop_recent_turns[: len(self._desktop_recent_turns) - DESKTOP_RECENT_TURNS_MAX]

    def _desktop_remember_memory_event(self, item: dict[str, Any]) -> None:
        self._desktop_recent_memory_events.append(dict(item))
        if len(self._desktop_recent_memory_events) > DESKTOP_RECENT_MEMORY_EVENTS_MAX:
            del self._desktop_recent_memory_events[
                : len(self._desktop_recent_memory_events) - DESKTOP_RECENT_MEMORY_EVENTS_MAX
            ]

    def _desktop_turn_base(self, payload: dict[str, Any], *, session_key: str, turn_id: str) -> dict[str, Any]:
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        source = _safe_str(payload.get("source") or payload.get("adapter") or "qq_gateway", "qq_gateway")
        session_kind = self._desktop_session_kind(payload)
        user_display_id = self._desktop_display_id(payload.get("user_id"))
        group_display_id = self._desktop_display_id(payload.get("group_id"))
        return {
            "turnId": _safe_str(turn_id),
            "commandId": _safe_str(metadata.get("desktop_command_id") or payload.get("command_id")),
            "sessionHash": self._desktop_hash(session_key),
            "sessionKind": session_kind,
            "sessionLabel": self._desktop_session_label(payload, session_kind=session_kind, metadata=metadata),
            "accountLabel": self._desktop_account_label(
                payload,
                session_kind=session_kind,
                metadata=metadata,
                user_display_id=user_display_id,
                group_display_id=group_display_id,
            ),
            "avatarUrl": self._desktop_avatar_url(payload, session_kind=session_kind, user_display_id=user_display_id),
            "groupAvatarUrl": self._desktop_group_avatar_url(group_display_id),
            "platform": _safe_str(payload.get("platform"), "qq"),
            "source": source,
            "messageType": _safe_str(payload.get("message_type")),
            "isOwner": _as_bool(metadata.get("is_owner_user"), default=False),
            "isTrusted": _as_bool(metadata.get("is_trusted_user"), default=False),
            "trustLevel": _safe_str(metadata.get("user_trust_level")),
            "senderName": self._desktop_text_preview(_safe_str(payload.get("sender_name")), limit=80),
            "userDisplayId": user_display_id,
            "groupDisplayId": group_display_id,
            "userHash": self._desktop_hash(payload.get("user_id")),
            "groupHash": self._desktop_hash(payload.get("group_id")),
            "messageHash": self._desktop_hash(payload.get("message_id")),
        }

    @staticmethod
    def _desktop_session_kind(payload: dict[str, Any]) -> str:
        message_type = _safe_str(payload.get("message_type")).lower()
        platform = _safe_str(payload.get("platform")).lower()
        if platform == "desktop" or message_type.startswith("desktop"):
            return "desktop_private"
        if message_type.startswith("group") or _safe_str(payload.get("group_id")).strip():
            return "qq_group"
        if message_type.startswith("private") or _safe_str(payload.get("user_id")).strip():
            return "qq_private"
        return "system"

    def _desktop_session_label(
        self,
        payload: dict[str, Any],
        *,
        session_kind: str,
        metadata: dict[str, Any],
    ) -> str:
        sender_name = self._desktop_text_preview(_safe_str(payload.get("sender_name")), limit=48)
        user_hash = self._desktop_hash(payload.get("user_id"), length=8)
        group_hash = self._desktop_hash(payload.get("group_id"), length=8)
        fallback_contact = sender_name or (f"#{user_hash}" if user_hash else "未知联系人")
        if session_kind == "desktop_private":
            return "桌面主人"
        if session_kind == "qq_group":
            target = sender_name or (f"群#{group_hash}" if group_hash else "未知群聊")
            return f"QQ群聊 / {target}"
        if session_kind == "qq_private":
            if _as_bool(metadata.get("is_owner_user"), default=False):
                relation = "主人QQ"
            elif _as_bool(metadata.get("is_trusted_user"), default=False):
                relation = "可信QQ"
            else:
                relation = "外部QQ"
            return f"{relation} / {fallback_contact}"
        return "系统窗口"

    @staticmethod
    def _desktop_display_id(value: Any) -> str:
        text = _safe_str(value).strip()
        if re.fullmatch(r"\d{4,20}", text):
            return text
        return ""

    def _desktop_account_label(
        self,
        payload: dict[str, Any],
        *,
        session_kind: str,
        metadata: dict[str, Any],
        user_display_id: str,
        group_display_id: str,
    ) -> str:
        if session_kind == "desktop_private":
            return "桌面 owner"
        if session_kind == "qq_group":
            parts = []
            if group_display_id:
                parts.append(f"群 {group_display_id}")
            if user_display_id:
                parts.append(f"QQ {user_display_id}")
            return " / ".join(parts) or "QQ群聊"
        if session_kind == "qq_private":
            prefix = (
                "主人QQ"
                if _as_bool(metadata.get("is_owner_user"), default=False)
                else ("可信QQ" if _as_bool(metadata.get("is_trusted_user"), default=False) else "外部QQ")
            )
            return f"{prefix} {user_display_id}" if user_display_id else prefix
        return _safe_str(payload.get("platform"), "system")

    @staticmethod
    def _desktop_avatar_url(
        payload: dict[str, Any],
        *,
        session_kind: str,
        user_display_id: str,
    ) -> str:
        if session_kind in {"qq_private", "qq_group"} and user_display_id:
            return f"https://q1.qlogo.cn/g?b=qq&nk={user_display_id}&s=100"
        metadata = payload.get("metadata")
        if isinstance(metadata, dict):
            avatar = _safe_str(metadata.get("avatar_url") or metadata.get("qq_avatar_url")).strip()
            if avatar.startswith(("http://", "https://")):
                return avatar
        return ""

    @staticmethod
    def _desktop_group_avatar_url(group_display_id: str) -> str:
        if group_display_id:
            return f"https://p.qlogo.cn/gh/{group_display_id}/{group_display_id}/100"
        return ""

    @staticmethod
    def _desktop_privacy_for_payload(payload: dict[str, Any]) -> str:
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        message_type = _safe_str(payload.get("message_type")).lower()
        source = _safe_str(payload.get("source") or metadata.get("source")).lower()
        if message_type.startswith("group") or _safe_str(payload.get("group_id")).strip():
            return "group_context"
        if message_type.startswith("system") or source.startswith("maintenance"):
            return "system_internal"
        if _as_bool(metadata.get("is_owner_user"), default=False):
            return "owner_private"
        return "external_private"

    @staticmethod
    def _desktop_hash(value: Any, *, length: int = 16) -> str:
        text = _safe_str(value).strip()
        if not text:
            return ""
        return "sha256:" + hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:length]

    @staticmethod
    def _desktop_text_preview(text: str, *, limit: int) -> str:
        compact = re.sub(r"\s+", " ", _desktop_scrub_action_markers(text)).strip()
        if limit > 3 and len(compact) > limit:
            return compact[: limit - 3].rstrip() + "..."
        return compact

    def _v1_health(self) -> dict[str, Any]:
        return xinyu_bridge_v1_routes.health(self)

    def _ensure_v1_app(self) -> Any:
        return xinyu_bridge_v1_routes.ensure_app(self)

    def _record_v1_shadow_readiness(
        self,
        shadow_payload: dict[str, Any],
        *,
        accepted: bool,
        route: str,
        trace_id: str,
        elapsed_ms: int,
        error: str = "",
    ) -> list[str]:
        return xinyu_bridge_v1_routes.record_shadow_readiness(
            self,
            shadow_payload,
            accepted=accepted,
            route=route,
            trace_id=trace_id,
            elapsed_ms=elapsed_ms,
            error=error,
        )

    async def _run_v1_shadow(self, payload: dict[str, Any], *, text: str) -> dict[str, Any]:
        return await xinyu_bridge_v1_routes.run_shadow(self, payload, text=text)

    def _v1_canary_payload_allowed(self, payload: dict[str, Any], text: str) -> tuple[bool, list[str]]:
        return xinyu_bridge_v1_routes.canary_payload_allowed(self, payload, text)

    async def _maybe_handle_v1_canary_turn(
        self,
        payload: dict[str, Any],
        *,
        text: str,
        session_key: str,
        turn_id: str,
        turn_started_wall: str,
        turn_started_at: float,
        before_memory: dict[str, Any],
        cleanup: dict[str, Any],
        event_sidecar: dict[str, Any],
    ) -> dict[str, Any] | None:
        return await xinyu_bridge_v1_routes.handle_canary_turn(
            self,
            payload,
            text=text,
            session_key=session_key,
            turn_id=turn_id,
            turn_started_wall=turn_started_wall,
            turn_started_at=turn_started_at,
            before_memory=before_memory,
            cleanup=cleanup,
            event_sidecar=event_sidecar,
        )

    async def start_background_tasks(self) -> None:
        if self._closed:
            return
        await self._ensure_self_choice_ready()
        await self.self_choice_store.apply_time_decay()
        if not self._self_choice_boot_logged:
            print(self.self_choice_store.boot_log_line(), flush=True)
            self._self_choice_boot_logged = True
        if self._metabolism_wakeup_event is None:
            self._metabolism_wakeup_event = asyncio.Event()
        if self._metabolism_task is None or self._metabolism_task.done():
            self._metabolism_task = asyncio.create_task(
                self._metabolism_runner_loop(),
                name="xinyu-metabolism-runner",
            )
        if not self.autonomous_maintenance_enabled:
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

    async def _metabolism_runner_loop(self) -> None:
        wakeup = self._metabolism_wakeup_event
        if wakeup is None:
            wakeup = asyncio.Event()
            self._metabolism_wakeup_event = wakeup
        while not self._closed:
            try:
                await self._run_due_metabolism_once(trigger="tick")
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._metabolism_last_error = f"tick_error:{exc!r}"
                print(f"[xinyu_core_bridge] metabolism runner error: {exc!r}", flush=True)
            try:
                await asyncio.wait_for(wakeup.wait(), timeout=self.metabolism_runner_interval_seconds)
                wakeup.clear()
                if not self._closed:
                    await self._run_due_metabolism_once(trigger="wakeup")
            except asyncio.TimeoutError:
                continue

    async def _run_due_metabolism_once(self, *, trigger: str) -> dict[str, Any]:
        if self._closed or self._metabolism_in_progress:
            return {"ran": 0, "notes": ["closed_or_in_progress"]}
        self._metabolism_in_progress = True
        self._metabolism_last_started_at = datetime.now().astimezone().isoformat(timespec="seconds")
        try:
            result = await asyncio.to_thread(
                run_due_metabolism_tickets,
                self.xinyu_dir,
                runner_id=f"core_bridge:{os.getpid()}:{trigger}",
                max_tickets=3,
            )
            self._metabolism_run_count += int(result.get("ran") or 0)
            self._metabolism_last_result = result
            self._metabolism_last_success_at = datetime.now().astimezone().isoformat(timespec="seconds")
            self._metabolism_last_error = ""
            await self._publish_metabolism_runner_result(result, trigger=trigger)
            return result
        except Exception as exc:
            self._metabolism_last_error = f"{type(exc).__name__}: {exc}"
            self_choice_state = await self.self_choice_store.apply_event_impulse("ticket_failed")
            await self._desktop_publish_event(
                "metabolism_runner_failed",
                {"error": self._metabolism_last_error, "trigger": trigger, "selfChoiceState": self_choice_state},
                severity="error",
            )
            raise
        finally:
            self._metabolism_in_progress = False

    async def _publish_metabolism_runner_result(self, result: dict[str, Any], *, trigger: str) -> None:
        settled = result.get("settled") if isinstance(result.get("settled"), list) else []
        if not settled:
            return
        for item in settled:
            if not isinstance(item, dict):
                continue
            ticket = item.get("ticket") if isinstance(item.get("ticket"), dict) else {}
            status = _safe_str(ticket.get("status"))
            self_choice_state: dict[str, Any] = {}
            if status == "settled" or item.get("settled"):
                self_choice_state = await self.self_choice_store.apply_event_impulse("ticket_settled")
                await self.self_choice_store.consume_hibernation_residue_for_metabolism()
            elif status == "failed":
                self_choice_state = await self.self_choice_store.apply_event_impulse("ticket_failed")
                await self.self_choice_store.consume_hibernation_residue_for_metabolism()
            await self._desktop_publish_event(
                "metabolism_ticket_updated",
                {
                    "trigger": trigger,
                    "ticket": ticket,
                    "metabolism_path": _safe_str(item.get("metabolism_path")),
                    "dream_path": _safe_str(item.get("dream_path")),
                    "selfChoiceState": self_choice_state,
                    "notes": item.get("notes", []),
                },
                severity="info",
            )

    def _wake_metabolism_runner(self) -> None:
        wakeup = self._metabolism_wakeup_event
        if wakeup is not None:
            wakeup.set()

    def _metabolism_health(self) -> dict[str, Any]:
        task = self._metabolism_task
        return {
            "task_running": bool(task is not None and not task.done()),
            "in_progress": self._metabolism_in_progress,
            "interval_seconds": self.metabolism_runner_interval_seconds,
            "run_count": self._metabolism_run_count,
            "last_started_at": self._metabolism_last_started_at,
            "last_success_at": self._metabolism_last_success_at,
            "last_error": self._metabolism_last_error,
        }

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
            custom_dir = self.xinyu_dir / "custom"
            if str(custom_dir) not in sys.path:
                sys.path.insert(0, str(custom_dir))
            from github_autonomous_learning_engine import run_github_autonomous_learning

            github = run_github_autonomous_learning(
                self.xinyu_dir,
                checked_at=checked_at,
                mode="autonomous_maintenance_github_learning",
                max_stage=1,
                min_interval_seconds=max(self.autonomous_maintenance_interval_seconds, 21600),
            )
            notes.append(
                "github_learning:"
                f"{_safe_str(github.get('status'), 'unknown')}/"
                f"{_safe_str(github.get('candidates_found'), '0')}/"
                f"{_safe_str(github.get('staged_repos'), '0')}"
            )
        except Exception as exc:
            notes.append(f"github_learning_error:{type(exc).__name__}")
            self._trace_autonomous(f"github_learning_error={exc!r}")
        try:
            digest = run_daily_digest_maintenance(self.xinyu_dir, observed_at=checked_at)
            notes.append(
                "daily_digest:"
                f"{_safe_str(digest.get('status'), 'unknown')}/"
                f"{str(_as_bool(digest.get('generated'), default=False)).lower()}"
            )
        except Exception as exc:
            notes.append(f"daily_digest_error:{type(exc).__name__}")
            self._trace_autonomous(f"daily_digest_error={exc!r}")
        try:
            review = run_review_inbox_maintenance(
                self.xinyu_dir,
                owner_user_id=self._owner_private_user_id(),
                max_items=3,
                reason="autonomous_maintenance",
            )
            notes.append(
                "review_inbox:"
                f"{_safe_str(review.get('pending_count'), '0')}/"
                f"{str(_as_bool(review.get('queued'), default=False)).lower()}"
            )
        except Exception as exc:
            notes.append(f"review_inbox_error:{type(exc).__name__}")
            self._trace_autonomous(f"review_inbox_error={exc!r}")
        try:
            goldmark = run_goldmark_dehydration_maintenance(
                self.xinyu_dir,
                limit=5,
                provider="auto",
                timeout_seconds=45,
            )
            notes.append(
                "goldmark_dehydrate:"
                f"{_safe_str(goldmark.get('status'), 'unknown')}/"
                f"{_safe_str(goldmark.get('processed'), '0')}/"
                f"{_safe_str(goldmark.get('succeeded'), '0')}/"
                f"{_safe_str(goldmark.get('skipped'), '0')}/"
                f"{_safe_str(goldmark.get('failed'), '0')}"
            )
        except Exception as exc:
            notes.append(f"goldmark_dehydrate_error:{type(exc).__name__}")
            self._trace_autonomous(f"goldmark_dehydrate_error={exc!r}")
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
            self._append_proactivity_shadow_note(notes, checked_at=checked_at)
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
            self._append_proactivity_shadow_note(notes, checked_at=checked_at)
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
            if _safe_str(request.get("status")) in {"ready", "candidate_only"}:
                scheduled = self._desktop_schedule_proactive_candidate_ready_from_state(
                    notes=[_safe_str(note) for note in request.get("notes", [])[:4]],
                )
                if scheduled:
                    notes.append("desktop_proactive_candidate_ready_scheduled")
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
        self._append_proactivity_shadow_note(notes, checked_at=checked_at)
        return notes

    def _append_proactivity_shadow_note(self, notes: list[str], *, checked_at: str) -> None:
        try:
            shadow = run_proactivity_scorer_shadow(self.xinyu_dir, checked_at=checked_at)
            notes.append(
                "proactivity_shadow:"
                f"{_safe_str(shadow.get('status'), 'unknown')}/"
                f"{_safe_str(shadow.get('source_type'), 'none')}/"
                f"{_safe_str(shadow.get('total_score'), '0')}/"
                f"{_safe_str(shadow.get('preferred_channel'), 'silent')}"
            )
        except Exception as exc:
            notes.append(f"proactivity_shadow_error:{type(exc).__name__}")
            self._trace_autonomous(f"proactivity_shadow_error={exc!r}")
        self._append_impulse_soup_note(notes, checked_at=checked_at)

    def _append_impulse_soup_note(self, notes: list[str], *, checked_at: str) -> None:
        try:
            soup = run_impulse_soup(self.xinyu_dir, checked_at=checked_at)
            notes.append(
                "impulse_soup:"
                f"{_safe_str(soup.get('status'), 'unknown')}/"
                f"{_safe_str(soup.get('active_count'), '0')}/"
                f"{_safe_str(soup.get('lineage_count'), '0')}/"
                f"{_safe_str(soup.get('top_desire_shape'), 'none')}"
            )
        except Exception as exc:
            notes.append(f"impulse_soup_error:{type(exc).__name__}")
            self._trace_autonomous(f"impulse_soup_error={exc!r}")

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
            atomic_write_text(state_path, text)
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
            result = await proactive_bridge(
                xinyu_dir=self.xinyu_dir,
                memory_root=self.memory_root,
                payload=payload or {},
                proactive_min_interval_seconds=self.proactive_min_interval_seconds,
                cleanup_idle_sessions=self._cleanup_idle_sessions,
                session_count=lambda: len(self._sessions),
                lock=self._global_turn_lock,
            )
            if result.get("candidate_claimed"):
                await self._desktop_publish_proactive_delivery_from_state(
                    status_override="claimed",
                    notes=[_safe_str(note) for note in result.get("notes", [])[:4]],
                )
            elif _safe_str(result.get("preview_reply") or result.get("candidate_message")).strip():
                await self._desktop_publish_proactive_candidate_ready_from_state(
                    notes=[_safe_str(note) for note in result.get("notes", [])[:4]],
                )
            return result
        except ValueError as exc:
            raise BridgeRequestError(HTTPStatus.BAD_REQUEST, str(exc)) from exc

    async def proactive_ack(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._closed:
            raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")
        if payload is not None and not isinstance(payload, dict):
            raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
        result = await proactive_ack_bridge(
            xinyu_dir=self.xinyu_dir,
            memory_root=self.memory_root,
            payload=payload or {},
            cleanup_idle_sessions=self._cleanup_idle_sessions,
            session_count=lambda: len(self._sessions),
            lock=self._global_turn_lock,
        )
        if result.get("ack_recorded"):
            await self._desktop_publish_proactive_delivery_from_state(
                status_override=_safe_str(result.get("ack_status"), "sent"),
                notes=[_safe_str(note) for note in result.get("notes", [])[:4]],
                severity="error" if _safe_str(result.get("ack_status")) == "failed" else None,
            )
        return result

    async def desktop_proactive_ack(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._closed:
            raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")
        if payload is not None and not isinstance(payload, dict):
            raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
        payload = payload or {}
        candidate_id = _safe_str(
            payload.get("candidateId") or payload.get("candidate_id") or payload.get("requestId")
        ).strip()
        action = _safe_str(payload.get("action")).strip().lower()
        if not candidate_id:
            raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "missing candidateId")
        if action not in DESKTOP_PROACTIVE_ACK_ACTIONS:
            raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "invalid desktop proactive action")

        item = self._desktop_proactive_item_from_state(include_final=True)
        if not item:
            item = self._desktop_proactive_existing(candidate_id)
        if not item or _safe_str(item.get("candidateId")) != candidate_id:
            raise BridgeRequestError(HTTPStatus.NOT_FOUND, "desktop proactive candidate not found")

        if action == "read_locally":
            return await self._desktop_finish_proactive_ack(
                item,
                action="read_locally",
                status="read_locally",
                answer_state="read_locally",
                ack_status="read_locally",
                notes=["desktop_read_locally"],
            )
        if action == "dismiss":
            return await self._desktop_finish_proactive_ack(
                item,
                action="dismiss",
                status="dismissed",
                answer_state="dismissed",
                ack_status="dismissed",
                notes=["desktop_dismissed"],
            )
        if action == "reply":
            return await self._desktop_finish_proactive_ack(
                item,
                action="reply",
                status="answered",
                answer_state="owner_replied",
                ack_status="replied",
                notes=["desktop_owner_replied_to_proactive"],
            )
        return await self._desktop_approve_proactive_qq(item)

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
        await self._desktop_publish_proactive_delivery_from_state(
            status_override="claimed",
            notes=["proactive_request_claimed_via_outbox"],
        )
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
        self._desktop_publish_proactive_delivery_from_state_threadsafe(
            status_override="claimed",
            notes=["proactive_request_claimed_via_outbox_fast"],
        )
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
            if result.get("ack_recorded"):
                await self._desktop_publish_proactive_delivery_from_state(
                    status_override=_safe_str(result.get("ack_status"), "sent"),
                    notes=[_safe_str(note) for note in result.get("notes", [])[:4]],
                    severity="error" if _safe_str(result.get("ack_status")) == "failed" else None,
                )
            if result.get("ack_recorded") and result.get("ack_status") == "sent":
                self._record_proactive_outbound_dialogue(payload)
            return result
        return await asyncio.to_thread(ack_qq_outbox_message, self.xinyu_dir, payload or {})

    async def review_inbox_command(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._closed:
            raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")
        if payload is not None and not isinstance(payload, dict):
            raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
        async with self._review_admin_lock:
            return await asyncio.to_thread(handle_review_inbox_command, self.xinyu_dir, payload or {})

    async def message_ack(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._closed:
            raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")
        if payload is not None and not isinstance(payload, dict):
            raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
        return await asyncio.to_thread(register_sent_reply_ack, self.xinyu_dir, payload or {})

    async def goldmark_mark_request(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._closed:
            raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")
        if payload is not None and not isinstance(payload, dict):
            raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
        return await asyncio.to_thread(mark_goldmark_request_bridge, self.xinyu_dir, payload or {})

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
            if result.get("ack_recorded"):
                self._desktop_publish_proactive_delivery_from_state_threadsafe(
                    status_override=_safe_str(result.get("ack_status"), "sent"),
                    notes=[_safe_str(note) for note in result.get("notes", [])[:4]],
                    severity="error" if _safe_str(result.get("ack_status")) == "failed" else None,
                )
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

    async def _desktop_finish_proactive_ack(
        self,
        item: dict[str, Any],
        *,
        action: str,
        status: str,
        answer_state: str,
        ack_status: str,
        notes: list[str],
        adapter_message_id: str = "",
        adapter_error: str = "",
        extra: dict[str, Any] | None = None,
        claim_id: str = "",
    ) -> dict[str, Any]:
        candidate_id = _safe_str(item.get("candidateId"))
        updated = self._desktop_update_proactive_request_state(
            candidate_id=candidate_id,
            status=status,
            answer_state=answer_state,
            ack_status=ack_status,
            adapter_message_id=adapter_message_id,
            adapter_error=adapter_error,
            claim_id=claim_id,
        )
        event_item = {**item, **updated, **(extra or {})} if updated else {**item, **(extra or {})}
        event = await self._desktop_publish_proactive_delivery_item(
            event_item,
            status_override=status,
            notes=notes,
            severity="error" if status == "failed" else None,
        )
        return {
            "accepted": True,
            "ack_recorded": True,
            "candidateId": candidate_id,
            "action": action,
            "status": status,
            "eventId": _safe_str(event.get("id")),
            **(extra or {}),
            "notes": notes + (["proactive_request_state_updated"] if updated else ["proactive_request_state_not_updated"]),
        }

    async def _desktop_approve_proactive_qq(self, item: dict[str, Any]) -> dict[str, Any]:
        candidate_id = _safe_str(item.get("candidateId"))
        if not bool(item.get("claimable")):
            return {
                "accepted": False,
                "ack_recorded": False,
                "candidateId": candidate_id,
                "action": "approve_qq",
                "status": _safe_str(item.get("status")),
                "notes": ["desktop_proactive_candidate_not_qq_claimable"],
            }
        owner_user_id = self._owner_private_user_id()
        if not owner_user_id:
            return {
                "accepted": False,
                "ack_recorded": False,
                "candidateId": candidate_id,
                "action": "approve_qq",
                "notes": ["missing_owner_user_id"],
            }
        message = _safe_str(item.get("candidatePreview")).strip()
        if not message:
            return {
                "accepted": False,
                "ack_recorded": False,
                "candidateId": candidate_id,
                "action": "approve_qq",
                "notes": ["missing_candidate_message"],
            }
        queued = await asyncio.to_thread(
            enqueue_qq_outbox_message,
            self.xinyu_dir,
            user_id=owner_user_id,
            message=message,
            source="desktop_proactive_ack",
            dedupe_key=f"desktop-proactive:{candidate_id}",
            metadata={
                "source": "xinyu_desktop_shell",
                "desktop_candidate_id": candidate_id,
                "proactive_request_id": _safe_str(item.get("requestId")),
                "desktop_action": "approve_qq",
            },
        )
        if not queued.get("accepted"):
            return {
                "accepted": False,
                "ack_recorded": False,
                "candidateId": candidate_id,
                "action": "approve_qq",
                "notes": ["qq_outbox_enqueue_failed"] + [_safe_str(note) for note in queued.get("notes", [])],
            }
        outbox_message_id = _safe_str(queued.get("message_id"))
        claim_id = f"desktop-proactive-{int(time.time())}"
        write_proactive_qq_dispatch_state(
            self.xinyu_dir,
            claimed_at=datetime.now().astimezone().isoformat(),
            claim_id=claim_id,
            candidate=message,
            request_id=_safe_str(item.get("requestId"), "none") or "none",
            min_interval_seconds=self.proactive_min_interval_seconds,
        )
        return await self._desktop_finish_proactive_ack(
            item,
            action="approve_qq",
            status="queued_qq",
            answer_state="approved_qq",
            ack_status="queued",
            adapter_message_id=outbox_message_id,
            notes=["desktop_approved_qq"] + [_safe_str(note) for note in queued.get("notes", [])],
            extra={
                "outboxMessageId": outbox_message_id,
                "queued": bool(queued.get("queued")),
            },
            claim_id=claim_id,
        )

    def _desktop_update_proactive_request_state(
        self,
        *,
        candidate_id: str,
        status: str,
        answer_state: str = "",
        ack_status: str = "",
        adapter_message_id: str = "",
        adapter_error: str = "",
        claim_id: str = "",
    ) -> dict[str, Any]:
        path = self.xinyu_dir / "memory/context/proactive_request_state.md"
        state = _read_text_safe(path)
        if not state:
            return {}
        current = self._desktop_proactive_item_from_state(include_final=True)
        if _safe_str(current.get("candidateId")) != candidate_id:
            return {}
        updated_at = datetime.now().astimezone().isoformat()
        updated = self._desktop_replace_frontmatter_field(state, "updated_at", updated_at)
        updated = self._desktop_replace_list_field(updated, "status", status)
        if answer_state:
            updated = self._desktop_replace_list_field(updated, "request_answer_state", answer_state)
        if ack_status:
            updated = self._desktop_replace_list_field(updated, "last_ack_status", ack_status)
        if claim_id:
            updated = self._desktop_replace_list_field(updated, "last_claim_id", claim_id)
        if adapter_message_id:
            updated = self._desktop_replace_list_field(updated, "adapter_message_id", adapter_message_id)
        if adapter_error:
            updated = self._desktop_replace_list_field(updated, "adapter_error", adapter_error)
        atomic_write_text(path, updated.rstrip())
        return self._desktop_proactive_item_from_state(include_final=True)

    @staticmethod
    def _desktop_replace_frontmatter_field(text: str, field: str, value: str) -> str:
        replacement = f"{field}: {_safe_str(value).strip() or 'none'}"
        updated, count = re.subn(
            rf"(?m)^{re.escape(field)}:\s*.*$",
            replacement,
            text,
            count=1,
        )
        if count:
            return updated
        return text.rstrip() + "\n" + replacement + "\n"

    @staticmethod
    def _desktop_replace_list_field(text: str, field: str, value: str) -> str:
        replacement = f"- {field}: {_safe_str(value).strip() or 'none'}"
        updated, count = re.subn(
            rf"(?m)^-\s+{re.escape(field)}:\s*.*$",
            replacement,
            text,
            count=1,
        )
        if count:
            return updated
        return text.rstrip() + "\n" + replacement + "\n"

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
        atomic_write_text(path, text)

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

    async def _build_life_reply_policy(self, *, user_text: str) -> dict[str, Any]:
        try:
            await self._ensure_self_choice_ready()
            await self.self_choice_store.apply_time_decay()
            self_choice_public = await self.self_choice_store.snapshot_public(consume_cues=False)
            proactive_items = (await self.desktop_proactive_inbox({})).get("items", [])
            recent_turns = list(self._desktop_recent_turns[-30:])
            recent_memory_events = (await self.desktop_memory_recent({"limit": 30})).get("items", [])
            environment = sample_environment(self.xinyu_dir)
            entropy = build_entropy_state(
                environment=environment,
                proactive_items=proactive_items if isinstance(proactive_items, list) else [],
                recent_turns=recent_turns,
                recent_memory_events=recent_memory_events if isinstance(recent_memory_events, list) else [],
            )
            entropy_state = entropy.model_dump(mode="json") if hasattr(entropy, "model_dump") else {}
            policy = build_life_reply_policy(
                self_choice_public=self_choice_public,
                entropy_state=entropy_state,
                recent_action_context=read_recent_action_context(self.xinyu_dir),
                user_text=user_text,
            )
            policy.setdefault("notes", []).append("life_reply_policy_built")
            return policy
        except Exception as exc:
            return {
                "version": 1,
                "mode": "steady",
                "reply_pressure": "normal",
                "technical_turn": False,
                "max_sentences": 3,
                "suppress_optional_question": False,
                "reasons": [],
                "notes": [f"life_reply_policy_error:{type(exc).__name__}"],
            }

    def _owner_private_payload_matches(self, payload: dict[str, Any]) -> bool:
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        if not _as_bool(metadata.get("is_owner_user"), default=False):
            return False
        message_type = _safe_str(payload.get("message_type")).lower()
        return message_type.startswith("private") or not _safe_str(payload.get("group_id")).strip()

    def _trusted_private_payload_matches(self, payload: dict[str, Any]) -> bool:
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        if _as_bool(metadata.get("is_owner_user"), default=False):
            return False
        if not _as_bool(metadata.get("is_trusted_user"), default=False):
            return False
        message_type = _safe_str(payload.get("message_type")).lower()
        if message_type and not message_type.startswith("private"):
            return False
        group_id = _safe_str(payload.get("group_id")).strip()
        return group_id in {"", "0", "none", "None"}

    @staticmethod
    def _trusted_public_search_task_allowed(task_text: str) -> bool:
        compact = re.sub(r"\s+", "", _safe_str(task_text)).lower()
        if not compact:
            return False
        if TRUSTED_CODEX_LOCAL_PATH_RE.search(_safe_str(task_text)):
            return False
        if any(marker.lower() in compact for marker in TRUSTED_CODEX_LOCAL_BLOCK_MARKERS):
            return False
        if any(marker in compact for marker in TRUSTED_CODEX_LOCAL_ENGLISH_BLOCK_MARKERS):
            return False
        return any(marker.lower() in compact for marker in TRUSTED_CODEX_PUBLIC_SEARCH_MARKERS)

    def _proactive_thread_context(self, payload: dict[str, Any], current_text: str) -> str:
        if not self._owner_private_payload_matches(payload):
            return ""
        metadata = payload.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        desktop_candidate_id = _safe_str(metadata.get("desktop_proactive_candidate_id")).strip()
        if desktop_candidate_id:
            request = _read_text_safe(self.xinyu_dir / "memory/context/proactive_request_state.md")
            request_id = _state_field(request, "request_id", "")
            if request_id == desktop_candidate_id:
                candidate = _state_field(request, "concrete_question", "") or _safe_str(
                    metadata.get("desktop_proactive_preview")
                )
                return "\n".join(
                    [
                        "desktop proactive reply sidecar:",
                        f"- proactive_candidate_id: {desktop_candidate_id}",
                        f"- proactive_kind: {_state_field(request, 'kind', 'proactive')}",
                        f"- proactive_status: {_state_field(request, 'status', 'unknown')}",
                        f"- proactive_delivery_level: {_state_field(request, 'delivery_level', 'unknown')}",
                        f"- proactive_candidate_message: {candidate}",
                        f"- current_owner_reply_to_candidate: {_safe_str(current_text).strip()}",
                        (
                            "- continuity_rule: treat the current owner message as an explicit reply to this "
                            "desktop proactive candidate. Answer from that local thread instead of treating it "
                            "as unrelated chat."
                        ),
                    ]
                )
        dispatch = _read_text_safe(self.xinyu_dir / "memory/context/proactive_qq_dispatch_state.md")
        if _state_field(dispatch, "last_claim_status") not in {"claimed", "sent"}:
            return ""
        request = _read_text_safe(self.xinyu_dir / "memory/context/proactive_request_state.md")
        request_id = _state_field(request, "request_id")
        dispatch_request_id = _state_field(dispatch, "proactive_request_id")
        if request_id not in {"", "none", "unknown"} and dispatch_request_id not in {"", "none", "unknown"}:
            if request_id != dispatch_request_id:
                return ""
        if _state_field(request, "delivery_level") not in {"queue_owner_private", "claim_ack"}:
            return ""
        if _state_field(request, "status") not in {"claimed", "sent", "answered"}:
            return ""
        message = _state_field(dispatch, "last_claimed_message")
        if not message or message in {"none", "unknown"}:
            return ""
        age_seconds = _seconds_since_iso(_state_field(dispatch, "last_claimed_at"), default=999999.0)
        if age_seconds > 6 * 3600:
            return ""
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
        if _state_field(request, "status") not in {"claimed", "sent"}:
            return False
        if _state_field(request, "delivery_level") not in {"queue_owner_private", "claim_ack"}:
            return False
        if _state_field(request, "request_answer_state", "pending") not in {"pending", "", "unknown"}:
            return False
        dispatch = _read_text_safe(self.xinyu_dir / "memory/context/proactive_qq_dispatch_state.md")
        if _state_field(dispatch, "last_claim_status") != "sent":
            return False
        request_id = _state_field(request, "request_id")
        dispatch_request_id = _state_field(dispatch, "proactive_request_id")
        if request_id not in {"", "none", "unknown"} and dispatch_request_id not in {"", "none", "unknown"}:
            if request_id != dispatch_request_id:
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
            atomic_write_text(request_path, updated.rstrip() + extra, final_newline=False)
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
            return await self.learning_service.ingest(payload)
        except LearningBridgeError as exc:
            raise BridgeRequestError(exc.status, exc.message) from exc

    async def sticker_import(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._closed:
            raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")
        if payload is not None and not isinstance(payload, dict):
            raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
        async with self._global_turn_lock:
            return await asyncio.to_thread(import_sticker_from_payload, self.xinyu_dir, payload or {})

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
        return await self.learning_service.study(payload or {})

    async def learning_observe(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._closed:
            raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")
        if payload is not None and not isinstance(payload, dict):
            raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
        return await self.learning_service.observe(payload or {})

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
                "这句还不像一个明确的 Codex 任务，我先不启动。你把要查或要做的主题说完整一点。",
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
                "reply": self._codex_status_reply(
                    "started",
                    paths=paths,
                    auto_study=auto_study,
                    task_text=_safe_str(payload.get("raw_owner_task")).strip() or text,
                ),
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
        reply = self._codex_status_reply(
            status,
            paths=paths,
            auto_study=auto_study,
            exit_code=result.exit_code,
            task_text=_safe_str(payload.get("raw_owner_task")).strip() or text,
        )
        codex_report_material_id = ""
        codex_report_material_notes: list[str] = []
        if result.accepted and auto_study:
            async with self._global_turn_lock:
                report_material = await asyncio.to_thread(
                    stage_codex_report_material,
                    self.xinyu_dir,
                    report_path=result.report_path,
                    task_text=text,
                    job_id=presence_paths["job_id"],
                )
            codex_report_material_id = _safe_str(report_material.get("material_id")).strip()
            codex_report_material_notes = [
                _safe_str(note)
                for note in report_material.get("notes", [])
                if _safe_str(note)
            ][:3]
            asyncio.create_task(self._codex_learning_followup("codex_delegate_async"))

        notes = list(result.notes)
        if codex_report_material_id:
            notes.append(f"codex_report_material:{codex_report_material_id}")
        notes.extend(codex_report_material_notes)
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
            "memory_changed": before_memory != after_memory or bool(codex_report_material_id),
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

    def _prepare_self_code_watchdog_payload(self, payload: dict[str, Any], *, approval_id: str) -> dict[str, Any]:
        snapshot = create_self_code_snapshot(
            self.xinyu_dir,
            approval_id=approval_id,
            reason="owner_self_code_iteration_before_codex_patch",
        )
        manifest_path = _safe_str(snapshot.get("manifest_path")).strip()
        snapshot_id = _safe_str(snapshot.get("snapshot_id")).strip()
        if not manifest_path or not snapshot_id:
            raise RuntimeError("self-code watchdog snapshot did not return a manifest path")

        restart_command = (
            "powershell -NoProfile -ExecutionPolicy Bypass -File .\\start_xinyu_core_bridge.ps1 "
            f"-ForceRestart -SelfCodeSnapshotPath \"{manifest_path}\" -HealthTimeoutSeconds 60"
        )
        watchdog_block = _normalize_reply(
            "\n".join(
                [
                    "",
                    "Self-code watchdog:",
                    f"- snapshot_id: {snapshot_id}",
                    f"- snapshot_manifest: {manifest_path}",
                    "- before changing files, keep this snapshot unchanged.",
                    "- after implementing and testing the self-code patch, reload Core through the PowerShell health gate.",
                    f"- reload_command: {restart_command}",
                    "- the PowerShell gate waits up to 30 seconds for /health; on failure it restores the snapshot and restarts Core.",
                    "- do not bypass this reload command for a runtime code patch.",
                ]
            )
        )
        payload["text"] = _safe_str(payload.get("text")).rstrip() + "\n\n" + watchdog_block
        payload["raw_owner_task"] = _safe_str(payload.get("raw_owner_task")).rstrip() + "\n\n" + watchdog_block
        metadata = payload.get("metadata")
        if isinstance(metadata, dict):
            metadata["self_code_watchdog_snapshot_id"] = snapshot_id
            metadata["self_code_watchdog_manifest_path"] = manifest_path
            metadata["self_code_watchdog_restart_required"] = True
        return snapshot

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

    def _can_model_delegate_codex(self, payload: dict[str, Any], *, task_text: str = "") -> bool:
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        message_type = _safe_str(payload.get("message_type")).lower()
        if message_type and not (message_type.startswith("private") or message_type.startswith("desktop_private")):
            return False
        group_id = _safe_str(payload.get("group_id")).strip()
        if group_id not in {"", "0", "none", "None"}:
            return False
        if _as_bool(metadata.get("is_owner_user"), default=False):
            return True
        if not _as_bool(metadata.get("is_trusted_user"), default=False):
            return False
        return self._trusted_public_search_task_allowed(task_text)

    def _build_model_codex_payload(
        self,
        payload: dict[str, Any],
        *,
        session_key: str,
        task_text: str,
    ) -> dict[str, Any]:
        source_metadata = payload.get("metadata")
        if not isinstance(source_metadata, dict):
            source_metadata = {}
        is_owner = _as_bool(source_metadata.get("is_owner_user"), default=False)
        is_trusted = _as_bool(source_metadata.get("is_trusted_user"), default=False)
        trusted_public_search = is_trusted and not is_owner and self._trusted_public_search_task_allowed(task_text)
        owner_local_write_approved = is_owner and _as_bool(
            source_metadata.get("owner_local_write_approved"),
            default=False,
        )
        metadata = {
            "gateway": _safe_str(payload.get("adapter"), "xinyu_core_bridge"),
            "source": "qq_gateway_codex_execute_message",
            "is_owner_user": is_owner,
            "is_trusted_user": is_trusted,
            "trusted_public_search_task": trusted_public_search,
            "owner_local_write_approved": owner_local_write_approved,
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
            "text": (
                "Use Codex auxiliary brain for this trusted public-source search task:\n"
                if trusted_public_search
                else "Use Codex auxiliary brain for this owner-approved task:\n"
            )
            + task_text,
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
        task_text: str = "",
    ) -> str:
        return codex_status_reply(
            status,
            paths=paths,
            auto_study=auto_study,
            exit_code=exit_code,
            task_text=task_text,
        )

    @staticmethod
    def _codex_reply_variant(seed: str, options: tuple[str, ...]) -> str:
        return codex_reply_variant(seed, options)

    @staticmethod
    def _codex_owner_task_text(text: str) -> str:
        return codex_owner_task_text(text)

    @staticmethod
    def _codex_task_subject(task_text: str) -> str:
        return codex_task_subject(task_text)

    @staticmethod
    def _codex_started_reply(task_subject: str, variant: int) -> str:
        return codex_started_reply(task_subject, variant)

    def _codex_completion_summary(self, result: Any, *, limit: int = 220) -> str:
        return codex_completion_summary(self.xinyu_dir, result, limit=limit)

    def _codex_completion_outbox_message(
        self,
        result: Any,
        *,
        text: str,
        auto_study: bool,
        handoff_notes: list[str],
    ) -> str:
        return codex_completion_outbox_message(
            self.xinyu_dir,
            result,
            text=text,
            auto_study=auto_study,
            handoff_notes=handoff_notes,
        )

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
        enqueue_codex_completion_if_needed(
            self.xinyu_dir,
            payload,
            result=result,
            text=text,
            auto_study=auto_study,
            handoff_notes=handoff_notes,
            error=error,
        )

    def _codex_generated_image_artifacts(self, result: Any | None, *, task_text: str, limit: int = 3) -> list[Path]:
        return codex_generated_image_artifacts(self.xinyu_dir, result, task_text=task_text, limit=limit)

    @staticmethod
    def _looks_like_codex_image_generation_task(text: str) -> bool:
        return looks_like_codex_image_generation_task(text)

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
            action_experience_notes: list[str] = []
            action_request = metadata.get("action_layer_request")
            if isinstance(action_request, dict):
                codex_outcome = ActionOutcome(
                    ok=bool(result.accepted and not result.timed_out),
                    tool="codex_delegate",
                    summary=[self._codex_completion_summary(result)],
                    report_path=result.report_path,
                    duration_ms=0,
                    risk=DELEGATED_LOCAL_RISK,
                    result="success" if result.accepted and not result.timed_out else "failure",
                    load={
                        "codex_exit_code": result.exit_code,
                        "timeout": result.timed_out,
                        "scheduled": True,
                    },
                    error_code="" if result.accepted and not result.timed_out else "codex_delegate_incomplete",
                    notes=["codex_delegate_background_completion"],
                ).to_dict()
                _, _, action_experience_notes = await self._settle_action_experience(
                    payload,
                    request=action_request,
                    outcome=codex_outcome,
                )
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
            report_material_id = ""
            report_material_notes: list[str] = []
            if result.accepted and auto_study:
                async with self._global_turn_lock:
                    report_material = await asyncio.to_thread(
                        stage_codex_report_material,
                        self.xinyu_dir,
                        report_path=result.report_path,
                        task_text=text,
                        job_id=presence_paths["job_id"],
                    )
                report_material_id = _safe_str(report_material.get("material_id")).strip()
                report_material_notes = [
                    _safe_str(note)
                    for note in report_material.get("notes", [])
                    if _safe_str(note)
                ][:3]
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
                f"report_material={report_material_id or 'none'} "
                f"report_material_notes={';'.join(report_material_notes) or 'none'} "
                f"action_experience={';'.join(action_experience_notes) or 'none'} "
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

    async def _settle_action_experience(
        self,
        payload: dict[str, Any],
        *,
        request: dict[str, Any],
        outcome: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
        return await xinyu_bridge_action_routes.settle_action_experience(
            self,
            payload,
            request=request,
            outcome=outcome,
        )

    async def _maybe_handle_action_layer_turn(
        self,
        payload: dict[str, Any],
        *,
        text: str,
        session_key: str,
        turn_id: str,
        turn_started_wall: str,
        turn_started_at: float,
        before_memory: dict[str, Any],
        cleanup: dict[str, Any],
        event_sidecar: dict[str, Any],
    ) -> dict[str, Any] | None:
        return await xinyu_bridge_action_routes.handle_action_layer_turn(
            self,
            payload,
            text=text,
            session_key=session_key,
            turn_id=turn_id,
            turn_started_wall=turn_started_wall,
            turn_started_at=turn_started_at,
            before_memory=before_memory,
            cleanup=cleanup,
            event_sidecar=event_sidecar,
            bridge_request_error_type=BridgeRequestError,
        )

    async def _maybe_handle_recent_action_followup_turn(
        self,
        payload: dict[str, Any],
        *,
        text: str,
        session_key: str,
        turn_id: str,
        turn_started_wall: str,
        turn_started_at: float,
        before_memory: dict[str, Any],
        cleanup: dict[str, Any],
        event_sidecar: dict[str, Any],
    ) -> dict[str, Any] | None:
        return await xinyu_bridge_action_routes.handle_recent_action_followup_turn(
            self,
            payload,
            text=text,
            session_key=session_key,
            turn_id=turn_id,
            turn_started_wall=turn_started_wall,
            turn_started_at=turn_started_at,
            before_memory=before_memory,
            cleanup=cleanup,
            event_sidecar=event_sidecar,
        )

    async def _maybe_handle_action_digest_followup_turn(
        self,
        payload: dict[str, Any],
        *,
        text: str,
        session_key: str,
        turn_id: str,
        turn_started_wall: str,
        turn_started_at: float,
        before_memory: dict[str, Any],
        cleanup: dict[str, Any],
        event_sidecar: dict[str, Any],
    ) -> dict[str, Any] | None:
        return await xinyu_bridge_action_routes.handle_action_digest_followup_turn(
            self,
            payload,
            text=text,
            session_key=session_key,
            turn_id=turn_id,
            turn_started_wall=turn_started_wall,
            turn_started_at=turn_started_at,
            before_memory=before_memory,
            cleanup=cleanup,
            event_sidecar=event_sidecar,
        )

    async def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._closed:
            raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")
        try:
            chat_request = self.chat_service.prepare_request(
                payload,
                max_text_chars=self.max_text_chars,
                payload_text=self._payload_text,
                session_key=self._session_key,
            )
        except ChatServiceError as exc:
            raise BridgeRequestError(exc.status, exc.message) from exc
        if chat_request.empty_response is not None:
            return chat_request.empty_response

        text = chat_request.text
        session_key = chat_request.session_key
        turn_clock = self.chat_service.start_turn_clock()
        turn_started_at = turn_clock.started_at
        turn_started_wall = turn_clock.started_wall
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
            await self._desktop_publish_chat_started(
                payload,
                text=text,
                session_key=session_key,
                turn_id=_safe_str(presence_start.get("turn_id")),
                started_at=turn_started_wall,
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
            pre_model_routes = await run_pre_model_routes(
                self,
                payload,
                text=text,
                session_key=session_key,
                turn_id=_safe_str(presence_start.get("turn_id")),
                turn_started_wall=turn_started_wall,
                turn_started_at=turn_started_at,
                before_memory=before_memory,
                cleanup=cleanup,
            )
            event_sidecar = pre_model_routes.event_sidecar
            v1_shadow = pre_model_routes.v1_shadow
            if pre_model_routes.response is not None:
                return pre_model_routes.response
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
            recalled_context_event: dict[str, Any] = {}
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
                recalled_context_event = await self._desktop_publish_memory_recall(
                    payload,
                    recalled_context,
                    session_key=session_key,
                    turn_id=_safe_str(presence_start.get("turn_id")),
                )
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
            life_reply_policy = await self._build_life_reply_policy(user_text=text)
            try:
                self._inject_live_turn_context(
                    session.agent,
                    payload=payload,
                    text=text,
                    dialogue_tail=session.dialogue_tail,
                    turn_id=_safe_str(presence_start.get("turn_id")),
                    persona_context=_safe_str(persona_sidecar.get("prompt_block")),
                    curiosity_context=_safe_str(curiosity_eval.get("prompt_block")),
                    visible_turn=visible_turn,
                    recalled_context=_safe_str(getattr(recalled_context, "prompt_block", "")),
                    runtime_presence_context=runtime_presence_context,
                    continuity_context=build_continuity_handoff_prompt_block(self.xinyu_dir, user_text=text),
                    uncertainty_pause_context=build_uncertainty_pause_prompt_block(self.xinyu_dir),
                    life_reply_context=build_life_reply_prompt_block(life_reply_policy),
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
                elapsed_ms = int((time.perf_counter() - turn_started_at) * 1000)
                timeout_notes = ["turn_timeout"]
                record_turn_finished(
                    self.xinyu_dir,
                    turn_id=_safe_str(presence_start.get("turn_id")),
                    reply="",
                    elapsed_ms=elapsed_ms,
                    status="timeout",
                    notes=timeout_notes,
                )
                await self._desktop_publish_chat_finished(
                    payload,
                    text=text,
                    reply="",
                    session_key=session_key,
                    turn_id=_safe_str(presence_start.get("turn_id")),
                    started_at=turn_started_wall,
                    elapsed_ms=elapsed_ms,
                    status="timeout",
                    notes=timeout_notes,
                    memory_changed=False,
                    recall_event_id=_safe_str(recalled_context_event.get("id")),
                    recall_count=self._desktop_recall_count(recalled_context),
                    top_recall_sources=self._desktop_top_recall_sources(recalled_context),
                )
                raise BridgeRequestError(
                    HTTPStatus.GATEWAY_TIMEOUT,
                    f"XinYu turn timed out after {self.turn_timeout_seconds} seconds",
                ) from exc
            except Exception as exc:
                elapsed_ms = int((time.perf_counter() - turn_started_at) * 1000)
                error_notes = [f"turn_error:{type(exc).__name__}"]
                record_turn_finished(
                    self.xinyu_dir,
                    turn_id=_safe_str(presence_start.get("turn_id")),
                    reply="",
                    elapsed_ms=elapsed_ms,
                    status="error",
                    notes=error_notes,
                )
                await self._desktop_publish_chat_finished(
                    payload,
                    text=text,
                    reply="",
                    session_key=session_key,
                    turn_id=_safe_str(presence_start.get("turn_id")),
                    started_at=turn_started_wall,
                    elapsed_ms=elapsed_ms,
                    status="error",
                    notes=error_notes,
                    memory_changed=False,
                    recall_event_id=_safe_str(recalled_context_event.get("id")),
                    recall_count=self._desktop_recall_count(recalled_context),
                    top_recall_sources=self._desktop_top_recall_sources(recalled_context),
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
            reply_bubble_force_units: list[str] = []
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
                        watchdog_snapshot = self._prepare_self_code_watchdog_payload(
                            codex_payload,
                            approval_id=approval_id,
                        )
                        codex_response = await self.codex_execute(codex_payload)
                        mark_self_code_execution_scheduled(
                            self.xinyu_dir,
                            approval_id=approval_id,
                            job_id=_safe_str(codex_response.get("request_path") or codex_response.get("report_path") or ""),
                            watchdog_snapshot_id=_safe_str(watchdog_snapshot.get("snapshot_id"), "none"),
                            watchdog_manifest_path=_safe_str(watchdog_snapshot.get("manifest_path"), "none"),
                        )
                        reply = _normalize_reply(_safe_str(codex_response.get("reply")))
                        if not reply:
                            reply = "开了，我让 Codex 在专门窗口里做一个小范围代码改动。"
                        reply = "交给 Codex 跑了，结果回来我直接讲改动。"
                        model_codex_delegate_note = "owner_self_code_iteration:scheduled"
                    except BridgeRequestError as exc:
                        reply = exc.message
                        model_codex_delegate_note = f"owner_self_code_iteration_error:{exc.status.value}"
                    except Exception as exc:
                        reply = f"Self-code watchdog failed before Codex started: {type(exc).__name__}: {exc}"
                        model_codex_delegate_note = f"owner_self_code_iteration_watchdog_error:{type(exc).__name__}"
                self._replace_last_assistant_message(session.agent, reply)
            elif model_codex_task:
                if self._can_model_delegate_codex(payload, task_text=model_codex_task):
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
                        reply = "我去查，回来只讲结论。"
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
                        reply = "交给 Codex 跑了，结果回来我直接讲重点。"
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
                    if guarded_reply:
                        final_guard_flags = _dedupe(
                            final_guard_flags + ["final_guard_repair_fallback_naturalized"] + repaired_flags
                        )
                    else:
                        guarded_reply = ""
                        final_guard_flags = _dedupe(
                            final_guard_flags + ["final_guard_blocked_unsendable_reply"] + repaired_flags
                        )
                    self._replace_last_assistant_message(session.agent, guarded_reply)
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
            visible_dedupe = dedupe_visible_reply(reply)
            if visible_dedupe.changed:
                reply = visible_dedupe.text
                self._replace_last_assistant_message(session.agent, reply)
            life_reply_adjustment: dict[str, Any] = {"notes": []}
            if not self_code_task and not model_codex_task and not direct_codex_task and not wait_to_think_task:
                life_reply_adjustment = apply_life_reply_policy(reply, policy=life_reply_policy, user_text=text)
                if life_reply_adjustment.get("changed"):
                    reply = _safe_str(life_reply_adjustment.get("reply")).strip()
                    self._replace_last_assistant_message(session.agent, reply)
            reply_bubble_force_units = self._owner_requested_reply_bubble_units(
                user_text=text,
                reply=reply,
                dialogue_tail=session.dialogue_tail,
            )
            if reply_bubble_force_units:
                reply = " ".join(reply_bubble_force_units)
                final_guard_flags = _dedupe(final_guard_flags + ["owner_explicit_reply_bubble_units"])
                self._replace_last_assistant_message(session.agent, reply)
            elif self._looks_like_false_single_bubble_limitation(text, reply):
                reply = "可以拆。你要我拆哪段，我按一条一条发。"
                final_guard_flags = _dedupe(final_guard_flags + ["false_single_message_limit_naturalized"])
                self._replace_last_assistant_message(session.agent, reply)
            current_sticker_reply = self._current_sticker_question_reply(text, payload)
            recent_sticker_reply = "" if current_sticker_reply else self._recent_sticker_question_reply(text, session.dialogue_tail)
            if current_sticker_reply or recent_sticker_reply:
                reply = current_sticker_reply or recent_sticker_reply
                self._replace_last_assistant_message(session.agent, reply)
            empty_visible_reply_no_fallback = bool(not reply and self._owner_private_payload_matches(payload))
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
            voice_trial_overlay: dict[str, Any] = {"notes": []}
            if is_owner:
                try:
                    voice_trial_overlay = record_voice_trial_overlay(
                        self.xinyu_dir,
                        payload,
                        user_text=text,
                        reply=reply,
                        source="qq_gateway",
                    )
                except Exception as exc:
                    print(f"[xinyu_core_bridge] voice trial overlay failed: {exc}", flush=True)
                    voice_trial_overlay = {"notes": [f"voice_trial_overlay_error:{type(exc).__name__}"]}
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
            self._append_dialogue_tail(session, user_text=text, reply=reply, payload=payload)
            proactive_owner_reply_marked = self._mark_proactive_owner_reply(payload, text=text, reply=reply)
            if proactive_owner_reply_marked:
                await self._desktop_publish_proactive_delivery_from_state(
                    status_override="answered",
                    notes=["owner_replied_to_proactive"],
                )
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
            sticker_reply: dict[str, Any] = {"notes": []}
            try:
                sticker_reply = await asyncio.to_thread(
                    maybe_enqueue_sticker_reply,
                    self.xinyu_dir,
                    payload,
                    user_text=text,
                    reply=reply,
                    session_key=session_key,
                    turn_id=_safe_str(presence_start.get("turn_id")),
                )
            except Exception as exc:
                print(f"[xinyu_core_bridge] sticker reply enqueue failed: {exc}", flush=True)
                sticker_reply = {"notes": [f"sticker_reply_error:{type(exc).__name__}"]}
            sticker_tail_recorded = self._append_sticker_delivery_tail(session, sticker_reply)
            after_memory = _memory_snapshot(self.memory_root)
            notes: list[str] = []
            if not reply:
                notes.append("empty_reply")
            if empty_visible_reply_no_fallback:
                notes.append("empty_visible_reply_no_fallback")
            if rendered:
                notes.append(f"outward_renderer_applied:{renderer_reason or 'unknown'}")
            elif self.outward_renderer:
                notes.append(f"outward_renderer_skipped:{self.renderer_mode}")
            if final_guard_flags:
                notes.append("final_reply_guard_flags:" + ",".join(final_guard_flags[:3]))
            if final_guard_applied:
                notes.append("final_reply_guard_applied")
            notes.extend(visible_dedupe.notes)
            if residue_written:
                notes.append("persona_surface_residue_updated")
            if voice_calibrated:
                notes.append("voice_calibration_recorded")
            if voice_trial_overlay.get("recorded") or any(
                "error" in _safe_str(note) for note in voice_trial_overlay.get("notes", [])
            ):
                notes.extend(_safe_str(note) for note in voice_trial_overlay.get("notes", [])[:2])
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
            notes.extend(_safe_str(note) for note in life_reply_policy.get("notes", [])[:3])
            notes.extend(_safe_str(note) for note in life_reply_adjustment.get("notes", [])[:3])
            if current_sticker_reply:
                notes.append("current_sticker_question_answered")
            if recent_sticker_reply:
                notes.append("recent_sticker_question_answered")
            if reply_bubble_force_units:
                notes.append(f"reply_bubble_force_units:{len(reply_bubble_force_units)}")
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
            if sticker_tail_recorded:
                notes.append("sticker_delivery_tail_recorded")
            sticker_notes = [
                _safe_str(note)
                for note in sticker_reply.get("notes", [])
                if _safe_str(note) and not _safe_str(note).startswith("sticker_skip:not_requested")
            ]
            notes.extend(sticker_notes[:3])
            if cleanup["cleaned_sessions"]:
                notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")
            if session.dialogue_tail:
                notes.append("dialogue_working_memory_active")
            post_cleanup = await self._cleanup_idle_sessions(preserve_keys={session_key})
            if post_cleanup["cleaned_sessions"]:
                notes.append(f"cleaned_extra_sessions:{post_cleanup['cleaned_sessions']}")
            memory_changed = before_memory != after_memory
            elapsed_ms = int((time.perf_counter() - turn_started_at) * 1000)
            record_turn_finished(
                self.xinyu_dir,
                turn_id=_safe_str(presence_start.get("turn_id")),
                reply=reply,
                elapsed_ms=elapsed_ms,
                status="ok",
                notes=notes,
                memory_changed=memory_changed,
            )
            archive_message_ids = list(archive_result.get("message_ids", []))
            assistant_message_id = _safe_str(archive_message_ids[-1] if archive_message_ids else "")
            reply_hash = visible_text_hash(reply)
            await self._desktop_publish_chat_finished(
                payload,
                text=text,
                reply=reply,
                session_key=session_key,
                turn_id=_safe_str(presence_start.get("turn_id")),
                started_at=turn_started_wall,
                elapsed_ms=elapsed_ms,
                status="ok",
                notes=notes,
                memory_changed=memory_changed,
                archive_message_ids=archive_message_ids,
                reply_hash=reply_hash,
                recall_event_id=_safe_str(recalled_context_event.get("id")),
                recall_count=self._desktop_recall_count(recalled_context),
                top_recall_sources=self._desktop_top_recall_sources(recalled_context),
            )

            return {
                "accepted": True,
                "reply": reply,
                "memory_changed": memory_changed,
                "turn_id": _safe_str(presence_start.get("turn_id")),
                "command_id": _safe_str((payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}).get("desktop_command_id") or payload.get("command_id")),
                "session_id": session_key,
                "reply_hash": reply_hash,
                "archive_message_ids": archive_message_ids,
                "archive_assistant_message_id": assistant_message_id,
                "reply_bubble_force_units": reply_bubble_force_units,
                "notes": notes,
            }

    async def shutdown(self) -> None:
        self._closed = True
        metabolism_task = self._metabolism_task
        self._metabolism_task = None
        if self._metabolism_wakeup_event is not None:
            self._metabolism_wakeup_event.set()
        if metabolism_task is not None and not metabolism_task.done():
            metabolism_task.cancel()
            try:
                await metabolism_task
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                print(f"[xinyu_core_bridge] metabolism task shutdown warning: {exc}", flush=True)

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

        try:
            await self.self_choice_store.shutdown()
        except Exception as exc:
            print(f"[xinyu_core_bridge] self choice shutdown warning: {exc}", flush=True)

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
        return prompt_context_signature(self.xinyu_dir, PROMPT_CONTEXT_SIGNATURE_FILES)

    async def _cleanup_idle_sessions(self, *, preserve_keys: set[str] | None = None) -> dict[str, int]:
        preserve_keys = set(preserve_keys or set())
        if self.autonomous_maintenance_enabled and self.autonomous_maintenance_session_key:
            preserve_keys.add(self.autonomous_maintenance_session_key)
        if self.session_idle_ttl_seconds <= 0 and self.max_sessions <= 0:
            return {"cleaned_sessions": 0, "remaining_sessions": len(self._sessions)}

        to_stop: list[AgentSession] = []
        async with self._sessions_lock:
            expire_keys = session_keys_to_expire(
                self._sessions,
                now=time.time(),
                idle_ttl_seconds=self.session_idle_ttl_seconds,
                max_sessions=self.max_sessions,
                preserve_keys=preserve_keys,
            )
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
        return session_key_from_payload(payload)

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
        turn_id: str = "",
        dialogue_tail: list[dict[str, str]] | None = None,
        persona_context: str = "",
        curiosity_context: str = "",
        visible_turn: Any | None = None,
        recalled_context: str = "",
        runtime_presence_context: str = "",
        continuity_context: str = "",
        uncertainty_pause_context: str = "",
        life_reply_context: str = "",
    ) -> None:
        controller = getattr(agent, "controller", None)
        pending = getattr(controller, "_pending_injections", None)
        if not isinstance(pending, list):
            return

        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        is_owner = _as_bool(metadata.get("is_owner_user"), default=False)
        is_trusted = _as_bool(metadata.get("is_trusted_user"), default=False)
        message_type = _safe_str(payload.get("message_type"))
        sender_name = _safe_str(payload.get("sender_name")) or _safe_str(payload.get("user_id"))
        source_line = "QQ group chat" if message_type.startswith("group_") else "QQ private chat"
        relationship_line = (
            "owner"
            if is_owner
            else ("trusted contact" if is_trusted else "external contact")
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
        life_reply_block = _safe_str(life_reply_context).strip()
        if life_reply_block:
            sidecar_lines.extend([life_reply_block])
        recent_action_block = read_recent_action_context(self.xinyu_dir)
        if recent_action_block:
            sidecar_lines.extend([recent_action_block])
        action_digest_block = read_recent_action_digest_context(self.xinyu_dir)
        if action_digest_block:
            sidecar_lines.extend([action_digest_block])
        recalled_block = _safe_str(recalled_context).strip()
        if recalled_block:
            sidecar_lines.extend(["recalled context sidecar:", recalled_block])
        voice_trial_block = build_voice_trial_overlay_prompt_block(self.xinyu_dir, payload, user_text=text)
        if voice_trial_block:
            sidecar_lines.extend([voice_trial_block])
        dialogue_rule_trial_block = build_dialogue_rule_trial_overlay_prompt_block(self.xinyu_dir, payload, user_text=text)
        if dialogue_rule_trial_block:
            sidecar_lines.extend([dialogue_rule_trial_block])
        learning_loop_block = build_learning_closed_loop_prompt_block(self.xinyu_dir, user_text=text)
        if learning_loop_block:
            sidecar_lines.extend([learning_loop_block])
        proactive_block = self._proactive_thread_context(payload, text)
        if proactive_block:
            sidecar_lines.extend([proactive_block])
        daily_digest_block = build_daily_digest_prompt_block(self.xinyu_dir)
        if daily_digest_block:
            sidecar_lines.extend([daily_digest_block])
        goldmark_block = build_goldmark_auth_prompt_block(self.xinyu_dir)
        if goldmark_block:
            sidecar_lines.extend([goldmark_block])
        qq_rich_block = self._qq_rich_message_sidecar(payload)
        if qq_rich_block:
            sidecar_lines.extend(["qq rich message sidecar:", qq_rich_block])
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
        if _as_bool(metadata.get("qq_coalesced_owner_messages"), default=False):
            sidecar_lines.extend(
                [
                    "qq fragment coalescing sidecar:",
                    (
                        "The owner sent consecutive QQ fragments that the gateway merged into one turn. "
                        f"fragment_count: {_safe_str(metadata.get('qq_coalesced_message_count'), '2')}. "
                        "Treat the combined user text as one message and answer only once to the overall meaning; "
                        "do not answer each line separately."
                    ),
                ]
            )

        codex_delegate_contract = ""
        if self._owner_private_payload_matches(payload):
            codex_delegate_contract = (
                "codex_delegation_contract: in owner-private chat, use semantic intent before delegation. Only a "
                "current, concrete owner request to hand work to Codex, inspect code, search/verify, or perform a "
                "bounded local task may use the hidden "
                f"marker {CODEX_DELEGATE_OPEN}<concrete task>{CODEX_DELEGATE_CLOSE}. If the owner is discussing "
                "Codex, correcting a previous launch, negating permission, reporting that Codex failed, or saying "
                "what they might do later, answer normally and do not emit the marker. If uncertain, ask one concise "
                "clarifying question instead of launching. If you use the marker, output only that marker and no "
                "visible prose; the bridge will intercept it and open XinYu's dedicated Codex window. If the owner "
                "explicitly grants XinYu permission to change her own code or says to start after such a grant, do "
                "not turn it into 我可以试试 / 要现在开始吗; hand it to the bridge as an actionable bounded self-code "
                "iteration. A direct owner-private request to modify XinYu code is already a one-time approval; do "
                "not require a prior application first. Do not tell the owner manual /codex is required unless a "
                "real bridge rejection just happened."
            )
        elif self._trusted_private_payload_matches(payload):
            codex_delegate_contract = (
                "trusted_contact_search_contract: this private QQ sender is trusted for ordinary chat, rich QQ "
                "context, and public-source search only. For a current concrete request to search, verify, or compare "
                "public web/source material, you may use the hidden "
                f"marker {CODEX_DELEGATE_OPEN}<public search task>{CODEX_DELEGATE_CLOSE}. Do not use Codex for local "
                "files, code edits, package installs, account/admin actions, private data, tokens, logs, or XinYu "
                "self-code. If the request is not a public information search, answer normally or ask one short "
                "clarifying question. If you use the marker, output only that marker and no visible prose."
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
            "When the owner asks what just happened, what you just saw, or the main issue after a local action, answer from recent action sidecar before older recalled context.",
            "If this is technical work, do the technical work directly.",
        ]

        live_system_prompt = "\n".join(live_context_lines)
        pending.append(
            {
                "role": "system",
                "content": live_system_prompt,
            }
        )
        self._maybe_dump_live_system_prompt(
            agent,
            payload=payload,
            session_key=self._session_key(payload),
            turn_id=turn_id,
            live_system_prompt=live_system_prompt,
        )

    def _maybe_dump_live_system_prompt(
        self,
        agent: Any,
        *,
        payload: dict[str, Any],
        session_key: str,
        turn_id: str,
        live_system_prompt: str,
    ) -> None:
        if os.environ.get(DEBUG_PROMPT_DUMP_ENV) != "1":
            return
        if not self._owner_private_payload_matches(payload):
            return

        base_system_prompt = ""
        getter = getattr(agent, "get_system_prompt", None)
        if callable(getter):
            try:
                base_system_prompt = _safe_str(getter())
            except Exception as exc:
                base_system_prompt = f"[debug_error:get_system_prompt:{type(exc).__name__}]"

        full_prompt = "\n\n".join(part for part in (base_system_prompt, live_system_prompt) if part)
        generated_at = datetime.now().astimezone().isoformat()
        prompt_hash = hashlib.sha256(full_prompt.encode("utf-8", errors="replace")).hexdigest()
        live_hash = hashlib.sha256(live_system_prompt.encode("utf-8", errors="replace")).hexdigest()
        content = "\n".join(
            [
                "# XinYu Debug Live System Prompt Dump",
                f"generated_at: {generated_at}",
                f"session_id: {session_key}",
                f"turn_id: {_safe_str(turn_id).strip() or 'unknown'}",
                f"full_prompt_sha256: sha256:{prompt_hash}",
                f"live_injection_sha256: sha256:{live_hash}",
                f"env_gate: {DEBUG_PROMPT_DUMP_ENV}=1",
                "scope: owner_private_live_turn_only",
                "storage_policy: overwrite_last_dump_only",
                "",
                "## Base System Prompt",
                base_system_prompt,
                "",
                "## Live System Injection",
                live_system_prompt,
                "",
            ]
        )

        path = self.xinyu_dir / DEBUG_LIVE_SYSTEM_PROMPT_REL
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path.write_text(content, encoding="utf-8")
            tmp_path.replace(path)
        except OSError as exc:
            print(f"[xinyu_core_bridge] debug prompt dump failed: {type(exc).__name__}: {exc}", flush=True)

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

    def _qq_rich_message_sidecar(self, payload: dict[str, Any]) -> str:
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            return ""
        lines: list[str] = []
        if _as_bool(metadata.get("qq_rich_message"), default=False):
            lines.extend(
                [
                    (
                        "The current QQ message contains non-text rich segments. Interpret them as conversation "
                        "context; do not expose raw segment syntax unless the owner asks for debugging."
                    ),
                    f"summary: {_safe_str(metadata.get('qq_rich_summary'))[:600] or 'none'}",
                    f"sticker_count: {_safe_str(metadata.get('qq_sticker_count'), '0')}",
                    f"image_count: {_safe_str(metadata.get('qq_image_count'), '0')}",
                    f"forward_count: {_safe_str(metadata.get('qq_forward_count'), '0')}",
                ]
            )
            segments = metadata.get("qq_message_segments")
            low_information_sticker = False
            if isinstance(segments, list):
                for index, item in enumerate(segments[:6], start=1):
                    if not isinstance(item, dict):
                        continue
                    kind = _safe_str(item.get("kind"), "segment")
                    label = _safe_str(item.get("summary") or item.get("name") or item.get("id"))[:180]
                    mood = _safe_str(item.get("mood")).strip()
                    meaning = _safe_str(item.get("meaning")).strip()
                    confidence = _safe_str(item.get("confidence")).strip().lower()
                    if kind == "sticker" and confidence == "low":
                        low_information_sticker = True
                    suffix = f" mood={mood}" if mood else ""
                    if meaning:
                        suffix += f" meaning={meaning[:160]}"
                    lines.append(f"- segment {index}: {kind} {label}{suffix}".rstrip())
            sticker_count = _as_int(metadata.get("qq_sticker_count"), 0)
            if sticker_count > 0 and low_information_sticker and not _as_bool(
                metadata.get("qq_image_context_available"), default=False
            ):
                lines.extend(
                    [
                        (
                            "Sticker content note: QQ only supplied a generic sticker label and no visual "
                            "image context for this turn."
                        ),
                        (
                            "Do not claim you saw an empty/blank frame or the actual sticker content. "
                            "If needed, say the visual content is unavailable from QQ metadata and answer "
                            "from the surrounding conversation."
                        ),
                    ]
                )
            if _as_bool(metadata.get("sticker_import_queued"), default=False):
                lines.append("Sticker library import is queued in the background; do not wait for it before replying.")
            if _as_bool(metadata.get("sticker_import_completed"), default=False):
                lines.extend(
                    [
                        "Sticker library import completed before this reply.",
                        (
                            "sticker_import_result: "
                            f"accepted={_safe_str(metadata.get('sticker_import_accepted'))} "
                            f"imported={_safe_str(metadata.get('sticker_imported'))} "
                            f"mood={_safe_str(metadata.get('sticker_mood'))} "
                            f"label={_safe_str(metadata.get('sticker_mood_label'))} "
                            f"confidence={_safe_str(metadata.get('sticker_confidence'))} "
                            f"destination={_safe_str(metadata.get('sticker_destination'))[:240]}"
                        ),
                    ]
                )

        reply_id = _safe_str(metadata.get("qq_reply_message_id")).strip()
        reply_context = metadata.get("qq_reply_context")
        if reply_id or isinstance(reply_context, dict):
            lines.extend(
                [
                    "The current QQ message is replying to/quoting an earlier message.",
                    f"quoted_message_id: {reply_id or _safe_str((reply_context or {}).get('message_id'))}",
                ]
            )
            if isinstance(reply_context, dict):
                quoted_text = _safe_str(reply_context.get("text")).strip()
                quoted_rich = _safe_str(reply_context.get("rich_summary")).strip()
                sender = _safe_str(reply_context.get("sender_name") or reply_context.get("user_id")).strip()
                if sender:
                    lines.append(f"quoted_sender: {sender[:120]}")
                if quoted_text:
                    lines.extend(["quoted_text:", quoted_text[:1200]])
                if quoted_rich:
                    lines.append(f"quoted_rich_summary: {quoted_rich[:800]}")
        forward_context = metadata.get("qq_forward_context")
        if isinstance(forward_context, dict) or _as_bool(metadata.get("qq_forward_context_available"), default=False):
            forward_context_dict = forward_context if isinstance(forward_context, dict) else {}
            forward_ids = metadata.get("qq_forward_message_ids")
            if not isinstance(forward_ids, list):
                forward_ids = forward_context_dict.get("forward_ids")
            messages = forward_context_dict.get("messages")
            lines.extend(
                [
                    "The current QQ message includes a forwarded/merged chat record.",
                    (
                        "Read the forwarded chat as owner-supplied context for this turn. "
                        "Do not describe it as unavailable if the forwarded_text lines are present."
                    ),
                    f"forward_ids: {','.join(_safe_str(item) for item in (forward_ids or [])[:4]) or 'none'}",
                    f"forward_message_count: {_safe_str(forward_context_dict.get('message_count'), '0')}",
                ]
            )
            if isinstance(messages, list):
                for index, item in enumerate(messages[:8], start=1):
                    if not isinstance(item, dict):
                        continue
                    sender = _safe_str(item.get("sender_name") or item.get("user_id")).strip() or "unknown"
                    text = _safe_str(item.get("text") or item.get("rich_summary") or item.get("raw_message")).strip()
                    if not text:
                        continue
                    lines.append(f"- forwarded {index} {sender[:80]}: {text[:600]}")
        image_context = metadata.get("qq_image_context")
        if isinstance(image_context, dict) or _as_bool(metadata.get("qq_image_context_available"), default=False):
            image_context_dict = image_context if isinstance(image_context, dict) else {}
            lines.extend(
                [
                    "The current QQ image has been processed into image context.",
                    (
                        "Use OCR and visual summary as owner-supplied context for this turn. "
                        "If the summary says uncertain, keep that uncertainty in the reply."
                    ),
                ]
            )
            ocr_text = _safe_str(image_context_dict.get("ocr_text")).strip()
            vision_summary = _safe_str(image_context_dict.get("vision_summary")).strip()
            notes = image_context_dict.get("notes")
            if isinstance(notes, list) and notes:
                lines.append("image_context_notes: " + ",".join(_safe_str(note) for note in notes[:6]))
            if ocr_text:
                lines.extend(["image_ocr_text:", ocr_text[:1200]])
            if vision_summary:
                lines.extend(["image_visual_summary:", vision_summary[:1200]])
        if not lines:
            return ""
        return "\n".join(lines[:32])

    def _append_dialogue_tail(
        self,
        session: AgentSession,
        *,
        user_text: str,
        reply: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        recorded_at = datetime.now().astimezone().isoformat()
        user_content = self._dialogue_tail_user_content(user_text, payload=payload)
        if user_content.strip():
            session.dialogue_tail.append(
                {"role": "user", "content": user_content.strip(), "recorded_at": recorded_at}
            )
        if reply.strip():
            session.dialogue_tail.append(
                {"role": "assistant", "content": reply.strip(), "recorded_at": recorded_at}
            )
        if self.dialogue_session_tail_entries <= 0:
            session.dialogue_tail.clear()
        elif len(session.dialogue_tail) > self.dialogue_session_tail_entries:
            del session.dialogue_tail[:-self.dialogue_session_tail_entries]
        try:
            save_dialogue_tail(self.xinyu_dir, session.key, session.dialogue_tail, max_entries=self.dialogue_persisted_tail_entries)
        except Exception:
            pass

    def _dialogue_tail_user_content(self, user_text: str, *, payload: dict[str, Any] | None = None) -> str:
        text = user_text.strip()
        payload = payload if isinstance(payload, dict) else {}
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict) or not _as_bool(metadata.get("sticker_import_completed"), default=False):
            return text
        label = _safe_str(metadata.get("sticker_mood_label") or metadata.get("sticker_mood")).strip()
        mood = _safe_str(metadata.get("sticker_mood")).strip()
        confidence = _safe_str(metadata.get("sticker_confidence")).strip()
        destination = _safe_str(metadata.get("sticker_destination")).strip()
        image_context = metadata.get("qq_image_context")
        image_context = image_context if isinstance(image_context, dict) else {}
        vision_summary = _safe_str(image_context.get("vision_summary")).strip()
        meaning = _safe_str(image_context.get("meaning")).strip()
        parts = [text or "我发了一张表情包。"]
        details = ["owner 刚发来一张 QQ 表情包"]
        if label:
            details.append(f"分类={label}")
        if mood and mood != label:
            details.append(f"mood={mood}")
        if confidence:
            details.append(f"置信度={confidence}")
        if meaning:
            details.append(f"语义={meaning}")
        if destination:
            details.append(f"入库位置={destination}")
        if vision_summary:
            details.append(f"摘要={vision_summary[:500]}")
        parts.append("【收到的表情记录】" + "；".join(details))
        return "\n".join(parts)

    @staticmethod
    def _is_recent_sticker_question(user_text: str) -> bool:
        compact = re.sub(r"\s+", "", _safe_str(user_text))
        if not compact:
            return False
        exact_markers = (
            "我刚发的是什么",
            "刚发的是什么",
            "刚才发的是什么",
            "我刚发了什么",
            "刚发了什么",
            "刚才发了什么",
            "我发的是什么",
            "我发了什么",
            "刚那个表情是什么",
            "刚才那个表情是什么",
            "刚刚那个表情是什么",
        )
        if any(marker in compact for marker in exact_markers):
            return True
        return "刚" in compact and "表情" in compact and any(marker in compact for marker in ("什么", "啥", "内容"))

    @staticmethod
    def _current_sticker_question_reply(user_text: str, payload: dict[str, Any]) -> str:
        if not XinYuBridgeRuntime._is_recent_sticker_question(user_text):
            return ""
        metadata = payload.get("metadata") if isinstance(payload, dict) else {}
        if not isinstance(metadata, dict):
            return ""
        if _as_bool(metadata.get("recent_sticker_unavailable"), default=False):
            return "你刚发的是一张表情包。但这次 QQ 只给了动画表情占位，我没抓到具体画面。"
        if not (
            _as_bool(metadata.get("recent_sticker_question"), default=False)
            or _as_bool(metadata.get("sticker_import_completed"), default=False)
        ):
            return ""
        if not _as_bool(metadata.get("sticker_import_completed"), default=False):
            return ""
        label = _safe_str(metadata.get("sticker_mood_label") or metadata.get("sticker_mood")).strip()
        confidence = _safe_str(metadata.get("sticker_confidence")).strip()
        image_context = metadata.get("qq_image_context")
        image_context = image_context if isinstance(image_context, dict) else {}
        meaning = _safe_str(image_context.get("meaning")).strip()
        if label:
            reply = f"你刚发的是偏{label}的表情包。"
        else:
            reply = "你刚发的是一张表情包。"
        if meaning:
            reply += f"看起来是{meaning}。"
        if confidence.lower() in {"low", "低", "unclear"}:
            reply += "不过这个判断不太稳。"
        return reply

    @staticmethod
    def _recent_sticker_question_reply(user_text: str, dialogue_tail: list[dict[str, str]]) -> str:
        if not XinYuBridgeRuntime._is_recent_sticker_question(user_text):
            return ""
        for item in reversed(dialogue_tail[-12:]):
            content = _safe_str(item.get("content"))
            marker = "【收到的表情记录】"
            if marker not in content:
                continue
            detail = content.split(marker, 1)[1]
            label = ""
            meaning = ""
            confidence = ""
            for key, assign in (("label", "分类="), ("meaning", "语义="), ("confidence", "置信度=")):
                match = re.search(re.escape(assign) + r"([^；\n]+)", detail)
                if not match:
                    continue
                if key == "label":
                    label = match.group(1).strip()
                elif key == "meaning":
                    meaning = match.group(1).strip()
                else:
                    confidence = match.group(1).strip()
            if label:
                reply = f"你刚发的是偏{label}的表情包。"
            else:
                reply = "你刚发的是一张表情包。"
            if meaning:
                reply += f"看起来是{meaning}。"
            if confidence and confidence.lower() in {"low", "低", "unclear"}:
                reply += "不过这个判断不太稳。"
            return reply
        return ""

    def _append_sticker_delivery_tail(self, session: AgentSession, sticker_reply: dict[str, Any]) -> bool:
        if not isinstance(sticker_reply, dict) or not _as_bool(sticker_reply.get("queued"), default=False):
            return False
        mood = _safe_str(sticker_reply.get("mood")).strip()
        mood_label = sticker_mood_label(mood) if mood else "表情"
        mode = _safe_str(sticker_reply.get("mode")).strip()
        image_name = Path(_safe_str(sticker_reply.get("image_path")).strip()).name
        detail = f"我刚刚在 QQ 私聊里补发了一张{mood_label}表情"
        if image_name:
            detail += f"（{image_name}）"
        if mode:
            detail += f"，发送模式是 {mode}"
        detail += "。如果 owner 追问刚才的表情，就按这条发送记录回应。"
        session.dialogue_tail.append(
            {
                "role": "assistant",
                "content": f"【表情发送记录】{detail}",
                "recorded_at": datetime.now().astimezone().isoformat(),
            }
        )
        if self.dialogue_session_tail_entries <= 0:
            session.dialogue_tail.clear()
            return False
        if len(session.dialogue_tail) > self.dialogue_session_tail_entries:
            del session.dialogue_tail[:-self.dialogue_session_tail_entries]
        try:
            save_dialogue_tail(
                self.xinyu_dir,
                session.key,
                session.dialogue_tail,
                max_entries=self.dialogue_persisted_tail_entries,
            )
        except Exception:
            pass
        return True

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
    def _owner_requested_reply_bubble_units(
        *,
        user_text: str,
        reply: str,
        dialogue_tail: list[dict[str, str]],
    ) -> list[str]:
        compact = re.sub(r"\s+", "", _safe_str(user_text)).lower()
        if not compact:
            return []
        split_markers = (
            "每个数字单独发",
            "每个数字单独发出来",
            "每一个数字单独发",
            "一个数字一条",
            "每个数一条",
            "每个字单独发",
            "一个字一条",
            "一条一条发",
            "逐条发",
            "分开发",
            "拆开发",
            "拆成十句",
            "拆成十条",
        )
        if not any(marker in compact for marker in split_markers):
            return []

        ranged = re.search(r"从\s*(\d{1,3})\s*(?:数)?到\s*(\d{1,3})", _safe_str(user_text))
        if ranged:
            start = int(ranged.group(1))
            end = int(ranged.group(2))
            step = 1 if end >= start else -1
            count = abs(end - start) + 1
            if 2 <= count <= 20:
                return [str(value) for value in range(start, end + step, step)]

        for candidate in (_safe_str(reply), *(
            _safe_str(item.get("content"))
            for item in reversed(dialogue_tail[-12:])
            if item.get("role") == "assistant"
        )):
            units = XinYuBridgeRuntime._numeric_bubble_units_from_text(candidate)
            if units:
                return units
        return []

    @staticmethod
    def _numeric_bubble_units_from_text(text: str) -> list[str]:
        clean = _safe_str(text).strip()
        if not clean:
            return []
        numbers = re.findall(r"\d{1,3}", clean)
        if not (2 <= len(numbers) <= 20):
            return []
        residue = re.sub(r"\d{1,3}", "", clean)
        if re.sub(r"[\s,，、.。;；:：\-—]+", "", residue):
            return []
        values = [int(item) for item in numbers]
        if values != list(range(values[0], values[0] + len(values))):
            return []
        return numbers

    @staticmethod
    def _looks_like_false_single_bubble_limitation(user_text: str, reply: str) -> bool:
        user_compact = re.sub(r"\s+", "", _safe_str(user_text)).lower()
        reply_compact = re.sub(r"\s+", "", _safe_str(reply)).lower()
        if not user_compact or not reply_compact:
            return False
        wants_split = any(
            marker in user_compact
            for marker in (
                "单独发",
                "分开发",
                "拆开发",
                "一条一条发",
                "逐条发",
                "一个数字一条",
                "每个数字",
            )
        )
        if not wants_split:
            return False
        false_limits = (
            "一次只能发一条",
            "只能发一条",
            "没法拆成",
            "不能拆成",
            "没办法拆成",
            "发不了十句",
            "发不了这么多",
        )
        return any(marker in reply_compact for marker in false_limits)

    def _empty_visible_reply_fallback(self, *, payload: dict[str, Any], user_text: str, delegate_note: str = "") -> str:
        return ""

    @staticmethod
    def _critical_final_guard_flags(flags: list[str] | tuple[str, ...]) -> list[str]:
        critical = {
            "pseudo_tool_call_naturalized",
            "machine_introspection_naturalized",
            "visible_memory_mechanics_naturalized",
            "false_codex_unavailable_claim_blocked",
            "layered_voice_self_analysis_blocked",
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
    parser.add_argument(
        "--desktop-events-host",
        default=os.environ.get("XINYU_DESKTOP_EVENTS_HOST", "127.0.0.1"),
        help="Loopback host for the dark-launched desktop WebSocket event stream.",
    )
    parser.add_argument(
        "--desktop-events-port",
        type=int,
        default=_as_int(os.environ.get("XINYU_DESKTOP_EVENTS_PORT"), 8766),
        help="Port for the dark-launched desktop WebSocket event stream.",
    )
    parser.add_argument(
        "--disable-desktop-events",
        action="store_true",
        default=_as_bool(os.environ.get("XINYU_DISABLE_DESKTOP_EVENTS"), default=False),
        help="Disable the desktop WebSocket event stream dark launch.",
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
    if not args.disable_desktop_events:
        enforce_bridge_token_guard(args.desktop_events_host, args.bridge_token.strip())
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
    desktop_service = build_desktop_service(
        enabled=not args.disable_desktop_events,
        loop=loop,
        host=args.desktop_events_host,
        port=args.desktop_events_port,
        token=args.bridge_token.strip(),
    )
    desktop_service.attach_runtime(runtime)
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

    if desktop_service.enabled:
        try:
            future = asyncio.run_coroutine_threadsafe(desktop_service.start(), loop)
            future.result(timeout=10)
            print(
                "[xinyu_core_bridge] desktop event stream dark launch listening on "
                f"{desktop_service.listener_url()}",
                flush=True,
            )
        except Exception as exc:
            print(f"[xinyu_core_bridge] desktop event stream startup warning: {exc}", flush=True)

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
        if desktop_service.enabled:
            try:
                future = asyncio.run_coroutine_threadsafe(desktop_service.stop(), loop)
                future.result(timeout=10)
                print("[xinyu_core_bridge] desktop event stream stopped", flush=True)
            except Exception as exc:
                print(f"[xinyu_core_bridge] desktop event stream shutdown warning: {exc}", flush=True)
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
