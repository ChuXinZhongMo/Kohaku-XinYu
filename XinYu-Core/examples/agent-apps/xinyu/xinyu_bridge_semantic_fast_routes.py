from __future__ import annotations

import time
from contextlib import nullcontext
from datetime import datetime
from typing import Any

import v1_canary_gate
from xinyu_bridge_memory_snapshot import memory_snapshot as _memory_snapshot
from xinyu_bridge_reply_text import normalize_bridge_reply
from xinyu_runtime_presence import record_turn_finished
from xinyu_sent_reply_index import visible_text_hash
from xinyu_turn_route_trace import record_turn_route_stage
from xinyu_visible_reply_guard import dedupe_visible_reply


SEMANTIC_FAST_ALLOWED_INTENTS = frozenset(
    {"greeting", "ack", "reply_quality_complaint", "runtime_status_question", "owner_state_question"}
)

_REPLY_QUALITY_COMPLAINT_MARKERS = (
    "\u4f60\u5728\u8bf4\u4ec0\u4e48",
    "\u7b54\u975e\u6240\u95ee",
    "\u4ec0\u4e48\u60c5\u51b5",
    "\u6ca1\u53cd\u5e94",
    "\u4e0d\u56de\u8bdd",
    "\u4e0d\u56de\u6d88\u606f",
    "\u600e\u4e48\u8fd9\u4e48\u4e45",
    "\u8fd9\u4e48\u4e45\u624d\u56de",
    "\u524d\u53f0\u6b63\u5728\u56de\u590d",
    "\u6b63\u5728\u56de\u590d",
    "\u6ca1\u6709\u7136\u540e",
    "\u6839\u672c\u6ca1\u56de",
    "\u6ca1\u56de\u6211",
    "\u5957\u6a21\u677f",
    "\u592a\u6a21\u677f",
    "\u8bdd\u672f\u6a21\u677f",
    "\u8d8a\u6539\u8d8a\u51fa\u95ee\u9898",
    "\u4f60\u5728\u5e72\u561b",
    "what are you talking about",
    "why so slow",
)
_RUNTIME_STATUS_MARKERS = (
    "\u540e\u53f0\u5728\u8dd1",
    "\u540e\u53f0\u8dd1",
    "\u5728\u8dd1\u4ec0\u4e48",
    "\u8dd1\u4ec0\u4e48\u4e1c\u897f",
    "\u8fd0\u884c\u72b6\u6001",
    "core \u72b6\u6001",
    "core\u72b6\u6001",
    "qq \u72b6\u6001",
    "qq\u72b6\u6001",
    "napcat \u72b6\u6001",
    "napcat\u72b6\u6001",
    "\u67e5\u4e00\u4e0b\u72b6\u6001",
    "/status",
    "what is running",
)
_OWNER_STATE_QUESTION_MARKERS = (
    "\u8fd8\u597d\u5417",
    "\u8fd8\u597d\u4e48",
    "\u8fd8\u597d\u561b",
    "\u4f60\u600e\u4e48\u6837",
    "\u4f60\u73b0\u5728\u600e\u4e48\u6837",
    "\u73b0\u5728\u600e\u4e48\u6837",
    "\u611f\u89c9\u600e\u4e48\u6837",
    "\u611f\u89c9\u5982\u4f55",
    "\u5fc3\u60c5\u600e\u4e48\u6837",
    "\u72b6\u6001\u600e\u4e48\u6837",
    "\u72b6\u6001\u5982\u4f55",
    "\u4ec0\u4e48\u72b6\u6001",
    "\u4f60\u73b0\u5728\u4ec0\u4e48\u72b6\u6001",
)
_OWNER_STATE_FAST_MAX_CHARS = 24
_OWNER_STATE_EMPTY_REPLY_NOTICES = (
    "\u8fd9\u8f6e\u4e3b\u6a21\u578b\u6ca1\u751f\u6210\u51fa\u80fd\u53d1\u7684\u56de\u590d\uff0c\u4e0d\u662f\u4f60\u6d88\u606f\u6ca1\u5230\u3002",
    "\u8fd9\u6761\u6211\u6536\u5230\u4e86\uff0c\u4f46\u6a21\u578b\u90a3\u8f6e\u6ca1\u5410\u51fa\u53ef\u89c1\u56de\u590d\u3002",
    "\u521a\u624d\u65ad\u5728\u751f\u6210\u4e0a\uff0c\u4e0d\u662f QQ \u6ca1\u6536\u5230\uff1b\u8fd9\u8f6e\u522b\u7ee7\u7eed\u7b49\u3002",
)
_CONFUSION_ONLY_MARKERS = ("??", "???", "????", "\uff1f\uff1f", "\uff1f\uff1f\uff1f", "\uff1f\uff1f\uff1f\uff1f")
_STALE_PLAN_REPLY_MARKERS = (
    "\u5148\u628a\u8303\u56f4\u538b\u5c0f",
    "\u672c\u5730\u53ef\u8fd0\u884c",
    "\u53ef\u56de\u6eda",
    "\u6700\u5c0f\u53ef\u8fd0\u884c",
    "\u4e3b\u94fe\u8def",
    "shadow",
)


