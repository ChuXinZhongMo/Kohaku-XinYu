from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import tempfile
from pathlib import Path
from types import SimpleNamespace

from xinyu_conversation_experience_cases import import_seed_owner_cases
from xinyu_conversation_experience_sidecar import build_conversation_experience_prompt_block


def _visible(**kwargs: object) -> SimpleNamespace:
    base = {
        "turn_kind": "ordinary_owner_chat",
        "technical_work": False,
        "owner_style_pressure": False,
        "owner_no_change_pressure": False,
        "relationship_pressure": False,
        "rest_silence": False,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-conversation-experience-sidecar-") as tmp:
        root = Path(tmp)
        imported = import_seed_owner_cases(root, seed_path=ROOT / "data/conversation_experience/seed_owner_cases.jsonl")
        if imported.get("errors"):
            failures.append(f"seed import failed: {imported}")
        block = build_conversation_experience_prompt_block(
            root,
            {"message_type": "private_text", "metadata": {"is_owner_user": True}},
            user_text="why did you stop, continue the implementation progress",
            visible_turn=_visible(technical_work=True),
            turn_id="smoke-turn",
            max_chars=600,
        )
        if "conversation experience hints:" not in block:
            failures.append("eligible owner technical turn did not receive a conversation experience sidecar")
        if "case-owner" in block or "abstract_seed" in block:
            failures.append("sidecar leaked case id or source ref")
        if len(block) > 600:
            failures.append(f"sidecar exceeded budget: {len(block)}")

        quiet = build_conversation_experience_prompt_block(
            root,
            {"message_type": "private_text", "metadata": {"is_owner_user": True}},
            user_text="hello",
            visible_turn=_visible(),
            turn_id="smoke-quiet",
        )
        if quiet:
            failures.append("quiet ordinary owner chat received a case hint")

    if failures:
        print("conversation_experience_sidecar_smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("conversation_experience_sidecar_smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
