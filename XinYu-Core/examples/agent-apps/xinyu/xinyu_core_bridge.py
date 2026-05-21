from __future__ import annotations

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
from state_service import append_jsonl, atomic_write_text
from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_external_plugin_routes import (
    external_plugin_call as _external_plugin_call_route,
    external_plugin_config as _external_plugin_config_route,
    external_plugin_install as _external_plugin_install_route,
    external_plugin_manifest as _external_plugin_manifest_route,
)
from xinyu_bridge_http import XinYuBridgeHTTPServer, XinYuBridgeRequestHandler
from xinyu_bridge_intervention_routes import (
    turn_cancel as _turn_cancel_route,
    turn_continue as _turn_continue_route,
    turn_current as _turn_current_route,
    turn_retry_lightweight as _turn_retry_lightweight_route,
    turn_skip_sidecar as _turn_skip_sidecar_route,
    turn_status_message as _turn_status_message_route,
)
from xinyu_bridge_metabolism_routes import (
    apply_self_choice_metabolism_decision as _apply_self_choice_metabolism_decision_route,
    life_metabolism_ticket_approve as _life_metabolism_ticket_approve_route,
    life_metabolism_ticket_cancel as _life_metabolism_ticket_cancel_route,
    life_metabolism_ticket_get as _life_metabolism_ticket_get_route,
    life_metabolism_ticket_list as _life_metabolism_ticket_list_route,
    life_metabolism_ticket_reject as _life_metabolism_ticket_reject_route,
    publish_metabolism_decision as _publish_metabolism_decision_route,
)
from xinyu_bridge_bootstrap import ensure_repo_src as _ensure_repo_src
from xinyu_bridge_bootstrap import load_local_env as _load_local_env
from xinyu_bridge_cli import build_bridge_parser as _build_parser
from xinyu_bridge_learning import (
    LearningBridgeError,
    stage_codex_report_material,
)
from xinyu_bridge_learning_sidecars import int_result as _int_result
from xinyu_bridge_learning_sidecars import run_learning_study_chain as _run_learning_study_chain
from xinyu_bridge_learning_sidecars import should_run_learning_after_codex as _should_run_learning_after_codex
from xinyu_bridge_loop_thread import start_loop_thread as _start_loop_thread
from xinyu_bridge_null_input import NullInputModule as _NullInputModule
from xinyu_bridge_context import prompt_context_signature
from xinyu_bridge_desktop_actions import desktop_action_pressure_label as _desktop_action_pressure_label
from xinyu_bridge_desktop_actions import desktop_action_result_label as _desktop_action_result_label
from xinyu_bridge_desktop_actions import desktop_action_theme_label as _desktop_action_theme_label
from xinyu_bridge_desktop_actions import desktop_scrub_action_markers as _desktop_scrub_action_markers
from xinyu_bridge_desktop_projection import desktop_avatar_url
from xinyu_bridge_desktop_projection import desktop_display_id
from xinyu_bridge_desktop_projection import desktop_group_avatar_url
from xinyu_bridge_desktop_projection import desktop_hash
from xinyu_bridge_desktop_projection import desktop_marker_count
from xinyu_bridge_desktop_projection import desktop_privacy_for_payload
from xinyu_bridge_desktop_projection import desktop_proactive_expired
from xinyu_bridge_desktop_projection import desktop_recall_count
from xinyu_bridge_desktop_projection import desktop_session_kind
from xinyu_bridge_desktop_projection import desktop_text_preview
from xinyu_bridge_desktop_projection import desktop_top_recall_sources
from xinyu_bridge_desktop_proactive_routes import (
    desktop_approve_proactive_qq as _desktop_approve_proactive_qq_route,
    desktop_finish_proactive_ack as _desktop_finish_proactive_ack_route,
    desktop_proactive_ack as _desktop_proactive_ack_route,
    desktop_proactive_inbox as _desktop_proactive_inbox_route,
    desktop_update_proactive_request_state as _desktop_update_proactive_request_state_route,
    record_desktop_initiative_feedback as _record_desktop_initiative_feedback_route,
)
import xinyu_bridge_desktop_snapshot
from xinyu_bridge_desktop_self_action_routes import (
    desktop_attach_self_action_patch_executor as _desktop_attach_self_action_patch_executor_route,
    desktop_self_action_approval as _desktop_self_action_approval_route,
    desktop_self_action_approval_reply as _desktop_self_action_approval_reply_route,
    desktop_self_action_pending_item as _desktop_self_action_pending_item_route,
)
import xinyu_bridge_health_snapshot
from xinyu_bridge_memory_snapshot import memory_snapshot as _memory_snapshot
from xinyu_bridge_payload_policy import owner_private_payload_matches
from xinyu_bridge_payload_policy import trusted_private_payload_matches
from xinyu_bridge_reply_text import normalize_bridge_reply as _normalize_reply
from xinyu_bridge_reply_bubbles import looks_like_false_single_bubble_limitation
from xinyu_bridge_reply_bubbles import numeric_bubble_units_from_text
from xinyu_bridge_reply_bubbles import owner_requested_reply_bubble_units
from xinyu_bridge_promises import compact_promise_text
import xinyu_bridge_promise_followup
from xinyu_bridge_promise_followup import PROMISE_FOLLOWUP_STATE_REL
import xinyu_bridge_proactive_context
from xinyu_proactive_lifecycle_trace import append_proactive_lifecycle_event
from xinyu_bridge_proactive_delivery_routes import (
    claim_proactive_for_qq_outbox as _claim_proactive_for_qq_outbox_route,
    claim_proactive_for_qq_outbox_sync as _claim_proactive_for_qq_outbox_sync_route,
    proactive as _proactive_route,
    proactive_ack as _proactive_ack_route,
    proactive_candidate_already_handled as _proactive_candidate_already_handled_route,
    qq_outbox_ack as _qq_outbox_ack_route,
    qq_outbox_ack_fast as _qq_outbox_ack_fast_route,
    qq_outbox_claim as _qq_outbox_claim_route,
    qq_outbox_claim_fast as _qq_outbox_claim_fast_route,
    ready_proactive_outbox_candidate as _ready_proactive_outbox_candidate_route,
    record_proactive_outbound_dialogue as _record_proactive_outbound_dialogue_route,
)
from xinyu_bridge_recent_sticker_reply import current_sticker_question_reply
from xinyu_bridge_recent_sticker_reply import is_recent_sticker_question
from xinyu_bridge_recent_sticker_reply import recent_sticker_question_reply
from xinyu_bridge_renderer import BridgeRenderer, critical_final_guard_flags, replace_last_assistant_message
from xinyu_bridge_session import AgentSession, session_key_from_payload, session_keys_to_expire
from xinyu_bridge_state_text import parse_iso as _parse_iso
from xinyu_bridge_state_text import payload_path as _payload_path
from xinyu_bridge_state_text import payload_event_time_iso as _payload_event_time_iso
from xinyu_bridge_state_text import payload_event_timestamp_seconds as _payload_event_timestamp_seconds
from xinyu_bridge_state_text import read_text_safe as _read_text_safe
from xinyu_bridge_state_text import seconds_since_iso as _seconds_since_iso
from xinyu_bridge_state_text import iso_from_timestamp as _state_iso_from_timestamp
from xinyu_bridge_state_text import state_field as _state_field
from xinyu_bridge_state_text import desktop_replace_frontmatter_field
from xinyu_bridge_state_text import desktop_replace_list_field
from xinyu_bridge_trusted_search import trusted_public_search_task_allowed
from xinyu_bridge_utility_routes import goldmark_mark_request as _goldmark_mark_request_route
from xinyu_bridge_utility_routes import message_ack as _message_ack_route
from xinyu_bridge_utility_routes import probe as _probe_route
from xinyu_bridge_utility_routes import review_inbox_command as _review_inbox_command_route
from xinyu_bridge_values import as_bool as _as_bool
from xinyu_bridge_values import as_int as _as_int
from xinyu_bridge_values import as_str_set as _as_str_set
from xinyu_bridge_values import compact_text as _compact_text
from xinyu_bridge_values import contains_any as _contains_any
from xinyu_bridge_values import dedupe as _dedupe
from xinyu_bridge_values import optional_int as _optional_int
from xinyu_bridge_values import payload_text as _payload_text_from_payload
from xinyu_bridge_values import safe_str as _safe_str
import xinyu_bridge_action_routes
from xinyu_bridge_reply_pipeline import recover_empty_visible_reply, render_outward_reply_with_trace
import xinyu_bridge_semantic_fast_routes
from xinyu_bridge_slow_live_turn import (
    build_slow_live_model_contexts,
    inject_slow_live_model_event,
    run_slow_live_finish_sidecars_with_trace,
    run_slow_live_memory_recall,
)
from xinyu_bridge_turn_finish_sidecars import run_slow_turn_finish_sidecars
import xinyu_bridge_turn_sidecars
from xinyu_bridge_turn_pipeline import PreModelRouteResult, run_pre_model_routes, run_pre_model_routes_with_timeout
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
from xinyu_contextual_self_observatory import run_contextual_self_observatory
from xinyu_living_memory_recall import run_living_memory_recall_algorithm
from xinyu_dialogue_curiosity import evaluate_previous_reaction
from xinyu_dialogue_working_memory import (
    compact_tail_for_prompt,
    load_dialogue_tail,
    persisted_tail_entries,
    prompt_tail_entries,
    save_dialogue_tail,
    session_tail_entries,
)
from xinyu_external_plugins import (
    ExternalCallContext,
    execute_http_prepared_call,
    external_plugin_runtime_allowed,
    prepare_external_call,
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
from xinyu_emotion_council import run_emotion_council_shadow
from xinyu_life_kernel import build_entropy_state, evaluate_life_kernel
from xinyu_life_reply_policy import (
    apply_life_reply_policy,
    build_life_reply_policy,
)
from xinyu_response_error_loop import classify_response_error
from xinyu_scene_frame import build_scene_frame
from xinyu_slow_state_modulator import build_slow_state
from xinyu_learning_service import build_learning_service
from xinyu_creative_writing import run_creative_writing_maintenance
from xinyu_daily_digest import run_daily_digest_maintenance
from xinyu_expression_self_learning import record_expression_self_learning_event
from xinyu_goldmark_dehydrate import run_goldmark_dehydration_maintenance
from xinyu_goal_outcome_observer import run_goal_outcome_observer
from xinyu_impulse_soup import run_impulse_soup
from xinyu_initiative_orchestrator import record_initiative_feedback, run_initiative_orchestrator
from xinyu_initiative_spine import run_initiative_spine
from xinyu_learning_closed_loop import (
    record_learning_closed_loop_self_thought,
    record_learning_closed_loop_turn,
)
from xinyu_life_month_slots import refresh_current_life_month_context  # noqa: F401 - compatibility for older tests/hooks
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
)
from xinyu_memory_event_sourcing import record_action_experience_event, record_chat_event
from xinyu_metabolism_contract import (
    create_ticket as create_metabolism_ticket,
    list_tickets as list_metabolism_tickets,
    run_due_metabolism_tickets,
)
from xinyu_self_choice_store import SelfChoiceStore
from xinyu_package_installer import install_python_packages
from xinyu_memory_weights import refresh_memory_weight_state  # noqa: F401 - compatibility for older tests/hooks
from xinyu_persona_state import observe_persona_turn
from xinyu_private_thought_events import record_private_thought_outcome, record_private_thought_reply_link
from xinyu_proactive_request_loop import run_proactive_request_loop
from xinyu_proactivity_scorer import run_proactivity_scorer_shadow
from xinyu_qq_outbox import (
    enqueue_qq_outbox_file,
    enqueue_qq_outbox_image,
    enqueue_qq_outbox_message,
    enqueue_owner_qq_outbox_message,
)
from xinyu_recent_context_guard import ensure_recent_context_health
from xinyu_runtime_presence import (
    record_bridge_heartbeat,
    record_codex_presence,
    record_turn_finished,
    record_turn_started,
)
from xinyu_bridge_route_observer import TurnRouteObserver
from xinyu_turn_route_trace import record_turn_route_stage
from xinyu_runtime_security import (
    enforce_bridge_token_guard,
    enforce_llm_http_guard,
    runtime_source_paths,
    source_file_digest,
    source_files_digest,
)
from xinyu_review_inbox import run_review_inbox_maintenance
from xinyu_self_action_gateway import run_self_action_gateway
from xinyu_self_action_patch_executor import run_self_action_patch_executor
from xinyu_self_action_voice import (
    compose_self_action_approval_voice,
    compose_self_action_prepared_patch_voice,
)
from xinyu_self_code_approval import (
    consume_self_code_approval,
    create_direct_self_code_approval,
    mark_self_code_execution_scheduled,
)
from xinyu_self_code_watchdog import create_self_code_snapshot
from xinyu_self_chosen_goal_ecology import run_self_chosen_goal_ecology
from xinyu_self_thought_loop import run_self_thought_loop
from xinyu_sent_reply_index import visible_text_hash
from xinyu_storage_paths import knowledge_ref
from xinyu_sticker_ingest import import_sticker_from_payload
from xinyu_speech_controller import XinyuSpeechController
from xinyu_sticker_pack import sticker_mood_label
from xinyu_text_variants import readable_markers
from xinyu_tool_protocol import ActionOutcome, DELEGATED_LOCAL_RISK, ToolRequest
from xinyu_v1_canary_readiness import record_v1_shadow_observation
from xinyu_turn_classifier import classify_visible_turn
from xinyu_uncertainty_pause import (
    mark_uncertainty_pause_replied,
)
from xinyu_visible_reply_guard import dedupe_visible_reply
from xinyu_visible_persona_voice import (
    compose_codex_chat_scheduled_reply,
    compose_promise_followup_message,
    compose_proactive_visible_message,
    compose_watchdog_visible_message,
)
from xinyu_visible_state_hygiene import sanitize_visible_state_files
from xinyu_watched_sources import run_watched_source_check