def _compact_text(text: str) -> str:
    return "".join(text.split())


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in markers)


def _repair_intents_for_text(text: str) -> tuple[str, ...]:
    compact = _compact_text(text)
    if not compact:
        return ()
    intents: list[str] = []
    if _contains_any(compact, _RUNTIME_STATUS_MARKERS):
        intents.append("runtime_status_question")
    if _contains_any(compact, _REPLY_QUALITY_COMPLAINT_MARKERS) or compact in _CONFUSION_ONLY_MARKERS:
        intents.append("reply_quality_complaint")
    return tuple(intents)


def _looks_like_owner_state_question(text: str) -> bool:
    compact = _compact_text(text)
    if not compact:
        return False
    return any(marker in compact for marker in _OWNER_STATE_QUESTION_MARKERS)


def owner_private_empty_state_notice(text: str, *, seed: str = "") -> str:
    if not _looks_like_owner_state_question(text):
        return ""
    basis = _compact_text(seed or text)
    index = sum(ord(char) for char in basis) % len(_OWNER_STATE_EMPTY_REPLY_NOTICES)
    return _OWNER_STATE_EMPTY_REPLY_NOTICES[index]


def owner_private_direct_repair_reply(runtime: Any, text: str, intents: tuple[str, ...] | None = None) -> str:
    del runtime
    detected = tuple(intents or _repair_intents_for_text(text))
    if "runtime_status_question" in detected:
        return (
            "\u540e\u53f0\u5728\u5904\u7406\u5f53\u524d\u8fd9\u6761\u79c1\u804a\uff1b"
            "\u521a\u624d\u6162\u662f core \u8d70\u4e86\u6162\u94fe\u8def\uff0c"
            "\u4e0d\u662f QQ \u6ca1\u6536\u5230\u3002"
        )
    if "reply_quality_complaint" in detected:
        if _contains_any(
            _compact_text(text),
            ("\u600e\u4e48\u8fd9\u4e48\u4e45", "\u8fd9\u4e48\u4e45\u624d\u56de", "why so slow"),
        ):
            return (
                "\u4e0d\u662f\u6ca1\u6536\u5230\uff0c"
                "\u662f\u521a\u624d\u90a3\u8f6e\u8fdb\u4e86\u6162\u94fe\u8def\uff1b"
                "\u8fd9\u53e5\u6211\u5148\u6309\u4f60\u5f53\u524d\u95ee\u9898\u56de\u3002"
            )
        return (
            "\u521a\u624d\u90a3\u53e5\u63a5\u9519\u4e86\uff0c"
            "\u662f\u65e7\u4e0a\u4e0b\u6587\u4e32\u8fdb\u6765\u4e86\uff1b"
            "\u8fd9\u53e5\u6211\u6309\u4f60\u5f53\u524d\u95ee\u9898\u6765\u3002"
        )
    return _ordinary_private_repair_reply(text)


