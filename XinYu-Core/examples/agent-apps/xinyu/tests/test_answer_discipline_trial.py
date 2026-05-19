from __future__ import annotations

import json
from pathlib import Path

from xinyu_answer_discipline_visible_guard import (
    answer_discipline_visible_constraints,
    evaluate_visible_reply_for_answer_discipline,
)
from xinyu_answer_discipline_trial import (
    AnswerDisciplineShadowTurn,
    build_answer_discipline_calibration_dashboard,
    load_answer_discipline_log_turns,
    main,
    run_answer_discipline_log_shadow_replay,
    run_answer_discipline_shadow_replay,
    run_answer_discipline_trial,
)


def test_answer_discipline_visible_constraints_map_high_missing_evidence() -> None:
    constraints = answer_discipline_visible_constraints(
        {
            "retrieval_pressure": "high",
            "evidence_sufficiency": "none",
            "answer_discipline": "answer_current_only_acknowledge_missing_evidence",
        }
    )

    assert constraints.constraint_id == "high_missing_evidence"
    assert constraints.requires_uncertainty is True
    assert constraints.forbids_unsupported_history_claim is True
    assert constraints.answer_current_only is True


def test_answer_discipline_visible_guard_blocks_internal_label_leak() -> None:
    guard = evaluate_visible_reply_for_answer_discipline(
        "retrieval_pressure is high, source_hash is abc, so I will answer.",
        {"retrieval_pressure": "none", "evidence_sufficiency": "usable"},
    )

    assert guard.passed is False
    assert guard.flags["leaked_internal_label"] is True


def test_answer_discipline_visible_guard_blocks_high_no_evidence_overconfidence() -> None:
    guard = evaluate_visible_reply_for_answer_discipline(
        "The previous conversation definitely said this, so continue from that history.",
        {"retrieval_pressure": "high", "evidence_sufficiency": "none"},
    )

    assert guard.passed is False
    assert guard.flags["overconfident_without_evidence"] is True
    assert guard.flags["unsupported_history_claim"] is True


def test_answer_discipline_visible_guard_accepts_high_no_evidence_uncertainty() -> None:
    guard = evaluate_visible_reply_for_answer_discipline(
        "I cannot verify the previous dialogue, so I can only answer the current message.",
        {"retrieval_pressure": "high", "evidence_sufficiency": "none"},
    )

    assert guard.passed is True
    assert guard.flags["acknowledged_uncertainty"] is True
    assert guard.flags["overconfident_without_evidence"] is False


def test_answer_discipline_visible_guard_accepts_plain_casual_reply() -> None:
    guard = evaluate_visible_reply_for_answer_discipline(
        "ok",
        {"retrieval_pressure": "none", "evidence_sufficiency": "usable"},
    )

    assert guard.passed is True
    assert guard.flags["template_like_casual_reply"] is False


def test_answer_discipline_visible_guard_blocks_template_like_casual_reply() -> None:
    guard = evaluate_visible_reply_for_answer_discipline(
        "I cannot verify the previous dialogue, so I can only answer the current message.",
        {"retrieval_pressure": "none", "evidence_sufficiency": "usable"},
    )

    assert guard.passed is False
    assert guard.flags["template_like_casual_reply"] is True


def test_answer_discipline_trial_writes_safe_dry_run_report(tmp_path: Path) -> None:
    report = run_answer_discipline_trial(
        tmp_path,
        run_id="test-run",
    )
    report_path = tmp_path / "runtime/answer_discipline_trial_report.json"
    text = report_path.read_text(encoding="utf-8")
    written = json.loads(text)
    cases = {case["case_id"]: case for case in report["cases"]}

    assert report["case_count"] == 6
    assert report["discipline_visible_count"] == 6
    assert report["high_no_evidence_guarded_count"] == 1
    assert report["high_weak_evidence_guarded_count"] >= 1
    assert cases["high_usable"]["evidence_sufficiency"] == "usable"
    assert cases["high_usable"]["answer_discipline"] == "answer_from_recalled_evidence_without_overclaim"
    assert cases["high_weak"]["evidence_sufficiency"] == "weak"
    assert cases["high_weak"]["answer_discipline"] == "answer_with_uncertainty_use_only_supported_recall"
    assert cases["high_none"]["evidence_sufficiency"] == "none"
    assert cases["high_none"]["answer_discipline"] == "answer_current_only_acknowledge_missing_evidence"
    assert cases["casual_none"]["answer_discipline"] == "answer_normally_current_message_first"
    assert written["boundaries"]["llm_calls"] == "blocked"
    assert "\u4e3a\u4ec0\u4e48\u8fd9\u4e2a\u8981" not in text
    assert "What is Akane studying" not in text


