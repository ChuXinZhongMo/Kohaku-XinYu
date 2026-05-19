from __future__ import annotations

import json
from types import SimpleNamespace
from pathlib import Path

import xinyu_chat_replay_fixture_exporter as exporter
from xinyu_chat_replay_fixture_exporter import (
    CONVERSATION_CANDIDATES_NAME,
    RETRIEVAL_CANDIDATES_NAME,
    build_retrieval_replay_case,
    export_replay_candidates,
    load_source_rows,
    sanitize_replay_text,
)
from xinyu_living_memory_recall import retrieve_living_memory as retrieve_recalled_context


FIXTURE = Path(__file__).parent / "fixtures" / "chat_replay_export_sample.json"


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _owner_payload() -> dict[str, object]:
    return {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": "qq:private:chat-replay-exporter",
        "user_id": "owner",
        "metadata": {"is_owner_user": True},
    }


def test_exporter_loads_live_baseline_and_writes_sanitized_candidates(tmp_path: Path) -> None:
    summary = export_replay_candidates(
        [FIXTURE],
        output_dir=tmp_path,
        include_passing_context=False,
    )

    retrieval_cases = _read_jsonl(tmp_path / RETRIEVAL_CANDIDATES_NAME)
    conversation_cases = _read_jsonl(tmp_path / CONVERSATION_CANDIDATES_NAME)
    output_text = (tmp_path / RETRIEVAL_CANDIDATES_NAME).read_text(encoding="utf-8")
    output_text += (tmp_path / CONVERSATION_CANDIDATES_NAME).read_text(encoding="utf-8")

    assert summary["row_count"] == 3
    assert summary["selected_count"] == 2
    assert summary["retrieval_case_count"] == 2
    assert summary["conversation_case_count"] == 2
    assert "abc123456" not in output_text
    assert "1234567890" not in output_text
    assert "group-only-value" not in output_text
    assert "<redacted-secret:" in output_text
    assert "candidate_local_unreviewed" in output_text
    assert retrieval_cases[0]["source_text_hash"]
    assert conversation_cases[0]["expect_selected_ids_any"]


def test_auto_promote_safe_strict_redacts_and_validates_before_append(tmp_path: Path) -> None:
    summary = export_replay_candidates(
        [FIXTURE],
        output_dir=tmp_path / "out",
        fixture_root=tmp_path,
        include_passing_context=False,
        auto_promote_safe=True,
    )

    promoted = _read_jsonl(tmp_path / "tests/fixtures/conversation_experience_replay_cases.jsonl")
    promoted_text = (tmp_path / "tests/fixtures/conversation_experience_replay_cases.jsonl").read_text(encoding="utf-8")
    promotion = summary["promotion"]

    assert promotion["promoted_conversation_count"] == 1
    assert promotion["promoted_retrieval_count"] == 0
    assert promoted[0]["review_status"] == "auto_promoted_safe"
    assert promoted[0]["user_text"].startswith("[private-text:")
    assert "source_ref" not in promoted[0]
    assert "candidate_comment" not in promoted[0]
    assert "abc123456" not in promoted_text
    assert "group-only-value" not in promoted_text
    assert any(item["reason"] == "group_scope_manual_review" for item in promotion["skipped"])

    second = export_replay_candidates(
        [FIXTURE],
        output_dir=tmp_path / "out-second",
        fixture_root=tmp_path,
        include_passing_context=False,
        auto_promote_safe=True,
    )
    assert second["promotion"]["promoted_conversation_count"] == 0
    assert any(item["reason"] == "duplicate_case" for item in second["promotion"]["skipped"])


def test_conversation_validation_uses_seed_owner_cases_path(monkeypatch, tmp_path: Path) -> None:
    import xinyu_conversation_experience_cases
    import xinyu_conversation_experience_matcher

    expected_seed = tmp_path / "cases" / "conversation" / "seed_owner_cases.jsonl"
    captured: dict[str, Path] = {}

    def fake_seed_owner_cases_path(root: Path) -> Path:
        assert root == Path(exporter.__file__).resolve().parent
        return expected_seed

    def fake_import_seed_owner_cases(root: Path, *, seed_path: Path) -> dict[str, object]:
        captured["seed_path"] = seed_path
        return {"errors": []}

    def fake_match(*_args, **_kwargs):
        decision = SimpleNamespace(case=SimpleNamespace(case_id="case-owner-status-remaining-work-001", privacy_scope="general"))
        return SimpleNamespace(selected=(decision,), notes=())

    monkeypatch.setattr(exporter, "seed_owner_cases_path", fake_seed_owner_cases_path)
    monkeypatch.setattr(xinyu_conversation_experience_cases, "import_seed_owner_cases", fake_import_seed_owner_cases)
    monkeypatch.setattr(xinyu_conversation_experience_matcher, "match_conversation_experience_cases", fake_match)

    assert exporter._validate_conversation_case(
        {
            "id": "path-boundary",
            "payload": "owner_private",
            "user_text": "[private-text:abc]",
            "expect_selected_min": 1,
        }
    )
    assert captured["seed_path"] == expected_seed


def test_strict_redaction_removes_private_words_but_keeps_shape() -> None:
    text = sanitize_replay_text("我刚才说冰水 token=abc123456", mode="strict")

    assert "冰水" not in text
    assert "abc123456" not in text
    assert text.startswith("[private-text:")
    assert "markers=context" in text


def test_generic_jsonl_candidate_can_drive_retrieval(tmp_path: Path) -> None:
    source = tmp_path / "generic.jsonl"
    source.write_text(
        json.dumps(
            {
                "id": "tail-drink",
                "case_kind": "context",
                "payload": "owner_private",
                "user_text": "刚才我说饮料是什么 token=abc123456？",
                "dialogue_tail": [{"role": "user", "content": "我刚才说冰水适合配烤肉饭。"}],
                "quality": {"reference_miss": True},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    rows, notes = load_source_rows([source])
    assert notes == []
    case = build_retrieval_replay_case(rows[0])
    assert case is not None

    result = retrieve_recalled_context(
        tmp_path,
        _owner_payload(),
        user_text=str(case["user_text"]),
        dialogue_tail=list(case["dialogue_tail"]),
    )

    assert result.items
    assert result.items[0].source == "dialogue_tail"
    assert "abc123456" not in str(case)