def _ordinary_private_repair_reply(text: str) -> str:
    compact = _compact_text(text)
    if not compact:
        return "\u6211\u5728\u3002"
    if any(marker in compact for marker in ("\u4e0d\u5435", "\u65e9\u70b9\u7761", "\u65e9\u7761", "\u4f11\u606f")):
        return "\u55ef\uff0c\u6211\u6536\u4f4f\u3002\u4f60\u4e5f\u65e9\u70b9\u7761\u3002"
    if any(marker in compact for marker in ("\u51cc\u6668", "\u592a\u665a", "\u5f88\u665a")):
        return "\u55ef\uff0c\u592a\u665a\u4e86\u3002\u4f60\u5148\u7761\u3002"
    if any(marker in compact for marker in ("\u56f0", "\u7761", "\u7d2f", "\u6ca1\u7cbe\u795e")):
        if "?" in text or "\uff1f" in text:
            return "\u6709\u70b9\u3002\u4f60\u4e5f\u65e9\u70b9\u7761\u3002"
        return "\u55ef\uff0c\u5148\u4e0d\u786c\u804a\u4e86\u3002"
    if "?" in text or "\uff1f" in text:
        return "\u8fd9\u53e5\u6211\u521a\u624d\u63a5\u9519\u4e86\u3002\u4f60\u518d\u95ee\u4e00\u904d\uff0c\u6211\u6309\u73b0\u5728\u8fd9\u53e5\u6765\u3002"
    if len(compact) <= 8:
        return "\u55ef\uff0c\u6211\u5728\u3002"
    return "\u8fd9\u53e5\u6211\u521a\u624d\u4e32\u5230\u65e7\u8bed\u5883\u4e86\u3002\u6211\u5148\u6536\u56de\u6765\u3002"


def reply_looks_like_stale_plan_residue(reply: str) -> bool:
    compact = _compact_text(reply)
    if not compact:
        return False
    hits = sum(1 for marker in _STALE_PLAN_REPLY_MARKERS if marker.lower() in compact.lower())
    return hits >= 2


def _direct_greeting_ack_reply(text: str, intents: tuple[str, ...]) -> str:
    compact = _compact_text(text)
    lowered = compact.lower()
    if any(marker in compact for marker in ("\u4e2d\u5348\u597d",)):
        return "\u4e2d\u5348\u597d\u3002"
    if any(marker in compact for marker in ("\u4e0b\u5348\u597d",)):
        return "\u4e0b\u5348\u597d\u3002"
    if any(marker in compact for marker in ("\u665a\u4e0a\u597d",)):
        return "\u665a\u4e0a\u597d\u3002"
    if any(marker in compact for marker in ("\u65e9\u4e0a\u597d", "\u65e9\u5b89", "\u65e9")):
        return "\u65e9\u3002"
    if any(marker in compact for marker in ("\u665a\u5b89",)):
        return "\u665a\u5b89\u3002"
    if any(marker in compact for marker in ("\u4f60\u597d", "\u5728\u5417")) or lowered in {"hi", "hello", "hey"}:
        return "\u5728\u3002"
    if "greeting" in intents:
        return "\u5728\u3002"
    return "\u55ef\u3002"


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default


def _timestamp_or_now_iso(value: Any = None) -> str:
    text = _safe_str(value).strip()
    if not text:
        return datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now().astimezone().isoformat(timespec="seconds")
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone().isoformat(timespec="seconds")


def _command_id(payload: dict[str, Any]) -> str:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    return _safe_str(metadata.get("desktop_command_id") or payload.get("command_id"))


def _provider_failover_context(provider: Any, context: dict[str, Any] | None) -> Any:
    if provider is None or not context:
        return nullcontext()
    try:
        from xinyu_runtime.llm.failover import provider_failover_context
    except ModuleNotFoundError:
        return nullcontext()
    return provider_failover_context(provider, context)


def ensure_v1_app(runtime: Any) -> Any:
    if runtime._v1_app is not None:
        return runtime._v1_app
    from xinyu_v1.app import XinYuV1App
    from xinyu_v1.config import XinYuV1Config

    runtime._v1_app = XinYuV1App(XinYuV1Config.load(runtime.xinyu_dir))
    return runtime._v1_app


