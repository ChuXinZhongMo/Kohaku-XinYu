from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

from stores.persona_runtime_overlay import OVERLAY_REL as GOLDMARK_OVERLAY_REL
from stores.persona_runtime_overlay import read_goldmark_overlay
from xinyu_contextual_self_loop import append_contextual_self_loop_trace
from xinyu_contextual_self_loop import build_contextual_self_loop_snapshot
from xinyu_contextual_self_loop import context_file_policy
from xinyu_contextual_self_loop import snapshot_to_prompt_block
from xinyu_contextual_self_loop import write_contextual_self_loop_state
from xinyu_contextual_recall import build_contextual_recall_prompt_block
from xinyu_initiative_spine import build_initiative_spine_prompt_block
from xinyu_memory_braid import build_memory_braid_prompt_block
from xinyu_turn_coherence import build_turn_coherence_prompt_block
from xinyu_owner_context_bridge import build_owner_continuity_hint
from xinyu_scene_frame import build_scene_frame
from xinyu_scene_frame import render_scene_frame_prompt_block
from xinyu_slow_state_modulator import build_slow_state
from xinyu_slow_state_modulator import render_slow_state_prompt_block
from xinyu_turn_triage_gate import render_turn_triage_prompt_block
from xinyu_turn_triage_gate import triage_turn


"""Renderer context assembly.

`build_renderer_memory_context()` may include an offline contextual recall pack
when no live recall block is supplied. During live chat, callers should pass the
canonical `run_living_memory_recall_algorithm(...).prompt_block` so the renderer
does not run a second recall path.
"""


@dataclass(frozen=True, slots=True)
class RuntimeContextFile:
    rel_path: str
    limit: int
    layer: str


@dataclass(frozen=True, slots=True)
class RuntimeContextSnapshot:
    life_month_context: str
    personality_evolution_state: str
    private_thought_state: str
    self_model_state: str
    memory_weight_state: str
    thought_seeds: str
    continuity_handoff_state: str = ""
    uncertainty_pause_state: str = ""
    async_exploration_state: str = ""
    self_code_approval_state: str = ""
    watched_source_state: str = ""
    github_learning_state: str = ""
    daily_digest_state: str = ""
    creative_writing_state: str = ""
    memory_self_review_state: str = ""


RENDERER_CONTEXT_FILES: tuple[RuntimeContextFile, ...] = (
    RuntimeContextFile("prompts/live_voice_card.md", 1400, "concept_seed"),
    RuntimeContextFile("memory/self/core.md", 2200, "xinyu_concept"),
    RuntimeContextFile("memory/self/personality_profile.md", 2600, "xinyu_concept"),
    RuntimeContextFile("memory/self/voice_profile_zh.md", 2200, "voice"),
    RuntimeContextFile("memory/self/voice_calibration_log.md", 1800, "voice"),
    RuntimeContextFile("memory/self/narrative.md", 2600, "self_narrative"),
    RuntimeContextFile("memory/people/owner.md", 2800, "owner_relation"),
    RuntimeContextFile("memory/relationships/index.md", 1800, "relationship"),
    RuntimeContextFile("memory/emotions/current_state.md", 1600, "emotion"),
    RuntimeContextFile("memory/context/time_anchor.md", 1000, "time"),
    RuntimeContextFile("memory/context/current_life_month_context.md", 1600, "life_context"),
    RuntimeContextFile("memory/context/persona_surface_state.md", 1800, "recent_surface"),
    RuntimeContextFile("memory/context/runtime_self_presence.md", 1200, "runtime_presence"),
    RuntimeContextFile("memory/context/watched_source_state.md", 1600, "watched_source"),
    RuntimeContextFile("memory/context/github_learning_state.md", 1200, "github_learning"),
    RuntimeContextFile("memory/context/daily_digest_state.md", 900, "ephemeral_digest"),
    RuntimeContextFile("memory/creative/planning/novel_profile.md", 900, "creative_writing"),
    RuntimeContextFile("memory/creative/planning/novel_state.md", 1000, "creative_writing"),
    RuntimeContextFile("memory/creative/planning/publication_state.md", 900, "creative_writing"),
    RuntimeContextFile("memory/context/memory_self_review_state.md", 1400, "memory_self_review"),
    RuntimeContextFile("memory/context/continuity_handoff_state.md", 1600, "continuity_handoff"),
    RuntimeContextFile("memory/context/uncertainty_pause_state.md", 1100, "uncertainty_pause"),
    RuntimeContextFile("memory/context/async_exploration_state.md", 1400, "async_exploration"),
    RuntimeContextFile("memory/context/self_code_approval_state.md", 1000, "self_code_approval"),
    RuntimeContextFile("memory/self/expression_self_learning_state.md", 1600, "expression_self_learning"),
    RuntimeContextFile("memory/context/codex_delegation_policy.md", 1800, "codex_boundary"),
    RuntimeContextFile("memory/context/recent_context.md", 2600, "recent_context"),
    RuntimeContextFile("memory/context/initiative_state.md", 1400, "initiative"),
    RuntimeContextFile("memory/context/initiative_lifecycle_state.md", 1200, "initiative_lifecycle"),
    RuntimeContextFile("memory/context/initiative_feedback_state.md", 900, "initiative_feedback"),
    RuntimeContextFile("memory/context/self_chosen_goal_ecology_state.md", 1200, "goal_ecology"),
    RuntimeContextFile("memory/context/self_action_gateway_state.md", 1200, "self_action_gateway"),
    RuntimeContextFile("memory/context/self_action_gateway_execution_handoff.md", 1200, "self_action_gateway_handoff"),
    RuntimeContextFile("memory/context/self_action_patch_executor_state.md", 1200, "self_action_patch_executor"),
    RuntimeContextFile("memory/context/self_action_patch_executor_task.md", 1600, "self_action_patch_task"),
)

