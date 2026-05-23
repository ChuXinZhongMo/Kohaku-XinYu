from __future__ import annotations

from pathlib import Path

from xinyu_status import check_state, status_fields


def test_status_reports_post_reply_self_observation_without_raw_text(tmp_path: Path) -> None:
    state_path = tmp_path / "memory/self/expression_self_learning_state.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        """# Expression Self Learning State

## Latest Post Reply Observation
- observation_kind: owner_private_reply_self_observation
- self_state_kind: feeling_inquiry
- alive_voice: medium
- mechanical_risk: low
- template_risk: medium
- over_explained_risk: low
- emotional_grounding: present
- self_state_grounding: present
- raw_text_saved: false
- stable_personality_write: no
""",
        encoding="utf-8",
    )

    fields = status_fields(tmp_path)
    checks = {check.name: check for check in check_state(tmp_path)}

    assert fields["post_reply_observation_kind"] == "owner_private_reply_self_observation"
    assert fields["post_reply_alive_voice"] == "medium"
    assert fields["post_reply_stable_personality_write"] == "no"
    assert checks["post_reply_self_observation"].ok is True
    assert "stable_write=no" in checks["post_reply_self_observation"].detail