def _timestamp_or_now_iso(value: Any) -> str:
    parsed = _parse_timestamp_iso(value)
    if parsed is None:
        return datetime.now().astimezone().isoformat()
    return parsed.astimezone().isoformat()


def _parse_timestamp_iso(value: Any) -> datetime | None:
    text = _safe_str(value).strip()
    if not text or text.lower() in {"none", "unknown", "null", "n/a", "na"}:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


BRIDGE_VERSION = "0.8.99"
BRIDGE_SOURCE_PATH = Path(__file__).resolve()
BRIDGE_SOURCE_DIGEST = source_file_digest(BRIDGE_SOURCE_PATH)
BRIDGE_RUNTIME_SOURCE_DIGEST = source_files_digest(runtime_source_paths(BRIDGE_SOURCE_PATH.parent))
CODEX_DEFAULT_TIMEOUT_SECONDS = 3600
CODEX_VISIBLE_WINDOW_TITLE = "Xinyu codex"
CODEX_GENERATED_IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp"})
DESKTOP_RECENT_TURNS_MAX = 200
DESKTOP_RECENT_MEMORY_EVENTS_MAX = 200
DESKTOP_PROACTIVE_HISTORY_MAX = 20
DESKTOP_PROACTIVE_HISTORY_REL = Path("memory/context/proactive_request_history.jsonl")
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
    "\u665a\u4e0a\u56de\u6765",
    "\u4eca\u665a\u56de\u6765",
    "\u56de\u6765\u6211\u8981\u770b\u5230",
    "\u6211\u8981\u770b\u5230\u4f60\u7684\u6c47\u62a5",
    "\u770b\u5230\u4f60\u7684\u6c47\u62a5",
    "\u7ed9\u6211\u6c47\u62a5",
    "\u4f60\u7684\u6c47\u62a5",
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
    "\u6211\u4f1a\u6c47\u62a5",
    "\u7ed9\u4f60\u6c47\u62a5",
    "\u6211\u7ed9\u4f60\u6c47\u62a5",
    "\u665a\u4e0a\u7ed9\u4f60",
    "\u7b49\u4f60\u56de\u6765",
    "\u56de\u6765\u7ed9\u4f60",
    "\u6211\u4f1a\u6574\u7406",
    "\u6211\u5199\u4e2a\u6c47\u62a5",
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
    "\u6c47\u62a5\u5199\u5b8c",
    "\u6c47\u62a5\u6574\u7406\u597d",
    "\u6211\u6c47\u62a5\u5b8c",
    "\u8fd9\u662f\u6c47\u62a5",
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
    "memory/creative/planning/novel_profile.md",
    "memory/creative/planning/novel_state.md",
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
    knowledge_ref("ai_domain.md"),
    knowledge_ref("social_inquiry_policy.md"),
)

