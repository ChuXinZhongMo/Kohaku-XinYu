from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from xinyu_bridge_desktop_snapshot_state_payload import DesktopXinyuStatePayload


@dataclass(frozen=True)
class DesktopActionResidueProjection:
    seed_id: str
    reflection_item_id: str
    route: str
    pressure: str
    result: str
    attention: str
    concern: str
    label: str


def _action_route(consumed_at: str, reflection_item_id: str) -> str:
    consumed = bool(consumed_at and consumed_at != "none")
    if consumed and reflection_item_id:
        return "已进梦境和反思"
    if consumed:
        return "已被梦境消费"
    if reflection_item_id:
        return "已排入反思"
    return "等待梦境处理"


def _action_summary(
    *,
    route: str,
    result: str,
    pressure: str,
    compact_text_func: Callable[..., str],
    desktop_action_result_label_func: Callable[[str], str],
    desktop_action_pressure_label_func: Callable[[str], str],
) -> tuple[str, str]:
    route_label = route or "行动沉淀"
    result_label = desktop_action_result_label_func(result)
    pressure_label = desktop_action_pressure_label_func(pressure)
    concern = compact_text_func(f"{route_label}；{result_label}，{pressure_label}", 72)
    label = compact_text_func(f"{route_label} · {result_label} · {pressure_label}", 72)
    return concern, label


def project_action_residue(
    payload: DesktopXinyuStatePayload,
    *,
    safe_str_func: Callable[..., str],
    compact_text_func: Callable[..., str],
    desktop_action_theme_label_func: Callable[[str], str],
    desktop_action_result_label_func: Callable[[str], str],
    desktop_action_pressure_label_func: Callable[[str], str],
) -> DesktopActionResidueProjection:
    latest_action = payload.latest_action
    seed_id = safe_str_func(latest_action.get("seed_id"))
    reflection_item_id = safe_str_func(latest_action.get("reflection_item_id"))
    action_result = safe_str_func(latest_action.get("result"), "unknown") or "unknown"
    action_pressure = safe_str_func(latest_action.get("pressure"), "unknown") or "unknown"

    if not seed_id:
        return DesktopActionResidueProjection(
            seed_id=seed_id,
            reflection_item_id=reflection_item_id,
            route="",
            pressure=action_pressure,
            result=action_result,
            attention="",
            concern="",
            label="",
        )

    seed_detail = payload.seed_detail
    action_route = _action_route(
        safe_str_func(seed_detail.get("consumed_at")),
        reflection_item_id,
    )
    action_theme = compact_text_func(safe_str_func(seed_detail.get("theme")) or "行动经验正在沉淀", 96)
    action_attention = compact_text_func(
        f"行动残留：{desktop_action_theme_label_func(action_theme)}",
        96,
    )
    action_concern, action_label = _action_summary(
        route=action_route,
        result=action_result,
        pressure=action_pressure,
        compact_text_func=compact_text_func,
        desktop_action_result_label_func=desktop_action_result_label_func,
        desktop_action_pressure_label_func=desktop_action_pressure_label_func,
    )

    return DesktopActionResidueProjection(
        seed_id=seed_id,
        reflection_item_id=reflection_item_id,
        route=action_route,
        pressure=action_pressure,
        result=action_result,
        attention=action_attention,
        concern=action_concern,
        label=action_label,
    )
