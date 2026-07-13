"""Owner co-evolution grants for kernel changes (Higher Goal 3 prep / K-012)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

GrantScope = Literal["self_model", "belief", "world_model", "reorganization", "all"]

OWNER_GRANTS_REL = Path("memory") / "kernel" / "owner_grants.json"


def _grants_path(root: Path) -> Path:
    return root / OWNER_GRANTS_REL


def load_owner_grants(root: Path) -> dict[str, Any]:
    path = _grants_path(root)
    if not path.exists():
        return {"grants": [], "default_policy": "review_required"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"grants": [], "default_policy": "review_required"}


def save_owner_grants(root: Path, data: dict[str, Any]) -> None:
    path = _grants_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def grant_owner_scope(
    root: Path,
    scope: GrantScope,
    *,
    granted_by: str = "owner",
    note: str = "",
    event_id: str | None = None,
) -> dict[str, Any]:
    """Record an explicit owner grant for a kernel domain."""
    data = load_owner_grants(root)
    entry = {
        "scope": scope,
        "granted_by": granted_by,
        "note": note[:200],
        "event_id": event_id,
    }
    data.setdefault("grants", []).append(entry)
    save_owner_grants(root, data)
    return entry


def is_scope_granted(root: Path | None, scope: GrantScope) -> bool:
    if root is None:
        return False
    data = load_owner_grants(root)
    for g in data.get("grants", []):
        if g.get("scope") in (scope, "all"):
            return True
    return False