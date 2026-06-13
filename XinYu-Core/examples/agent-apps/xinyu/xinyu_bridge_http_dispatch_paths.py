from __future__ import annotations


def life_ticket_child_id(route: str, *, prefix: str) -> str | None:
    marker = f"{prefix}/"
    if not route.startswith(marker):
        return None
    return route[len(marker) :]
