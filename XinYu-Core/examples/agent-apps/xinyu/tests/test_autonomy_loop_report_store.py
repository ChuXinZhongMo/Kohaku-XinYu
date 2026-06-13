from __future__ import annotations

from pathlib import Path

from xinyu_autonomy_loop_report import ATTENTION_STATE_REL as MODULE_ATTENTION_STATE_REL
from xinyu_autonomy_loop_report import INTENTION_STATE_REL as MODULE_INTENTION_STATE_REL
from xinyu_autonomy_loop_report import INTENTION_TRACE_REL as MODULE_INTENTION_TRACE_REL
from xinyu_autonomy_loop_report import RELATION_STATE_REL as MODULE_RELATION_STATE_REL
from xinyu_autonomy_loop_report import REPORT_REL as MODULE_REPORT_REL
from xinyu_autonomy_loop_report import SELF_THOUGHT_STATE_REL as MODULE_SELF_THOUGHT_STATE_REL
from xinyu_autonomy_loop_report import SHORT_TERM_CONTINUITY_STATE_REL as MODULE_SHORT_TERM_CONTINUITY_STATE_REL
from xinyu_autonomy_loop_report_store import ATTENTION_STATE_REL
from xinyu_autonomy_loop_report_store import INTENTION_STATE_REL
from xinyu_autonomy_loop_report_store import INTENTION_TRACE_REL
from xinyu_autonomy_loop_report_store import RELATION_STATE_REL
from xinyu_autonomy_loop_report_store import REPORT_REL
from xinyu_autonomy_loop_report_store import SELF_THOUGHT_STATE_REL
from xinyu_autonomy_loop_report_store import SHORT_TERM_CONTINUITY_STATE_REL
from xinyu_autonomy_loop_report_store import autonomy_loop_intention_trace_path
from xinyu_autonomy_loop_report_store import autonomy_loop_report_path
from xinyu_autonomy_loop_report_store import autonomy_loop_state_path
from xinyu_autonomy_loop_report_store import read_autonomy_loop_state_text
from xinyu_autonomy_loop_report_store import read_latest_intention_trace
from xinyu_autonomy_loop_report_store import write_autonomy_loop_report_text


def test_autonomy_loop_report_store_exports_legacy_paths() -> None:
    assert REPORT_REL == MODULE_REPORT_REL
    assert INTENTION_STATE_REL == MODULE_INTENTION_STATE_REL
    assert INTENTION_TRACE_REL == MODULE_INTENTION_TRACE_REL
    assert ATTENTION_STATE_REL == MODULE_ATTENTION_STATE_REL
    assert RELATION_STATE_REL == MODULE_RELATION_STATE_REL
    assert SELF_THOUGHT_STATE_REL == MODULE_SELF_THOUGHT_STATE_REL
    assert SHORT_TERM_CONTINUITY_STATE_REL == MODULE_SHORT_TERM_CONTINUITY_STATE_REL
    assert REPORT_REL == Path("worklog/xinyu-autonomy-loop-latest.md")
    assert INTENTION_TRACE_REL == Path("runtime/intention_ecology_trace.jsonl")


def test_autonomy_loop_report_store_reads_state_text_safely(tmp_path: Path) -> None:
    assert read_autonomy_loop_state_text(tmp_path, INTENTION_STATE_REL) == ""

    path = autonomy_loop_state_path(tmp_path, INTENTION_STATE_REL)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\ufeff- selected_intent: answer_current_turn\n", encoding="utf-8")

    assert path == tmp_path / INTENTION_STATE_REL
    assert read_autonomy_loop_state_text(tmp_path, INTENTION_STATE_REL) == "- selected_intent: answer_current_turn\n"


def test_autonomy_loop_report_store_reads_latest_intention_trace(tmp_path: Path) -> None:
    assert read_latest_intention_trace(tmp_path) == {}

    path = autonomy_loop_intention_trace_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\ufeff" + "\n".join(['{"seq":1}', '{"seq":2}', ""]) + "\n",
        encoding="utf-8",
    )
    assert read_latest_intention_trace(tmp_path) == {"seq": 2}

    path.write_text("{bad\n{\"seq\":3}\n", encoding="utf-8")
    assert read_latest_intention_trace(tmp_path) == {}


def test_autonomy_loop_report_store_writes_report_with_output_resolution(tmp_path: Path) -> None:
    relative = write_autonomy_loop_report_text(tmp_path, "# Report\n", output=Path("custom/report.md"))
    absolute = write_autonomy_loop_report_text(tmp_path, "# Absolute\n", output=tmp_path / "abs.md")

    assert autonomy_loop_report_path(tmp_path) == tmp_path / REPORT_REL
    assert relative == tmp_path / "custom/report.md"
    assert absolute == tmp_path / "abs.md"
    assert relative.read_text(encoding="utf-8") == "# Report\n"
    assert absolute.read_text(encoding="utf-8") == "# Absolute\n"


def test_autonomy_loop_report_store_preserves_relative_root_path_semantics() -> None:
    root = Path("relative-root")

    assert autonomy_loop_state_path(root, INTENTION_STATE_REL) == root / INTENTION_STATE_REL
    assert autonomy_loop_intention_trace_path(root) == root / INTENTION_TRACE_REL
    assert autonomy_loop_report_path(root, Path("custom/report.md")) == root / "custom/report.md"
    assert autonomy_loop_report_path(root) == root / root / REPORT_REL
