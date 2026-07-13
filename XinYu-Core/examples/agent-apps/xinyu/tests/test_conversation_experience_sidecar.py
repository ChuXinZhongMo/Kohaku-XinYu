from __future__ import annotations

from xinyu_storage_paths import seed_owner_cases_path

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


def test_sidecar_renders_compact_hidden_advisory_block(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    import_seed_owner_cases(tmp_path, seed_path=seed_owner_cases_path(root))

    block = build_conversation_experience_prompt_block(
        tmp_path,
        {"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="why did you stop, continue the implementation progress",
        visible_turn=_visible(technical_work=True),
        turn_id="turn-sidecar",
        max_chars=600,
    )

    assert "conversation experience hints:" in block
    assert "priority_rule:" in block
    assert "useful_adjustment:" in block
    assert "case-owner" not in block
    assert "SQL" in block
    assert len(block) <= 600


def test_sidecar_empty_without_matching_cases(tmp_path: Path) -> None:
    block = build_conversation_experience_prompt_block(
        tmp_path,
        {"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="hello",
        visible_turn=_visible(),
    )

    assert block == ""