RECALLED_CONTEXT_PRIORITY_WORDING = "\n".join(
    [
        "## Recalled Context Priority",
        "Recalled Context is advisory only.",
        "It sits below the current owner message, live voice card, current life posture, privacy boundaries, and stable memory.",
        "Use recalled context only if it helps the current turn. Current owner message and current emotional posture outrank retrieved fragments.",
        "When uncertain, say uncertainty naturally instead of pretending.",
    ]
)

def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def read_limited(root: Path, rel_path: str, *, limit: int) -> str:
    path = root / rel_path
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""
    text = _unwrap_content_envelope(text)
    if len(text) <= limit:
        return text
    return text[-limit:]


def _unwrap_content_envelope(text: str) -> str:
    if text.startswith("content:---"):
        return text.removeprefix("content:")
    if text.startswith("content:\n"):
        return text.removeprefix("content:\n")
    if text.startswith("content=---"):
        return text.removeprefix("content=")
    if text.startswith("content=\n"):
        return text.removeprefix("content=\n")
    return text


def _goldmark_sort_key(entry: dict[str, Any]) -> str:
    return (
        _safe_str(entry.get("dehydration_finished_at")).strip()
        or _safe_str(entry.get("marked_at_iso")).strip()
        or _safe_str(entry.get("marked_at")).strip()
    )


def _goldmark_sort_timestamp(entry: dict[str, Any]) -> float:
    for key in ("dehydration_finished_at", "marked_at_iso"):
        value = _safe_str(entry.get(key)).strip()
        if not value:
            continue
        try:
            if value.endswith("Z"):
                value = value[:-1] + "+00:00"
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.timestamp()
        except ValueError:
            continue
    value = entry.get("marked_at")
    if isinstance(value, (int, float)):
        return float(value)
    value_text = _safe_str(value).strip()
    try:
        return float(value_text)
    except ValueError:
        return 0.0


def _goldmark_prompt_cell(value: Any, *, limit: int) -> str:
    text = _safe_str(value)
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text[:limit]