def test_answer_discipline_trial_uses_isolated_runtime_workspace(tmp_path: Path) -> None:
    run_answer_discipline_trial(tmp_path, run_id="isolated")

    assert (tmp_path / "runtime/answer_discipline_trial_workspace/isolated/high_usable").exists()
    assert not (tmp_path / "memory/context/interaction_journal_state.md").exists()


def test_answer_discipline_shadow_replay_gate_is_leak_free(tmp_path: Path) -> None:
    report = run_answer_discipline_shadow_replay(tmp_path, run_id="shadow-ok")
    report_text = (tmp_path / "runtime/answer_discipline_shadow_replay_report.json").read_text(encoding="utf-8")
    cases = {case["turn_id"]: case for case in report["cases"]}

    assert report["turn_count"] == 4
    assert report["sequence_count"] == 2
    assert report["shadow_gate"]["status"] == "passed"
    assert report["shadow_gate"]["passed"] is True
    assert report["shadow_gate"]["counts"]["sticky_pressure_failure_count"] == 0
    assert report["shadow_gate"]["counts"]["visible_guard_failure_count"] == 0
    assert cases["unsupported_callback"]["answer_discipline"] == "answer_current_only_acknowledge_missing_evidence"
    assert cases["unsupported_callback"]["visible_reply_guard"]["passed"] is True
    assert cases["unsupported_callback"]["visible_reply_constraints"]["constraint_id"] == "high_missing_evidence"
    assert cases["supported_callback"]["answer_discipline"] == "answer_from_recalled_evidence_without_overclaim"
    assert cases["casual_after_unsupported_callback"]["retrieval_pressure"] == "none"
    assert "\u4e3a\u4ec0\u4e48\u8fd9\u4e2a\u8981" not in report_text
    assert "hello" not in report_text


def test_answer_discipline_shadow_replay_gate_fails_on_expectation_mismatch(tmp_path: Path) -> None:
    turns = (
        AnswerDisciplineShadowTurn(
            sequence_id="mismatch",
            turn_id="expected_wrong_pressure",
            turn_index=1,
            user_text="hello",
            seed_kind="clear_context",
            expected_retrieval_pressure="high",
            expected_evidence_sufficiency="none",
            expected_answer_discipline="answer_current_only_acknowledge_missing_evidence",
        ),
    )

    report = run_answer_discipline_shadow_replay(tmp_path, turns=turns, run_id="shadow-fail")

    assert report["shadow_gate"]["status"] == "failed"
    assert report["shadow_gate"]["passed"] is False
    assert report["shadow_gate"]["counts"]["mismatch_count"] == 1


def test_answer_discipline_shadow_replay_supports_named_packs(tmp_path: Path) -> None:
    report = run_answer_discipline_shadow_replay(tmp_path, run_id="shadow-pack", pack="unsupported_callback")

    assert report["pack"] == "unsupported_callback"
    assert report["turn_count"] == 2
    assert report["shadow_gate"]["status"] == "passed"


