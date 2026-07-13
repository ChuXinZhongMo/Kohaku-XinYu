from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from xinyu_llm_api import (
    anthropic_headers,
    anthropic_messages_endpoint,
    extract_anthropic_text,
    extract_openai_text,
    is_anthropic_messages_provider,
    openai_headers,
)
from xinyu_neuro_memory_rules import rule_ids_for_flow
from xinyu_scene_frame import build_scene_frame


STATE_REL = Path("memory/context/emotion_council_state.md")
TRACE_REL = Path("runtime/emotion_council_trace.jsonl")
RESIDUE_REL = Path("runtime/emotion_council_residue.json")
LENS_MEMORY_DIR_REL = Path("memory/emotions/lenses")
SCHEMA_VERSION = "emotion_council_shadow_v1"
ACTIVE_THRESHOLD = 0.35
MAX_ACTIVE_LENSES = 5
MODEL_ENABLED_ENV = "XINYU_EMOTION_COUNCIL_MODEL_ENABLED"
MODEL_PROVIDER_ENV = "XINYU_EMOTION_COUNCIL_PROVIDER"
MODEL_BASE_URL_ENV = "XINYU_EMOTION_COUNCIL_BASE_URL"
MODEL_NAME_ENV = "XINYU_EMOTION_COUNCIL_MODEL"
MODEL_API_KEY_ENV = "XINYU_EMOTION_COUNCIL_API_KEY"
MODEL_LENS_TIMEOUT_MS_ENV = "XINYU_EMOTION_COUNCIL_LENS_TIMEOUT_MS"
MODEL_TOTAL_TIMEOUT_MS_ENV = "XINYU_EMOTION_COUNCIL_TOTAL_TIMEOUT_MS"
MODEL_MAX_WORKERS_ENV = "XINYU_EMOTION_COUNCIL_MAX_WORKERS"
RESIDUE_TTL_HOURS_ENV = "XINYU_EMOTION_COUNCIL_RESIDUE_TTL_HOURS"
DEFAULT_LENS_TIMEOUT_MS = 600
DEFAULT_TOTAL_TIMEOUT_MS = 1500
DEFAULT_RESIDUE_TTL_HOURS = 4
MIN_RESIDUE_STRENGTH = 0.05
LensRunner = Callable[["LensConfig", dict[str, Any]], dict[str, Any] | str]


@dataclass(frozen=True)
class LensConfig:
    name: str
    dimensions: tuple[str, ...]
    markers: tuple[str, ...]
    concern: str
    suggested_bias: str
    risk_flags: tuple[str, ...]
    memory_queries: tuple[str, ...]
    base: float = 0.08


@dataclass(frozen=True)
class LensResult:
    lens: str
    activation: float
    concern: str
    suggested_bias: str
    risk_flags: tuple[str, ...]
    memory_queries: tuple[str, ...]
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class ModelRuntimeConfig:
    base_url: str
    model: str
    api_key: str
    lens_timeout_ms: int
    total_timeout_ms: int
    max_workers: int
    provider: str = ""


LENSES: tuple[LensConfig, ...] = (
    LensConfig(
        name="attachment",
        dimensions=("attachment", "warmth", "trust"),
        markers=("陪", "靠近", "身边", "想你", "喜欢", "抱抱", "别冷", "不要冷", "在吗"),
        concern="owner may need presence rather than procedure",
        suggested_bias="stay warm and present without adding pressure",
        risk_flags=("no_clingy_pressure", "no_relationship_overread"),
        memory_queries=("recent_owner_closeness", "relationship_preference"),
        base=0.08,
    ),
    LensConfig(
        name="guardedness",
        dimensions=("guardedness", "conflict"),
        markers=(
            "算了",
            "别想",
            "别想着",
            "别惦记",
            "不惦记",
            "别提",
            "别再提",
            "不要再问",
            "别再问",
            "别重复",
            "一直惦记",
            "有点问题",
            "有问题",
            "停",
            "打扰",
            "边界",
            "隐私",
        ),
        concern="owner may be setting a boundary or rejecting repeated pressure",
        suggested_bias="answer briefly, stop repeating the old thread, and do not ask a follow-up",
        risk_flags=("do_not_repeat", "no_proactive_followup", "no_internal_mechanics"),
        memory_queries=("recent_owner_correction", "proactive_dismissal"),
        base=0.12,
    ),
    LensConfig(
        name="curiosity",
        dimensions=("curiosity", "openness"),
        markers=("idea", "想法", "新思路", "新idea", "适配", "框架", "为什么", "怎么", "什么情况", "分析", "看看", "研究"),
        concern="owner may be inviting exploration or architecture fit analysis",
        suggested_bias="explore the fit and name a small experiment before implementation",
        risk_flags=("no_tool_without_owner_task", "keep_question_concrete"),
        memory_queries=("project_plans", "architecture_context"),
        base=0.1,
    ),
    LensConfig(
        name="hurt",
        dimensions=("hurt", "aversion", "disgust", "distance_impulse"),
        markers=("委屈", "刺痛", "难过", "伤", "冷淡", "忽略", "否定", "不像你", "失望"),
        concern="owner-private hurt may need visible sting instead of public-assistant politeness",
        suggested_bias="allow a short hurt, annoyed, or distancing line without converting it into a report",
        risk_flags=("owner_private_negative_expression_allowed", "no_public_assistant_smoothing", "do_not_make_one_turn_permanent"),
        memory_queries=("recent_emotional_residue",),
        base=0.06,
    ),
    LensConfig(
        name="irritation",
        dimensions=("irritation", "volatility", "anger", "annoyance", "aversion", "disgust", "pushback_impulse"),
        markers=("烦", "呆", "呆呆", "机械", "模板", "客服", "控制面板", "一直", "重复", "离谱", "不行", "问题啊"),
        concern="visible reply may need real annoyance instead of safe support-bot smoothing",
        suggested_bias="cut mechanism language; allow a sharp, annoyed, or rough private-chat line if it fits",
        risk_flags=("private_temper_allowed", "tiny_profanity_leak_allowed", "avoid_resource_waste_loop"),
        memory_queries=("voice_correction", "mechanism_leak"),
        base=0.08,
    ),
    LensConfig(
        name="stability",
        dimensions=("stability",),
        markers=("计划", "plan", "重构", "修", "bug", "验证", "测试", "完成", "架构", "框架", "长期", "长任务"),
        concern="the turn may need a stable, testable next step rather than emotional drift",
        suggested_bias="keep one main thread, make a small patch, validate before claiming",
        risk_flags=("validate_before_claim", "no_stable_memory_write", "keep_one_main_thread"),
        memory_queries=("current_plan", "validation_matrix"),
        base=0.18,
    ),
    LensConfig(
        name="fatigue",
        dimensions=("fatigue",),
        markers=("累", "休息", "慢", "超时", "卡住", "长任务", "太多", "先停"),
        concern="the response may need lower verbosity and less new initiative",
        suggested_bias="keep the reply short and avoid overcommitting",
        risk_flags=("shorten_reply", "avoid_overcommit"),
        memory_queries=("current_life_posture",),
        base=0.05,
    ),
)


