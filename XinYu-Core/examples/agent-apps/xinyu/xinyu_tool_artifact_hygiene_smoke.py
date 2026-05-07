from __future__ import annotations

import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CUSTOM = ROOT / "custom"
CORE_SRC = ROOT.parents[2] / "src"
if str(CORE_SRC) not in sys.path:
    sys.path.insert(0, str(CORE_SRC))
if str(CUSTOM) not in sys.path:
    sys.path.insert(0, str(CUSTOM))

from memory_sync_plugin import sync_from_texts  # noqa: E402
from xinyu_proactive_request_loop import run_proactive_request_loop  # noqa: E402
from xinyu_self_thought_loop import _reflection_share_message, _shareable_dream  # noqa: E402
from xinyu_visible_text_sanitizer import (  # noqa: E402
    sanitize_visible_text,
    visible_text_has_tool_artifact,
)


ARTIFACT = "owner 留下了一次有轻微留痕意义的互动：[Tool batch completed] ## read_9601cfa6 - OK 1→-"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def main() -> int:
    failures: list[str] = []
    if not visible_text_has_tool_artifact(ARTIFACT):
        failures.append("shared artifact detector missed tool batch output")
    cleaned = sanitize_visible_text(ARTIFACT)
    for marker in ("[Tool batch completed]", "## read", "OK 1→", "owner 留下了一次有轻微留痕意义的互动"):
        if marker in cleaned:
            failures.append(f"sanitizer leaked tool artifact marker: {marker}")

    with tempfile.TemporaryDirectory(prefix="xinyu-tool-artifact-") as tmp:
        root = Path(tmp)
        if sync_from_texts(root, ARTIFACT, "ok"):
            failures.append("memory sync accepted tool artifact as owner memory material")
        if (root / "memory/context/continuity_index.md").exists():
            failures.append("memory sync wrote continuity from tool artifact")

    if _reflection_share_message({"topic": ARTIFACT, "waking_residue": ARTIFACT}) != "none":
        failures.append("reflection share allowed tool artifact")

    snapshot = {
        "thought_seeds": "- latest_dream_id: dream-artifact\n- latest_fragments: none\n- reality_boundary: only a dream\n",
        "dream_log": (
            "## dream-artifact\n"
            f"- dream_surface: {ARTIFACT}\n"
            "- reality_boundary_check: only a dream\n"
        ),
    }
    if _shareable_dream(snapshot, "dream-artifact") is not None:
        failures.append("dream share allowed tool artifact")

    with tempfile.TemporaryDirectory(prefix="xinyu-proactive-artifact-") as tmp:
        root = Path(tmp)
        _write(
            root / "memory/context/self_thought_state.md",
            f"""# Self Thought State
- candidate_enabled: true
- intention: share_dream
- focus_kind: dream_residue
- focus_label: dream-artifact
- evidence_label: {ARTIFACT}
- evidence_hash: none
- concrete_question: 有个梦醒来还留着：{ARTIFACT}
- requested_action: owner_response_optional
- after_owner_replies: owner may listen
""",
        )
        result = run_proactive_request_loop(
            root,
            evaluated_at="2026-05-06T20:30:00+08:00",
            delivery_level="queue_owner_private",
            cooldown_seconds=0,
        )
        if result["status"] in {"ready", "candidate_only"}:
            failures.append(f"proactive request accepted tool artifact: {result}")
        state = (root / "memory/context/proactive_request_state.md").read_text(encoding="utf-8-sig")
        if "tool_artifact_candidate_blocked" not in state:
            failures.append("proactive request state did not record tool artifact block")

    if failures:
        print("XinYu tool artifact hygiene smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu tool artifact hygiene smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
