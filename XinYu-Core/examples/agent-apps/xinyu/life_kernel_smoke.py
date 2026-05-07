from __future__ import annotations

from xinyu_life_kernel import evaluate_life_kernel


def _environment(pressure: str, phrase: str) -> dict:
    return {
        "physicalSensation": {
            "pressure": pressure,
            "phrase": phrase,
            "tag": pressure,
            "intensity": 0.9 if pressure == "high" else 0.5,
        }
    }


def _intent() -> dict:
    return {
        "candidateId": "proreq-life-smoke",
        "candidatePreview": "你是不是还在忙？我有点想问，但又怕打扰。",
        "whyNowPreview": "旧牵挂没有收住，桌面端还开着。",
        "focusLabel": "想靠近但犹豫",
    }


def main() -> int:
    failures: list[str] = []

    suppressed = evaluate_life_kernel(
        environment=_environment("high", "极热，像被机器的重压贴住"),
        proactive_items=[_intent()],
        recent_turns=[],
        recent_memory_events=[],
    )
    if suppressed is None:
        failures.append("high-pressure unresolved intent did not create ActiveDesire")
    elif suppressed.chosen_action != "suppress_and_wait":
        failures.append(f"high-pressure desire should suppress_and_wait: {suppressed.chosen_action}")
    elif not suppressed.hesitation or "打扰" not in (suppressed.inhibition_reason or ""):
        failures.append(f"suppressed desire did not carry inhibition reason: {suppressed}")

    note = evaluate_life_kernel(
        environment=_environment("normal", "温热，稳定在场"),
        proactive_items=[_intent()],
        recent_turns=[],
        recent_memory_events=[],
    )
    if note is None:
        failures.append("normal unresolved intent did not create ActiveDesire")
    elif note.chosen_action != "leave_note_on_desk":
        failures.append(f"normal first-pass desire should leave note on desk: {note.chosen_action}")

    quiet = evaluate_life_kernel(
        environment=_environment("low", "失重，很安静"),
        proactive_items=[],
        recent_turns=[],
        recent_memory_events=[],
    )
    if quiet is not None:
        failures.append(f"quiet no-intent state should not create desire: {quiet}")

    if failures:
        print("Life kernel smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Life kernel smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
