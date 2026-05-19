from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

from xinyu_life_kernel import build_entropy_state, evaluate_life_kernel


def _environment() -> dict:
    return {
        "physicalSensation": {
            "pressure": "normal",
            "phrase": "steady",
            "tag": "normal",
            "intensity": 0.5,
        }
    }


def _suppressed_residue(index: int) -> dict:
    return {
        "eventId": f"suppressed-{index}",
        "kind": "suppressed_desire",
        "textPreview": "suppressed residue, unsent",
    }


def _self_choice(*, urge: float, closure: float, fatigue: float, last_choice: str = "") -> dict:
    return {
        "version": 1,
        "runtime_affect": {
            "urge_to_express": urge,
            "self_closure": closure,
            "fatigue": fatigue,
            "last_choice": last_choice,
            "last_choice_at": "",
        },
        "affective_sediment": {
            "baseline_urge": 0.38,
            "baseline_closure": 0.32,
            "rejection_scar": 0.0,
            "repair_trust": 0.2,
            "motif_biases": {},
        },
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
    if not entropy.metabolism_needed:
        failures.append(f"smoke entropy should need metabolism: {entropy}")

    legacy = evaluate_life_kernel(
        environment=_environment(),
        proactive_items=[],
        recent_turns=[],
        recent_memory_events=residues,
        entropy_state=entropy,
    )
    if legacy is None or legacy.chosen_action != "request_metabolism_window":
        failures.append(f"legacy no-self-choice path should still request metabolism: {legacy}")

    expressive = evaluate_life_kernel(
        environment=_environment(),
        proactive_items=[],
        recent_turns=[],
        recent_memory_events=residues,
        entropy_state=entropy,
        self_choice_state=_self_choice(urge=0.92, closure=0.08, fatigue=0.05),
    )
    guarded = evaluate_life_kernel(
        environment=_environment(),
        proactive_items=[],
        recent_turns=[],
        recent_memory_events=residues,
        entropy_state=entropy,
        self_choice_state=_self_choice(urge=0.12, closure=0.92, fatigue=0.82),
    )
    if expressive is None or expressive.chosen_action != "request_metabolism_window":
        failures.append(f"high urge/open state should request metabolism: {expressive}")
    if guarded is None or guarded.chosen_action != "suppress_and_wait":
        failures.append(f"withdrawn/fatigued state should branch to suppress: {guarded}")
    if expressive and guarded and expressive.desire_id == guarded.desire_id:
        failures.append("self-choice branches should not collapse to the same desire id")

    if failures:
        print("Life kernel self choice bias smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Life kernel self choice bias smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
