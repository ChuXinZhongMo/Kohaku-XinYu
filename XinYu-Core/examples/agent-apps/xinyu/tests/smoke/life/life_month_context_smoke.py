from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import sys
from datetime import datetime
from pathlib import Path

from xinyu_bridge_renderer import BridgeRenderer
from xinyu_life_month_slots import (
    CURRENT_LIFE_MONTH_CONTEXT_REL,
    parse_life_month_slots,
    refresh_current_life_month_context,
    select_relevant_life_month_slots,
    validate_life_month_slots,
)
from xinyu_memory_weights import calculate_memory_weights
from xinyu_speech_controller import XinyuSpeechController


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    root = ROOT
    failures: list[str] = []
    evaluated_at = datetime.fromisoformat("2026-04-28T00:00:00+08:00")

    failures.extend(validate_life_month_slots(root))
    blueprint = parse_life_month_slots(root)
    if blueprint.slot_count != 192:
        failures.append(f"unexpected slot_count: {blueprint.slot_count}")
    if "2026-04" not in blueprint.slots:
        failures.append("current construction month slot is missing")

    study_selection = select_relevant_life_month_slots(
        root,
        user_text="今天学习压力有点大，物理题也卡住了",
        evaluated_at=evaluated_at,
    )
    selected_months = {item.slot.year_month for item in study_selection}
    if "2026-04" not in selected_months:
        failures.append("current month was not selected")
    if "2021-07" not in selected_months:
        failures.append("study-pressure public-time anchor was not selected")

    context_text = refresh_current_life_month_context(
        root,
        user_text="今天学习压力有点大，物理题也卡住了",
        evaluated_at=evaluated_at,
    )
    for marker in (
        "# Current Life Month Context",
        "selection_rule: current month",
        "selected_slot 2026-04",
        "selected_slot 2021-07",
        "boundary_rule: selected month slots are speech texture",
    ):
        if marker not in context_text:
            failures.append(f"current context missing marker: {marker}")

    context_file = root / CURRENT_LIFE_MONTH_CONTEXT_REL
    if not context_file.exists():
        failures.append("current_life_month_context file was not written")

    config = (root / "config.yaml").read_text(encoding="utf-8-sig")
    system = (root / "prompts/system.md").read_text(encoding="utf-8-sig")
    if "current_life_month_context: memory/context/current_life_month_context.md" not in config:
        failures.append("config does not inject current_life_month_context")
    if "{{ current_life_month_context }}" in system or "[context/current_life_month_context.md]" in system:
        failures.append("base system prompt should not include full current_life_month_context")
    if "life-month context" not in system or "live-turn runtime context" not in system:
        failures.append("system prompt does not document life-month runtime injection")

    renderer = BridgeRenderer(
        xinyu_dir=root,
        speech_controller=XinyuSpeechController(root),
        renderer_mode="quality",
        render_timeout_seconds=1,
    )
    renderer_context = renderer.renderer_memory_context(user_text="学习压力")
    if "[memory/context/current_life_month_context.md]" not in renderer_context:
        failures.append("renderer context does not include current_life_month_context")

    weights = calculate_memory_weights(root)
    if not any(row["path"] == "memory/context/current_life_month_context.md" for row in weights):
        failures.append("memory weight calculation does not include current_life_month_context")

    if failures:
        print("Life month context smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Life month context smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