def owner_private_semantic_fast_decision(runtime: Any, payload: dict[str, Any], text: str) -> dict[str, Any]:
    if not getattr(runtime, "owner_private_semantic_fast_route", True):
        return {"allowed": False, "notes": ["owner_private_semantic_fast_route_disabled"]}
    if not runtime._owner_private_payload_matches(payload):
        return {"allowed": False, "notes": ["not_owner_private"]}
    if v1_canary_gate.payload_has_attachment_signal(payload):
        return {"allowed": False, "notes": ["attachment_present"]}
    raw_text = _safe_str(text)
    compact = "".join(raw_text.split())
    if not compact:
        return {"allowed": False, "notes": ["empty_text"]}
    if "\n" in raw_text or "\r" in raw_text:
        return {"allowed": False, "notes": ["multiline_text"]}

    repair_intents = _repair_intents_for_text(raw_text)
    if "reply_quality_complaint" in repair_intents:
        return {
            "allowed": False,
            "intents": repair_intents,
            "notes": [
                "reply_quality_complaint_needs_live_model",
                "semantic_fast_not_low_risk",
                f"semantic_fast_intents:{','.join(repair_intents)}",
            ],
        }
    if repair_intents and len(compact) <= 64:
        reply = owner_private_direct_repair_reply(runtime, raw_text, repair_intents)
        return {
            "allowed": True,
            "route": "fast_path",
            "intents": repair_intents,
            "reasons": ("owner_private_live_repair",),
            "direct_reply": reply,
            "notes": ["semantic_fast_allowed", f"semantic_fast_intents:{','.join(repair_intents)}"],
        }
    if _looks_like_owner_state_question(raw_text):
        if len(compact) <= _OWNER_STATE_FAST_MAX_CHARS:
            return {
                "allowed": True,
                "route": "fast_path",
                "intents": ("owner_state_question",),
                "reasons": ("owner_private_state_question_live_renderer",),
                "direct_reply": "",
                "notes": [
                    "semantic_fast_allowed",
                    "semantic_fast_intents:owner_state_question",
                    "owner_state_question_live_renderer_required",
                ],
            }
        return {
            "allowed": False,
            "notes": ["owner_state_question_needs_live_model", "semantic_fast_not_low_risk"],
        }
    if len(compact) > 20:
        return {"allowed": False, "notes": ["text_too_long_for_semantic_fast_route"]}

    app = ensure_v1_app(runtime)
    v1_payload = dict(payload)
    v1_payload.setdefault("text", text)
    metadata = v1_payload.get("metadata")
    v1_payload["metadata"] = dict(metadata) if isinstance(metadata, dict) else {}
    v1_payload["metadata"]["is_owner_user"] = True
    v1_payload["metadata"]["v1_semantic_fast_source"] = "xinyu_core_bridge"
    turn = app.normalizer.normalize(v1_payload)
    decision = app.router.decide(turn)
    classification = decision.classification
    route = _safe_str(getattr(decision.route, "value", decision.route))
    intents = tuple(_safe_str(intent) for intent in classification.intents)
    intent_set = {intent for intent in intents if intent}
    if (
        route == "fast_path"
        and intent_set
        and intent_set.issubset(SEMANTIC_FAST_ALLOWED_INTENTS)
        and not classification.needs_model
        and not classification.needs_memory
    ):
        notes = ["semantic_fast_allowed", f"semantic_fast_intents:{','.join(intents)}"]
        if "greeting" in intent_set:
            reply = ""
            notes.append("owner_greeting_live_renderer_required")
        else:
            reply = _direct_greeting_ack_reply(raw_text, intents)
        return {
            "allowed": True,
            "route": route,
            "intents": intents,
            "reasons": tuple(_safe_str(reason) for reason in decision.reasons),
            "direct_reply": reply,
            "notes": notes,
        }
    return {
        "allowed": False,
        "route": route,
        "intents": intents,
        "reasons": tuple(_safe_str(reason) for reason in decision.reasons),
        "notes": ["semantic_fast_not_low_risk", f"semantic_fast_intents:{','.join(intents) or 'none'}"],
    }


