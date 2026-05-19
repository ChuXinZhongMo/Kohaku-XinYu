from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

from xinyu_life_kernel import build_entropy_state, evaluate_life_kernel


def _environment(pressure: str = "normal") -> dict:
    return {
        "physicalSensation": {
            "pressure": pressure,
            "phrase": "温热，稳定在场",
            "tag": pressure,
            "intensity": 0.5,
        }
    }


def _suppressed_residue(index: int) -> dict:
    return {
        "eventId": f"suppressed-{index}",
        "kind": "suppressed_desire",
        "textPreview": "忍住了，没有发出去。旧牵挂还在。",
    }


def main() -> int:
    failures: list[str] = []
    residues = [_suppressed_residue(index) for index in range(8)]

    entropy = build_entropy_state(
        environment=_environment(),
        proactive_items=[],
        recent_turns=[],
        recent_memory_events=residues,
    )
    if entropy.entropy_band not in {"fracture", "terminal"}:
        failures.append(f"entropy residue should fracture: {entropy.entropy_band} {entropy.entropy_level}")
    if not entropy.metabolism_needed or entropy.resource_request is None:
        failures.append(f"entropy fracture should request metabolism: {entropy}")

    desire = evaluate_life_kernel(
        environment=_environment(),
        proactive_items=[],
        recent_turns=[],
        recent_memory_events=residues,
        entropy_state=entropy,
    )
    if desire is None:
        failures.append("entropy-only fracture did not create ActiveDesire")
    elif desire.chosen_action != "request_metabolism_window":
        failures.append(f"entropy-only fracture should request metabolism window: {desire.chosen_action}")
    elif not desire.entropy.metabolism_needed:
        failures.append("metabolism desire did not carry entropy state")
    elif "十分钟" not in desire.visible_trace:
        failures.append(f"metabolism visible trace lost survival fragment: {desire.visible_trace}")

    quiet_entropy = build_entropy_state(
        environment=_environment("low"),
        proactive_items=[],
        recent_turns=[],
        recent_memory_events=[],
    )
    if quiet_entropy.metabolism_needed:
        failures.append(f"quiet entropy should not request metabolism: {quiet_entropy}")

    if failures:
        print("Life kernel entropy smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Life kernel entropy smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
