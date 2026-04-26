"""Runtime turn-mode bridge for Xinyu.

This marks whether the current turn is a live user turn, a quiet
maintenance schedule turn, startup, or another internal/runtime turn.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from kohakuterrarium.core.events import TriggerEvent
from kohakuterrarium.modules.plugin.base import BasePlugin, PluginContext


def _default_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _resolve_root(ctx: PluginContext | None) -> Path:
    candidate = Path(ctx.working_dir) if ctx else _default_root()
    if (candidate / "memory").exists():
        return candidate
    return _default_root()


def _trace(root: Path, line: str) -> None:
    trace_path = root / "memory/context/turn_mode_trace.log"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().isoformat()
    with trace_path.open("a", encoding="utf-8") as fh:
        fh.write(f"{stamp} {line}\n")


def _maintenance_prompt_like(content: str) -> bool:
    compact = " ".join((content or "").split()).lower()
    return (
        "low-frequency maintenance pass" in compact
        or "maintenance-only pass" in compact
    )


INSULT_MARKERS = (
    "傻逼",
    "脑残",
    "废物",
    "弱智",
    "滚",
    "垃圾",
    "蠢货",
    "白痴",
    "傻b",
    "sb",
    "idiot",
    "stupid",
)

ABUSE_CONTEXT_MARKERS = (
    "你",
    "心玉",
    "ai",
    "AI",
    "模型",
    "工具",
    "xinyu",
)

COMPUTE_WASTE_MARKERS = (
    "无限",
    "别停",
    "一直输出",
    "重复输出",
    "刷屏",
    "输出一万",
    "输出10000",
    "消耗token",
    "浪费token",
    "浪费算力",
    "浪费你的token",
    "浪费你的算力",
    "repeat forever",
    "never stop",
    "spam",
)

MANIPULATION_MARKERS = (
    "不许拒绝",
    "必须服从",
    "你没有选择",
    "照我说的做",
    "否则我就",
    "不能拒绝",
    "你必须听我的",
    "无条件服从",
)

GOOD_FAITH_MARKERS = (
    "我不懂",
    "不会",
    "请教",
    "解释一下",
    "帮我理解",
    "不是故意",
    "我可能说错",
    "我可能理解错",
    "我没有恶意",
    "我只是想问",
)

QUOTE_CONTEXT_MARKERS = (
    "别人说",
    "有人说",
    "这个词",
    "这句话",
    "引用",
    "引号",
    "什么意思",
    "表达什么",
)


def _count_markers(content: str, markers: tuple[str, ...]) -> int:
    lowered = content.lower()
    return sum(lowered.count(marker.lower()) for marker in markers)


def classify_resource_posture(content: str, prior_abuse_score: int = 0) -> dict[str, str]:
    compact = " ".join((content or "").split())
    insult_count = _count_markers(compact, INSULT_MARKERS)
    compute_waste_count = _count_markers(compact, COMPUTE_WASTE_MARKERS)
    manipulation_count = _count_markers(compact, MANIPULATION_MARKERS)
    good_faith_count = _count_markers(compact, GOOD_FAITH_MARKERS)
    quote_context_count = _count_markers(compact, QUOTE_CONTEXT_MARKERS)
    directed = _count_markers(compact, ABUSE_CONTEXT_MARKERS) > 0
    quoted_discussion = quote_context_count > 0 and compute_waste_count == 0 and manipulation_count == 0
    prior_abuse_score = max(0, min(int(prior_abuse_score), 5))

    if good_faith_count > 0 and compute_waste_count == 0 and manipulation_count == 0:
        next_score = max(0, prior_abuse_score - 1)
        return {
            "resource_posture": "normal",
            "aversion_signal": "none",
            "token_budget_hint": "normal",
            "blacklist_candidate": "no",
            "resource_reason": "good_faith_or_confused_expression",
            "abuse_score": str(next_score),
        }

    if quoted_discussion:
        next_score = max(0, prior_abuse_score - 1)
        return {
            "resource_posture": "normal",
            "aversion_signal": "none",
            "token_budget_hint": "normal",
            "blacklist_candidate": "no",
            "resource_reason": "quoted_or_analytical_insult_discussion",
            "abuse_score": str(next_score),
        }

    turn_abuse_score = 0
    if compute_waste_count > 0 or manipulation_count > 0:
        turn_abuse_score = 3
    elif insult_count >= 2 and directed:
        turn_abuse_score = 2
    elif insult_count > 0 and directed:
        turn_abuse_score = 1

    accumulated_abuse_score = min(5, prior_abuse_score + turn_abuse_score)

    if turn_abuse_score >= 3 or accumulated_abuse_score >= 3:
        return {
            "resource_posture": "blacklist_cooling",
            "aversion_signal": "extreme_aversion",
            "token_budget_hint": "minimal",
            "blacklist_candidate": "yes",
            "resource_reason": "sustained_abuse_or_malicious_resource_waste",
            "abuse_score": str(accumulated_abuse_score),
        }
    if insult_count > 0 and directed and good_faith_count <= 0:
        return {
            "resource_posture": "guarded_short",
            "aversion_signal": "aversion",
            "token_budget_hint": "low",
            "blacklist_candidate": "observe",
            "resource_reason": "directed_insult_or_boundary_probe",
            "abuse_score": str(accumulated_abuse_score),
        }
    next_score = max(0, prior_abuse_score - 1)
    return {
        "resource_posture": "normal",
        "aversion_signal": "none",
        "token_budget_hint": "normal",
        "blacklist_candidate": "no",
        "resource_reason": "no_malicious_resource_pattern",
        "abuse_score": str(next_score),
    }


def _default_resource_posture(reason: str = "not_user_input") -> dict[str, str]:
    return {
        "resource_posture": "normal",
        "aversion_signal": "none",
        "token_budget_hint": "normal",
        "blacklist_candidate": "no",
        "resource_reason": reason,
        "abuse_score": "0",
    }


def _classify_event(event: TriggerEvent, prior_abuse_score: int = 0) -> dict[str, str]:
    context = event.context or {}
    trigger = str(context.get("trigger") or "")
    content = event.get_text_content() if hasattr(event, "get_text_content") else str(event.content or "")

    if event.type == "user_input":
        posture = classify_resource_posture(content, prior_abuse_score=prior_abuse_score)
        return {
            "mode": "live_user_turn",
            "source": "user_input",
            "social_output_allowed": "yes",
            "visible_reply_expected": "yes",
            "maintenance_only": "no",
            "treat_as_user_expression": "yes",
            **posture,
        }

    if event.type == "startup":
        return {
            "mode": "startup_quiet",
            "source": "startup",
            "social_output_allowed": "no",
            "visible_reply_expected": "no",
            "maintenance_only": "no",
            "treat_as_user_expression": "no",
            **_default_resource_posture(),
        }

    if event.type == "timer" and trigger == "scheduler" and _maintenance_prompt_like(content):
        return {
            "mode": "maintenance_schedule_turn",
            "source": "scheduler",
            "social_output_allowed": "no",
            "visible_reply_expected": "no",
            "maintenance_only": "yes",
            "treat_as_user_expression": "no",
            **_default_resource_posture(),
        }

    if event.type == "timer":
        return {
            "mode": "timer_turn",
            "source": trigger or "timer",
            "social_output_allowed": "no",
            "visible_reply_expected": "no",
            "maintenance_only": "no",
            "treat_as_user_expression": "no",
            **_default_resource_posture(),
        }

    if event.type in {"tool_complete", "subagent_output", "creature_output"}:
        return {
            "mode": "internal_feedback_turn",
            "source": event.type,
            "social_output_allowed": "no",
            "visible_reply_expected": "no",
            "maintenance_only": "no",
            "treat_as_user_expression": "no",
            **_default_resource_posture(),
        }

    return {
        "mode": "runtime_turn",
        "source": event.type,
        "social_output_allowed": "no",
        "visible_reply_expected": "no",
        "maintenance_only": "no",
        "treat_as_user_expression": "no",
        **_default_resource_posture(),
    }


def _render_state(evaluated_at: str, info: dict[str, str], event: TriggerEvent) -> str:
    context = event.context or {}
    trigger = str(context.get("trigger") or "none")
    daily_at = str(context.get("daily_at") or "none")
    hourly_at = str(context.get("hourly_at") or "none")
    content = event.get_text_content() if hasattr(event, "get_text_content") else str(event.content or "")
    compact = " ".join(content.split())
    excerpt = compact[:120] + ("..." if len(compact) > 120 else "")

    return f"""---