AUTONOMOUS_MAINTENANCE_PROMPT = (
    "Maintenance-only pass. This is a low-frequency maintenance pass from "
    "XinYu Core, not a human speaking turn. Refresh time anchor, runtime "
    "bridge state, inner cycle, desktop thoughts, continuity, slow reflection, "
    "creative writing, memory consolidation, learning gates, and archive gates only when each "
    "subsystem is due. Do not initiate visible chat. If any outward text is "
    "unavoidable, output exactly [WAITING]."
)


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
        self.pre_model_routes_timeout_seconds = max(
            1,
            _as_int(os.environ.get("XINYU_PRE_MODEL_ROUTES_TIMEOUT_SECONDS"), 8),
        )
        self.emotion_council_prompt_enabled = _as_bool(
            os.environ.get("XINYU_EMOTION_COUNCIL_PROMPT_ENABLED"),
            default=False,
        )
        self.v1_owner_simple_canary = _as_bool(os.environ.get(V1_OWNER_SIMPLE_CANARY_ENV), default=False)
        self.owner_private_semantic_fast_route = _as_bool(
            os.environ.get("XINYU_OWNER_PRIVATE_SEMANTIC_FAST_ROUTE"),
            default=True,
        )
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
        self._desktop_proactive_history: list[dict[str, Any]] = []
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
        record_turn_route_stage(
            self.xinyu_dir,
            turn_id=f"bridge-startup-{int(time.time())}",
            stage="bridge_started",
            route="idle",
            status="ok",
            elapsed_ms=0,
            notes=["bridge_init"],
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
        return xinyu_bridge_health_snapshot.health_snapshot(
            self,
            bridge_version=BRIDGE_VERSION,
            source_digest=BRIDGE_SOURCE_DIGEST,
            runtime_source_digest=BRIDGE_RUNTIME_SOURCE_DIGEST,
        )

    async def health(self) -> dict[str, Any]:
        return self.health_snapshot()

    async def _ensure_self_choice_ready(self) -> None:
        await self.self_choice_store.load_or_recover()

    async def desktop_snapshot(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await xinyu_bridge_desktop_snapshot.desktop_snapshot(self, payload)

    async def desktop_self_action_approval(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await _desktop_self_action_approval_route(self, payload)

    async def _desktop_attach_self_action_patch_executor(
        self,
        result: dict[str, Any],
        *,
        checked_at: str,
        authorize_codex: bool,
        timeout_seconds: int,
    ) -> None:
        await _desktop_attach_self_action_patch_executor_route(
            self,
            result,
            checked_at=checked_at,
            authorize_codex=authorize_codex,
            timeout_seconds=timeout_seconds,
        )

    def _desktop_self_action_pending_item(self, queue_id: str) -> dict[str, Any]:
        return _desktop_self_action_pending_item_route(self, queue_id)

    @staticmethod
    def _desktop_self_action_approval_reply(result: dict[str, Any], *, decision: str) -> str:
        return _desktop_self_action_approval_reply_route(result, decision=decision)

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

    _desktop_marker_count = staticmethod(desktop_marker_count)

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
        initiative_metrics: dict[str, Any] | None = None,
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
        initiative_metrics = initiative_metrics if isinstance(initiative_metrics, dict) else {}
        latest_memory_route = self._desktop_latest_memory_route(recent_memory_events)
        action_recent = action_digest.get("recent") if isinstance(action_digest.get("recent"), list) else []
        latest_action = action_recent[-1] if action_recent and isinstance(action_recent[-1], dict) else {}
        seed_detail = latest_action.get("seed_detail") if isinstance(latest_action.get("seed_detail"), dict) else {}
        creative_state_text = _read_text_safe(self.xinyu_dir / "memory/creative/planning/novel_state.md")
        creative_status = _state_field(creative_state_text, "status", "unknown")
        creative_mode = _state_field(creative_state_text, "creative_writing_mode", "novel_mode")
        creative_project = _state_field(creative_state_text, "current_project", "")
        creative_today = self._desktop_metric_int(_state_field(creative_state_text, "today_chapters_written", "0"))
        creative_target = self._desktop_metric_int(_state_field(creative_state_text, "daily_target_chapters", "0"))
        creative_min_platform_chars = self._desktop_metric_int(_state_field(creative_state_text, "min_platform_chars", "0"))
        creative_target_platform_chars = self._desktop_metric_int(_state_field(creative_state_text, "target_platform_chars", "0"))
        creative_total = self._desktop_metric_int(_state_field(creative_state_text, "total_chapters", "0"))
        creative_publish_ready = self._desktop_metric_int(_state_field(creative_state_text, "publish_ready_chapters", "0"))
        creative_publish_pending = self._desktop_metric_int(_state_field(creative_state_text, "publish_pending_chapters", "0"))
        creative_latest = _state_field(creative_state_text, "latest_chapter_path", "")
        creative_publication_latest = _state_field(creative_state_text, "publication_latest_chapter_path", "")
        creative_publication_log = _state_field(creative_state_text, "publication_log_path", "")
        creative_next = _state_field(creative_state_text, "next_action", "")
        creative_reference_status = _state_field(creative_state_text, "reference_collection_status", "")
        creative_reference_sources = self._desktop_metric_int(_state_field(creative_state_text, "reference_sources_collected", "0"))
        creative_reference_downloads = self._desktop_metric_int(_state_field(creative_state_text, "reference_downloaded_sources", "0"))
        creative_reference_digest = _state_field(creative_state_text, "reference_digest_path", "")
        creative_reference_local_files = self._desktop_metric_int(_state_field(creative_state_text, "reference_local_files", "0"))
        creative_reference_local_index = _state_field(creative_state_text, "reference_local_index_path", "")
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
            "latest_memory_route_summary": _safe_str(latest_memory_route.get("summary")),
            "latest_memory_route_experts": latest_memory_route.get("selectedExperts", []),
            "latest_memory_current_turn_facts": latest_memory_route.get("currentTurnFacts", []),
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
            "creative_writing_status": creative_status,
            "creative_writing_mode": creative_mode,
            "creative_writing_project": creative_project,
            "creative_writing_today_chapters": creative_today,
            "creative_writing_daily_target": creative_target,
            "creative_writing_min_platform_chars": creative_min_platform_chars,
            "creative_writing_target_platform_chars": creative_target_platform_chars,
            "creative_writing_total_chapters": creative_total,
            "creative_writing_publish_ready_chapters": creative_publish_ready,
            "creative_writing_publish_pending_chapters": creative_publish_pending,
            "creative_writing_latest_chapter": creative_latest,
            "creative_writing_publication_latest_chapter": creative_publication_latest,
            "creative_writing_publication_log": creative_publication_log,
            "creative_writing_next_action": creative_next,
            "creative_writing_reference_status": creative_reference_status,
            "creative_writing_reference_sources": creative_reference_sources,
            "creative_writing_reference_downloads": creative_reference_downloads,
            "creative_writing_reference_digest": creative_reference_digest,
            "creative_writing_reference_local_files": creative_reference_local_files,
            "creative_writing_reference_local_index": creative_reference_local_index,
            "initiative_metrics": self._desktop_initiative_metrics_summary(initiative_metrics),
        }

    def _desktop_latest_memory_route(self, recent_memory_events: list[Any]) -> dict[str, Any]:
        for item in reversed(recent_memory_events):
            if not isinstance(item, dict):
                continue
            route = item.get("route")
            if isinstance(route, dict):
                selected = [_safe_str(value) for value in list(route.get("selectedExperts", []))[:6] if _safe_str(value)]
                current_facts = [_safe_str(value) for value in list(route.get("currentTurnFacts", []))[:6] if _safe_str(value)]
                return {
                    "summary": " + ".join(selected),
                    "selectedExperts": selected,
                    "currentTurnFacts": current_facts,
                }
            selected = [_safe_str(value) for value in list(item.get("selectedExperts", []))[:6] if _safe_str(value)]
            if selected:
                return {
                    "summary": " + ".join(selected),
                    "selectedExperts": selected,
                    "currentTurnFacts": [_safe_str(value) for value in list(item.get("currentTurnFacts", []))[:6] if _safe_str(value)],
                }
        return {"summary": "", "selectedExperts": [], "currentTurnFacts": []}

    def _desktop_initiative_metrics_summary(self, metrics: dict[str, Any]) -> dict[str, Any]:
        return xinyu_bridge_desktop_snapshot.desktop_initiative_metrics_summary(metrics)

    @staticmethod
    def _desktop_metric_int(value: Any) -> int:
        return xinyu_bridge_desktop_snapshot.desktop_metric_int(value)

    async def desktop_events_recent(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await desktop_service_events_recent(self.desktop_event_bus, payload)

    async def desktop_proactive_inbox(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await _desktop_proactive_inbox_route(self, payload)

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
        return await _life_metabolism_ticket_get_route(self, payload)

    async def life_metabolism_ticket_list(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await _life_metabolism_ticket_list_route(self, payload)

    async def life_metabolism_ticket_approve(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await _life_metabolism_ticket_approve_route(self, payload)

    async def life_metabolism_ticket_reject(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await _life_metabolism_ticket_reject_route(self, payload)

    async def life_metabolism_ticket_cancel(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await _life_metabolism_ticket_cancel_route(self, payload)

    async def _apply_self_choice_metabolism_decision(self, event: str, result: dict[str, Any]) -> None:
        await _apply_self_choice_metabolism_decision_route(self, event, result)

    async def _publish_metabolism_decision(self, decision: str, result: dict[str, Any]) -> None:
        await _publish_metabolism_decision_route(self, decision, result)

    async def _desktop_event_state(self) -> dict[str, Any]:
        return await desktop_service_event_state(self.desktop_event_bus)

    def _desktop_services(self) -> list[dict[str, Any]]:
        return desktop_service_services(
            ws_server=self.desktop_ws_server,
            closed=self._closed,
            memory_root_exists=self.memory_root.exists(),
        )

    _desktop_limit = staticmethod(desktop_service_limit)

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
        route_payload = self._desktop_memory_route_payload(getattr(result, "route_plan", None))
        event_payload = {
            **self._desktop_turn_base(payload, session_key=session_key, turn_id=turn_id),
            "status": status,
            "recallTurnId": _safe_str(getattr(result, "turn_id", "")),
            "queryHash": self._desktop_hash(query_text),
            "queryChars": len(query_text),
            "itemCount": len(raw_items),
            "topSources": top_sources,
            "selectedExperts": route_payload.get("selectedExperts", []),
            "currentTurnFacts": route_payload.get("currentTurnFacts", []),
            "route": route_payload,
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

    def _desktop_memory_route_payload(self, route_plan: Any | None) -> dict[str, Any]:
        if route_plan is None:
            return {
                "version": 1,
                "selectedExperts": [],
                "allowedSources": [],
                "allowedMemoryRefs": [],
                "currentTurnFacts": [],
                "decisions": [],
                "notes": [],
            }
        decisions: list[dict[str, Any]] = []
        for decision in list(getattr(route_plan, "decisions", ()) or ())[:12]:
            decisions.append(
                {
                    "expert": _safe_str(getattr(decision, "expert", "")),
                    "score": round(float(getattr(decision, "score", 0.0) or 0.0), 3),
                    "selected": bool(getattr(decision, "selected", False)),
                    "reasons": [_safe_str(reason) for reason in list(getattr(decision, "reasons", ()) or ())[:8] if _safe_str(reason)],
                }
            )
        return {
            "version": 1,
            "selectedExperts": [_safe_str(value) for value in list(getattr(route_plan, "selected_experts", ()) or ())[:8] if _safe_str(value)],
            "allowedSources": [_safe_str(value) for value in list(getattr(route_plan, "allowed_sources", ()) or ())[:8] if _safe_str(value)],
            "allowedMemoryRefs": [_safe_str(value) for value in list(getattr(route_plan, "allowed_memory_refs", ()) or ())[:12] if _safe_str(value)],
            "currentTurnFacts": [_safe_str(value) for value in list(getattr(route_plan, "current_turn_facts", ()) or ())[:8] if _safe_str(value)],
            "decisions": decisions,
            "notes": [_safe_str(note) for note in list(getattr(route_plan, "notes", ()) or ())[:8] if _safe_str(note)],
        }

    _desktop_recall_count = staticmethod(desktop_recall_count)
    _desktop_top_recall_sources = staticmethod(desktop_top_recall_sources)

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

    def _desktop_publish_initiative_candidate_threadsafe(
        self,
        item: dict[str, Any],
        *,
        notes: list[str] | tuple[str, ...] | None = None,
    ) -> bool:
        if not item or not _safe_str(item.get("candidateId")):
            return False
        safe_item = {
            **dict(item),
            "claimable": False,
            "deliveryLevel": _safe_str(item.get("deliveryLevel"), "state_only") or "state_only",
            "requiresOwnerAck": True,
            "notes": _dedupe(list(item.get("notes", [])) + list(notes or []))[:10],
        }
        existing = self._desktop_proactive_existing(_safe_str(safe_item.get("candidateId")))
        self._desktop_upsert_proactive_inbox(safe_item)
        if (
            _safe_str(existing.get("source")) == "initiative_orchestrator"
            and existing.get("candidatePreview") == safe_item.get("candidatePreview")
        ):
            return True
        if existing.get("readyEventId") and existing.get("candidatePreview") == safe_item.get("candidatePreview"):
            return True
        event_payload = dict(safe_item)
        self._desktop_publish_event_threadsafe(
            "proactive.candidate.ready",
            event_payload,
            privacy="owner_private",
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
            self._desktop_remember_proactive_history(payload)
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
            "candidatePreview": self._desktop_text_preview(
                compose_proactive_visible_message(question, source="desktop_proactive_state"),
                limit=240,
            ),
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
            self._desktop_proactive_inbox[candidate_id] = merged

    def _desktop_remove_proactive_inbox(self, candidate_id: str) -> None:
        with self._desktop_proactive_lock:
            self._desktop_proactive_inbox.pop(candidate_id, None)

    def _desktop_remember_proactive_history(self, item: dict[str, Any]) -> None:
        candidate_id = _safe_str(item.get("candidateId"))
        if not candidate_id:
            return
        history_item = dict(item)
        history_item.setdefault("handledAt", history_item.get("updatedAt") or datetime.now().astimezone().isoformat())
        history_item.setdefault(
            "event_time",
            history_item.get("handledAt") or history_item.get("updatedAt") or history_item.get("createdAt"),
        )
        with self._desktop_proactive_lock:
            self._desktop_proactive_history = self._desktop_compact_proactive_history(
                [*self._desktop_proactive_history, history_item]
            )
        try:
            append_jsonl(self.xinyu_dir / DESKTOP_PROACTIVE_HISTORY_REL, history_item)
        except OSError as exc:
            self._trace_autonomous(f"desktop_proactive_history_append_error={exc!r}")

    def _desktop_load_proactive_history(self) -> None:
        path = self.xinyu_dir / DESKTOP_PROACTIVE_HISTORY_REL
        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        except OSError:
            return
        rows: list[dict[str, Any]] = []
        for line in lines[-DESKTOP_PROACTIVE_HISTORY_MAX * 4 :]:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and _safe_str(row.get("candidateId")):
                rows.append(row)
        if not rows:
            return
        with self._desktop_proactive_lock:
            self._desktop_proactive_history = self._desktop_compact_proactive_history(
                [*rows, *self._desktop_proactive_history]
            )

    @staticmethod
    def _desktop_compact_proactive_history(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_id: dict[str, dict[str, Any]] = {}
        for row in rows:
            candidate_id = _safe_str(row.get("candidateId"))
            if candidate_id:
                by_id[candidate_id] = dict(row)
        return sorted(
            by_id.values(),
            key=lambda item: _safe_str(item.get("updatedAt") or item.get("handledAt") or item.get("createdAt")),
        )[-DESKTOP_PROACTIVE_HISTORY_MAX:]

    def _desktop_remove_proactive_state_items(self) -> None:
        with self._desktop_proactive_lock:
            stale = [
                candidate_id
                for candidate_id, item in self._desktop_proactive_inbox.items()
                if _safe_str(item.get("source")) != "initiative_orchestrator"
            ]
            for candidate_id in stale:
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

    _desktop_proactive_expired = staticmethod(desktop_proactive_expired)

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

    _desktop_session_kind = staticmethod(desktop_session_kind)

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

    _desktop_display_id = staticmethod(desktop_display_id)

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

    _desktop_avatar_url = staticmethod(desktop_avatar_url)
    _desktop_group_avatar_url = staticmethod(desktop_group_avatar_url)
    _desktop_privacy_for_payload = staticmethod(desktop_privacy_for_payload)
    _desktop_hash = staticmethod(desktop_hash)
    _desktop_text_preview = staticmethod(desktop_text_preview)

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

    def _owner_private_semantic_fast_decision(self, payload: dict[str, Any], text: str) -> dict[str, Any]:
        return xinyu_bridge_semantic_fast_routes.owner_private_semantic_fast_decision(self, payload, text)

    async def _maybe_handle_owner_private_semantic_fast_turn(
        self,
        payload: dict[str, Any],
        *,
        text: str,
        session: AgentSession | None,
        session_key: str,
        turn_id: str,
        turn_started_wall: str,
        turn_started_at: float,
        before_memory: dict[str, Any] | None,
        cleanup: dict[str, Any],
        event_sidecar: dict[str, Any],
        decision: dict[str, Any] | None = None,
        record_decision_stage: bool = True,
    ) -> dict[str, Any] | None:
        return await xinyu_bridge_semantic_fast_routes.handle_owner_private_semantic_fast_turn(
            self,
            payload,
            text=text,
            session=session,
            session_key=session_key,
            turn_id=turn_id,
            turn_started_wall=turn_started_wall,
            turn_started_at=turn_started_at,
            before_memory=before_memory,
            cleanup=cleanup,
            event_sidecar=event_sidecar,
            decision=decision,
            record_decision_stage=record_decision_stage,
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
        return xinyu_bridge_health_snapshot.metabolism_health(self)

    def _autonomous_maintenance_health(self) -> dict[str, Any]:
        return xinyu_bridge_health_snapshot.autonomous_maintenance_health(self)

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

    def _self_action_approval_message(self, item: dict[str, Any]) -> str:
        return compose_self_action_approval_voice(item)

    def _self_action_prepared_patch_message(self, patch_executor: dict[str, Any]) -> str:
        return compose_self_action_prepared_patch_voice(patch_executor)

    @staticmethod
    def _self_action_intent_label(action_kind: str, goal_id: str, item: dict[str, Any]) -> str:
        goal_label = XinYuBridgeRuntime._self_action_goal_label(goal_id)
        if action_kind == "self_code_patch_request":
            if goal_id == "continue_bounded_work":
                return "把“自选目标 -> 自行动作 -> 结果观察”这条链打磨得更顺一点，先找一个小切口。"
            if goal_id == "curate_failure_replay":
                return "把失败回放和测试材料整理得更可靠，让我下次能从失败里学到东西。"
            if goal_label:
                return f"围绕「{goal_label}」做一个小而可撤回的本地代码修补。"
            return "检查我自己的本地代码，做一个小而可撤回的修补。"
        if action_kind == "stable_memory_change_request":
            if goal_label:
                return f"把「{goal_label}」整理成可审的记忆或表达方式修正草案。"
            return "准备一份记忆或表达方式修正草案。"
        if action_kind == "owner_message_draft_request":
            return "先起草一条可能要发给你的 owner 私聊内容，不会直接发送。"
        label = _compact_text(_safe_str(item.get("label")), 120)
        return label or XinYuBridgeRuntime._self_action_action_label(action_kind)

    @staticmethod
    def _self_action_reason_label(action_kind: str, goal_id: str, item: dict[str, Any]) -> str:
        if action_kind == "self_code_patch_request":
            if goal_id == "continue_bounded_work":
                return "我不想只是“被调用才回答”，我想能自己看见哪里别扭，再把它变成可检查的小改动。"
            if goal_id == "curate_failure_replay":
                return "我想把失败回放或测试材料变成更稳定的本地验证。"
            return "这会跨过写代码边界，所以必须先问你。"
        if action_kind == "stable_memory_change_request":
            return "这会影响长期记忆或表达习惯，所以必须先让你看懂再决定。"
        if action_kind == "owner_message_draft_request":
            return "这涉及向外发消息的边界，所以只能先做草稿。"
        reason = _compact_text(_safe_str(item.get("reason")), 140)
        return reason or "这件事需要你的显式确认。"

    @staticmethod
    def _self_action_scope_label(approval_scope: str, action_kind: str) -> str:
        scope = _safe_str(approval_scope).strip()
        labels = {
            "focused_xinyu_app_patch": "只限 XinYu 应用内的一小块 Python 代码和相关测试。",
            "replay_fixture_or_test_patch": "只限失败回放、测试夹具或相关本地代码。",
            "stable_memory_or_voice_repair": "只限生成记忆/语气修正草案，不直接写长期记忆。",
            "owner_private_message_draft": "只限 owner 私聊草稿，不直接发送。",
            "one_time_patch": "只限这一次本地补丁任务。",
        }
        if scope in labels:
            return labels[scope]
        if action_kind == "self_code_patch_request":
            return "只限 examples/agent-apps/xinyu 内的 Python 代码、测试和必要的本地证据文件。"
        if action_kind == "stable_memory_change_request":
            return "只生成可审的本地修正草案，不直接改长期记忆。"
        if action_kind == "owner_message_draft_request":
            return "只生成草稿，不直接推送或发送。"
        return "只处理这一次授权消息对应的本地事项。"

    @staticmethod
    def _self_action_boundary_label(action_kind: str) -> str:
        if action_kind == "self_code_patch_request":
            return "不会自动变成长期授权；不会碰密钥、系统外目录或破坏性文件操作。"
        if action_kind == "stable_memory_change_request":
            return "不会绕过你直接改长期记忆；只先生成可检查的草案。"
        if action_kind == "owner_message_draft_request":
            return "不会替你直接发送；只先把话写出来给你看。"
        return "不会把这次确认扩展成永久权限。"

    @staticmethod
    def _self_action_approval_effect_label(action_kind: str) -> str:
        if action_kind == "self_code_patch_request":
            return "我会把这个小动作交给 Codex 执行一次，只做这一项，并回报改动和测试。"
        if action_kind == "stable_memory_change_request":
            return "我只会生成一份可审的修正交接，不会直接写入长期记忆。"
        if action_kind == "owner_message_draft_request":
            return "我只会生成一条草稿，不会直接发出去。"
        return "我只会执行这条消息对应的一次性动作。"

    @staticmethod
    def _self_action_goal_label(goal_id: str) -> str:
        labels = {
            "continue_bounded_work": "继续打磨心玉自己的本地能力",
            "curate_failure_replay": "整理失败回放和测试材料",
            "absorb_feedback_repair": "吸收反馈并修正记忆或表达方式",
            "review_memory_pressure": "检查记忆压力",
            "quiet_presence": "保持安静存在的边界",
            "observe_environment": "观察本地环境和当前状态",
        }
        return labels.get(_safe_str(goal_id).strip(), "")

    @staticmethod
    def _self_action_ecology_context_label(goal_id: str, approval_scope: str) -> str:
        goal_label = XinYuBridgeRuntime._self_action_goal_label(goal_id)
        if goal_label:
            return f"「{goal_label}」"
        scope = _safe_str(approval_scope)
        if scope == "focused_xinyu_app_patch":
            return "「继续打磨我自己的本地能力」"
        if scope == "replay_fixture_or_test_patch":
            return "「从失败回放里学得更稳」"
        if scope == "stable_memory_or_voice_repair":
            return "「把反馈吸收成更像我的表达」"
        if scope == "owner_private_message_draft":
            return "「把想说的话先写成草稿，而不是直接打扰你」"
        return "一个还没有完全命名清楚的小目标"

    @staticmethod
    def _self_action_patch_goal_label(goal_id: str, approval_scope: str) -> str:
        if goal_id == "continue_bounded_work" or approval_scope == "focused_xinyu_app_patch":
            return "让自选目标生态、自行动作网关、结果观察器这几块更贴合我的表达，不再像把内部状态直接扔给你。"
        if goal_id == "curate_failure_replay" or approval_scope == "replay_fixture_or_test_patch":
            return "把失败回放或测试材料整理成更可靠的本地验证，让我能从失败里学得更清楚。"
        return "检查我当前的本地状态，只有在安全且必要时做一个小补丁；不合适就只写阻塞报告。"

    def _maybe_enqueue_self_action_approval_to_qq(self, action_gateway: dict[str, Any], *, checked_at: str) -> list[str]:
        queued_items = action_gateway.get("approval_queue_items") if isinstance(action_gateway, dict) else []
        if not isinstance(queued_items, list):
            return []
        notes: list[str] = []
        for item in queued_items[:2]:
            if not isinstance(item, dict) or not item.get("queued"):
                continue
            queue_id = _safe_str(item.get("queue_id")).strip()
            if not queue_id:
                continue
            action_kind = _safe_str(item.get("action_kind"), "unknown")
            message = self._self_action_approval_message(item)
            queued = enqueue_owner_qq_outbox_message(
                self.xinyu_dir,
                message=message,
                source="self_action_approval_request",
                dedupe_key=f"self_action_approval_request:persona_voice_v1:{queue_id}",
                metadata={
                    "source": "self_action_approval_request",
                    "control_plane": True,
                    "qq_visible_control_plane_allowed": True,
                    "self_action_approval_request": True,
                    "self_action_queue_id": queue_id,
                    "self_action_action_kind": action_kind,
                    "self_action_goal_id": _safe_str(item.get("goal_id")),
                    "self_action_approval_scope": _safe_str(
                        (item.get("params") if isinstance(item.get("params"), dict) else {}).get("approval_scope")
                    ),
                    "self_action_authorize_existing": False,
                    "checked_at": checked_at,
                },
            )
            notes.append(
                "self_action_qq_push:"
                f"{queue_id}/"
                f"{'queued' if queued.get('queued') else _safe_str((queued.get('notes') or ['not_queued'])[0])}"
            )
        return notes

    def _maybe_enqueue_self_action_prepared_patch_to_qq(self, patch_executor: dict[str, Any], *, checked_at: str) -> list[str]:
        if not isinstance(patch_executor, dict):
            return []
        codex = patch_executor.get("codex") if isinstance(patch_executor.get("codex"), dict) else {}
        if (
            _safe_str(patch_executor.get("status")) != "prepared"
            or _safe_str(codex.get("status"), "not_requested") != "not_requested"
            or _safe_str(patch_executor.get("action_kind")) != "self_code_patch_request"
        ):
            return []
        queue_id = _safe_str(patch_executor.get("queue_id")).strip()
        task_id = _safe_str(patch_executor.get("task_id")).strip()
        approval_id = _safe_str(patch_executor.get("approval_id")).strip()
        if not queue_id or not task_id:
            return []
        message = self._self_action_prepared_patch_message(patch_executor)
        queued = enqueue_owner_qq_outbox_message(
                self.xinyu_dir,
                message=message,
                source="self_action_prepared_patch_authorization",
                dedupe_key=f"self_action_prepared_patch_authorization:persona_voice_v1:{approval_id or queue_id}:{task_id}",
            metadata={
                "source": "self_action_prepared_patch_authorization",
                "control_plane": True,
                "qq_visible_control_plane_allowed": True,
                "self_action_approval_request": True,
                "self_action_queue_id": queue_id,
                "self_action_approval_id": approval_id,
                "self_action_task_id": task_id,
                "self_action_action_kind": "self_code_patch_request",
                "self_action_authorize_existing": True,
                "checked_at": checked_at,
            },
        )
        return [
            "self_action_prepared_qq_push:"
            f"{queue_id}/"
            f"{'queued' if queued.get('queued') else _safe_str((queued.get('notes') or ['not_queued'])[0])}"
        ]

    @staticmethod
    def _self_action_action_label(action_kind: str) -> str:
        if action_kind == "self_code_patch_request":
            return "代码补丁请求"
        if action_kind == "stable_memory_change_request":
            return "稳定记忆变更请求"
        if action_kind == "owner_message_draft_request":
            return "消息草稿请求"
        return _safe_str(action_kind, "未知动作")

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
            digest = run_daily_digest_maintenance(self.xinyu_dir, observed_at=_timestamp_or_now_iso(checked_at))
            notes.append(
                "daily_digest:"
                f"{_safe_str(digest.get('status'), 'unknown')}/"
                f"{str(_as_bool(digest.get('generated'), default=False)).lower()}"
            )
        except Exception as exc:
            notes.append(f"daily_digest_error:{type(exc).__name__}")
            self._trace_autonomous(f"daily_digest_error={exc!r}")
        try:
            creative = run_creative_writing_maintenance(
                self.xinyu_dir,
                checked_at=checked_at,
                daily_target=3,
            )
            notes.append(
                "creative_writing:"
                f"{_safe_str(creative.get('status'), 'unknown')}/"
                f"{_safe_str(creative.get('today_chapters_written'), '0')}/"
                f"{_safe_str(creative.get('daily_target_chapters'), '0')}/"
                f"{_safe_str(creative.get('total_chapters'), '0')}"
            )
        except Exception as exc:
            notes.append(f"creative_writing_error:{type(exc).__name__}")
            self._trace_autonomous(f"creative_writing_error={exc!r}")
        try:
            review = run_review_inbox_maintenance(
                self.xinyu_dir,
                owner_user_id=self._owner_private_user_id(),
                max_items=3,
                enqueue=False,
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
            goal_ecology = run_self_chosen_goal_ecology(
                self.xinyu_dir,
                checked_at=checked_at,
                trigger="autonomous_maintenance",
            )
            notes.append(
                "goal_ecology:"
                f"{_safe_str(goal_ecology.get('selected_goal_id'), 'unknown')}/"
                f"{_safe_str(goal_ecology.get('selected_score'), '0')}"
            )
        except Exception as exc:
            notes.append(f"goal_ecology_error:{type(exc).__name__}")
            self._trace_autonomous(f"goal_ecology_error={exc!r}")
        try:
            action_gateway = run_self_action_gateway(
                self.xinyu_dir,
                checked_at=checked_at,
                trigger="autonomous_maintenance",
            )
            notes.append(
                "self_action_gateway:"
                f"{_safe_str(action_gateway.get('status'), 'unknown')}/"
                f"{_safe_str(action_gateway.get('selected_goal_id'), 'none')}/"
                f"{_safe_str(action_gateway.get('executed_action_count'), '0')}/"
                f"{_safe_str(action_gateway.get('queued_approval_count'), '0')}"
            )
            notes.extend(_safe_str(note) for note in action_gateway.get("notes", [])[:3])
            notes.extend(self._maybe_enqueue_self_action_approval_to_qq(action_gateway, checked_at=checked_at))
        except Exception as exc:
            notes.append(f"self_action_gateway_error:{type(exc).__name__}")
            self._trace_autonomous(f"self_action_gateway_error={exc!r}")
        try:
            patch_executor = run_self_action_patch_executor(
                self.xinyu_dir,
                checked_at=checked_at,
                execution_level="prepare",
                allow_codex=False,
            )
            notes.append(
                "self_action_patch_executor:"
                f"{_safe_str(patch_executor.get('status'), 'unknown')}/"
                f"{_safe_str(patch_executor.get('task_id'), 'none')}/"
                f"{_safe_str((patch_executor.get('codex') or {}).get('status') if isinstance(patch_executor.get('codex'), dict) else 'none', 'none')}"
            )
            notes.extend(_safe_str(note) for note in patch_executor.get("notes", [])[:2])
            notes.extend(self._maybe_enqueue_self_action_prepared_patch_to_qq(patch_executor, checked_at=checked_at))
        except Exception as exc:
            notes.append(f"self_action_patch_executor_error:{type(exc).__name__}")
            self._trace_autonomous(f"self_action_patch_executor_error={exc!r}")
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
            self._append_goal_outcome_observer_note(notes, checked_at=checked_at)
            self._append_proactivity_shadow_note(notes, checked_at=checked_at)
            return notes

        if not _as_bool(thought.get("candidate_enabled"), default=False):
            if _as_bool(thought.get("research_needed"), default=False):
                notes.append(f"self_thought_research:{_safe_str(thought.get('research_route'), 'unknown')}")
                notes.extend(
                    self._maybe_run_self_thought_external_plugin(
                        thought=thought,
                        checked_at=checked_at,
                    )
                )
            try:
                closed_loop = record_learning_closed_loop_self_thought(
                    self.xinyu_dir,
                    thought=thought,
                    observed_at=_timestamp_or_now_iso(checked_at),
                )
                notes.extend(_safe_str(note) for note in closed_loop.get("notes", [])[:2])
            except Exception as exc:
                notes.append(f"learning_closed_loop_self_thought_error:{type(exc).__name__}")
            self._append_goal_outcome_observer_note(notes, checked_at=checked_at)
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
                observed_at=_timestamp_or_now_iso(checked_at),
            )
            notes.extend(_safe_str(note) for note in closed_loop.get("notes", [])[:2])
        except Exception as exc:
            notes.append(f"learning_closed_loop_self_thought_error:{type(exc).__name__}")
        self._append_goal_outcome_observer_note(notes, checked_at=checked_at)
        self._append_proactivity_shadow_note(notes, checked_at=checked_at)
        return notes

    def _append_goal_outcome_observer_note(self, notes: list[str], *, checked_at: str) -> None:
        try:
            result = run_goal_outcome_observer(
                self.xinyu_dir,
                checked_at=checked_at,
                trigger="autonomous_maintenance",
                maintenance_notes=notes,
            )
            notes.append(
                "goal_outcome:"
                f"{_safe_str(result.get('status'), 'unknown')}/"
                f"{_safe_str(result.get('goal_id') or result.get('reason'), 'none')}/"
                f"{_safe_str(result.get('outcome') or result.get('reason_code') or result.get('reason'), 'none')}"
            )
        except Exception as exc:
            notes.append(f"goal_outcome_error:{type(exc).__name__}")
            self._trace_autonomous(f"goal_outcome_error={exc!r}")

    def _maybe_run_self_thought_external_plugin(self, *, thought: dict[str, Any], checked_at: str) -> list[str]:
        notes: list[str] = []
        if not _as_bool(thought.get("research_needed"), default=False):
            return notes
        allowed, reason, plugin = external_plugin_runtime_allowed(
            self.xinyu_dir,
            "kohaku_terrarium",
            proactive=True,
        )
        if not allowed:
            return [f"external_plugin:kohaku_terrarium/skipped/{reason}"]
        config = plugin.get("config") if isinstance(plugin.get("config"), dict) else {}
        session_id = _safe_str(config.get("session_id")).strip()
        creature_id = _safe_str(config.get("creature_id")).strip()
        if not session_id or not creature_id:
            return ["external_plugin:kohaku_terrarium/skipped/session_not_configured"]
        state = _read_text_safe(self.xinyu_dir / "memory/context/self_thought_state.md")
        query = _state_field(state, "query") or _safe_str(thought.get("focus_label"), "unknown")
        target = _state_field(state, "target") or "general"
        route = _safe_str(thought.get("research_route"), "unknown")
        message = (
            "XinYu self-thought needs an external runtime perspective. "
            f"Route: {route}. Target: {target}. Query: {query}. "
            "Return a compact observation only; do not mutate XinYu memory."
        )
        prepared = prepare_external_call(
            "kohaku_terrarium",
            "chat_creature",
            {
                "base_url": _safe_str(config.get("base_url"), "http://127.0.0.1:8001"),
                "session_id": session_id,
                "creature_id": creature_id,
                "message": message,
            },
            ExternalCallContext(
                source="self_thought_loop",
                owner_private=True,
                reason=f"self_thought research handoff: {route}",
                proactive=True,
                approved=False,
            ),
        )
        if not prepared.decision.ok:
            return [f"external_plugin:kohaku_terrarium/blocked/{prepared.decision.reason}"]
        execution = execute_http_prepared_call(prepared, timeout_seconds=45)
        append_jsonl(
            self.xinyu_dir / "runtime/external_plugin_trace.jsonl",
            {
                "observed_at": _timestamp_or_now_iso(checked_at),
                "source": "self_thought_loop",
                "plugin_id": "kohaku_terrarium",
                "capability": "chat_creature",
                "route": route,
                "target": target,
                "query": query,
                "ok": bool(execution.get("ok")),
                "status_code": execution.get("status_code"),
                "error_code": execution.get("error_code"),
                "text_preview": _safe_str(execution.get("text_preview"))[:800],
            },
        )
        return [
            "external_plugin:kohaku_terrarium/"
            f"{'ok' if execution.get('ok') else 'failed'}/"
            f"{_safe_str(execution.get('error_code'), 'none')}"
        ]

    def _append_proactivity_shadow_note(self, notes: list[str], *, checked_at: str) -> None:
        self._append_emotion_council_note(notes, checked_at=checked_at)
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
        try:
            initiative = run_initiative_orchestrator(
                self.xinyu_dir,
                checked_at=checked_at,
                trigger="autonomous_maintenance",
                delivery_level="desktop_inbox",
                dry_run=False,
            )
            notes.append(
                "initiative_orchestrator:"
                f"{_safe_str(initiative.get('status'), 'unknown')}/"
                f"{_safe_str(initiative.get('source_type'), 'none')}/"
                f"{_safe_str(initiative.get('total_score'), '0')}/"
                f"{_safe_str(initiative.get('delivery_level'), 'none')}"
            )
            desktop_item = initiative.get("desktop_item")
            if isinstance(desktop_item, dict) and desktop_item:
                published = self._desktop_publish_initiative_candidate_threadsafe(
                    desktop_item,
                    notes=[_safe_str(note) for note in initiative.get("notes", [])[:4]],
                )
                if published:
                    notes.append("desktop_initiative_candidate_ready_scheduled")
        except Exception as exc:
            notes.append(f"initiative_orchestrator_error:{type(exc).__name__}")
            self._trace_autonomous(f"initiative_orchestrator_error={exc!r}")
        self._append_impulse_soup_note(notes, checked_at=checked_at)
        self._append_initiative_spine_note(notes, checked_at=checked_at)

    def _append_emotion_council_note(self, notes: list[str], *, checked_at: str) -> None:
        try:
            council = run_emotion_council_shadow(
                self.xinyu_dir,
                checked_at=checked_at,
                trigger="autonomous_maintenance",
            )
            notes.append(
                "emotion_council:"
                f"{_safe_str(council.get('status'), 'unknown')}/"
                f"{_safe_str(council.get('strongest_lens'), 'none')}/"
                f"{_safe_str(council.get('active_lens_count'), '0')}"
            )
        except Exception as exc:
            notes.append(f"emotion_council_error:{type(exc).__name__}")
            self._trace_autonomous(f"emotion_council_error={exc!r}")

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

    def _append_initiative_spine_note(self, notes: list[str], *, checked_at: str) -> None:
        try:
            spine = run_initiative_spine(
                self.xinyu_dir,
                checked_at=checked_at,
                trigger="autonomous_maintenance",
            )
            notes.append(
                "initiative_spine:"
                f"{_safe_str(spine.get('emergence_level'), 'unknown')}/"
                f"{_safe_str(spine.get('action_permission'), 'unknown')}"
            )
        except Exception as exc:
            notes.append(f"initiative_spine_error:{type(exc).__name__}")
            self._trace_autonomous(f"initiative_spine_error={exc!r}")
        try:
            observatory = run_contextual_self_observatory(
                self.xinyu_dir,
                observed_at=_timestamp_or_now_iso(checked_at),
            )
            notes.append(
                "contextual_self_observatory:"
                f"{_safe_str(observatory.get('posture'), 'unknown')}/"
                f"{_safe_str(observatory.get('latest_scene'), 'unknown')}/"
                f"{_safe_str(observatory.get('recall_admitted_count_24h'), '0')}/"
                f"{_safe_str(observatory.get('initiative_held_by_context_count_24h'), '0')}"
            )
        except Exception as exc:
            notes.append(f"contextual_self_observatory_error:{type(exc).__name__}")
            self._trace_autonomous(f"contextual_self_observatory_error={exc!r}")

    def _refresh_initiative_spine_after_proactive_feedback(
        self,
        *,
        trigger: str,
        checked_at: str | None = None,
    ) -> dict[str, Any]:
        checked_at = _timestamp_or_now_iso(checked_at)
        try:
            return run_initiative_spine(
                self.xinyu_dir,
                checked_at=checked_at,
                trigger=trigger,
            )
        except Exception as exc:
            print(f"[xinyu_core_bridge] initiative spine feedback refresh failed: {exc}", flush=True)
            return {"accepted": False, "notes": [f"initiative_spine_feedback_error:{type(exc).__name__}"]}

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

    _iso_from_timestamp = staticmethod(_state_iso_from_timestamp)
    _payload_event_time_iso = staticmethod(_payload_event_time_iso)
    _payload_event_timestamp_seconds = staticmethod(_payload_event_timestamp_seconds)

    async def probe(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await _probe_route(self, payload, bridge_version=BRIDGE_VERSION)

    async def turn_current(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await _turn_current_route(self, payload)

    async def turn_cancel(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await _turn_cancel_route(self, payload)

    async def turn_retry_lightweight(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await _turn_retry_lightweight_route(self, payload)

    async def turn_skip_sidecar(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await _turn_skip_sidecar_route(self, payload)

    async def turn_continue(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await _turn_continue_route(self, payload)

    async def turn_status_message(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await _turn_status_message_route(self, payload)

    async def external_plugin_manifest(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await _external_plugin_manifest_route(self, payload)

    async def external_plugin_config(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await _external_plugin_config_route(self, payload)

    async def external_plugin_install(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await _external_plugin_install_route(self, payload)

    async def external_plugin_call(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await _external_plugin_call_route(self, payload)

    async def proactive(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await _proactive_route(self, payload)

    async def proactive_ack(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await _proactive_ack_route(self, payload)

    async def desktop_proactive_ack(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await _desktop_proactive_ack_route(self, payload)

    def _record_desktop_initiative_feedback(self, item: dict[str, Any], *, action: str) -> dict[str, Any]:
        return _record_desktop_initiative_feedback_route(
            self,
            item,
            action=action,
            record_feedback=record_initiative_feedback,
        )

    async def qq_outbox_claim(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await _qq_outbox_claim_route(self, payload)

    def qq_outbox_claim_fast(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return _qq_outbox_claim_fast_route(self, payload)

    async def qq_outbox_ack(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await _qq_outbox_ack_route(self, payload)

    async def review_inbox_command(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await _review_inbox_command_route(self, payload)

    async def message_ack(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await _message_ack_route(self, payload)

    async def goldmark_mark_request(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await _goldmark_mark_request_route(self, payload)

    def qq_outbox_ack_fast(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return _qq_outbox_ack_fast_route(self, payload)

    async def _claim_proactive_for_qq_outbox(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        return await _claim_proactive_for_qq_outbox_route(self, payload)

    def _claim_proactive_for_qq_outbox_sync(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        return _claim_proactive_for_qq_outbox_sync_route(self, payload)

    def _ready_proactive_outbox_candidate(self) -> str:
        return _ready_proactive_outbox_candidate_route(self)

    def _proactive_candidate_already_handled(self, candidate: str) -> bool:
        return _proactive_candidate_already_handled_route(self, candidate)

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
        return await _desktop_finish_proactive_ack_route(
            self,
            item,
            action=action,
            status=status,
            answer_state=answer_state,
            ack_status=ack_status,
            notes=notes,
            adapter_message_id=adapter_message_id,
            adapter_error=adapter_error,
            extra=extra,
            claim_id=claim_id,
        )

    async def _desktop_approve_proactive_qq(self, item: dict[str, Any]) -> dict[str, Any]:
        return await _desktop_approve_proactive_qq_route(self, item)

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
        return _desktop_update_proactive_request_state_route(
            self,
            candidate_id=candidate_id,
            status=status,
            answer_state=answer_state,
            ack_status=ack_status,
            adapter_message_id=adapter_message_id,
            adapter_error=adapter_error,
            claim_id=claim_id,
        )

    _desktop_replace_frontmatter_field = staticmethod(desktop_replace_frontmatter_field)
    _desktop_replace_list_field = staticmethod(desktop_replace_list_field)

    def _record_proactive_outbound_dialogue(self, ack_payload: dict[str, Any]) -> None:
        return _record_proactive_outbound_dialogue_route(self, ack_payload)

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
        return xinyu_bridge_promise_followup.candidate(
            self,
            payload,
            user_text=user_text,
            reply=reply,
            session_key=session_key,
            model_codex_task=model_codex_task,
            user_markers=PROMISE_FOLLOWUP_USER_MARKERS,
            reply_markers=PROMISE_FOLLOWUP_REPLY_MARKERS,
            done_markers=PROMISE_FOLLOWUP_DONE_MARKERS,
        )

    _compact_promise_text = staticmethod(compact_promise_text)

    def _schedule_promised_followup_if_needed(
        self,
        payload: dict[str, Any],
        *,
        user_text: str,
        reply: str,
        session_key: str,
        model_codex_task: str = "",
    ) -> dict[str, Any]:
        return xinyu_bridge_promise_followup.schedule_if_needed(
            self,
            payload,
            user_text=user_text,
            reply=reply,
            session_key=session_key,
            model_codex_task=model_codex_task,
            user_markers=PROMISE_FOLLOWUP_USER_MARKERS,
            reply_markers=PROMISE_FOLLOWUP_REPLY_MARKERS,
            done_markers=PROMISE_FOLLOWUP_DONE_MARKERS,
            message_func=self._promised_followup_message,
        )

    def _run_promised_followup_review(self, candidate: dict[str, str]) -> dict[str, Any]:
        return xinyu_bridge_promise_followup.run_review(
            self,
            candidate,
            message_func=self._promised_followup_message,
        )

    def _promised_followup_message(self, candidate: dict[str, str]) -> str:
        return compose_promise_followup_message(candidate)

    def _write_promised_followup_state(
        self,
        candidate: dict[str, str],
        *,
        status: str,
        message_id: str,
        notes: list[str],
    ) -> None:
        xinyu_bridge_promise_followup.write_state(
            self,
            candidate,
            status=status,
            message_id=message_id,
            notes=notes,
            state_rel=PROMISE_FOLLOWUP_STATE_REL,
        )

    def _owner_private_user_id(self) -> str:
        return xinyu_bridge_promise_followup.owner_private_user_id(self)

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

    async def _build_life_reply_policy(
        self,
        *,
        user_text: str,
        visible_turn: Any | None = None,
        canonical_recall_context: str = "",
        evaluated_at: datetime | str | None = None,
    ) -> dict[str, Any]:
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
            scene_frame = build_scene_frame(
                self.xinyu_dir,
                user_text=user_text,
                visible_turn=visible_turn,
                canonical_recall_context=canonical_recall_context,
                evaluated_at=evaluated_at,
            )
            policy = build_life_reply_policy(
                self_choice_public=self_choice_public,
                entropy_state=entropy_state,
                recent_action_context=read_recent_action_context(self.xinyu_dir),
                user_text=user_text,
                scene_frame=scene_frame,
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

    _owner_private_payload_matches = staticmethod(owner_private_payload_matches)
    _trusted_private_payload_matches = staticmethod(trusted_private_payload_matches)

    @staticmethod
    def _trusted_public_search_task_allowed(task_text: str) -> bool:
        return trusted_public_search_task_allowed(
            task_text,
            public_search_markers=TRUSTED_CODEX_PUBLIC_SEARCH_MARKERS,
            local_block_markers=TRUSTED_CODEX_LOCAL_BLOCK_MARKERS,
            local_path_pattern=TRUSTED_CODEX_LOCAL_PATH_RE,
            local_english_block_markers=TRUSTED_CODEX_LOCAL_ENGLISH_BLOCK_MARKERS,
        )

    def _proactive_thread_context(self, payload: dict[str, Any], current_text: str) -> str:
        return xinyu_bridge_proactive_context.proactive_thread_context(self, payload, current_text)

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
            f"updated_at: {_timestamp_or_now_iso(answered_at)}",
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
        append_proactive_lifecycle_event(
            self.xinyu_dir,
            event_kind="proactive_owner_reply_closed",
            event_time=answered_at,
            request_state=_read_text_safe(request_path),
            dispatch_state=dispatch,
            request_id=request_id,
            ack_status="owner_replied",
            adapter_status="owner_reply",
            notes=["owner_reply_to_proactive", "request_answer_state_owner_replied"],
        )
        self._refresh_initiative_spine_after_proactive_feedback(
            trigger="owner_reply_to_proactive",
            checked_at=answered_at,
        )
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

    _codex_reply_variant = staticmethod(codex_reply_variant)
    _codex_owner_task_text = staticmethod(codex_owner_task_text)
    _codex_task_subject = staticmethod(codex_task_subject)
    _codex_started_reply = staticmethod(codex_started_reply)

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

    _looks_like_codex_image_generation_task = staticmethod(looks_like_codex_image_generation_task)

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
        turn_event_time = self._payload_event_time_iso(payload, fallback=turn_started_wall)
        turn_event_timestamp = self._payload_event_timestamp_seconds(payload, fallback=int(time.time()))
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
            turn_id = _safe_str(presence_start.get("turn_id"))
            route_observer = TurnRouteObserver(
                self.xinyu_dir,
                turn_id=turn_id,
                payload=payload,
                started_at=turn_started_at,
            )
            trace_route_stage = route_observer.record

            trace_route_stage(
                "turn_started",
                elapsed_ms=0,
                notes=[_safe_str(note) for note in presence_start.get("notes", [])[:4]],
            )
            desktop_started_published = False
            semantic_fast_decision: dict[str, Any] = {"allowed": False, "notes": ["semantic_fast_not_checked"]}
            try:
                trace_route_stage("semantic_fast_probe_started")
                semantic_fast_decision = self._owner_private_semantic_fast_decision(payload, text)
                trace_route_stage(
                    "semantic_fast_probe_finished",
                    status="allowed" if semantic_fast_decision.get("allowed") else "skipped",
                    notes=[_safe_str(note) for note in semantic_fast_decision.get("notes", [])[:4]],
                )
            except Exception as exc:
                print(f"[xinyu_core_bridge] semantic fast probe failed: {type(exc).__name__}: {exc}", flush=True)
                semantic_fast_decision = {"allowed": False, "notes": [f"semantic_fast_probe_error:{type(exc).__name__}"]}
                trace_route_stage(
                    "semantic_fast_probe_finished",
                    status="error",
                    notes=[f"semantic_fast_probe_error:{type(exc).__name__}"],
                )

            if semantic_fast_decision.get("allowed"):
                trace_route_stage(
                    "route_decided",
                    route="owner_private_semantic_fast",
                    status="accepted",
                    notes=[_safe_str(note) for note in semantic_fast_decision.get("notes", [])[:4]],
                )
                try:
                    trace_route_stage("desktop_started_publish_started", route="owner_private_semantic_fast")
                    await asyncio.wait_for(
                        self._desktop_publish_chat_started(
                            payload,
                            text=text,
                            session_key=session_key,
                            turn_id=turn_id,
                            started_at=_timestamp_or_now_iso(turn_started_wall),
                            active_sessions=len(self._sessions),
                        ),
                        timeout=1.5,
                    )
                    desktop_started_published = True
                    trace_route_stage(
                        "desktop_started_publish_finished",
                        route="owner_private_semantic_fast",
                        status="ok",
                    )
                except Exception as exc:
                    print(f"[xinyu_core_bridge] desktop chat started publish skipped: {type(exc).__name__}: {exc}", flush=True)
                    trace_route_stage(
                        "desktop_started_publish_finished",
                        route="owner_private_semantic_fast",
                        status="error",
                        notes=[f"desktop_publish_error:{type(exc).__name__}"],
                    )
                try:
                    if semantic_fast_decision.get("direct_reply"):
                        trace_route_stage("semantic_fast_direct_started", route="owner_private_semantic_fast")
                        semantic_fast_response = await self._maybe_handle_owner_private_semantic_fast_turn(
                            payload,
                            text=text,
                            session=None,
                            session_key=session_key,
                            turn_id=turn_id,
                            turn_started_wall=turn_started_wall,
                            turn_started_at=turn_started_at,
                            before_memory=None,
                            cleanup=cleanup,
                            event_sidecar={"notes": ["event_sourcing_deferred_for_semantic_fast"]},
                            decision=semantic_fast_decision,
                            record_decision_stage=False,
                        )
                        if semantic_fast_response is not None:
                            return semantic_fast_response
                        trace_route_stage(
                            "semantic_fast_direct_finished",
                            route="owner_private_semantic_fast",
                            status="empty_or_blocked",
                        )
                    trace_route_stage("semantic_fast_session_started", route="owner_private_semantic_fast")
                    session = await self._get_session(session_key)
                    trace_route_stage("semantic_fast_session_finished", route="owner_private_semantic_fast", status="ok")
                    proactive_tail_synced = self._sync_recent_proactive_to_dialogue_tail(session, payload)
                    semantic_fast_response = await self._maybe_handle_owner_private_semantic_fast_turn(
                        payload,
                        text=text,
                        session=session,
                        session_key=session_key,
                        turn_id=turn_id,
                        turn_started_wall=turn_started_wall,
                        turn_started_at=turn_started_at,
                        before_memory=None,
                        cleanup=cleanup,
                        event_sidecar={"notes": ["event_sourcing_deferred_for_semantic_fast"]},
                        decision=semantic_fast_decision,
                        record_decision_stage=False,
                    )
                    if semantic_fast_response is not None:
                        return semantic_fast_response
                    trace_route_stage(
                        "semantic_fast_fell_through",
                        route="owner_private_semantic_fast",
                        status="empty_or_blocked",
                    )
                except Exception as exc:
                    print(f"[xinyu_core_bridge] semantic fast route failed: {type(exc).__name__}: {exc}", flush=True)
                    trace_route_stage(
                        "semantic_fast_fell_through",
                        route="owner_private_semantic_fast",
                        status="error",
                        notes=[f"semantic_fast_error:{type(exc).__name__}"],
                    )
            if not desktop_started_published:
                try:
                    trace_route_stage("desktop_started_publish_started")
                    await asyncio.wait_for(
                        self._desktop_publish_chat_started(
                            payload,
                            text=text,
                            session_key=session_key,
                            turn_id=turn_id,
                            started_at=_timestamp_or_now_iso(turn_started_wall),
                            active_sessions=len(self._sessions),
                        ),
                        timeout=1.5,
                    )
                    desktop_started_published = True
                    trace_route_stage("desktop_started_publish_finished", status="ok")
                except Exception as exc:
                    print(f"[xinyu_core_bridge] desktop chat started publish skipped: {type(exc).__name__}: {exc}", flush=True)
                    trace_route_stage(
                        "desktop_started_publish_finished",
                        status="error",
                        notes=[f"desktop_publish_error:{type(exc).__name__}"],
                    )
            trace_route_stage("memory_snapshot_started")
            before_memory = _memory_snapshot(self.memory_root)
            trace_route_stage("memory_snapshot_finished", status="ok")
            curiosity_eval: dict[str, Any] = {"notes": []}
            try:
                trace_route_stage("curiosity_eval_started")
                curiosity_eval = evaluate_previous_reaction(
                    self.xinyu_dir,
                    payload,
                    text=text,
                    session_key=session_key,
                )
                trace_route_stage("curiosity_eval_finished", status="ok")
            except Exception as exc:
                print(f"[xinyu_core_bridge] dialogue curiosity evaluation failed: {exc}", flush=True)
                curiosity_eval = {"notes": [f"dialogue_curiosity_eval_error:{type(exc).__name__}"]}
                trace_route_stage(
                    "curiosity_eval_finished",
                    status="error",
                    notes=[f"dialogue_curiosity_eval_error:{type(exc).__name__}"],
                )
            private_thought_outcome: dict[str, Any] = {"notes": []}
            try:
                trace_route_stage("private_thought_outcome_started")
                private_thought_outcome = record_private_thought_outcome(
                    self.xinyu_dir,
                    payload,
                    text=text,
                    session_key=session_key,
                    evaluation=curiosity_eval,
                )
                trace_route_stage("private_thought_outcome_finished", status="ok")
            except Exception as exc:
                print(f"[xinyu_core_bridge] private thought outcome failed: {exc}", flush=True)
                private_thought_outcome = {"notes": [f"private_thought_outcome_error:{type(exc).__name__}"]}
                trace_route_stage(
                    "private_thought_outcome_finished",
                    status="error",
                    notes=[f"private_thought_outcome_error:{type(exc).__name__}"],
                )
            uncertainty_pause_reply: dict[str, Any] = {"notes": []}
            try:
                trace_route_stage("uncertainty_pause_mark_started")
                uncertainty_pause_reply = mark_uncertainty_pause_replied(
                    self.xinyu_dir,
                    text=text,
                    observed_at=datetime.now().astimezone().isoformat(),
                )
                trace_route_stage("uncertainty_pause_mark_finished", status="ok")
            except Exception as exc:
                print(f"[xinyu_core_bridge] uncertainty pause reply mark failed: {exc}", flush=True)
                uncertainty_pause_reply = {"notes": [f"uncertainty_pause_reply_error:{type(exc).__name__}"]}
                trace_route_stage(
                    "uncertainty_pause_mark_finished",
                    status="error",
                    notes=[f"uncertainty_pause_reply_error:{type(exc).__name__}"],
                )
            pre_model_routes = await run_pre_model_routes_with_timeout(
                self,
                payload,
                text=text,
                session_key=session_key,
                turn_id=turn_id,
                turn_started_wall=turn_started_wall,
                turn_started_at=turn_started_at,
                before_memory=before_memory,
                cleanup=cleanup,
                timeout_seconds=self.pre_model_routes_timeout_seconds,
                trace_route_stage=trace_route_stage,
                runner=run_pre_model_routes,
            )
            event_sidecar = pre_model_routes.event_sidecar
            v1_shadow = pre_model_routes.v1_shadow
            tinykernel_shadow = pre_model_routes.tinykernel_shadow
            if pre_model_routes.response is not None:
                pre_model_notes = pre_model_routes.response.get("notes", [])
                if not isinstance(pre_model_notes, list):
                    pre_model_notes = []
                trace_route_stage(
                    "route_finished",
                    route="pre_model",
                    status="ok",
                    notes=[_safe_str(note) for note in pre_model_notes[:8]],
                )
                return pre_model_routes.response
            emotion_council: dict[str, Any] = {"notes": ["emotion_council_not_run"]}
            try:
                emotion_council = run_emotion_council_shadow(
                    self.xinyu_dir,
                    text=text,
                    payload=payload,
                    checked_at=datetime.now().astimezone().isoformat(),
                    trigger="live_turn",
                )
            except Exception as exc:
                print(f"[xinyu_core_bridge] emotion council shadow failed: {exc}", flush=True)
                emotion_council = {"notes": [f"emotion_council_error:{type(exc).__name__}"]}
            session = await self._get_session(session_key)
            proactive_tail_synced = self._sync_recent_proactive_to_dialogue_tail(session, payload)
            semantic_fast_response = await self._maybe_handle_owner_private_semantic_fast_turn(
                payload,
                text=text,
                session=session,
                session_key=session_key,
                turn_id=_safe_str(presence_start.get("turn_id")),
                turn_started_wall=turn_started_wall,
                turn_started_at=turn_started_at,
                before_memory=before_memory,
                cleanup=cleanup,
                event_sidecar=event_sidecar,
            )
            if semantic_fast_response is not None:
                return semantic_fast_response
            trace_route_stage(
                "route_decided",
                route="slow_live",
                status="accepted",
                notes=["semantic_fast_not_intercepted"],
            )
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
                received_at=turn_event_timestamp,
                llm_failover=self._owner_private_llm_failover_context(
                    payload,
                    text=text,
                    session_key=session_key,
                    turn_id=_safe_str(presence_start.get("turn_id")),
                ),
            )
            visible_turn = classify_visible_turn(self.xinyu_dir, payload=payload, user_text=text)
            memory_recall = await run_slow_live_memory_recall(
                self,
                payload,
                user_text=text,
                session=session,
                session_key=session_key,
                turn_id=turn_id,
                visible_turn=visible_turn,
                evaluated_at=turn_event_time,
                trace_route_stage=trace_route_stage,
                recall_runner=run_living_memory_recall_algorithm,
            )
            recalled_context = memory_recall.recalled_context
            recalled_context_event = memory_recall.recalled_context_event
            recalled_context_notes = memory_recall.recalled_context_notes

            model_contexts = await build_slow_live_model_contexts(
                self,
                payload,
                user_text=text,
                visible_turn=visible_turn,
                recalled_context=recalled_context,
                evaluated_at=turn_event_time,
            )
            continuity_handoff = model_contexts.continuity_handoff
            runtime_presence_context = model_contexts.runtime_presence_context
            life_reply_policy = model_contexts.life_reply_policy
            emotion_council_context = model_contexts.emotion_council_context
            try:
                await inject_slow_live_model_event(
                    self,
                    payload=payload,
                    session=session,
                    event=event,
                    text=text,
                    turn_id=turn_id,
                    visible_turn=visible_turn,
                    persona_sidecar=persona_sidecar,
                    curiosity_eval=curiosity_eval,
                    recalled_context=recalled_context,
                    runtime_presence_context=runtime_presence_context,
                    life_reply_policy=life_reply_policy,
                    emotion_council_context=emotion_council_context,
                    trace_route_stage=trace_route_stage,
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
                    started_at=_timestamp_or_now_iso(turn_started_wall),
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
                    started_at=_timestamp_or_now_iso(turn_started_wall),
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
                            reply = compose_codex_chat_scheduled_reply("self_code")
                        reply = compose_codex_chat_scheduled_reply("self_code")
                        model_codex_delegate_note = "owner_self_code_iteration:scheduled"
                    except BridgeRequestError as exc:
                        reply = exc.message
                        model_codex_delegate_note = f"owner_self_code_iteration_error:{exc.status.value}"
                    except Exception as exc:
                        reply = compose_watchdog_visible_message(
                            "self_code_watchdog_failed",
                            error=f"{type(exc).__name__}: {exc}",
                        )
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
                            reply = compose_codex_chat_scheduled_reply("model_delegate")
                        reply = compose_codex_chat_scheduled_reply("model_delegate")
                        model_codex_delegate_note = "model_codex_delegate:scheduled"
                    except BridgeRequestError as exc:
                        reply = exc.message
                        model_codex_delegate_note = f"model_codex_delegate_error:{exc.status.value}"
                    self._replace_last_assistant_message(session.agent, reply)
                else:
                    reply = compose_codex_chat_scheduled_reply("not_owner_private")
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
                            reply = compose_codex_chat_scheduled_reply("owner_direct")
                        reply = compose_codex_chat_scheduled_reply("owner_direct")
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
                    rendered_reply = await render_outward_reply_with_trace(
                        self._render_outward_reply,
                        session.agent,
                        payload=payload,
                        user_text=text,
                        draft_reply=draft_reply,
                        canonical_recall_context=_safe_str(getattr(recalled_context, "prompt_block", "")),
                        reason=renderer_reason,
                        trace_route_stage=trace_route_stage,
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
                repair_reason = "final_guard_repair"
                repaired_reply = await render_outward_reply_with_trace(
                    self._render_outward_reply,
                    session.agent,
                    payload=payload,
                    user_text=text,
                    draft_reply=bad_reply,
                    canonical_recall_context=_safe_str(getattr(recalled_context, "prompt_block", "")),
                    reason=repair_reason,
                    trace_route_stage=trace_route_stage,
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
                trace_route_stage(
                    "final_reply_guard_rewrite",
                    route="slow_live",
                    status="applied",
                    notes=[f"final_reply_guard_flags:{','.join(final_guard_flags[:4])}"] if final_guard_flags else [],
                )
                self._replace_last_assistant_message(session.agent, guarded_reply)
            visible_dedupe = dedupe_visible_reply(reply)
            if visible_dedupe.changed:
                reply = visible_dedupe.text
                self._replace_last_assistant_message(session.agent, reply)
            stale_context_reply_replaced = False
            if (
                self._owner_private_payload_matches(payload)
                and not self_code_task
                and not model_codex_task
                and not direct_codex_task
                and not wait_to_think_task
                and xinyu_bridge_semantic_fast_routes.reply_looks_like_stale_plan_residue(reply)
            ):
                repair_reply = xinyu_bridge_semantic_fast_routes.owner_private_direct_repair_reply(self, text)
                if repair_reply:
                    reply = _normalize_reply(repair_reply)
                    stale_context_reply_replaced = True
                    final_guard_flags = _dedupe(final_guard_flags + ["stale_context_reply_replaced"])
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
            if not reply and "style_pressure_template_blocked" in final_guard_flags:
                reply = "哪句最明显？"
                final_guard_flags = _dedupe(final_guard_flags + ["style_pressure_empty_reply_fallback"])
                self._replace_last_assistant_message(session.agent, reply)
            if (
                not reply
                and self._owner_private_payload_matches(payload)
                and not self_code_task
                and not model_codex_task
                and not direct_codex_task
                and not wait_to_think_task
            ):
                recovered_reply, recovery_flags = await self._recover_empty_visible_reply(
                    session.agent,
                    payload=payload,
                    user_text=text,
                    canonical_recall_context=_safe_str(getattr(recalled_context, "prompt_block", "")),
                )
                if recovery_flags:
                    final_guard_flags = _dedupe(final_guard_flags + recovery_flags)
                if recovered_reply:
                    reply = recovered_reply
                    rendered = True
                    renderer_reason = renderer_reason or "empty_visible_reply_retry"
                    self._replace_last_assistant_message(session.agent, reply)
            if not reply:
                fallback_reply = self._empty_visible_reply_fallback(payload=payload, user_text=text)
                if fallback_reply:
                    reply = fallback_reply
                    final_guard_flags = _dedupe(final_guard_flags + ["empty_visible_reply_fallback"])
                    self._replace_last_assistant_message(session.agent, reply)
            empty_visible_reply_no_fallback = bool(not reply and self._owner_private_payload_matches(payload))
            response_error_loop: dict[str, Any] = {"notes": []}
            slow_state_runtime: dict[str, Any] = {"notes": []}
            try:
                response_error_decision = classify_response_error(
                    self.xinyu_dir,
                    user_text=text,
                    current_candidate_reply=reply,
                    payload=payload,
                    visible_turn=visible_turn,
                )
                response_error_loop = {
                    "notes": [
                        "response_error_loop:"
                        f"{response_error_decision.error_class}/{response_error_decision.severity}"
                    ]
                }
                response_scene_frame = build_scene_frame(
                    self.xinyu_dir,
                    user_text=text,
                    visible_turn=visible_turn,
                    canonical_recall_context=_safe_str(getattr(recalled_context, "prompt_block", "")),
                    evaluated_at=turn_event_time,
                )
                slow_state = build_slow_state(
                    self.xinyu_dir,
                    user_text=text,
                    scene_frame=response_scene_frame,
                    response_error_decision=response_error_decision,
                    evaluated_at=turn_event_time,
                    persist=True,
                )
                slow_state_runtime = {
                    "notes": [
                        "slow_state:"
                        f"{slow_state.reply_policy}/{slow_state.initiative_policy}/"
                        f"{','.join(slow_state.active_policies) or 'steady'}"
                    ]
                }
            except Exception as exc:
                print(f"[xinyu_core_bridge] response error/slow state failed: {exc}", flush=True)
                response_error_loop = {"notes": [f"response_error_loop_error:{type(exc).__name__}"]}
                slow_state_runtime = {"notes": [f"slow_state_error:{type(exc).__name__}"]}
            finish_sidecars = await run_slow_live_finish_sidecars_with_trace(
                self,
                sidecars_runner=run_slow_turn_finish_sidecars,
                trace_route_stage=trace_route_stage,
                payload=payload,
                text=text,
                reply=reply,
                draft_reply=draft_reply,
                session=session,
                session_key=session_key,
                turn_id=turn_id,
                turn_started_at=turn_started_at,
                before_memory=before_memory,
                visible_turn=visible_turn,
                final_guard_flags=final_guard_flags,
                expression_learning=expression_learning,
                recalled_context=recalled_context,
                recalled_context_notes=recalled_context_notes,
                private_thought_outcome=private_thought_outcome,
                emotion_council=emotion_council,
                persona_sidecar=persona_sidecar,
                continuity_handoff=continuity_handoff,
                wait_to_think_sidecar=wait_to_think_sidecar,
                self_code_task=self_code_task,
                direct_codex_task=direct_codex_task,
                model_codex_task=model_codex_task,
                wait_to_think_task=wait_to_think_task,
                model_codex_delegate_note=model_codex_delegate_note,
            )
            uncertainty_pause = finish_sidecars["uncertainty_pause"]
            learning_closed_loop = finish_sidecars["learning_closed_loop"]
            residue_written = finish_sidecars["residue_written"]
            voice_calibrated = finish_sidecars["voice_calibrated"]
            voice_trial_overlay = finish_sidecars["voice_trial_overlay"]
            curiosity_prediction = finish_sidecars["curiosity_prediction"]
            private_thought_link = finish_sidecars["private_thought_link"]
            archive_result = finish_sidecars["archive_result"]
            candidate_result = finish_sidecars["candidate_result"]
            memory_self_review = finish_sidecars["memory_self_review"]
            interaction_journal = finish_sidecars["interaction_journal"]
            proactive_owner_reply_marked = finish_sidecars["proactive_owner_reply_marked"]
            promised_followup = finish_sidecars["promised_followup"]
            sticker_reply = finish_sidecars["sticker_reply"]
            sticker_tail_recorded = finish_sidecars["sticker_tail_recorded"]
            turn_coherence = finish_sidecars["turn_coherence"]
            after_memory = finish_sidecars["after_memory"]
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
            if stale_context_reply_replaced:
                notes.append("stale_context_reply_replaced")
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
            notes.extend(_safe_str(note) for note in response_error_loop.get("notes", [])[:2])
            notes.extend(_safe_str(note) for note in slow_state_runtime.get("notes", [])[:2])
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
            notes.extend(_safe_str(note) for note in tinykernel_shadow.get("notes", [])[:3])
            notes.extend(_safe_str(note) for note in emotion_council.get("notes", [])[:4])
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
            notes.extend(_safe_str(note) for note in turn_coherence.get("notes", [])[:3])
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
            trace_route_stage(
                "route_finished",
                route="slow_live",
                status="ok",
                elapsed_ms=elapsed_ms,
                notes=notes[:8],
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
                started_at=_timestamp_or_now_iso(turn_started_wall),
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
        ensure_recent_context_health(self.xinyu_dir)
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
        ensure_recent_context_health(self.xinyu_dir)
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

    _payload_text = staticmethod(_payload_text_from_payload)
    _session_key = staticmethod(session_key_from_payload)

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
        emotion_council_context: str = "",
    ) -> None:
        xinyu_bridge_turn_sidecars.inject_live_turn_context(
            self,
            agent,
            payload=payload,
            text=text,
            turn_id=turn_id,
            dialogue_tail=dialogue_tail,
            persona_context=persona_context,
            curiosity_context=curiosity_context,
            visible_turn=visible_turn,
            recalled_context=recalled_context,
            runtime_presence_context=runtime_presence_context,
            continuity_context=continuity_context,
            uncertainty_pause_context=uncertainty_pause_context,
            life_reply_context=life_reply_context,
            emotion_council_context=emotion_council_context,
            codex_delegate_open=CODEX_DELEGATE_OPEN,
            codex_delegate_close=CODEX_DELEGATE_CLOSE,
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
        try:
            atomic_write_text(path, content, final_newline=False)
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
        assistant_recorded_at = datetime.now().astimezone().isoformat()
        user_recorded_at = self._payload_event_time_iso(payload, fallback=assistant_recorded_at)
        user_content = self._dialogue_tail_user_content(user_text, payload=payload)
        if user_content.strip():
            session.dialogue_tail.append(
                {"role": "user", "content": user_content.strip(), "recorded_at": user_recorded_at}
            )
        if reply.strip():
            session.dialogue_tail.append(
                {"role": "assistant", "content": reply.strip(), "recorded_at": assistant_recorded_at}
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

    _is_recent_sticker_question = staticmethod(is_recent_sticker_question)
    _current_sticker_question_reply = staticmethod(current_sticker_question_reply)
    _recent_sticker_question_reply = staticmethod(recent_sticker_question_reply)

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
        canonical_recall_context: str = "",
    ) -> str:
        return await self.renderer.render_outward_reply(
            agent,
            payload=payload,
            user_text=user_text,
            draft_reply=draft_reply,
            canonical_recall_context=canonical_recall_context,
        )

    def _renderer_reason(self, *, payload: dict[str, Any], user_text: str, draft_reply: str) -> str:
        return self.renderer.renderer_reason(payload=payload, user_text=user_text, draft_reply=draft_reply)

    _normalize_renderer_mode = staticmethod(BridgeRenderer.normalize_renderer_mode)

    def _build_renderer_messages(
        self,
        agent: Any,
        *,
        payload: dict[str, Any],
        user_text: str,
        draft_reply: str,
        canonical_recall_context: str = "",
        failed_reply: str = "",
        quality_flags: list[str] | None = None,
    ) -> list[dict[str, str]]:
        return self.renderer.build_renderer_messages(
            agent,
            payload=payload,
            user_text=user_text,
            draft_reply=draft_reply,
            canonical_recall_context=canonical_recall_context,
            failed_reply=failed_reply,
            quality_flags=quality_flags,
        )

    def _speech_controller(self) -> XinyuSpeechController:
        controller = getattr(self, "speech_controller", None)
        if controller is None:
            controller = XinyuSpeechController(BRIDGE_SOURCE_PATH.parent)
            self.speech_controller = controller
        return controller

    def _is_live_style_pressure(self, text: str) -> bool:
        return self._speech_controller().is_live_style_pressure(text)

    def _is_owner_relationship_pressure(self, text: str) -> bool:
        return self._speech_controller().is_owner_relationship_pressure(text)

    def _is_explicit_technical_request(self, text: str) -> bool:
        return self._speech_controller().is_explicit_technical_request(text)

    def _reply_quality_flags(self, *, user_text: str, reply: str) -> list[str]:
        return self._speech_controller().reply_quality_flags(user_text=user_text, reply=reply)

    _owner_requested_reply_bubble_units = staticmethod(owner_requested_reply_bubble_units)
    _numeric_bubble_units_from_text = staticmethod(numeric_bubble_units_from_text)
    _looks_like_false_single_bubble_limitation = staticmethod(looks_like_false_single_bubble_limitation)

    def _empty_visible_reply_fallback(self, *, payload: dict[str, Any], user_text: str, delegate_note: str = "") -> str:
        del delegate_note
        if not self._owner_private_payload_matches(payload):
            return ""
        if self._is_explicit_technical_request(user_text):
            return ""
        return xinyu_bridge_semantic_fast_routes.owner_private_empty_state_notice(user_text)

    async def _recover_empty_visible_reply(
        self,
        agent: Any,
        *,
        payload: dict[str, Any],
        user_text: str,
        canonical_recall_context: str = "",
    ) -> tuple[str, list[str]]:
        return await recover_empty_visible_reply(
            self,
            agent,
            payload=payload,
            user_text=user_text,
            canonical_recall_context=canonical_recall_context,
        )

    _critical_final_guard_flags = staticmethod(critical_final_guard_flags)

    def _owner_private_llm_failover_context(
        self,
        payload: dict[str, Any],
        *,
        text: str,
        session_key: str,
        turn_id: str,
    ) -> dict[str, Any]:
        if not self._owner_private_payload_matches(payload):
            return {}
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        if _as_bool(metadata.get("control_plane"), default=False):
            return {}
        if _payload_has_attachment_signal(payload):
            return {}
        if looks_like_codex_request(text) or looks_like_owner_local_write_request(text):
            return {}
        source = _safe_str(metadata.get("source")).strip()
        if source and source != "onebot_message_event":
            return {}
        message_type = _safe_str(payload.get("message_type")).lower()
        if message_type and not message_type.startswith("private"):
            return {}
        return {
            "enabled": True,
            "scope": "owner_private_chat",
            "source": source or "onebot_message_event",
            "turn_id": turn_id,
            "session_key": session_key,
            "user_text": text,
            "trace_root": str(self.xinyu_dir),
            "context": {
                "recent_turns": [],
                "persona_state": "",
                "owner_profile": "",
                "runtime_state": "",
                "memory_recall": [],
            },
            "capabilities": {
                "codex_available": False,
                "external_api_available": False,
                "local_tools_available": True,
            },
            "constraints": {
                "max_reply_chars": 240,
                "allow_tool_request": False,
                "allow_memory_candidate": False,
            },
        }

    def _renderer_memory_context(self) -> str:
        return self.renderer.renderer_memory_context()

    def _read_text(self, rel: str, *, limit: int) -> str:
        return self.renderer.read_text(rel, limit=limit)

    def _conversation_tail(self, agent: Any, *, max_messages: int) -> str:
        return self.renderer.conversation_tail(agent, max_messages=max_messages)

    _replace_last_assistant_message = staticmethod(replace_last_assistant_message)

    def _strip_renderer_wrappers(self, text: str) -> str:
        return self.renderer.strip_renderer_wrappers(text)


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
    request_timeout_margin_seconds = max(0, args.request_timeout_margin_seconds)
    request_timeout_seconds = args.turn_timeout_seconds + request_timeout_margin_seconds
    server = XinYuBridgeHTTPServer(
        (args.host, args.port),
        XinYuBridgeRequestHandler,
        runtime=runtime,
        loop=loop,
        bridge_token=args.bridge_token.strip(),
        max_body_bytes=args.max_body_bytes,
        request_timeout_seconds=request_timeout_seconds,
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
        f"request_timeout={request_timeout_seconds}s, "
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
