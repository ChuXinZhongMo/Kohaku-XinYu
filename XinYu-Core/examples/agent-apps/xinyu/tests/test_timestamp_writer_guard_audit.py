from __future__ import annotations

import sys
from pathlib import Path


OPS_VALIDATION = Path(__file__).resolve().parents[1] / "ops" / "validation"
if str(OPS_VALIDATION) not in sys.path:
    sys.path.insert(0, str(OPS_VALIDATION))

from timestamp_writer_guard_audit import build_timestamp_writer_guard_audit, render_markdown  # noqa: E402


def test_timestamp_writer_guard_audit_reports_metadata_without_bodies(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    app.mkdir(parents=True)
    (app / "xinyu_guarded_writer.py").write_text(
        """
from datetime import datetime

def write(path):
    updated_at = datetime.now().astimezone().isoformat()
    path.write_text(f"updated_at: {updated_at}\\n")
""",
        encoding="utf-8",
    )
    (app / "xinyu_risky_writer.py").write_text(
        """
def write(path, value):
    path.write_text(f"updated_at: {value or 'unknown'}\\nPRIVATE_INLINE_WRITER_TEXT")
""",
        encoding="utf-8",
    )
    memory = app / "memory/context/private_state.md"
    memory.parent.mkdir(parents=True)
    memory.write_text("updated_at: not-a-time\nprivate body should not appear\n", encoding="utf-8")

    result = build_timestamp_writer_guard_audit(app)
    rendered = render_markdown(result) + str(result)
    by_file = {item["path"]: item for item in result["items"]}

    assert by_file["xinyu_guarded_writer.py"]["guard_status"] == "guarded"
    assert by_file["xinyu_risky_writer.py"]["guard_status"] == "risky_literal_fallback"
    assert result["guard_status_counts"]["guarded"] >= 1
    assert result["guard_status_counts"]["risky_literal_fallback"] == 1
    assert "private body should not appear" not in rendered
    assert "PRIVATE_INLINE_WRITER_TEXT" not in rendered
    assert "not-a-time" not in rendered


def test_timestamp_writer_guard_audit_marks_non_writers_as_reference_only(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    app.mkdir(parents=True)
    (app / "xinyu_reader.py").write_text(
        """
SCHEMA = {"updated_at": "sample"}

def read_only(row):
    return row.get("updated_at")
""",
        encoding="utf-8",
    )

    result = build_timestamp_writer_guard_audit(app)

    assert result["items"][0]["guard_status"] == "reference_only"
    assert result["items"][0]["writer_source"] is False


def test_timestamp_writer_guard_audit_does_not_escalate_parser_or_read_extraction(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    app.mkdir(parents=True)
    (app / "xinyu_cli_and_reader.py").write_text(
        """
def wire(parser, text):
    parser.add_argument("--started-at", default="", help="Optional ISO timestamp.")
    updated_at = _extract_field(text, "updated_at", "unknown")
    started_at=args.started_at or None
    return updated_at

def save(path):
    path.write_text("status: ok\\n")
""",
        encoding="utf-8",
    )

    result = build_timestamp_writer_guard_audit(app)

    assert {item["guard_status"] for item in result["items"]} == {"reference_only"}


def test_timestamp_writer_guard_audit_keeps_function_signature_reference_only(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    app.mkdir(parents=True)
    (app / "xinyu_signature_writer.py").write_text(
        """
def save(path, *, recorded_at: str = ""):
    path.write_text("status: ok\\n")
""",
        encoding="utf-8",
    )

    result = build_timestamp_writer_guard_audit(app)

    assert result["items"][0]["guard_status"] == "reference_only"
    assert result["items"][0]["line_kind"] == "schema_or_reference"


def test_timestamp_writer_guard_audit_keeps_sql_targets_and_row_reads_reference_only(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    app.mkdir(parents=True)
    (app / "xinyu_sql_writer.py").write_text(
        """
def save(conn, row):
    conn.execute(
        '''
        UPDATE sessions
        SET last_seen_at = ?
        ON CONFLICT(id) DO UPDATE SET
            updated_at = excluded.updated_at
        ''',
        (row["created_at"],),
    )
    return {"created_at": row["created_at"]}
""",
        encoding="utf-8",
    )

    result = build_timestamp_writer_guard_audit(app)

    assert {item["guard_status"] for item in result["items"]} == {"reference_only"}
    assert {item["line_kind"] for item in result["items"]} == {"schema_or_reference"}


def test_timestamp_writer_guard_audit_keeps_timestamp_conditionals_reference_only(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    app.mkdir(parents=True)
    (app / "xinyu_tail_reader.py").write_text(
        """
def save(path, row):
    marker = "no_recorded_time"
    recorded_at = row.get("recorded_at")
    if recorded_at:
        marker = "has_recorded_time"
    path.write_text(marker)
""",
        encoding="utf-8",
    )

    result = build_timestamp_writer_guard_audit(app)

    assert {item["guard_status"] for item in result["items"]} == {"reference_only"}
    assert {item["line_kind"] for item in result["items"]} == {"schema_or_reference"}


def test_timestamp_writer_guard_audit_keeps_age_calculation_anchor_reference_only(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    app.mkdir(parents=True)
    (app / "xinyu_initiative_orchestrator_like.py").write_text(
        """
def save_context_gate(path, evaluated_at, observed_at):
    age_seconds = _age_seconds(evaluated_at, observed_at=observed_at)
    path.write_text(f"age_seconds: {age_seconds}\\n")
""",
        encoding="utf-8",
    )

    result = build_timestamp_writer_guard_audit(app)

    assert result["items"][0]["guard_status"] == "reference_only"
    assert result["items"][0]["line_kind"] == "schema_or_reference"
    assert result["items"][0]["reason"] == "timestamp field is an age calculation anchor"


def test_timestamp_writer_guard_audit_keeps_monotonic_runtime_marker_reference_only(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    app.mkdir(parents=True)
    (app / "xinyu_runtime_age_writer.py").write_text(
        """
import time

def save(path):
    state = RecentState(updated_at=time.monotonic())
    payload = {"updated_at": time.monotonic()}
    path.write_text(str(payload))
    return state
""",
        encoding="utf-8",
    )

    result = build_timestamp_writer_guard_audit(app)

    assert {item["guard_status"] for item in result["items"]} == {
        "direct_writer_candidate",
        "reference_only",
    }
    by_kind = {item["line_kind"]: item["guard_status"] for item in result["items"]}
    assert by_kind["schema_or_reference"] == "reference_only"
    assert by_kind["direct_emitted_timestamp"] == "direct_writer_candidate"


def test_timestamp_writer_guard_audit_skips_virtualenv_and_codex_scratch_dirs(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    app.mkdir(parents=True)
    (app / "xinyu_real_writer.py").write_text(
        'def save(path):\n    path.write_text(f"updated_at: {value}\\n")\n',
        encoding="utf-8",
    )
    venv = app / ".venv/Lib/site-packages/pkg"
    venv.mkdir(parents=True)
    (venv / "third_party.py").write_text(
        'def save(path):\n    path.write_text(f"updated_at: {value}\\n")\n',
        encoding="utf-8",
    )
    scratch = app / "codex-qq-20260506T122357"
    scratch.mkdir()
    (scratch / "scratch.py").write_text(
        'def save(path):\n    path.write_text(f"updated_at: {value}\\n")\n',
        encoding="utf-8",
    )
    self_found = app / "learning/self_found/imported_bundle/selected_files/src"
    self_found.mkdir(parents=True)
    (self_found / "third_party_sample.py").write_text(
        'def save(path):\n    path.write_text(f"timestamp: {value}\\n")\n',
        encoding="utf-8",
    )

    result = build_timestamp_writer_guard_audit(app)

    assert result["source_file_count"] == 1
    assert [item["path"] for item in result["items"]] == ["xinyu_real_writer.py"]


def test_timestamp_writer_guard_audit_classifies_direct_emitted_timestamp(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    app.mkdir(parents=True)
    (app / "xinyu_json_writer.py").write_text(
        """
import json

def save(path, event_time):
    payload = {"event_time": event_time}
    path.write_text(json.dumps(payload))
""",
        encoding="utf-8",
    )

    result = build_timestamp_writer_guard_audit(app)

    assert result["items"][0]["guard_status"] == "direct_writer_candidate"
    assert result["items"][0]["line_kind"] == "direct_emitted_timestamp"
    assert result["guard_status_counts"]["direct_writer_candidate"] == 1
    assert result["line_kind_counts"]["direct_emitted_timestamp"] == 1


def test_timestamp_writer_guard_audit_classifies_template_timestamp_constant(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    app.mkdir(parents=True)
    (app / "xinyu_template_writer.py").write_text(
        '''
def save(path, updated_at):
    text = """
updated_at: {updated_at}
"""
    path.write_text(text)
''',
        encoding="utf-8",
    )

    result = build_timestamp_writer_guard_audit(app)

    assert result["items"][0]["guard_status"] == "template_timestamp_candidate"
    assert result["items"][0]["line_kind"] == "template_timestamp_constant"
    assert result["guard_status_counts"]["template_timestamp_candidate"] == 1
    assert result["line_kind_counts"]["template_timestamp_constant"] == 1


def test_timestamp_writer_guard_audit_classifies_report_metadata(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    app.mkdir(parents=True)
    (app / "xinyu_report_writer.py").write_text(
        """
def write_report(path, created_at):
    result = {"created_at": created_at}
    path.write_text(str(result))
""",
        encoding="utf-8",
    )

    result = build_timestamp_writer_guard_audit(app)

    assert result["items"][0]["guard_status"] == "report_metadata_candidate"
    assert result["items"][0]["line_kind"] == "report_metadata"
    assert result["guard_status_counts"]["report_metadata_candidate"] == 1
    assert result["line_kind_counts"]["report_metadata"] == 1


def test_timestamp_writer_guard_audit_keeps_writer_schema_reference_only(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    app.mkdir(parents=True)
    (app / "xinyu_schema_writer.py").write_text(
        """
SCHEMA = {"observed_at": "ISO timestamp"}

def save(path):
    path.write_text("status: ok\\n")
""",
        encoding="utf-8",
    )

    result = build_timestamp_writer_guard_audit(app)

    assert result["items"][0]["guard_status"] == "reference_only"
    assert result["items"][0]["line_kind"] == "schema_or_reference"
    assert result["items"][0]["writer_source"] is True
    assert result["line_kind_counts"]["schema_or_reference"] == 1


def test_timestamp_writer_guard_audit_keeps_default_and_loader_maps_reference_only(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    app.mkdir(parents=True)
    (app / "xinyu_runtime_presence_like.py").write_text(
        """
def _default_fields():
    return {"updated_at": ""}

def _load_codex_fields(data):
    updated_at = data.get("updated_at")
    return {"updated_at": updated_at}

def save(path):
    path.write_text("status: ok\\n")
""",
        encoding="utf-8",
    )

    result = build_timestamp_writer_guard_audit(app)

    assert {item["guard_status"] for item in result["items"]} == {"reference_only"}
    assert {item["line_kind"] for item in result["items"]} == {"schema_or_reference"}
    assert result["line_kind_counts"]["schema_or_reference"] == 3