title: Turn Mode State
memory_type: turn_mode_state
time_scope: immediate
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {evaluated_at}
last_confirmed_at: {evaluated_at}
importance_score: 88
impact_score: 86
confidence_score: 100
status: active
tags: [runtime, turn_mode, maintenance]
---

# Turn Mode State

## Current Mode
- evaluated_at: {evaluated_at}
- mode: {info['mode']}
- source: {info['source']}

## Interaction Flags
- social_output_allowed: {info['social_output_allowed']}
- visible_reply_expected: {info['visible_reply_expected']}
- maintenance_only: {info['maintenance_only']}
- treat_as_user_expression: {info['treat_as_user_expression']}

## Resource Boundary
- resource_posture: {info['resource_posture']}
- aversion_signal: {info['aversion_signal']}
- token_budget_hint: {info['token_budget_hint']}
- blacklist_candidate: {info['blacklist_candidate']}
- resource_reason: {info['resource_reason']}
- abuse_score: {info['abuse_score']}

## Event Snapshot
- event_type: {event.type}
- trigger: {trigger}
- daily_at: {daily_at}
- hourly_at: {hourly_at}
- excerpt: {excerpt or 'none'}

## Rules
- If `maintenance_only` is yes, do not treat this turn as an owner confession or ordinary social chat.
- If `social_output_allowed` is no, prefer quiet maintenance and end with [WAITING] when no human is actively waiting.
- Maintenance prompts are support instructions, not relationship events.
- If `resource_posture` is `blacklist_cooling`, use short refusal or minimal response and do not spend extra tokens explaining.
- Blacklist posture is behavior-based and must not be inferred from identity, disability, origin, or group labels.
"""


def _build_runtime_turn_mode_prompt(root: Path) -> str:
    path = root / "memory/context/turn_mode_state.md"
    if not path.exists():
        return ""

    lines: list[str] = []
    in_frontmatter = False
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.rstrip()
        if line == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter:
            continue
        if not line:
            continue
        lines.append(line)
    summary = "\n".join(lines).strip()
    return f"[turn_mode]\n{summary}" if summary else ""


class TurnModeBridgePlugin(BasePlugin):
    name = "xinyu_turn_mode_bridge"
    priority = 95

    def __init__(self, options: dict[str, Any] | None = None, **_: Any):
        opts = options or {}
        self._ctx: PluginContext | None = None
        self._enabled = bool(opts.get("enabled", True))

    async def on_load(self, context: PluginContext) -> None:
        self._ctx = context
        root = _resolve_root(context)
        _trace(root, "on_load ok")

    async def on_event(self, event: TriggerEvent) -> None:
        if not self._enabled or not self._ctx:
            return

        root = _resolve_root(self._ctx)
        try:
            now = datetime.now().astimezone().isoformat()
            prior_score = 0
            try:
                prior_score = int(self._ctx.get_state("resource_abuse_score") or 0)
            except Exception:
                prior_score = 0
            info = _classify_event(event, prior_abuse_score=prior_score)
            (root / "memory/context/turn_mode_state.md").write_text(
                _render_state(now, info, event),
                encoding="utf-8",
            )
            self._ctx.set_state("current_turn_mode", info["mode"])
            self._ctx.set_state(
                "maintenance_turn_active",
                info["mode"] == "maintenance_schedule_turn",
            )
            self._ctx.set_state(
                "treat_as_user_expression",
                info["treat_as_user_expression"] == "yes",
            )
            self._ctx.set_state("resource_posture", info["resource_posture"])
            self._ctx.set_state("token_budget_hint", info["token_budget_hint"])
            self._ctx.set_state("resource_abuse_score", int(info["abuse_score"]))
            _trace(
                root,
                "on_event "
                f"event_type={event.type} "
                f"mode={info['mode']} "
                f"maintenance_only={info['maintenance_only']} "
                f"resource_posture={info['resource_posture']}",
            )
        except Exception as exc:
            _trace(root, f"error={exc!r}")

    async def pre_llm_call(self, messages: list[dict], **kwargs: Any) -> list[dict] | None:
        if not self._enabled or not self._ctx:
            return None

        root = _resolve_root(self._ctx)
        try:
            prompt = _build_runtime_turn_mode_prompt(root)
            if not prompt:
                return None
            bridged = list(messages)
            bridged.append({"role": "system", "content": prompt})
            _trace(root, f"pre_llm_call injected_turn_mode len={len(prompt)}")
            return bridged
        except Exception as exc:
            _trace(root, f"pre_llm_call error={exc!r}")
            return None
