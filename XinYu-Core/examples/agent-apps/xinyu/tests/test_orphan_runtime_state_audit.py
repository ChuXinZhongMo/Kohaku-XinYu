from __future__ import annotations

from pathlib import Path

from ops.validation.orphan_runtime_state_audit import build_orphan_runtime_state_audit, render_markdown


def test_orphan_runtime_state_audit_lists_zero_reference_runtime_state_without_body(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    orphan = app / "memory/context/orphan_state.json"
    referenced = app / "memory/context/referenced_state.json"
    source = app / "xinyu_referenced_owner.py"
    orphan.parent.mkdir(parents=True, exist_ok=True)
    source.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_text('{"body": "private orphan body"}\n', encoding="utf-8")
    referenced.write_text('{"body": "private referenced body"}\n', encoding="utf-8")
    source.write_text('STATE = "memory/context/referenced_state.json"\n', encoding="utf-8")

    audit = build_orphan_runtime_state_audit(tmp_path)

    paths = [item["path"] for item in audit["items"]]
    assert "XinYu-Core/examples/agent-apps/xinyu/memory/context/orphan_state.json" in paths
    assert "XinYu-Core/examples/agent-apps/xinyu/memory/context/referenced_state.json" not in paths
    assert all(item["delete_allowed"] is False for item in audit["items"])
    assert "private orphan body" not in str(audit)
    assert "private referenced body" not in str(audit)


def test_orphan_runtime_state_audit_markdown_is_non_destructive() -> None:
    rendered = render_markdown(
        {
            "status": "review",
            "orphan_candidate_count": 1,
            "items": [
                {
                    "path": "XinYu-Core/examples/agent-apps/xinyu/memory/context/orphan_state.json",
                    "decision": "orphan_runtime_state_review",
                    "target_boundary": "stores/runtime_state",
                    "reference_count": 0,
                    "delete_allowed": False,
                    "handling": "Keep in place.",
                }
            ],
            "safety_rule": "This is a non-destructive review report.",
        }
    )

    assert "Orphan Runtime State Audit" in rendered
    assert "delete_allowed=False" in rendered
    assert "non-destructive" in rendered