async def handle_owner_private_semantic_fast_turn(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session: Any | None,
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
    started = time.perf_counter()
    if decision is None:
        try:
            decision = owner_private_semantic_fast_decision(runtime, payload, text)
        except Exception as exc:
            print(f"[xinyu_core_bridge] semantic fast route failed: {type(exc).__name__}: {exc}", flush=True)
            return None
    if not decision.get("allowed"):
        return None
    if record_decision_stage:
        record_turn_route_stage(
            runtime.xinyu_dir,
            turn_id=turn_id,
            stage="route_decided",
            route="owner_private_semantic_fast",
            status="accepted",
            elapsed_ms=int((time.perf_counter() - turn_started_at) * 1000),
            payload=payload,
            notes=[_safe_str(note) for note in decision.get("notes", [])[:4]],
        )

    renderer_name = "direct"
    reply = _safe_str(decision.get("direct_reply")).strip()
    if not reply:
        if session is None:
            return None
        renderer_name = "outward_reply"
        try:
            llm = getattr(session.agent, "llm", None)
            failover_context = None
            failover_builder = getattr(runtime, "_owner_private_llm_failover_context", None)
            if callable(failover_builder):
                try:
                    failover_context = failover_builder(
                        payload,
                        text=text,
                        session_key=session_key,
                        turn_id=turn_id,
                    )
                except Exception:
                    failover_context = None
            context_manager = (
                _provider_failover_context(llm, failover_context)
                if llm is not None and failover_context
                else nullcontext()
            )
            with context_manager:
                rendered = await runtime._render_outward_reply(
                    session.agent,
                    payload=payload,
                    user_text=text,
                    draft_reply="",
                    canonical_recall_context="",
                )
        except Exception as exc:
            print(f"[xinyu_core_bridge] semantic fast renderer failed: {type(exc).__name__}: {exc}", flush=True)
            return None

        reply = _safe_str(rendered).strip()
        if not reply:
            reply = owner_private_empty_state_notice(text, seed=turn_id)
            if not reply:
                return None
            renderer_name = "empty_state_notice"

    guarded_reply, guard_flags = runtime.speech_controller.final_reply_guard(
        payload=payload,
        user_text=text,
        reply=reply,
    )
    if not guarded_reply:
        return None
    reply = normalize_bridge_reply(guarded_reply)
    visible_dedupe = dedupe_visible_reply(reply)
    reply = visible_dedupe.text
    if not reply:
        return None

    if session is not None:
        try:
            runtime._replace_last_assistant_message(session.agent, reply)
        except Exception:
            pass
        try:
            runtime._append_dialogue_tail(session, user_text=text, reply=reply, payload=payload)
        except Exception as exc:
            print(f"[xinyu_core_bridge] semantic fast dialogue tail failed: {type(exc).__name__}: {exc}", flush=True)

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    total_elapsed_ms = int((time.perf_counter() - turn_started_at) * 1000)
    intents = tuple(_safe_str(intent) for intent in decision.get("intents", ()))
    notes: list[str] = [
        "owner_private_semantic_fast_intercepted",
        f"semantic_fast_route:{_safe_str(decision.get('route'), 'fast_path')}",
        f"semantic_fast_elapsed_ms:{elapsed_ms}",
    ]
    if intents:
        notes.append(f"semantic_fast_intents:{','.join(intents)}")
    if renderer_name == "direct":
        notes.append("semantic_fast_direct_reply")
    notes.extend(_safe_str(note) for note in decision.get("notes", [])[:3])
    notes.extend(_safe_str(note) for note in event_sidecar.get("notes", [])[:3])
    if guard_flags:
        notes.append("final_reply_guard_flags:" + ",".join(guard_flags[:3]))
    notes.extend(_safe_str(note) for note in visible_dedupe.notes[:3])
    if cleanup.get("cleaned_sessions"):
        notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")

    if before_memory is None:
        memory_changed = False
        notes.append("semantic_fast_memory_snapshot_skipped")
    else:
        after_memory = _memory_snapshot(runtime.memory_root)
        memory_changed = before_memory != after_memory
    record_turn_finished(
        runtime.xinyu_dir,
        turn_id=turn_id,
        reply=reply,
        elapsed_ms=total_elapsed_ms,
        status="ok",
        notes=notes,
        memory_changed=memory_changed,
    )
    record_turn_route_stage(
        runtime.xinyu_dir,
        turn_id=turn_id,
        stage="route_finished",
        route="owner_private_semantic_fast",
        status="ok",
        elapsed_ms=total_elapsed_ms,
        payload=payload,
        notes=notes[:8],
    )
    reply_hash = visible_text_hash(reply)
    await runtime._desktop_publish_chat_finished(
        payload,
        text=text,
        reply=reply,
        session_key=session_key,
        turn_id=turn_id,
        started_at=_timestamp_or_now_iso(turn_started_wall),
        elapsed_ms=total_elapsed_ms,
        status="ok",
        notes=notes,
        memory_changed=memory_changed,
        archive_message_ids=[],
        reply_hash=reply_hash,
        recall_event_id="",
        recall_count=0,
        top_recall_sources=[],
    )
    return {
        "accepted": True,
        "reply": reply,
        "memory_changed": memory_changed,
        "turn_id": turn_id,
        "command_id": _command_id(payload),
        "session_id": session_key,
        "reply_hash": reply_hash,
        "archive_message_ids": [],
        "archive_assistant_message_id": "",
        "semantic_fast": {
            "scope": "owner_private_direct_fast" if renderer_name == "direct" else "owner_private_live_fast",
            "route": _safe_str(decision.get("route"), "fast_path"),
            "intents": list(intents),
            "elapsed_ms": elapsed_ms,
            "renderer": renderer_name,
        },
        "notes": notes,
    }
