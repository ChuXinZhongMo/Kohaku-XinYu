from __future__ import annotations

import sys
from pathlib import Path

from xinyu_bridge_renderer import BridgeRenderer
from xinyu_persona_runtime import build_persona_runtime_state
from xinyu_speech_controller import XinyuSpeechController
from xinyu_turn_residue import read_turn_residue, write_turn_residue


def _snapshot(paths: list[Path]) -> dict[Path, str | None]:
    data: dict[Path, str | None] = {}
    for path in paths:
        try:
            data[path] = path.read_text(encoding="utf-8-sig")
        except OSError:
            data[path] = None
    return data


def _restore(data: dict[Path, str | None]) -> None:
    for path, text in data.items():
        if text is None:
            try:
                path.unlink()
            except OSError:
                pass
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    root = Path(__file__).resolve().parent
    touched = [
        root / "memory/context/persona_surface_state.md",
    ]
    before = _snapshot(touched)
    failures: list[str] = []

    try:
        controller = XinyuSpeechController(root)
        payload = {"metadata": {"is_owner_user": True}}
        scene = controller.classify(payload=payload, user_text="这句还是默认腔味太重了，像现成腔。")
        wrote = write_turn_residue(
            root,
            scene=scene,
            user_text="这句还是默认腔味太重了，像现成腔。",
            reply="这句先别发，我重新接你的意思。",
            source="persona_stability_layers_smoke",
        )
        if not wrote:
            failures.append("turn residue state was not written")

        residue = read_turn_residue(root)
        if not residue.active or residue.decayed_strength < 70:
            failures.append(f"turn residue did not remain active: {residue}")

        state = build_persona_runtime_state(
            root,
            payload=payload,
            user_text="下一轮别又变回默认腔那套。",
            draft_reply="",
        )
        prompt = state.to_prompt_block()
        identity_pos = prompt.find("## Concept")
        surface_pos = prompt.find("## Current Surface Seed")
        if not (0 <= identity_pos < surface_pos):
            failures.append("persona runtime prompt does not separate concept and surface layers")
        if state.previous_residue_strength < 70 or state.previous_tone == "none":
            failures.append("persona runtime did not carry previous tone residue")

        canned_reply = "我理解你的感受，你的感受很重要，如果你愿意可以继续说。"
        flags = controller.reply_quality_flags(
            payload=payload,
            user_text="别用现成腔糊我。",
            reply=canned_reply,
        )
        if any("canned assistant voice" in flag for flag in flags):
            failures.append("concept-seed quality gate should not police canned wording")
        guarded, guard_flags = controller.final_reply_guard(
            payload=payload,
            user_text="别用现成腔糊我。",
            reply=canned_reply,
        )
        if guarded != canned_reply or guard_flags:
            failures.append("final reply guard should only clean wrappers, not run the quality gate")
        leaked_reply = "不确定，你听出来的小算。我自己改的时候有时候还是会滑回去。"
        leak_flags = controller.reply_quality_flags(
            payload=payload,
            user_text="这个用词还是不像人。",
            reply=leaked_reply,
        )
        if any("surface/internal wording leaked" in flag for flag in leak_flags):
            failures.append("concept-seed quality gate should not police internal wording")

        renderer = BridgeRenderer(
            xinyu_dir=root,
            speech_controller=controller,
            renderer_mode="quality",
            render_timeout_seconds=1,
        )
        context = renderer.renderer_memory_context()
        if "[memory/context/persona_surface_state.md]" not in context:
            failures.append("renderer context missing persona_surface_state")
        if "[memory/self/system_prompt_memory.md]" in context:
            failures.append("renderer context should not include system_prompt_memory")
        if "[memory/context/memory_weight_state.md]" in context:
            failures.append("renderer context should not include mechanical memory_weight_state")
    finally:
        _restore(before)

    if failures:
        print("Persona stability layers smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Persona stability layers smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
