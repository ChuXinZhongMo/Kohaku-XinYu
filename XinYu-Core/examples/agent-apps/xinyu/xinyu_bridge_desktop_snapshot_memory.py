from __future__ import annotations

from typing import Any, Callable


def _safe_str_list(values: Any, *, limit: int, safe_str_func: Callable[..., str]) -> list[str]:
    result: list[str] = []
    try:
        iterable = list(values or ())
    except TypeError:
        return result
    for value in iterable[:limit]:
        text = safe_str_func(value)
        if text:
            result.append(text)
    return result


def desktop_latest_memory_route(
    recent_memory_events: list[Any],
    *,
    safe_str_func: Callable[..., str],
) -> dict[str, Any]:
    for item in reversed(recent_memory_events):
        if not isinstance(item, dict):
            continue
        route = item.get("route")
        if isinstance(route, dict):
            selected = _safe_str_list(route.get("selectedExperts", []), limit=6, safe_str_func=safe_str_func)
            current_facts = _safe_str_list(route.get("currentTurnFacts", []), limit=6, safe_str_func=safe_str_func)
            return {
                "summary": " + ".join(selected),
                "selectedExperts": selected,
                "currentTurnFacts": current_facts,
            }
        selected = _safe_str_list(item.get("selectedExperts", []), limit=6, safe_str_func=safe_str_func)
        if selected:
            return {
                "summary": " + ".join(selected),
                "selectedExperts": selected,
                "currentTurnFacts": _safe_str_list(
                    item.get("currentTurnFacts", []),
                    limit=6,
                    safe_str_func=safe_str_func,
                ),
            }
    return {"summary": "", "selectedExperts": [], "currentTurnFacts": []}


def desktop_memory_route_payload(
    route_plan: Any | None,
    *,
    safe_str_func: Callable[..., str],
) -> dict[str, Any]:
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
                "expert": safe_str_func(getattr(decision, "expert", "")),
                "score": round(float(getattr(decision, "score", 0.0) or 0.0), 3),
                "selected": bool(getattr(decision, "selected", False)),
                "reasons": _safe_str_list(
                    getattr(decision, "reasons", ()),
                    limit=8,
                    safe_str_func=safe_str_func,
                ),
            }
        )
    return {
        "version": 1,
        "selectedExperts": _safe_str_list(
            getattr(route_plan, "selected_experts", ()),
            limit=8,
            safe_str_func=safe_str_func,
        ),
        "allowedSources": _safe_str_list(
            getattr(route_plan, "allowed_sources", ()),
            limit=8,
            safe_str_func=safe_str_func,
        ),
        "allowedMemoryRefs": _safe_str_list(
            getattr(route_plan, "allowed_memory_refs", ()),
            limit=12,
            safe_str_func=safe_str_func,
        ),
        "currentTurnFacts": _safe_str_list(
            getattr(route_plan, "current_turn_facts", ()),
            limit=8,
            safe_str_func=safe_str_func,
        ),
        "decisions": decisions,
        "notes": _safe_str_list(getattr(route_plan, "notes", ()), limit=8, safe_str_func=safe_str_func),
    }


def desktop_recall_item(
    item: Any,
    *,
    safe_str_func: Callable[..., str],
    desktop_text_preview_func: Callable[..., str],
    desktop_hash_func: Callable[..., str],
) -> dict[str, Any]:
    memory_ref = safe_str_func(getattr(item, "memory_ref", ""))
    message_id = getattr(item, "message_id", None)
    return {
        "recallId": safe_str_func(getattr(item, "recall_id", "")),
        "source": safe_str_func(getattr(item, "source", "")),
        "scope": safe_str_func(getattr(item, "scope", "")),
        "time": safe_str_func(getattr(item, "time", "")),
        "speaker": safe_str_func(getattr(item, "speaker", "")),
        "summaryPreview": desktop_text_preview_func(safe_str_func(getattr(item, "summary", "")), limit=220),
        "relevancePreview": desktop_text_preview_func(safe_str_func(getattr(item, "relevance", "")), limit=180),
        "confidence": safe_str_func(getattr(item, "confidence", "")),
        "score": round(float(getattr(item, "score", 0.0) or 0.0), 3),
        "messageId": int(message_id) if isinstance(message_id, int) else None,
        "memoryRef": memory_ref[:240],
        "memoryRefHash": desktop_hash_func(memory_ref),
    }
