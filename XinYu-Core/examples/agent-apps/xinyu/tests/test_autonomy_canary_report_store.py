from __future__ import annotations

import json
import sys
from pathlib import Path

from xinyu_autonomy_canary_report import main
from xinyu_autonomy_canary_report import INTENTION_STATE_REL as MODULE_INTENTION_STATE_REL
from xinyu_autonomy_canary_report import INTENTION_TRACE_REL as MODULE_INTENTION_TRACE_REL
from xinyu_autonomy_canary_report import RELATION_STATE_REL as MODULE_RELATION_STATE_REL
from xinyu_autonomy_canary_report import build_report
from xinyu_autonomy_canary_report_store import INTENTION_STATE_REL
from xinyu_autonomy_canary_report_store import INTENTION_TRACE_REL
from xinyu_autonomy_canary_report_store import RELATION_STATE_REL
from xinyu_autonomy_canary_report_store import read_autonomy_canary_recent_traces
from xinyu_autonomy_canary_report_store import read_autonomy_canary_text


def test_autonomy_canary_report_store_exports_legacy_paths() -> None:
    assert RELATION_STATE_REL == MODULE_RELATION_STATE_REL
    assert INTENTION_STATE_REL == MODULE_INTENTION_STATE_REL
    assert INTENTION_TRACE_REL == MODULE_INTENTION_TRACE_REL
    assert RELATION_STATE_REL == Path("memory/context/relation_posture_state.md")
    assert INTENTION_TRACE_REL == Path("runtime/intention_ecology_trace.jsonl")


def test_autonomy_canary_report_store_reads_bom_state_text(tmp_path: Path) -> None:
    path = tmp_path / RELATION_STATE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\ufeff- status: ready\n", encoding="utf-8")

    assert read_autonomy_canary_text(tmp_path / "missing.md") == ""
    assert read_autonomy_canary_text(path) == "- status: ready\n"


def test_autonomy_canary_report_store_reads_recent_trace_tail(tmp_path: Path) -> None:
    path = tmp_path / INTENTION_TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    older = {"checked_at": "old", "selected_intent": "old_intent", "ignored": "not exported"}
    recent = {"checked_at": "recent", "selected_intent": "comfort_quietly", "proactive_candidate": "none"}
    newest = {
        "checked_at": "newest",
        "selected_intent": "hold_presence",
        "selected_gate": "hold_or_silence",
        "autonomy_posture": "restrained",
        "feedback_signal": "owner_space",
        "proactive_candidate": "bad_direct_send",
        "memory_candidate": "none",
        "restraint_reason": "space_requested",
        "private": "hidden",
    }
    path.write_text(
        "\ufeff"
        + "\n".join(
            (
                json.dumps(older, ensure_ascii=False),
                json.dumps(recent, ensure_ascii=False),
                "[\"not\", \"dict\"]",
                "{bad",
                json.dumps(newest, ensure_ascii=False),
            )
        )
        + "\n",
        encoding="utf-8",
    )

    rows = read_autonomy_canary_recent_traces(path, limit=4)

    assert rows == [
        {
            "checked_at": "recent",
            "selected_intent": "comfort_quietly",
            "selected_gate": "",
            "autonomy_posture": "",
            "feedback_signal": "",
            "proactive_candidate": "none",
            "memory_candidate": "",
            "restraint_reason": "",
        },
        {
            "checked_at": "newest",
            "selected_intent": "hold_presence",
            "selected_gate": "hold_or_silence",
            "autonomy_posture": "restrained",
            "feedback_signal": "owner_space",
            "proactive_candidate": "bad_direct_send",
            "memory_candidate": "none",
            "restraint_reason": "space_requested",
        },
    ]


def test_autonomy_canary_report_build_report_uses_store_inputs(tmp_path: Path) -> None:
    context = tmp_path / "memory/context"
    runtime = tmp_path / "runtime"
    context.mkdir(parents=True)
    runtime.mkdir(parents=True)
    (tmp_path / RELATION_STATE_REL).write_text(
        "- status: ready\n- response_posture: quiet\n",
        encoding="utf-8",
    )
    (tmp_path / INTENTION_STATE_REL).write_text(
        "- status: ready\n"
        "- proactive_candidate: direct_send\n"
        "- proactive_delivery: direct\n"
        "- raw_private_body_retained: true\n",
        encoding="utf-8",
    )
    (tmp_path / INTENTION_TRACE_REL).write_text(
        json.dumps({"checked_at": "1", "proactive_candidate": "review_gated:comfort"}, ensure_ascii=False)
        + "\n"
        + json.dumps({"checked_at": "2", "proactive_candidate": "direct_send"}, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )

    report = build_report(tmp_path, trace_limit=1)

    assert report["relation_state"]["response_posture"] == "quiet"
    assert report["recent_intention_traces"] == [
        {
            "checked_at": "2",
            "selected_intent": "",
            "selected_gate": "",
            "autonomy_posture": "",
            "feedback_signal": "",
            "proactive_candidate": "direct_send",
            "memory_candidate": "",
            "restraint_reason": "",
        }
    ]
    assert report["warnings"] == [
        "unexpected proactive_candidate shape: direct_send",
        "unexpected proactive_delivery: direct",
        "raw_private_body_retained is not false: true",
        "trace has unexpected proactive_candidate: direct_send",
    ]


def test_autonomy_canary_report_cli_json_and_text_outputs(tmp_path: Path, capsys, monkeypatch) -> None:  # noqa: ANN001
    (tmp_path / RELATION_STATE_REL).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / INTENTION_TRACE_REL).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / RELATION_STATE_REL).write_text("- status: ready\n", encoding="utf-8")
    (tmp_path / INTENTION_STATE_REL).write_text("- status: ready\n", encoding="utf-8")
    (tmp_path / INTENTION_TRACE_REL).write_text(
        json.dumps({"checked_at": "1", "selected_intent": "one"}, ensure_ascii=False)
        + "\n"
        + json.dumps({"checked_at": "2", "selected_intent": "two"}, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["xinyu_autonomy_canary_report.py", "--root", str(tmp_path), "--json", "--last", "0"],
    )
    assert main() == 0
    json_out = capsys.readouterr().out
    payload = json.loads(json_out)
    assert payload["recent_intention_traces"] == [
        {
            "checked_at": "2",
            "selected_intent": "two",
            "selected_gate": "",
            "autonomy_posture": "",
            "feedback_signal": "",
            "proactive_candidate": "",
            "memory_candidate": "",
            "restraint_reason": "",
        }
    ]

    monkeypatch.setattr(
        sys,
        "argv",
        ["xinyu_autonomy_canary_report.py", "--root", str(tmp_path), "--last", "1"],
    )
    assert main() == 0
    text_out = capsys.readouterr().out
    assert "# XinYu autonomy canary report" in text_out
    assert "## Send these owner-private QQ canary messages" in text_out
    assert "## Recent intention traces" in text_out
    assert "## Warnings" in text_out
