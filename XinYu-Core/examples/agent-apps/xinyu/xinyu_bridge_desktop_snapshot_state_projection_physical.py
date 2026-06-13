from __future__ import annotations

from typing import Callable

from xinyu_bridge_desktop_snapshot_state_payload import DesktopXinyuStatePayload
from xinyu_bridge_desktop_snapshot_state_projection_action import DesktopActionResidueProjection


def project_physical_sensation(
    payload: DesktopXinyuStatePayload,
    action: DesktopActionResidueProjection,
    *,
    safe_str_func: Callable[..., str],
    compact_text_func: Callable[..., str],
) -> str:
    physical_sensation = safe_str_func(payload.sensation.get("phrase"), "体感未校准")
    if action.seed_id and action.pressure in {"medium", "high"}:
        suffix = "行动余温偏重" if action.pressure == "high" else "行动余温未散"
        return compact_text_func(f"{physical_sensation}；{suffix}", 64)
    return physical_sensation
