from __future__ import annotations

from collections.abc import Callable
from typing import Any


TraceRouteStage = Callable[..., Any]


async def apply_final_reply_guard(
    runtime: Any,
    session: Any,
    payload: dict[str, Any],
    *,
    reply: str,
    user_text: str,
    recalled_context: Any,
    trace_route_stage: TraceRouteStage,
    codex_delegate_blocked: bool,
    render_func: Callable[..., Any],
    expression_record_func: Callable[..., dict[str, Any]],
    safe_str_func: Callable[..., str],
    dedupe_func: Callable[[list[str]], list[str]],
) -> dict[str, Any]:
    guarded_reply, final_guard_flags = runtime.speech_controller.final_reply_guard(
        payload=payload,
        user_text=user_text,
        reply=reply,
    )
    expression_learning: dict[str, Any] = {"notes": []}
    critical_guard_flags = runtime._critical_final_guard_flags(final_guard_flags)
    if critical_guard_flags and not codex_delegate_blocked:
        bad_reply = reply
        repaired_reply = await render_func(
            runtime._render_outward_reply,
            session.agent,
            payload=payload,
            user_text=user_text,
            draft_reply=bad_reply,
            canonical_recall_context=safe_str_func(getattr(recalled_context, "prompt_block", "")),
            reason="final_guard_repair",
            trace_route_stage=trace_route_stage,
        )
        repaired_guarded, repaired_flags = runtime.speech_controller.final_reply_guard(
            payload=payload,
            user_text=user_text,
            reply=repaired_reply,
        )
        if repaired_guarded and not runtime._critical_final_guard_flags(repaired_flags):
            guarded_reply = repaired_guarded
            final_guard_flags = dedupe_func(
                list(final_guard_flags or []) + ["final_guard_repair_rendered"] + list(repaired_flags or [])
            )
            runtime._replace_last_assistant_message(session.agent, repaired_guarded)
        else:
            if guarded_reply:
                final_guard_flags = dedupe_func(
                    list(final_guard_flags or [])
                    + ["final_guard_repair_fallback_naturalized"]
                    + list(repaired_flags or [])
                )
            else:
                guarded_reply = ""
                final_guard_flags = dedupe_func(
                    list(final_guard_flags or [])
                    + ["final_guard_blocked_unsendable_reply"]
                    + list(repaired_flags or [])
                )
            runtime._replace_last_assistant_message(session.agent, guarded_reply)
        try:
            expression_learning = expression_record_func(
                runtime.xinyu_dir,
                user_text=user_text,
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
        runtime._replace_last_assistant_message(session.agent, guarded_reply)
    return {
        "reply": reply,
        "final_guard_flags": final_guard_flags,
        "final_guard_applied": final_guard_applied,
        "expression_learning": expression_learning,
    }


async def apply_outward_renderer(
    runtime: Any,
    session: Any,
    payload: dict[str, Any],
    *,
    reply: str,
    draft_reply: str,
    user_text: str,
    recalled_context: Any,
    trace_route_stage: TraceRouteStage,
    blocked_by_delegate: bool,
    render_func: Callable[..., Any],
    safe_str_func: Callable[..., str],
) -> dict[str, Any]:
    rendered = False
    renderer_reason = ""
    if runtime.outward_renderer and not blocked_by_delegate:
        renderer_reason = runtime._renderer_reason(
            payload=payload,
            user_text=user_text,
            draft_reply=draft_reply,
        )
        if renderer_reason:
            rendered_reply = await render_func(
                runtime._render_outward_reply,
                session.agent,
                payload=payload,
                user_text=user_text,
                draft_reply=draft_reply,
                canonical_recall_context=safe_str_func(getattr(recalled_context, "prompt_block", "")),
                reason=renderer_reason,
                trace_route_stage=trace_route_stage,
            )
            if rendered_reply:
                reply = rendered_reply
                rendered = True
                runtime._replace_last_assistant_message(session.agent, rendered_reply)
    return {"reply": reply, "rendered": rendered, "renderer_reason": renderer_reason}
