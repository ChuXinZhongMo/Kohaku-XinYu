from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from xinyu_external_plugins import ExternalCallContext


@dataclass(frozen=True)
class SelfThoughtExternalPluginDeps:
    as_bool: Callable[..., bool]
    safe_str: Callable[..., str]
    runtime_allowed: Callable[..., tuple[bool, str, dict[str, Any]]]
    prepare_call: Callable[..., Any]
    execute_http: Callable[..., dict[str, Any]]
    read_text: Callable[[Any], str]
    state_field: Callable[[str, str], str | None]
    append_jsonl: Callable[[Any, dict[str, Any]], None]
    timestamp_or_now_iso: Callable[[str], str]


def maybe_run_self_thought_external_plugin_impl(
    runtime: Any,
    *,
    thought: dict[str, Any],
    checked_at: str,
    deps: SelfThoughtExternalPluginDeps,
) -> list[str]:
    as_bool = deps.as_bool
    safe_str = deps.safe_str

    if not as_bool(thought.get("research_needed"), default=False):
        return []
    allowed, reason, plugin = deps.runtime_allowed(
        runtime.xinyu_dir,
        "kohaku_terrarium",
        proactive=True,
    )
    if not allowed:
        return [f"external_plugin:kohaku_terrarium/skipped/{reason}"]

    config = plugin.get("config") if isinstance(plugin.get("config"), dict) else {}
    session_id = safe_str(config.get("session_id")).strip()
    creature_id = safe_str(config.get("creature_id")).strip()
    if not session_id or not creature_id:
        return ["external_plugin:kohaku_terrarium/skipped/session_not_configured"]

    state = deps.read_text(runtime.xinyu_dir / "memory/context/self_thought_state.md")
    query = deps.state_field(state, "query") or safe_str(thought.get("focus_label"), "unknown")
    target = deps.state_field(state, "target") or "general"
    route = safe_str(thought.get("research_route"), "unknown")
    prepared = deps.prepare_call(
        "kohaku_terrarium",
        "chat_creature",
        {
            "base_url": safe_str(config.get("base_url"), "http://127.0.0.1:8001"),
            "session_id": session_id,
            "creature_id": creature_id,
            "message": (
                "XinYu self-thought needs an external runtime perspective. "
                f"Route: {route}. Target: {target}. Query: {query}. "
                "Return a compact observation only; do not mutate XinYu memory."
            ),
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

    execution = deps.execute_http(prepared, timeout_seconds=45)
    deps.append_jsonl(
        runtime.xinyu_dir / "runtime/external_plugin_trace.jsonl",
        {
            "observed_at": deps.timestamp_or_now_iso(checked_at),
            "source": "self_thought_loop",
            "plugin_id": "kohaku_terrarium",
            "capability": "chat_creature",
            "route": route,
            "target": target,
            "query": query,
            "ok": bool(execution.get("ok")),
            "status_code": execution.get("status_code"),
            "error_code": execution.get("error_code"),
            "text_preview": safe_str(execution.get("text_preview"))[:800],
        },
    )
    return [
        "external_plugin:kohaku_terrarium/"
        f"{'ok' if execution.get('ok') else 'failed'}/"
        f"{safe_str(execution.get('error_code'), 'none')}"
    ]