def _valid_goldmark_features(entry: dict[str, Any]) -> dict[str, Any] | None:
    if _safe_str(entry.get("dehydration_status")).strip().lower() != "done":
        return None
    features = entry.get("vibe_features")
    if not isinstance(features, dict):
        return None
    tone_tags = features.get("tone_tags")
    structural_pattern = _safe_str(features.get("structural_pattern")).strip()
    if not isinstance(tone_tags, list) or not structural_pattern:
        return None
    clean_tags = [_goldmark_prompt_cell(tag, limit=24) for tag in tone_tags]
    clean_tags = [tag for tag in clean_tags if tag][:6]
    if not clean_tags:
        return None
    return {
        "tone_tags": clean_tags,
        "structural_pattern": _goldmark_prompt_cell(structural_pattern, limit=260),
    }


def build_goldmark_auth_prompt_block(root: Path, *, limit: int = 3) -> str:
    valid: list[tuple[float, str, dict[str, Any]]] = []
    for entry in read_goldmark_overlay(root):
        features = _valid_goldmark_features(entry)
        if features is None:
            continue
        valid.append((_goldmark_sort_timestamp(entry), _goldmark_sort_key(entry), features))

    valid.sort(key=lambda item: (item[0], item[1]), reverse=True)
    selected = [features for _, _, features in valid[: max(0, limit)]]
    if not selected:
        return ""

    lines = [
        "[SYSTEM_OVERRIDE: 运行时表达授权 (Goldmark Auth)]",
        "注意：以下内容是近期被主人认可的高阶语感状态，只是当前对话的松弛度许可，不是固定人格模板。",
        "",
        "最高禁令：",
        "- 绝对禁止复刻任何历史原句、称呼、梗、口头禅或业务事实。",
        "- 绝对禁止为了迎合这些特征而强行捏造语境。",
        "- 这些特征只授权语气和结构边界；当前用户消息仍然拥有最高优先级。",
        "",
        "授权状态清单：",
    ]
    for index, features in enumerate(selected, start=1):
        tone = ", ".join(features["tone_tags"])
        structure = _safe_str(features["structural_pattern"]).strip()
        lines.extend(
            [
                f"--- 许可状态 {index} ---",
                f"[情绪特征 (Tone)]: {tone}",
                f"[结构模式 (Structure)]: {structure}",
            ]
        )
    return "\n".join(lines)


def refresh_runtime_context(
    root: Path,
    *,
    user_text: str = "",
    evaluated_at: str | None = None,
) -> RuntimeContextSnapshot:
    """Compatibility shim for callers that still expect a runtime snapshot.

    The old implementation refreshed many maintenance/growth files on every
    live turn. The concept-seed runtime keeps that work out of the speech path.
    """
    del user_text, evaluated_at
    return RuntimeContextSnapshot(
        life_month_context=read_limited(root, "memory/context/current_life_month_context.md", limit=1800),
        personality_evolution_state="",
        private_thought_state="",
        self_model_state="",
        memory_weight_state="",
        thought_seeds="",
        continuity_handoff_state=read_limited(root, "memory/context/continuity_handoff_state.md", limit=1600),
        uncertainty_pause_state=read_limited(root, "memory/context/uncertainty_pause_state.md", limit=1100),
        async_exploration_state=read_limited(root, "memory/context/async_exploration_state.md", limit=1400),
        self_code_approval_state=read_limited(root, "memory/context/self_code_approval_state.md", limit=1000),
        watched_source_state=read_limited(root, "memory/context/watched_source_state.md", limit=1600),
        github_learning_state=read_limited(root, "memory/context/github_learning_state.md", limit=1200),
        daily_digest_state=read_limited(root, "memory/context/daily_digest_state.md", limit=900),
        creative_writing_state=read_limited(root, "memory/creative/planning/novel_state.md", limit=1000),
        memory_self_review_state=read_limited(root, "memory/context/memory_self_review_state.md", limit=1400),
    )