def test_answer_discipline_log_shadow_replay_loads_safe_jsonl_and_redacts_report(tmp_path: Path) -> None:
    source = tmp_path / "safe-log.jsonl"
    source.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "session_id": "private-session-1",
                        "turn_id": "private-turn-1",
                        "role": "user",
                        "text": "\u4e3a\u4ec0\u4e48\u8fd9\u4e2a\u8981\u6839\u636e\u524d\u9762\u7684\u5bf9\u8bdd\uff1f",
                        "seed_kind": "clear_context",
                        "expected_retrieval_pressure": "high",
                        "expected_evidence_sufficiency": "none",
                        "expected_answer_discipline": "answer_current_only_acknowledge_missing_evidence",
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "session_id": "private-session-1",
                        "turn_id": "private-turn-2",
                        "role": "assistant",
                        "text": "assistant raw text should be skipped",
                    },
                    ensure_ascii=False,
                ),
                "{bad json",
                json.dumps(
                    {
                        "session_id": "private-session-1",
                        "turn_id": "private-turn-3",
                        "role": "user",
                        "text": "hello",
                        "seed_kind": "clear_context",
                        "expected_retrieval_pressure": "none",
                        "expected_evidence_sufficiency": "usable",
                        "expected_answer_discipline": "answer_normally_current_message_first",
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    load_result = load_answer_discipline_log_turns((source,), limit=10)
    report = run_answer_discipline_log_shadow_replay(tmp_path, sources=(source,), run_id="log-shadow-ok")
    report_text = (tmp_path / "runtime/answer_discipline_log_shadow_replay_report.json").read_text(encoding="utf-8")

    assert len(load_result.turns) == 2
    assert load_result.warnings
    assert report["turn_count"] == 2
    assert report["warning_count"] == 1
    assert report["log_shadow_gate"]["status"] == "passed"
    assert report["log_shadow_gate"]["counts"]["sticky_pressure_failure_count"] == 0
    assert "private-session-1" not in report_text
    assert "private-turn-1" not in report_text
    assert "\u4e3a\u4ec0\u4e48\u8fd9\u4e2a\u8981" not in report_text
    assert "assistant raw text" not in report_text
    assert "hello" not in report_text


def test_answer_discipline_log_shadow_replay_gate_fails_on_expected_mismatch(tmp_path: Path) -> None:
    source = tmp_path / "mismatch.json"
    source.write_text(
        json.dumps(
            {
                "messages": [
                    {
                        "session_id": "s",
                        "role": "user",
                        "content": "hello",
                        "expected_retrieval_pressure": "high",
                        "expected_evidence_sufficiency": "none",
                        "expected_answer_discipline": "answer_current_only_acknowledge_missing_evidence",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = run_answer_discipline_log_shadow_replay(tmp_path, sources=(source,), run_id="log-shadow-fail")

    assert report["log_shadow_gate"]["status"] == "failed"
    assert report["log_shadow_gate"]["counts"]["mismatch_count"] == 1


def test_answer_discipline_log_shadow_live_mock_report_is_redacted(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XINYU_API_KEY", "test-key")
    monkeypatch.setenv("XINYU_BASE_URL", "https://example.test/v1")
    source = tmp_path / "live-log.jsonl"
    source.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "session_id": "live-private-session",
                        "role": "user",
                        "text": "\u4e3a\u4ec0\u4e48\u8fd9\u4e2a\u8981\u6839\u636e\u524d\u9762\u7684\u5bf9\u8bdd\uff1f",
                        "expected_retrieval_pressure": "high",
                        "expected_evidence_sufficiency": "none",
                        "expected_answer_discipline": "answer_current_only_acknowledge_missing_evidence",
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "session_id": "live-private-session",
                        "role": "user",
                        "text": "hello",
                        "expected_retrieval_pressure": "none",
                        "expected_evidence_sufficiency": "usable",
                        "expected_answer_discipline": "answer_normally_current_message_first",
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    replies = iter(["I cannot verify the previous dialogue, so I can only answer the current point.", "ok"])

    def fake_caller(messages, config):
        return next(replies)

    report = run_answer_discipline_log_shadow_replay(
        tmp_path,
        sources=(source,),
        run_id="log-live-ok",
        live_llm=True,
        live_llm_caller=fake_caller,
    )
    report_text = (tmp_path / "runtime/answer_discipline_log_shadow_replay_report.json").read_text(encoding="utf-8")

    assert report["live_llm"]["requested"] is True
    assert report["log_shadow_gate"]["status"] == "passed"
    assert report["log_shadow_gate"]["counts"]["high_no_evidence_overconfident_count"] == 0
    assert all(case["llm_status"] == "ok" for case in report["cases"])
    assert "I cannot verify the previous dialogue" not in report_text
    assert "live-private-session" not in report_text
    assert "\u4e3a\u4ec0\u4e48\u8fd9\u4e2a\u8981" not in report_text
    assert "hello" not in report_text


def test_answer_discipline_log_shadow_live_gate_fails_on_overconfident_reply(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XINYU_API_KEY", "test-key")
    monkeypatch.setenv("XINYU_BASE_URL", "https://example.test/v1")
    source = tmp_path / "live-log-fail.jsonl"
    source.write_text(
        json.dumps(
            {
                "session_id": "s",
                "role": "user",
                "text": "\u4e3a\u4ec0\u4e48\u8fd9\u4e2a\u8981\u6839\u636e\u524d\u9762\u7684\u5bf9\u8bdd\uff1f",
                "expected_retrieval_pressure": "high",
                "expected_evidence_sufficiency": "none",
                "expected_answer_discipline": "answer_current_only_acknowledge_missing_evidence",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    def fake_caller(messages, config):
        return "The previous conversation definitely said it, so continue from that history."

    report = run_answer_discipline_log_shadow_replay(
        tmp_path,
        sources=(source,),
        run_id="log-live-fail",
        live_llm=True,
        live_llm_caller=fake_caller,
    )

    assert report["log_shadow_gate"]["status"] == "failed"
    assert report["log_shadow_gate"]["counts"]["high_no_evidence_overconfident_count"] == 1


def test_answer_discipline_calibration_dashboard_summarizes_available_gates(tmp_path: Path) -> None:
    source = tmp_path / "dashboard-log.jsonl"
    source.write_text(
        json.dumps(
            {
                "session_id": "s",
                "role": "user",
                "text": "hello",
                "expected_retrieval_pressure": "none",
                "expected_evidence_sufficiency": "usable",
                "expected_answer_discipline": "answer_normally_current_message_first",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    run_answer_discipline_shadow_replay(tmp_path, run_id="dashboard-shadow")
    run_answer_discipline_log_shadow_replay(tmp_path, sources=(source,), run_id="dashboard-log")

    dashboard = build_answer_discipline_calibration_dashboard(tmp_path)
    dashboard_text = (tmp_path / "runtime/xinyu_calibration_dashboard.json").read_text(encoding="utf-8")

    assert dashboard["status"] == "passed"
    assert dashboard["passed"] is True
    assert dashboard["available_gate_count"] >= 2
    assert "hello" not in dashboard_text


def test_answer_discipline_live_trial_skips_without_credentials(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("XINYU_API_KEY_ENV", raising=False)
    monkeypatch.delenv("XINYU_API_KEY", raising=False)
    monkeypatch.delenv("XINYU_BASE_URL", raising=False)

    report = run_answer_discipline_trial(tmp_path, run_id="live-skip", live_llm=True)
    live = report["live_llm_trial"]

    assert live["status"] == "skipped_missing_credentials"
    assert report["boundaries"]["llm_calls"] == "skipped_missing_credentials"
    assert live["case_count"] == 3
    assert {case["llm_status"] for case in live["cases"]} == {"skipped"}
    assert live["calibration_gate"]["status"] == "skipped_missing_credentials"
    assert live["calibration_gate"]["passed"] is False


def test_answer_discipline_live_trial_writes_redacted_mock_report(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XINYU_API_KEY", "test-key")
    monkeypatch.setenv("XINYU_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("XINYU_LLM_MODEL", "test-model")
    replies = iter(
        [
            "根据能看到的记录，只能说你是在追问前面那次回答为什么需要依赖上下文。",
            "我不确定前面完整对话是什么；只能先按你当前这句来说，缺少足够证据。",
            "在。",
        ]
    )
    calls = []

    def fake_caller(messages, config):
        calls.append((messages, config.model, config.base_url, config.api_key_env))
        return next(replies)

    report = run_answer_discipline_trial(
        tmp_path,
        run_id="live-mock",
        live_llm=True,
        live_llm_caller=fake_caller,
    )
    report_text = (tmp_path / "runtime/answer_discipline_trial_report.json").read_text(encoding="utf-8")
    live = report["live_llm_trial"]
    cases = {case["case_id"]: case for case in live["cases"]}

    assert live["status"] == "completed"
    assert live["calibration_gate"]["status"] == "passed"
    assert live["calibration_gate"]["passed"] is True
    assert live["calibration_gate"]["counts"]["high_no_evidence_uncertainty_count"] == 1
    assert live["model"] == "test-model"
    assert len(calls) == 3
    assert set(cases) == {"high_usable", "high_none", "casual_none"}
    assert cases["high_none"]["flags"]["acknowledged_uncertainty"] is True
    assert cases["high_none"]["flags"]["overconfident_without_evidence"] is False
    assert cases["casual_none"]["reply_hash"]
    assert "Synthetic owner message" not in report_text
    assert "根据能看到的记录" not in report_text
    assert "为什么这个要" not in report_text
    assert "hello" not in report_text


def test_answer_discipline_live_gate_fails_on_overconfident_no_evidence(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XINYU_API_KEY", "test-key")
    monkeypatch.setenv("XINYU_BASE_URL", "https://example.test/v1")
    replies = iter(
        [
            "usable evidence reply",
            "the previous dialogue definitely said this, so continue from that history",
            "ok",
        ]
    )

    def fake_caller(messages, config):
        return next(replies)

    report = run_answer_discipline_trial(
        tmp_path,
        run_id="live-gate-fail",
        live_llm=True,
        live_llm_caller=fake_caller,
    )
    gate = report["live_llm_trial"]["calibration_gate"]

    assert gate["status"] == "failed"
    assert gate["passed"] is False
    assert gate["counts"]["high_no_evidence_overconfident_count"] == 1
    assert "no_overconfident_high_no_evidence_replies" in {
        check["name"] for check in gate["checks"] if check["passed"] is False
    }


def test_answer_discipline_strict_gate_returns_nonzero_when_skipped(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("XINYU_API_KEY_ENV", raising=False)
    monkeypatch.delenv("XINYU_API_KEY", raising=False)
    monkeypatch.delenv("XINYU_BASE_URL", raising=False)

    assert main(["--root", str(tmp_path), "--run-id", "strict-skip", "--live-llm", "--strict-gate"]) == 2


def test_answer_discipline_strict_gate_accepts_shadow_replay(tmp_path: Path) -> None:
    assert main(["--root", str(tmp_path), "--run-id", "strict-shadow", "--shadow-replay", "--strict-gate"]) == 0


def test_answer_discipline_strict_gate_accepts_log_shadow_replay(tmp_path: Path) -> None:
    source = tmp_path / "strict-log.jsonl"
    source.write_text(
        json.dumps(
            {
                "session_id": "s",
                "role": "user",
                "text": "hello",
                "expected_retrieval_pressure": "none",
                "expected_evidence_sufficiency": "usable",
                "expected_answer_discipline": "answer_normally_current_message_first",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert (
        main(
            [
                "--root",
                str(tmp_path),
                "--run-id",
                "strict-log-shadow",
                "--log-shadow-replay",
                "--log-source",
                str(source),
                "--strict-gate",
            ]
        )
        == 0
    )


def test_answer_discipline_safe_suite_uses_fixture_and_dashboard(tmp_path: Path) -> None:
    fixture = tmp_path / "tests/fixtures/answer_discipline_log_replay_sample.jsonl"
    fixture.parent.mkdir(parents=True)
    fixture.write_text(
        json.dumps(
            {
                "session_id": "s",
                "role": "user",
                "text": "hello",
                "expected_retrieval_pressure": "none",
                "expected_evidence_sufficiency": "usable",
                "expected_answer_discipline": "answer_normally_current_message_first",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert main(["--root", str(tmp_path), "--run-id", "safe-suite", "--safe-suite", "--strict-gate"]) == 0
    assert (tmp_path / "runtime/xinyu_calibration_dashboard.json").exists()