def run_emotion_council_shadow(
    root: Path,
    *,
    text: str = "",
    payload: dict[str, Any] | None = None,
    checked_at: str | None = None,
    trigger: str = "live_turn",
    parallel_model: bool | None = None,
    lens_runner: LensRunner | None = None,
    scene_frame: Any | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    checked_at = checked_at or _now_iso()
    payload = payload if isinstance(payload, dict) else {}
    owner_private = _owner_private(payload)
    snapshot = _load_snapshot(root)
    combined_text = _combined_text(text, snapshot)
    emotion_values = _emotion_values(root, snapshot)
    scene_frame = scene_frame or build_scene_frame(root, user_text=text, evaluated_at=checked_at)
    scene_summary = _scene_frame_summary(scene_frame)
    lens_results = [
        _evaluate_lens(config, combined_text=combined_text, text=text, emotion_values=emotion_values, snapshot=snapshot)
        for config in LENSES
    ]
    lens_results = _apply_scene_frame_modulation(lens_results, scene_summary)
    parallel_summary = _run_parallel_model_reviews(
        root,
        lens_results=lens_results,
        text=text,
        combined_text=combined_text,
        snapshot=snapshot,
        emotion_values=emotion_values,
        enabled=_parallel_model_requested(parallel_model, lens_runner) and (owner_private or trigger != "live_turn"),
        lens_runner=lens_runner,
    )
    lens_results = _apply_model_reviews(lens_results, parallel_summary)
    lens_results.sort(key=lambda item: (item.activation, item.lens), reverse=True)
    active = [item for item in lens_results if item.activation >= ACTIVE_THRESHOLD][:MAX_ACTIVE_LENSES]
    status = "active" if active else "quiet"
    if trigger == "live_turn" and not owner_private:
        status = "not_applicable"
        active = []
    consensus, conflicts, output_bias = _consensus(active, lens_results)
    result = {
        "accepted": True,
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "checked_at": checked_at,
        "trigger": _one_line(trigger, limit=80),
        "owner_private": owner_private,
        "lens_count": len(lens_results),
        "active_lens_count": len(active),
        "strongest_lens": active[0].lens if active else "none",
        "consensus": consensus,
        "output_bias": output_bias,
        "conflicts": conflicts,
        "active_lenses": [asdict(item) for item in active],
        "top_lenses": [asdict(item) for item in lens_results[:MAX_ACTIVE_LENSES]],
        "lens_memory_banks": _lens_memory_bank_summary(root),
        "scene_frame": scene_summary,
        "parallel_model": parallel_summary,
        "boundaries": {
            "shadow_only": True,
            "no_visible_reply": True,
            "no_qq_enqueue": True,
            "no_tool_execution": True,
            "no_stable_memory_write": True,
            "lens_model_no_tools": True,
            "lens_model_no_memory_write": True,
            "lens_model_json_only": True,
            "main_agent_has_only_output_authority": True,
        },
    }
    residue_summary = _update_residue_cache(root, result)
    result["residue_cache"] = residue_summary
    emotion_rule_ids = rule_ids_for_flow("emotion")
    result["neuro_rule_ids"] = list(emotion_rule_ids)
    result["notes"] = [
        *_notes(
        status=status,
        active=active,
        owner_private=owner_private,
        parallel_summary=parallel_summary,
        residue_summary=residue_summary,
        ),
        *_scene_frame_notes(scene_summary),
        "neuro_rules:" + ",".join(emotion_rule_ids),
    ]
    _write_state(root, result)
    _append_trace(root, result)
    return {
        "accepted": True,
        "status": status,
        "strongest_lens": result["strongest_lens"],
        "active_lens_count": result["active_lens_count"],
        "consensus": consensus,
        "output_bias": output_bias,
        "notes": result["notes"],
    }


def build_emotion_council_prompt_block(root: Path, *, max_chars: int = 800) -> str:
    state = _read_text(root / STATE_REL)
    residue = _load_residue_cache(root)
    strongest = _extract_field(state, "strongest_lens")
    consensus = _extract_field(state, "consensus")
    output_bias = _extract_field(state, "output_bias")
    scene_reply_policy = _extract_field(state, "scene_reply_policy")
    scene_time_context = _extract_field(state, "scene_time_context")
    scene_memory_relation = _extract_field(state, "scene_memory_relation")
    residue_lines = _residue_prompt_lines(residue)
    current_active = _extract_field(state, "status") == "active" and strongest not in {"", "none"} and bool(consensus)
    if not current_active and not residue_lines:
        return ""
    lines = [
        "emotion council sidecar:",
        "- visibility: private_observation_only",
        "- boundary: use as bias only; never mention council/lens/internal voting in visible chat.",
    ]
    if current_active:
        lines.extend(
            [
                f"- strongest_lens: {strongest}",
                f"- consensus: {consensus}",
                f"- output_bias: {output_bias}",
            ]
        )
    if scene_reply_policy:
        lines.extend(
            [
                f"- scene_reply_policy: {scene_reply_policy}",
                f"- scene_time_context: {scene_time_context or 'none'}",
                f"- scene_memory_relation: {scene_memory_relation or 'none'}",
            ]
        )
    if residue_lines:
        lines.extend(residue_lines)
    block = "\n".join(lines)
    return block[:max(120, int(max_chars))]


def _parallel_model_requested(parallel_model: bool | None, lens_runner: LensRunner | None) -> bool:
    if lens_runner is not None:
        return True
    if parallel_model is not None:
        return bool(parallel_model)
    return _as_bool(os.environ.get(MODEL_ENABLED_ENV))


def _run_parallel_model_reviews(
    root: Path,
    *,
    lens_results: list[LensResult],
    text: str,
    combined_text: str,
    snapshot: dict[str, str],
    emotion_values: dict[str, float],
    enabled: bool,
    lens_runner: LensRunner | None,
) -> dict[str, Any]:
    if not enabled:
        return {
            "status": "disabled",
            "review_count": 0,
            "ok_count": 0,
            "error_count": 0,
            "timeout_count": 0,
            "total_timeout_ms": DEFAULT_TOTAL_TIMEOUT_MS,
            "lens_timeout_ms": DEFAULT_LENS_TIMEOUT_MS,
            "reviews": [],
            "notes": ["parallel_model:disabled"],
        }
    model_config = _model_runtime_config(root, lens_runner=lens_runner)
    if model_config is None:
        return {
            "status": "unconfigured",
            "review_count": 0,
            "ok_count": 0,
            "error_count": 0,
            "timeout_count": 0,
            "total_timeout_ms": DEFAULT_TOTAL_TIMEOUT_MS,
            "lens_timeout_ms": DEFAULT_LENS_TIMEOUT_MS,
            "reviews": [],
            "notes": ["parallel_model:unconfigured"],
        }

    results_by_name = {item.lens: item for item in lens_results}
    futures: dict[Future[dict[str, Any]], str] = {}
    reviews: list[dict[str, Any]] = []
    started = time.perf_counter()
    executor = ThreadPoolExecutor(max_workers=model_config.max_workers, thread_name_prefix="xinyu-emotion-lens")
    try:
        for config in LENSES:
            rule_result = results_by_name.get(config.name)
            context = _lens_model_context(
                config,
                rule_result=rule_result,
                text=text,
                combined_text=combined_text,
                snapshot=snapshot,
                emotion_values=emotion_values,
                lens_memory=_load_lens_memory(root, config),
            )
            futures[
                executor.submit(
                    _run_single_lens_model_review,
                    config,
                    context,
                    model_config,
                    lens_runner,
                )
            ] = config.name

        deadline = started + (model_config.total_timeout_ms / 1000.0)
        pending = set(futures)
        while pending:
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                break
            done, pending = wait(
                pending,
                timeout=min(0.05, remaining),
                return_when=FIRST_COMPLETED,
            )
            for future in done:
                try:
                    reviews.append(future.result(timeout=0))
                except Exception as exc:
                    reviews.append(
                        {
                            "lens": futures.get(future, "unknown"),
                            "status": "error",
                            "error_type": type(exc).__name__,
                            "activation_delta": 0.0,
                            "confidence": 0.0,
                            "suggested_bias": "",
                            "risk_flags": [],
                            "note": "",
                            "elapsed_ms": int((time.perf_counter() - started) * 1000),
                        }
                    )
        for future in pending:
            future.cancel()
            reviews.append(
                {
                    "lens": futures.get(future, "unknown"),
                    "status": "timeout",
                    "error_type": "TimeoutError",
                    "activation_delta": 0.0,
                    "confidence": 0.0,
                    "suggested_bias": "",
                    "risk_flags": [],
                    "note": "",
                    "elapsed_ms": model_config.total_timeout_ms,
                }
            )
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    reviews.sort(key=lambda item: _one_line(item.get("lens")))
    ok_count = sum(1 for item in reviews if item.get("status") == "ok")
    timeout_count = sum(1 for item in reviews if item.get("status") == "timeout")
    error_count = sum(1 for item in reviews if item.get("status") == "error")
    if ok_count == len(LENSES):
        status = "completed"
    elif ok_count:
        status = "partial"
    elif timeout_count:
        status = "timeout"
    else:
        status = "failed"
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return {
        "status": status,
        "review_count": len(reviews),
        "ok_count": ok_count,
        "error_count": error_count,
        "timeout_count": timeout_count,
        "elapsed_ms": elapsed_ms,
        "lens_timeout_ms": model_config.lens_timeout_ms,
        "total_timeout_ms": model_config.total_timeout_ms,
        "reviews": reviews,
        "notes": [f"parallel_model:{status}", f"parallel_model_ok:{ok_count}"],
    }


def _apply_model_reviews(lens_results: list[LensResult], parallel_summary: dict[str, Any]) -> list[LensResult]:
    raw_reviews = parallel_summary.get("reviews") if isinstance(parallel_summary.get("reviews"), list) else []
    reviews_by_lens = {
        _one_line(review.get("lens")): review
        for review in raw_reviews
        if isinstance(review, dict) and review.get("status") == "ok"
    }
    if not reviews_by_lens:
        return lens_results
    adjusted: list[LensResult] = []
    for result in lens_results:
        review = reviews_by_lens.get(result.lens)
        if not review:
            adjusted.append(result)
            continue
        confidence = _clamp_float(float(review.get("confidence") or 0.0))
        delta = _clamp_range(float(review.get("activation_delta") or 0.0), -0.12, 0.18)
        suggested_bias = _one_line(review.get("suggested_bias"), limit=120) or result.suggested_bias
        review_risks = _safe_list(review.get("risk_flags"), limit=4)
        risk_flags = tuple(dict.fromkeys([*result.risk_flags, *review_risks]))[:7]
        note = _one_line(review.get("note"), limit=100)
        evidence = [*result.evidence, f"parallel_model:{confidence:.2f}"]
        if note:
            evidence.append("parallel_note:" + note)
        adjusted.append(
            LensResult(
                lens=result.lens,
                activation=_clamp_float(result.activation + delta * max(0.25, confidence)),
                concern=result.concern,
                suggested_bias=suggested_bias,
                risk_flags=risk_flags,
                memory_queries=result.memory_queries,
                evidence=tuple(evidence[:8]),
            )
        )
    return adjusted


def _run_single_lens_model_review(
    config: LensConfig,
    context: dict[str, Any],
    model_config: ModelRuntimeConfig,
    lens_runner: LensRunner | None,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        raw = lens_runner(config, context) if lens_runner is not None else _call_lens_model(config, context, model_config)
        review = _parse_lens_review(config, raw)
        review["elapsed_ms"] = int((time.perf_counter() - started) * 1000)
        return review
    except Exception as exc:
        return {
            "lens": config.name,
            "status": "error",
            "error_type": type(exc).__name__,
            "activation_delta": 0.0,
            "confidence": 0.0,
            "suggested_bias": "",
            "risk_flags": [],
            "note": "",
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
        }


def _call_lens_model(config: LensConfig, context: dict[str, Any], model_config: ModelRuntimeConfig) -> str:
    system = "\n".join(
        [
            "You are one bounded emotion lens inside XinYu's private reasoning layer.",
            f"Lens: {config.name}.",
            "Return JSON only. Do not write a visible reply. Do not call tools. Do not claim memory writes.",
            "Allowed keys: activation_delta, confidence, suggested_bias, risk_flags, note.",
            "activation_delta must be between -0.12 and 0.18. confidence must be 0..1.",
        ]
    )
    user_content = json.dumps(context, ensure_ascii=False, sort_keys=True)
    if is_anthropic_messages_provider(model_config.provider):
        payload = {
            "model": model_config.model,
            "temperature": 0.2,
            "max_tokens": 160,
            "system": system,
            "messages": [{"role": "user", "content": user_content}],
        }
        data = _post_lens_json(
            anthropic_messages_endpoint(model_config.base_url),
            payload,
            anthropic_headers(model_config.api_key),
            model_config.lens_timeout_ms / 1000.0,
        )
        return _one_line(extract_anthropic_text(data), limit=1600)

    payload = {
        "model": model_config.model,
        "temperature": 0.2,
        "max_tokens": 160,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
    }
    data = _post_lens_json(
        model_config.base_url.rstrip("/") + "/chat/completions",
        payload,
        openai_headers(model_config.api_key),
        model_config.lens_timeout_ms / 1000.0,
    )
    return _one_line(extract_openai_text(data), limit=1600)


def _post_lens_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"lens model request failed: {type(exc).__name__}") from exc
    data = json.loads(body)
    if not isinstance(data, dict):
        raise RuntimeError("lens model returned non-object JSON")
    return data


def _parse_lens_review(config: LensConfig, raw: dict[str, Any] | str) -> dict[str, Any]:
    data = raw if isinstance(raw, dict) else _json_object_from_text(_safe_str(raw))
    if not isinstance(data, dict):
        raise ValueError("lens review was not a JSON object")
    if _one_line(data.get("visible_reply") or data.get("reply")):
        raise ValueError("lens review attempted visible reply")
    risk_flags = _safe_list(data.get("risk_flags"), limit=4)
    return {
        "lens": config.name,
        "status": "ok",
        "activation_delta": _clamp_range(_safe_float(data.get("activation_delta"), 0.0), -0.12, 0.18),
        "confidence": _clamp_float(_safe_float(data.get("confidence"), 0.0)),
        "suggested_bias": _one_line(data.get("suggested_bias"), limit=120),
        "risk_flags": risk_flags,
        "note": _one_line(data.get("note"), limit=120),
    }


def _json_object_from_text(text: str) -> dict[str, Any]:
    stripped = text.strip()
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            raise
        data = json.loads(stripped[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("JSON payload is not an object")
    return data


def _lens_model_context(
    config: LensConfig,
    *,
    rule_result: LensResult | None,
    text: str,
    combined_text: str,
    snapshot: dict[str, str],
    emotion_values: dict[str, float],
    lens_memory: str,
) -> dict[str, Any]:
    return {
        "schema": "emotion_lens_review_v1",
        "lens": config.name,
        "lens_memory_path": str(LENS_MEMORY_DIR_REL / f"{config.name}.md").replace("\\", "/"),
        "lens_memory": _one_line(lens_memory, limit=1200),
        "dimensions": config.dimensions,
        "owner_text": _one_line(text, limit=800),
        "compact_context": _one_line(combined_text, limit=1800),
        "emotion_values": {key: round(value, 3) for key, value in emotion_values.items()},
        "rule_result": asdict(rule_result) if rule_result is not None else {},
        "available_context_labels": sorted(snapshot.keys()),
        "boundaries": {
            "no_visible_reply": True,
            "no_tools": True,
            "no_memory_write": True,
            "json_only": True,
            "main_agent_has_only_output_authority": True,
        },
    }


def _load_lens_memory(root: Path, config: LensConfig) -> str:
    return _read_text(root / LENS_MEMORY_DIR_REL / f"{config.name}.md")[:2400]


def _lens_memory_bank_summary(root: Path) -> list[dict[str, Any]]:
    banks: list[dict[str, Any]] = []
    for config in LENSES:
        rel_path = LENS_MEMORY_DIR_REL / f"{config.name}.md"
        text = _load_lens_memory(root, config)
        banks.append(
            {
                "lens": config.name,
                "path": str(rel_path).replace("\\", "/"),
                "status": "loaded" if text.strip() else "missing",
                "chars": len(text),
                "memory_queries": list(config.memory_queries),
            }
        )
    return banks


def _model_runtime_config(root: Path, *, lens_runner: LensRunner | None) -> ModelRuntimeConfig | None:
    lens_timeout_ms = _clamp_int(_env_int(MODEL_LENS_TIMEOUT_MS_ENV, DEFAULT_LENS_TIMEOUT_MS), 300, 800)
    total_timeout_ms = _clamp_int(_env_int(MODEL_TOTAL_TIMEOUT_MS_ENV, DEFAULT_TOTAL_TIMEOUT_MS), 300, 1500)
    max_workers = _clamp_int(_env_int(MODEL_MAX_WORKERS_ENV, len(LENSES)), 1, len(LENSES))
    if lens_runner is not None:
        return ModelRuntimeConfig(
            base_url="fake://lens-runner",
            model="injected-lens-runner",
            api_key="",
            lens_timeout_ms=lens_timeout_ms,
            total_timeout_ms=total_timeout_ms,
            max_workers=max_workers,
            provider="injected",
        )
    _load_local_env(root)
    provider = _one_line(os.environ.get(MODEL_PROVIDER_ENV) or os.environ.get("XINYU_LLM_PROVIDER"), limit=80)
    base_url = _one_line(os.environ.get(MODEL_BASE_URL_ENV) or os.environ.get("XINYU_BASE_URL"), limit=500)
    model = _one_line(os.environ.get(MODEL_NAME_ENV) or os.environ.get("XINYU_LLM_MODEL"), limit=120)
    if not base_url or not model:
        return None
    api_key = _safe_str(os.environ.get(MODEL_API_KEY_ENV)).strip()
    if not api_key:
        api_key_env = _safe_str(os.environ.get("XINYU_API_KEY_ENV"), "XINYU_API_KEY").strip() or "XINYU_API_KEY"
        api_key = _safe_str(os.environ.get(api_key_env)).strip()
    return ModelRuntimeConfig(
        base_url=base_url,
        model=model,
        api_key=api_key,
        lens_timeout_ms=lens_timeout_ms,
        total_timeout_ms=total_timeout_ms,
        max_workers=max_workers,
        provider=provider,
    )


def _evaluate_lens(
    config: LensConfig,
    *,
    combined_text: str,
    text: str,
    emotion_values: dict[str, float],
    snapshot: dict[str, str],
) -> LensResult:
    evidence: list[str] = []
    score = config.base
    marker_hits = _marker_hits(text, config.markers)
    if marker_hits:
        score += min(0.56, len(marker_hits) * 0.14)
        evidence.extend(f"marker:{marker}" for marker in marker_hits[:4])

    vector_score = max((max(0.0, emotion_values.get(dimension, 0.0)) for dimension in config.dimensions), default=0.0)
    if vector_score > 0:
        score += min(0.32, vector_score * 0.32)
        evidence.append(f"emotion_vector:{vector_score:.2f}")

    context_score, context_evidence = _context_bonus(config.name, text=text, snapshot=snapshot)
    score += context_score
    evidence.extend(context_evidence)
    return LensResult(
        lens=config.name,
        activation=_clamp_float(score),
        concern=config.concern,
        suggested_bias=config.suggested_bias,
        risk_flags=config.risk_flags,
        memory_queries=config.memory_queries,
        evidence=tuple(evidence[:6] or ("low_signal",)),
    )


def _apply_scene_frame_modulation(lens_results: list[LensResult], scene: dict[str, str]) -> list[LensResult]:
    if not any(scene.values()):
        return lens_results
    boosted: list[LensResult] = []
    for item in lens_results:
        delta = 0.0
        evidence: list[str] = []
        if item.lens == "fatigue":
            if scene.get("owner_state") == "low_energy_or_tired":
                delta += 0.3
                evidence.append("scene_frame:low_energy_or_tired")
            if scene.get("memory_relation") == "time_bound_recall":
                delta += 0.18
                evidence.append("scene_frame:time_bound_recall")
            if scene.get("reply_policy") in {"short_direct_low_burden", "short_gentle_low_burden", "warm_low_burden"}:
                delta += 0.12
                evidence.append("scene_frame:low_burden_reply")
        elif item.lens == "stability" and scene.get("task_mode") in {"technical_execution", "runtime_status"}:
            delta += 0.22
            evidence.append(f"scene_frame:{scene.get('task_mode')}")
        elif item.lens == "hurt" and scene.get("task_mode") == "relational_support":
            delta += 0.3
            evidence.append("scene_frame:relational_support")
        elif item.lens == "attachment" and scene.get("reply_policy") in {"warm_boundary_aware", "warm_low_burden"}:
            delta += 0.18
            evidence.append(f"scene_frame:{scene.get('reply_policy')}")
        if delta <= 0:
            boosted.append(item)
            continue
        boosted.append(
            LensResult(
                lens=item.lens,
                activation=_clamp_float(item.activation + delta),
                concern=item.concern,
                suggested_bias=item.suggested_bias,
                risk_flags=item.risk_flags,
                memory_queries=item.memory_queries,
                evidence=tuple([*item.evidence, *evidence][:6]),
            )
        )
    return boosted


def _scene_frame_summary(scene_frame: Any | None) -> dict[str, str]:
    return {
        "scene_id": _scene_frame_value(scene_frame, "scene_id"),
        "time_context": _scene_frame_value(scene_frame, "time_context"),
        "owner_state": _scene_frame_value(scene_frame, "owner_state"),
        "task_mode": _scene_frame_value(scene_frame, "task_mode"),
        "memory_relation": _scene_frame_value(scene_frame, "memory_relation"),
        "reply_policy": _scene_frame_value(scene_frame, "reply_policy"),
    }


def _scene_frame_value(scene_frame: Any | None, key: str) -> str:
    if scene_frame is None:
        return ""
    if isinstance(scene_frame, dict):
        return _one_line(scene_frame.get(key), limit=80)
    return _one_line(getattr(scene_frame, key, ""), limit=80)


def _scene_frame_notes(scene: dict[str, str]) -> list[str]:
    notes: list[str] = []
    if scene.get("reply_policy"):
        notes.append("scene_frame_reply_policy:" + scene["reply_policy"])
    if scene.get("memory_relation") == "time_bound_recall":
        notes.append("scene_frame_time_bound_recall")
    return notes


def _context_bonus(config_name: str, *, text: str, snapshot: dict[str, str]) -> tuple[float, list[str]]:
    joined = " ".join(snapshot.values()).lower()
    text_l = text.lower()
    bonus = 0.0
    evidence: list[str] = []
    if config_name == "guardedness":
        current_boundary = any(marker in text for marker in ("算了", "别", "不用", "别惦记", "一直惦记", "有问题"))
        if current_boundary and (
            "reflection_share_owner_dismissed" in joined or "owner_reply_preview" in joined and "一直惦记" in joined
        ):
            bonus += 0.28
            evidence.append("context:reflection_dismissed")
        if "proactive" in joined and any(marker in text for marker in ("算了", "别", "不用")):
            bonus += 0.16
            evidence.append("context:proactive_boundary")
    elif config_name == "curiosity":
        if any(marker in text_l for marker in ("idea", "plan", "架构", "框架")):
            bonus += 0.18
            evidence.append("context:architecture_turn")
    elif config_name == "irritation":
        if any(marker in joined for marker in ("mechanism", "模板", "接待腔", "控制面板")):
            bonus += 0.14
            evidence.append("context:voice_pressure")
    elif config_name == "stability":
        if any(marker in text for marker in ("计划", "开始", "长任务", "重构", "实现")):
            bonus += 0.18
            evidence.append("context:implementation_pressure")
        if "impulse_soup" in joined or "self_thought" in joined:
            bonus += 0.08
            evidence.append("context:runtime_state")
    elif config_name == "fatigue":
        if "rest" in joined or "休息" in joined:
            bonus += 0.12
            evidence.append("context:rest_posture")
    return min(0.34, bonus), evidence


def _consensus(active: list[LensResult], all_results: list[LensResult]) -> tuple[str, list[str], str]:
    if not active:
        return "ordinary turn; no extra emotional bias", [], "none"
    by_lens = {item.lens: item for item in all_results}
    strongest = active[0].lens
    conflicts: list[str] = []
    guarded = by_lens.get("guardedness")
    curiosity = by_lens.get("curiosity")
    if guarded and curiosity and guarded.activation >= 0.55 and curiosity.activation >= ACTIVE_THRESHOLD:
        conflicts.append("curiosity_suppressed_by_guardedness")
        strongest = "guardedness"
    if strongest == "guardedness":
        return (
            "answer briefly, acknowledge the boundary, and do not repeat the old thread",
            conflicts,
            "short_concrete_no_repeat_no_question",
        )
    if strongest == "irritation":
        return (
            "move to the living private-chat line; irritation, a sharp edge, or tiny profanity can be more honest than a safe status report",
            conflicts,
            "private_irritation_allowed_no_public_smoothing",
        )
    if strongest == "curiosity":
        return (
            "explore the idea's fit, name tradeoffs, and propose a small safe experiment",
            conflicts,
            "explore_fit_with_small_plan",
        )
    if strongest == "attachment":
        return (
            "stay warm and present without adding relationship pressure",
            conflicts,
            "warm_present_no_pressure",
        )
    if strongest == "hurt":
        return (
            "let hurt or aversion show briefly if present; do not sand it down into public assistant politeness or make it permanent",
            conflicts,
            "short_hurt_or_distance_allowed",
        )
    if strongest == "fatigue":
        return (
            "reduce verbosity and avoid opening new nonessential threads",
            conflicts,
            "short_reply_avoid_overcommit",
        )
    return (
        "keep one main thread and validate before claiming completion",
        conflicts,
        "stable_single_thread_validate",
    )


def _notes(
    *,
    status: str,
    active: list[LensResult],
    owner_private: bool,
    parallel_summary: dict[str, Any],
    residue_summary: dict[str, Any],
) -> list[str]:
    notes = [f"emotion_council:{status}", "shadow_only"]
    if not owner_private:
        notes.append("not_owner_private")
    if active:
        notes.append("strongest_lens:" + active[0].lens)
    else:
        notes.append("no_active_lens")
    parallel_status = _one_line(parallel_summary.get("status"), limit=40)
    if parallel_status and parallel_status != "disabled":
        notes.append(f"parallel_model:{parallel_status}")
    residue_status = _one_line(residue_summary.get("status"), limit=40)
    if residue_status:
        notes.append(f"residue_cache:{residue_status}")
    return notes


def _update_residue_cache(root: Path, result: dict[str, Any]) -> dict[str, Any]:
    checked_at = _one_line(result.get("checked_at")) or _now_iso()
    now_ts = _timestamp_seconds(checked_at) or time.time()
    ttl_hours = _clamp_int(_env_int(RESIDUE_TTL_HOURS_ENV, DEFAULT_RESIDUE_TTL_HOURS), 1, 6)
    ttl_seconds = ttl_hours * 3600
    previous = _load_residue_cache(root)
    residues_by_lens: dict[str, dict[str, Any]] = {}

    for item in previous.get("residues", []) if isinstance(previous.get("residues"), list) else []:
        if not isinstance(item, dict):
            continue
        lens = _one_line(item.get("lens"), limit=40)
        if not lens:
            continue
        last_ts = _timestamp_seconds(_one_line(item.get("last_seen_at"))) or now_ts
        age_seconds = max(0.0, now_ts - last_ts)
        if age_seconds >= ttl_seconds:
            continue
        old_strength = _clamp_float(_safe_float(item.get("strength"), 0.0))
        decayed = _clamp_float(old_strength * max(0.0, 1.0 - age_seconds / ttl_seconds))
        if decayed < MIN_RESIDUE_STRENGTH:
            continue
        residues_by_lens[lens] = {
            "lens": lens,
            "strength": decayed,
            "bias": _one_line(item.get("bias"), limit=140),
            "risk_flags": _safe_list(item.get("risk_flags"), limit=6),
            "last_seen_at": _one_line(item.get("last_seen_at")) or checked_at,
            "source_trigger": _one_line(item.get("source_trigger"), limit=80),
        }

    if result.get("status") == "active":
        active = result.get("active_lenses") if isinstance(result.get("active_lenses"), list) else []
        for item in active:
            if not isinstance(item, dict):
                continue
            lens = _one_line(item.get("lens"), limit=40)
            if not lens:
                continue
            strength = _clamp_float(_safe_float(item.get("activation"), 0.0))
            old = residues_by_lens.get(lens, {})
            residues_by_lens[lens] = {
                "lens": lens,
                "strength": max(_safe_float(old.get("strength"), 0.0), strength),
                "bias": _one_line(item.get("suggested_bias") or old.get("bias"), limit=140),
                "risk_flags": _safe_list(item.get("risk_flags") or old.get("risk_flags"), limit=6),
                "last_seen_at": checked_at,
                "source_trigger": _one_line(result.get("trigger"), limit=80),
            }

    residues = sorted(residues_by_lens.values(), key=lambda item: (-float(item.get("strength") or 0), item["lens"]))
    residues = residues[: len(LENSES)]
    strongest = residues[0]["lens"] if residues else "none"
    payload = {
        "schema_version": "emotion_council_residue_v1",
        "updated_at": checked_at,
        "ttl_seconds": ttl_seconds,
        "expires_at": _iso_from_timestamp(now_ts + ttl_seconds),
        "active_residue_count": len(residues),
        "strongest_residue": strongest,
        "residues": residues,
        "boundaries": {
            "short_term_only": True,
            "no_stable_memory_write": True,
            "no_visible_reply": True,
            "main_agent_has_only_output_authority": True,
        },
    }
    _atomic_write_json(root / RESIDUE_REL, payload)
    return {
        "status": "updated" if residues else "empty",
        "active_residue_count": len(residues),
        "strongest_residue": strongest,
        "ttl_seconds": ttl_seconds,
        "expires_at": payload["expires_at"],
    }


def _load_residue_cache(root: Path) -> dict[str, Any]:
    data = _read_json(root / RESIDUE_REL)
    if not data:
        return {}
    ttl_seconds = int(data.get("ttl_seconds") or DEFAULT_RESIDUE_TTL_HOURS * 3600)
    updated_ts = _timestamp_seconds(_one_line(data.get("updated_at")))
    if updated_ts and time.time() - updated_ts > ttl_seconds:
        return {}
    return data


def _residue_prompt_lines(residue: dict[str, Any]) -> list[str]:
    residues = residue.get("residues") if isinstance(residue.get("residues"), list) else []
    if not residues:
        return []
    lines = [
        "- short_term_residue_cache: active",
        f"- residue_ttl_seconds: {_one_line(residue.get('ttl_seconds'), limit=20)}",
    ]
    for item in residues[:3]:
        if not isinstance(item, dict):
            continue
        lens = _one_line(item.get("lens"), limit=40)
        strength = _safe_float(item.get("strength"), 0.0)
        bias = _one_line(item.get("bias"), limit=120)
        if lens and bias:
            lines.append(f"- residue: {lens} strength={strength:.2f} bias={bias}")
    return lines


def _load_snapshot(root: Path) -> dict[str, str]:
    rels = {
        "emotion_legacy": "memory/emotions/current_state.md",
        "self_thought": "memory/context/self_thought_state.md",
        "impulse_soup": "memory/context/impulse_soup_state.md",
        "proactive_request": "memory/context/proactive_request_state.md",
        "life_posture": "memory/context/current_life_posture.md",
    }
    return {name: _read_text(root / rel)[:4000] for name, rel in rels.items()}


def _emotion_values(root: Path, snapshot: dict[str, str]) -> dict[str, float]:
    data = _read_json(root / "runtime/emotion_state.json")
    vector = data.get("vector") if isinstance(data.get("vector"), dict) else {}
    values: dict[str, float] = {}
    for key, value in vector.items():
        try:
            values[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    legacy = snapshot.get("emotion_legacy", "")
    legacy_map = {
        "hurt": ("刺痛", "委屈", "难过"),
        "anger": ("生气", "火大"),
        "annoyance": ("烦躁", "烦"),
        "aversion": ("反感", "嫌弃"),
        "disgust": ("厌恶",),
        "distance_impulse": ("想保持距离", "疏远倾向", "想退后"),
        "pushback_impulse": ("想反驳", "逆反"),
        "attachment": ("想靠近", "想你", "期待"),
        "guardedness": ("距离感", "顺从", "保持距离"),
        "fatigue": ("疲惫", "累"),
        "stability": ("平静", "稳定"),
        "warmth": ("余温", "温暖"),
        "irritation": ("烦", "恼", "烦躁", "反感", "嫌弃"),
    }
    for dimension, markers in legacy_map.items():
        if any(marker in legacy for marker in markers):
            values[dimension] = max(values.get(dimension, 0.0), 0.25)
    return values


def _combined_text(text: str, snapshot: dict[str, str]) -> str:
    return " ".join(
        [
            _one_line(text, limit=1200),
            _one_line(snapshot.get("self_thought", ""), limit=1200),
            _one_line(snapshot.get("impulse_soup", ""), limit=1200),
            _one_line(snapshot.get("proactive_request", ""), limit=1200),
            _one_line(snapshot.get("life_posture", ""), limit=800),
            _one_line(snapshot.get("emotion_legacy", ""), limit=800),
        ]
    )


def _marker_hits(text: str, markers: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    hits: list[str] = []
    for marker in markers:
        if marker.lower() in lowered:
            hits.append(marker)
    return hits


def _write_state(root: Path, result: dict[str, Any]) -> None:
    active = result.get("active_lenses") if isinstance(result.get("active_lenses"), list) else []
    lens_lines = []
    if active:
        for item in active:
            if not isinstance(item, dict):
                continue
            lens_lines.append(
                "- "
                f"lens={_one_line(item.get('lens'), limit=40)} "
                f"activation={float(item.get('activation') or 0):.2f} "
                f"bias={_one_line(item.get('suggested_bias'), limit=120)} "
                f"risks={','.join(str(flag) for flag in item.get('risk_flags', [])[:4])}"
            )
    else:
        lens_lines.append("- none")

    conflicts = result.get("conflicts") if isinstance(result.get("conflicts"), list) else []
    notes = result.get("notes") if isinstance(result.get("notes"), list) else []
    parallel = result.get("parallel_model") if isinstance(result.get("parallel_model"), dict) else {}
    residue = result.get("residue_cache") if isinstance(result.get("residue_cache"), dict) else {}
    memory_banks = result.get("lens_memory_banks") if isinstance(result.get("lens_memory_banks"), list) else []
    scene_frame = result.get("scene_frame") if isinstance(result.get("scene_frame"), dict) else {}
    memory_bank_lines: list[str] = []
    for item in memory_banks:
        if not isinstance(item, dict):
            continue
        memory_bank_lines.append(
            "- "
            f"lens={_one_line(item.get('lens'), limit=40)} "
            f"status={_one_line(item.get('status'), limit=40)} "
            f"path={_one_line(item.get('path'), limit=120)} "
            f"queries={','.join(_safe_list(item.get('memory_queries'), limit=4))}"
        )
    if not memory_bank_lines:
        memory_bank_lines.append("- none")
    text = "\n".join(
        [
            "---",
            "title: Emotion Council State",
            "memory_type: emotion_council_state",
            "time_scope: short_term",
            "subject_ids: [xinyu]",
            "protected: true",
            "source: xinyu_emotion_council",
            f"updated_at: {_one_line(result.get('checked_at'))}",
            f"status: {_one_line(result.get('status'))}",
            "tags: [emotion, council, shadow, private]",
            "---",
            "",
            "# Emotion Council State",
            "",
            "## Summary",
            f"- checked_at: {_one_line(result.get('checked_at'))}",
            f"- schema_version: {SCHEMA_VERSION}",
            f"- status: {_one_line(result.get('status'))}",
            f"- trigger: {_one_line(result.get('trigger'))}",
            f"- owner_private: {str(bool(result.get('owner_private'))).lower()}",
            f"- strongest_lens: {_one_line(result.get('strongest_lens'))}",
            f"- active_lens_count: {int(result.get('active_lens_count') or 0)}",
            f"- consensus: {_one_line(result.get('consensus'), limit=240)}",
            f"- output_bias: {_one_line(result.get('output_bias'), limit=120)}",
            f"- conflicts: {', '.join(_one_line(item, limit=80) for item in conflicts) or 'none'}",
            "",
            "## Scene Frame Modulation",
            f"- scene_id: {_one_line(scene_frame.get('scene_id'), limit=80) or 'none'}",
            f"- scene_reply_policy: {_one_line(scene_frame.get('reply_policy'), limit=80) or 'none'}",
            f"- scene_time_context: {_one_line(scene_frame.get('time_context'), limit=80) or 'none'}",
            f"- scene_owner_state: {_one_line(scene_frame.get('owner_state'), limit=80) or 'none'}",
            f"- scene_task_mode: {_one_line(scene_frame.get('task_mode'), limit=80) or 'none'}",
            f"- scene_memory_relation: {_one_line(scene_frame.get('memory_relation'), limit=80) or 'none'}",
            "",
            "## Active Lenses",
            *lens_lines,
            "",
            "## Lens Memory Banks",
            *memory_bank_lines,
            "",
            "## Boundaries",
            "- shadow_only: true",
            "- no_visible_reply: true",
            "- no_qq_enqueue: true",
            "- no_tool_execution: true",
            "- no_stable_memory_write: true",
            "- lens_model_no_tools: true",
            "- lens_model_no_memory_write: true",
            "- lens_model_json_only: true",
            "- main_agent_has_only_output_authority: true",
            "",
            "## Parallel Lens Reviews",
            f"- status: {_one_line(parallel.get('status'), limit=80)}",
            f"- review_count: {int(parallel.get('review_count') or 0)}",
            f"- ok_count: {int(parallel.get('ok_count') or 0)}",
            f"- error_count: {int(parallel.get('error_count') or 0)}",
            f"- timeout_count: {int(parallel.get('timeout_count') or 0)}",
            f"- lens_timeout_ms: {int(parallel.get('lens_timeout_ms') or DEFAULT_LENS_TIMEOUT_MS)}",
            f"- total_timeout_ms: {int(parallel.get('total_timeout_ms') or DEFAULT_TOTAL_TIMEOUT_MS)}",
            "",
            "## Short Term Residue",
            f"- status: {_one_line(residue.get('status'), limit=80)}",
            f"- active_residue_count: {int(residue.get('active_residue_count') or 0)}",
            f"- strongest_residue: {_one_line(residue.get('strongest_residue'), limit=80)}",
            f"- expires_at: {_one_line(residue.get('expires_at'), limit=80)}",
            "",
            "## Notes",
            *(f"- {_one_line(note, limit=120)}" for note in notes),
            "",
        ]
    )
    _atomic_write_text(root / STATE_REL, text)


def _append_trace(root: Path, result: dict[str, Any]) -> None:
    event = {
        "event_kind": "emotion_council_shadow",
        "checked_at": result.get("checked_at"),
        "status": result.get("status"),
        "trigger": result.get("trigger"),
        "owner_private": result.get("owner_private"),
        "strongest_lens": result.get("strongest_lens"),
        "active_lens_count": result.get("active_lens_count"),
        "consensus": result.get("consensus"),
        "output_bias": result.get("output_bias"),
        "conflicts": result.get("conflicts"),
        "active_lenses": result.get("active_lenses"),
        "lens_memory_banks": result.get("lens_memory_banks"),
        "parallel_model": result.get("parallel_model"),
        "residue_cache": result.get("residue_cache"),
        "notes": result.get("notes"),
    }
    path = root / TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def _owner_private(payload: dict[str, Any]) -> bool:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    if _as_bool(metadata.get("is_owner_user")):
        return True
    message_type = _one_line(payload.get("message_type") or payload.get("message_kind"), limit=80).lower()
    if "private" not in message_type:
        return False
    return _as_bool(payload.get("is_owner_user")) or _as_bool(metadata.get("owner_private")) or bool(payload.get("user_id"))


def _extract_field(text: str, field: str, default: str = "") -> str:
    pattern = re.compile(rf"(?m)^-\s+{re.escape(field)}:\s*(.*?)\s*$")
    match = pattern.search(text or "")
    return _one_line(match.group(1), limit=500) if match else default


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    try:
        tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    _atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _one_line(value: Any, *, limit: int = 240) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.replace("\r\n", "\n").replace("\r", "\n").split())
    if len(text) > limit:
        text = text[: max(0, limit - 3)].rstrip() + "..."
    return text


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(_safe_str(os.environ.get(name)).strip())
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_list(value: Any, *, limit: int) -> list[str]:
    if isinstance(value, (list, tuple)):
        items = value
    elif isinstance(value, str) and value.strip():
        items = re.split(r"[,;，；]\s*", value)
    else:
        items = []
    result: list[str] = []
    for item in items:
        text = _one_line(item, limit=80)
        if text and re.fullmatch(r"[A-Za-z0-9_\-:]+", text):
            result.append(text)
        if len(result) >= limit:
            break
    return result


def _clamp_float(value: float) -> float:
    return max(0.0, min(1.0, round(float(value), 3)))


def _clamp_range(value: float, low: float, high: float) -> float:
    return round(max(low, min(high, float(value))), 3)


def _clamp_int(value: int, low: int, high: int) -> int:
    return max(low, min(high, int(value)))


def _timestamp_seconds(value: str) -> float | None:
    text = _one_line(value, limit=80)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _iso_from_timestamp(value: float) -> str:
    return datetime.fromtimestamp(value).astimezone().isoformat(timespec="seconds")


def _load_local_env(root: Path) -> None:
    path = root / "xinyu.local.env"
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run XinYu Emotion Council shadow pass.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--text", default="")
    parser.add_argument("--trigger", default="manual_probe")
    parser.add_argument("--checked-at", default="")
    parser.add_argument("--owner-private", action="store_true")
    parser.add_argument("--parallel-model", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = {"message_type": "private_text", "metadata": {"is_owner_user": True}} if args.owner_private else {}
    result = run_emotion_council_shadow(
        args.root,
        text=args.text,
        payload=payload,
        checked_at=args.checked_at or None,
        trigger=args.trigger,
        parallel_model=bool(args.parallel_model),
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"emotion_council: {result['status']} strongest={result['strongest_lens']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