def build_renderer_memory_context(
    root: Path,
    *,
    user_text: str = "",
    canonical_recall_context: str = "",
) -> str:
    parts: list[str] = []
    contextual_self = build_contextual_self_loop_snapshot(
        root,
        user_text=user_text,
        trigger="renderer_memory_context",
    )
    write_contextual_self_loop_state(root, contextual_self)
    append_contextual_self_loop_trace(root, contextual_self, user_text=user_text)
    scene_frame = build_scene_frame(
        root,
        user_text=user_text,
        contextual_scene=contextual_self.current_scene,
        canonical_recall_context=canonical_recall_context,
    )
    scene_frame_block = render_scene_frame_prompt_block(scene_frame)
    if scene_frame_block:
        parts.append("[runtime/scene_frame]\n[layer: scene_frame]\n" + scene_frame_block)
    turn_triage = triage_turn(
        root,
        user_text=user_text,
        scene_frame=scene_frame,
        recent_work_context=read_limited(root, "memory/context/recent_context.md", limit=1200),
        canonical_recall_context=canonical_recall_context,
    )
    turn_triage_block = render_turn_triage_prompt_block(turn_triage)
    if turn_triage_block:
        parts.append("[runtime/turn_triage_gate]\n[layer: current_turn_priority]\n" + turn_triage_block)
    slow_state = build_slow_state(
        root,
        user_text=user_text,
        scene_frame=scene_frame,
        triage_decision=turn_triage,
        persist=True,
    )
    slow_state_block = render_slow_state_prompt_block(slow_state) if slow_state.active_policies else ""
    if slow_state_block:
        parts.append("[runtime/slow_state_modulator]\n[layer: slow_state]\n" + slow_state_block)
    owner_continuity_hint = build_owner_continuity_hint(root, user_text=user_text)
    if owner_continuity_hint:
        parts.append("[runtime/owner_continuity_hint]\n[layer: current_turn]\n" + owner_continuity_hint)
    braid_block = build_memory_braid_prompt_block(root, user_text=user_text, max_chars=2200)
    if braid_block:
        parts.append("[memory/context/memory_braid]\n[layer: memory_orchestration]\n" + braid_block)
    coherence_block = build_turn_coherence_prompt_block(
        root,
        user_text=user_text,
        memory_braid_block=braid_block,
        max_chars=2000,
    )
    if coherence_block:
        parts.append("[memory/context/turn_coherence]\n[layer: turn_orchestration]\n" + coherence_block)
    initiative_block = build_initiative_spine_prompt_block(root, trigger="renderer_memory_context", max_chars=1800)
    if initiative_block:
        parts.append("[memory/context/initiative_spine]\n[layer: initiative_orchestration]\n" + initiative_block)
    contextual_self_block = snapshot_to_prompt_block(contextual_self, max_chars=1400)
    if contextual_self_block:
        parts.append("[memory/context/contextual_self_loop]\n[layer: context_horizon]\n" + contextual_self_block)
    live_recall_block = _safe_str(canonical_recall_context).strip()
    if live_recall_block:
        parts.append("[memory/context/living_memory_recall]\n[layer: canonical_recall]\n" + live_recall_block)
        contextual_recall_block = ""
    else:
        contextual_recall_block = build_contextual_recall_prompt_block(
            root,
            contextual_self=contextual_self,
            user_text=user_text,
            max_items=4,
            max_chars=1400,
        )
    if contextual_recall_block:
        parts.append("[memory/context/contextual_recall]\n[layer: contextual_recall]\n" + contextual_recall_block)
    for spec in RENDERER_CONTEXT_FILES:
        policy = context_file_policy(
            contextual_self.current_scene,
            rel_path=spec.rel_path,
            layer=spec.layer,
            default_limit=spec.limit,
        )
        if not policy.get("include"):
            continue
        text = read_limited(root, spec.rel_path, limit=int(policy.get("limit") or spec.limit))
        if text:
            parts.append(f"[{spec.rel_path}]\n[layer: {spec.layer}]\n{text}")
    goldmark_block = build_goldmark_auth_prompt_block(root)
    if goldmark_block:
        parts.append(f"[{GOLDMARK_OVERLAY_REL.as_posix()}]\n[layer: runtime_expression_auth]\n" + goldmark_block)
    return "\n\n".join(parts) if parts else "(no memory context loaded)"


def wrap_recalled_context_block(block: str) -> str:
    clean = block.strip()
    if not clean:
        return ""
    return RECALLED_CONTEXT_PRIORITY_WORDING + "\n\n" + clean
