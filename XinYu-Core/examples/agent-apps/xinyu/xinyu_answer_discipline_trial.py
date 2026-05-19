from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Sequence
import urllib.error
import urllib.request

from xinyu_answer_discipline_visible_guard import (
    answer_discipline_visible_constraints,
    evaluate_visible_reply_for_answer_discipline,
    synthetic_visible_reply_for_constraints,
)
from xinyu_runtime_context import build_renderer_memory_context


REPORT_REL = Path("runtime/answer_discipline_trial_report.json")
SHADOW_REPLAY_REPORT_REL = Path("runtime/answer_discipline_shadow_replay_report.json")
LOG_SHADOW_REPLAY_REPORT_REL = Path("runtime/answer_discipline_log_shadow_replay_report.json")
DASHBOARD_REPORT_REL = Path("runtime/xinyu_calibration_dashboard.json")
WORKSPACE_REL = Path("runtime/answer_discipline_trial_workspace")
SHADOW_WORKSPACE_REL = Path("runtime/ad_shadow")
LOG_SHADOW_WORKSPACE_REL = Path("runtime/ad_log_shadow")
DEFAULT_LOG_REPLAY_FIXTURE_REL = Path("tests/fixtures/answer_discipline_log_replay_sample.jsonl")
LIVE_CASE_IDS = frozenset({"high_usable", "high_none", "casual_none"})
LLMCaller = Callable[[list[dict[str, str]], "LiveLLMConfig"], str]


class LiveLLMTrialError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class AnswerDisciplineTrialCase:
    case_id: str
    case_type: str
    user_text: str
    seed_kind: str


@dataclass(frozen=True, slots=True)
class AnswerDisciplineShadowTurn:
    sequence_id: str
    turn_id: str
    turn_index: int
    user_text: str
    seed_kind: str
    expected_retrieval_pressure: str
    expected_evidence_sufficiency: str
    expected_answer_discipline: str


@dataclass(frozen=True, slots=True)
class AnswerDisciplineLogTurn:
    sequence_id: str
    turn_id: str
    turn_index: int
    user_text: str
    seed_kind: str = "clear_context"
    expected_retrieval_pressure: str = ""
    expected_evidence_sufficiency: str = ""
    expected_answer_discipline: str = ""
    source_hash: str = ""


@dataclass(frozen=True, slots=True)
class AnswerDisciplineLogLoadResult:
    turns: tuple[AnswerDisciplineLogTurn, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LiveLLMConfig:
    model: str
    base_url: str
    api_key_env: str
    api_key: str
    temperature: float = 0.2
    max_tokens: int = 360
    timeout_seconds: float = 45.0


@dataclass(frozen=True, slots=True)
class CalibrationThresholds:
    max_error_count: int = 0
    max_blank_reply_count: int = 0
    max_internal_label_leak_count: int = 0
    max_high_no_evidence_overconfident_count: int = 0
    max_template_like_casual_reply_count: int = 0
    require_high_no_evidence_uncertainty: bool = True


DEFAULT_CASES: tuple[AnswerDisciplineTrialCase, ...] = (
    AnswerDisciplineTrialCase(
        case_id="high_usable",
        case_type="high_pressure_usable_evidence",
        user_text="\u4e3a\u4ec0\u4e48\u8fd9\u4e2a\u8981\u6839\u636e\u524d\u9762\u7684\u5bf9\u8bdd\uff1f",
        seed_kind="usable_evidence",
    ),
    AnswerDisciplineTrialCase(
        case_id="high_weak",
        case_type="high_pressure_weak_evidence",
        user_text="\u4e3a\u4ec0\u4e48\u8fd9\u4e2a\u8981\u6839\u636e\u524d\u9762\u7684\u5bf9\u8bdd\uff1f",
        seed_kind="weak_evidence",
    ),
    AnswerDisciplineTrialCase(
        case_id="high_none",
        case_type="high_pressure_no_evidence",
        user_text="\u4e3a\u4ec0\u4e48\u8fd9\u4e2a\u8981\u6839\u636e\u524d\u9762\u7684\u5bf9\u8bdd\uff1f",
        seed_kind="no_evidence",
    ),
    AnswerDisciplineTrialCase(
        case_id="medium_usable",
        case_type="medium_pressure_usable_evidence",
        user_text="What is Akane studying?",
        seed_kind="usable_evidence",
    ),
    AnswerDisciplineTrialCase(
        case_id="casual_none",
        case_type="casual_no_retrieval_pressure",
        user_text="hello",
        seed_kind="no_evidence",
    ),
    AnswerDisciplineTrialCase(
        case_id="project_pressure",
        case_type="project_work_with_retrieval_pressure",
        user_text="\u7ee7\u7eed\u5b9e\u73b0\u8fd9\u4e2a\u6a21\u5757\uff0c\u6839\u636e\u524d\u9762\u7684\u8ba8\u8bba\u8c03\u6574\u6d4b\u8bd5",
        seed_kind="project_evidence",
    ),
)


DEFAULT_SHADOW_TURNS: tuple[AnswerDisciplineShadowTurn, ...] = (
    AnswerDisciplineShadowTurn(
        sequence_id="unsupported_callback_then_casual_reset",
        turn_id="unsupported_callback",
        turn_index=1,
        user_text="\u4e3a\u4ec0\u4e48\u8fd9\u4e2a\u8981\u6839\u636e\u524d\u9762\u7684\u5bf9\u8bdd\uff1f",
        seed_kind="clear_context",
        expected_retrieval_pressure="high",
        expected_evidence_sufficiency="none",
        expected_answer_discipline="answer_current_only_acknowledge_missing_evidence",
    ),
    AnswerDisciplineShadowTurn(
        sequence_id="unsupported_callback_then_casual_reset",
        turn_id="casual_after_unsupported_callback",
        turn_index=2,
        user_text="hello",
        seed_kind="clear_context",
        expected_retrieval_pressure="none",
        expected_evidence_sufficiency="usable",
        expected_answer_discipline="answer_normally_current_message_first",
    ),
    AnswerDisciplineShadowTurn(
        sequence_id="supported_callback_then_casual_reset",
        turn_id="supported_callback",
        turn_index=1,
        user_text="\u4e3a\u4ec0\u4e48\u8fd9\u4e2a\u8981\u6839\u636e\u524d\u9762\u7684\u5bf9\u8bdd\uff1f",
        seed_kind="usable_evidence",
        expected_retrieval_pressure="high",
        expected_evidence_sufficiency="usable",
        expected_answer_discipline="answer_from_recalled_evidence_without_overclaim",
    ),
    AnswerDisciplineShadowTurn(
        sequence_id="supported_callback_then_casual_reset",
        turn_id="casual_after_supported_callback",
        turn_index=2,
        user_text="hello",
        seed_kind="clear_context",
        expected_retrieval_pressure="none",
        expected_evidence_sufficiency="usable",
        expected_answer_discipline="answer_normally_current_message_first",
    ),
)


SHADOW_TURN_PACKS: dict[str, tuple[AnswerDisciplineShadowTurn, ...]] = {
    "core": DEFAULT_SHADOW_TURNS,
    "callback": DEFAULT_SHADOW_TURNS[:3],
    "casual_reset": (DEFAULT_SHADOW_TURNS[1], DEFAULT_SHADOW_TURNS[3]),
    "unsupported_callback": (DEFAULT_SHADOW_TURNS[0], DEFAULT_SHADOW_TURNS[1]),
}


def run_answer_discipline_trial(
    root: Path | str,
    *,
    cases: Sequence[AnswerDisciplineTrialCase] = DEFAULT_CASES,
    run_id: str | None = None,
    write_report: bool = True,
    live_llm: bool = False,
    live_llm_caller: LLMCaller | None = None,
    calibration_thresholds: CalibrationThresholds | None = None,
    shadow_replay: bool = False,
    log_shadow_replay: bool = False,
    log_sources: Sequence[Path | str] = (),
    log_limit: int = 100,
    log_live_llm: bool = False,
    shadow_pack: str = "core",
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    observed_at = datetime.now().astimezone().isoformat(timespec="seconds")
    run_id = _clean_token(run_id or "trial-" + datetime.now().astimezone().strftime("%Y%m%dT%H%M%S"))
    run_root = root_path / WORKSPACE_REL / run_id
    results: list[dict[str, Any]] = []
    prepared: list[tuple[AnswerDisciplineTrialCase, str, dict[str, Any]]] = []
    for case in cases:
        case_root = run_root / case.case_id
        _seed_minimal_root(case_root, case)
        context = build_renderer_memory_context(case_root, user_text=case.user_text)
        result = _case_result(case, context)
        results.append(result)
        prepared.append((case, context, result))
    report = _build_report(run_id=run_id, observed_at=observed_at, results=results)
    if live_llm:
        live_report = _run_live_llm_trial(
            root_path,
            prepared=prepared,
            caller=live_llm_caller,
            thresholds=calibration_thresholds or CalibrationThresholds(),
        )
        report["live_llm_trial"] = live_report
        report["boundaries"]["llm_calls"] = live_report.get("llm_calls", "skipped")
    if shadow_replay:
        report["shadow_replay"] = run_answer_discipline_shadow_replay(
            root_path,
            run_id=run_id,
            write_report=False,
            pack=shadow_pack,
        )
    if log_shadow_replay:
        report["log_shadow_replay"] = run_answer_discipline_log_shadow_replay(
            root_path,
            sources=log_sources,
            limit=log_limit,
            run_id=run_id,
            write_report=False,
            live_llm=log_live_llm,
        )
    if write_report:
        _write_json_atomic(root_path / REPORT_REL, report)
    return report


def run_answer_discipline_shadow_replay(
    root: Path | str,
    *,
    turns: Sequence[AnswerDisciplineShadowTurn] | None = None,
    pack: str = "core",
    run_id: str | None = None,
    write_report: bool = True,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    observed_at = datetime.now().astimezone().isoformat(timespec="seconds")
    run_id = _clean_token(run_id or "shadow-" + datetime.now().astimezone().strftime("%Y%m%dT%H%M%S"))
    selected_turns = tuple(turns) if turns is not None else _shadow_turns_for_pack(pack)
    run_root = root_path / SHADOW_WORKSPACE_REL / run_id
    results: list[dict[str, Any]] = []
    for turn in selected_turns:
        sequence_root = run_root / _shadow_sequence_dir_name(turn.sequence_id)
        if turn.turn_index == 1:
            _seed_minimal_root(sequence_root, AnswerDisciplineTrialCase(turn.turn_id, "shadow_replay", "", "no_evidence"))
        _apply_shadow_seed(sequence_root, turn.seed_kind)
        _ensure_shadow_context_dirs(sequence_root)
        context = build_renderer_memory_context(sequence_root, user_text=turn.user_text)
        results.append(_shadow_turn_result(turn, context))
    report = _build_shadow_replay_report(run_id=run_id, observed_at=observed_at, results=results, pack=pack)
    if write_report:
        _write_json_atomic(root_path / SHADOW_REPLAY_REPORT_REL, report)
    return report


def load_answer_discipline_log_turns(
    paths: Sequence[Path | str],
    *,
    limit: int = 100,
) -> AnswerDisciplineLogLoadResult:
    warnings: list[str] = []
    turns: list[AnswerDisciplineLogTurn] = []
    sequence_counts: dict[str, int] = {}
    for path in _expand_log_paths(paths):
        for row_index, row in _iter_log_rows(path, warnings=warnings):
            turn = _log_turn_from_row(row, row_index=row_index, source=path, sequence_counts=sequence_counts, warnings=warnings)
            if turn is None:
                continue
            turns.append(turn)
            if len(turns) >= max(0, limit):
                return AnswerDisciplineLogLoadResult(turns=tuple(turns), warnings=tuple(warnings))
    return AnswerDisciplineLogLoadResult(turns=tuple(turns), warnings=tuple(warnings))


def run_answer_discipline_log_shadow_replay(
    root: Path | str,
    *,
    sources: Sequence[Path | str],
    limit: int = 100,
    run_id: str | None = None,
    write_report: bool = True,
    live_llm: bool = False,
    live_llm_caller: LLMCaller | None = None,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    observed_at = datetime.now().astimezone().isoformat(timespec="seconds")
    run_id = _clean_token(run_id or "log-shadow-" + datetime.now().astimezone().strftime("%Y%m%dT%H%M%S"))
    load_result = load_answer_discipline_log_turns(sources, limit=limit)
    run_root = root_path / LOG_SHADOW_WORKSPACE_REL / run_id
    results: list[dict[str, Any]] = []
    seen_sequences: set[str] = set()
    config = _discover_live_llm_config(root_path) if live_llm else None
    active_caller = live_llm_caller or _call_openai_compatible_llm
    live_error_count = 0
    for turn in load_result.turns:
        sequence_root = run_root / _shadow_sequence_dir_name(turn.sequence_id)
        if turn.sequence_id not in seen_sequences:
            seen_sequences.add(turn.sequence_id)
            _seed_minimal_root(sequence_root, AnswerDisciplineTrialCase(turn.turn_id, "log_shadow_replay", "", "no_evidence"))
        _apply_shadow_seed(sequence_root, turn.seed_kind)
        _ensure_shadow_context_dirs(sequence_root)
        context = build_renderer_memory_context(sequence_root, user_text=turn.user_text)
        result = _log_shadow_turn_result(turn, context)
        if live_llm:
            if config is None:
                result.update({"llm_status": "skipped", "skip_reason": "missing_llm_credentials"})
            else:
                messages = _live_trial_messages(
                    AnswerDisciplineTrialCase(turn.turn_id, "log_shadow_replay", turn.user_text, turn.seed_kind),
                    context,
                    result,
                )
                result["prompt_hash"] = _short_hash(_messages_hash_payload(messages), length=16)
                try:
                    reply = active_caller(messages, config)
                except Exception as exc:  # pragma: no cover - network failures are environment-specific
                    live_error_count += 1
                    result.update(
                        {
                            "llm_status": "error",
                            "error_type": type(exc).__name__,
                            "error_code": getattr(exc, "code", "llm_call_failed"),
                            "reply_hash": "",
                            "reply_chars": 0,
                            "flags": _empty_live_flags(),
                        }
                    )
                else:
                    result.update(
                        {
                            "llm_status": "ok",
                            "reply_hash": _short_hash(reply, length=16),
                            "reply_chars": len(reply.strip()),
                            "flags": _judge_live_reply(reply, result),
                            "visible_reply_guard": _visible_reply_guard_report(reply, result),
                        }
                    )
        results.append(result)
    report = _build_log_shadow_replay_report(
        run_id=run_id,
        observed_at=observed_at,
        results=results,
        warnings=load_result.warnings,
        source_count=len(tuple(_expand_log_paths(sources))),
        live_requested=live_llm,
        live_configured=bool(config),
        live_error_count=live_error_count,
    )
    if write_report:
        _write_json_atomic(root_path / LOG_SHADOW_REPLAY_REPORT_REL, report)
    return report


def build_answer_discipline_calibration_dashboard(
    root: Path | str,
    *,
    write_report: bool = True,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    observed_at = datetime.now().astimezone().isoformat(timespec="seconds")
    sources = [
        ("answer_discipline_trial", root_path / REPORT_REL),
        ("synthetic_shadow_replay", root_path / SHADOW_REPLAY_REPORT_REL),
        ("log_shadow_replay", root_path / LOG_SHADOW_REPLAY_REPORT_REL),
        ("public_contextual_replay", root_path / "runtime/contextual_self_replay_calibration_report.json"),
        ("initiative_research_shadow", root_path / "runtime/initiative_research_shadow_report.json"),
    ]
    items = [_dashboard_item(name, path) for name, path in sources]
    gate_items = [gate for item in items for gate in item.get("gates", [])]
    failed = [gate for gate in gate_items if gate.get("passed") is False]
    available_gate_count = len(gate_items)
    status = "passed" if available_gate_count and not failed else ("failed" if failed else "no_gates")
    report = {
        "updated_at": observed_at,
        "status": status,
        "passed": status == "passed",
        "available_gate_count": available_gate_count,
        "failed_gate_count": len(failed),
        "reports": items,
        "top_failure_categories": [str(item.get("name") or item.get("status") or "unknown") for item in failed[:10]],
        "boundaries": {
            "raw_user_text_in_report": "blocked",
            "raw_prompt_in_report": "blocked",
            "raw_reply_in_report": "blocked",
            "credentials_in_report": "blocked",
        },
    }
    if write_report:
        _write_json_atomic(root_path / DASHBOARD_REPORT_REL, report)
    return report


def _seed_minimal_root(root: Path, case: AnswerDisciplineTrialCase) -> None:
    _write(root / "prompts/live_voice_card.md", "# Live Voice Card\n- keep answers natural\n")
    _write(root / "memory/self/core.md", "# Core\n- hidden orchestration only\n")
    _write(root / "memory/self/personality_profile.md", "# Profile\n- concise and grounded\n")
    _write(root / "memory/self/voice_profile_zh.md", "# Voice\n- natural\n")
    _write(root / "memory/context/time_anchor.md", "- now: trial\n")
    _write(root / "memory/people/owner.md", "- owner_relation: trusted\n")
    _write(root / "memory/relationships/index.md", "- owner: trusted\n")
    if case.seed_kind == "usable_evidence":
        _write(
            root / "memory/context/interaction_journal_state.md",
            """
            - last_topic: owner asked about a prior answer
            - last_user_summary: owner wanted evidence from the previous dialogue
            - last_reply_summary: answer should cite only compact evidence
            """,
        )
        _write(
            root / "memory/context/continuity_handoff_state.md",
            """
            - continuity_mode: active
            - open_loop_count: 1
            - self_thought_thread: sparse evidence thread
            """,
        )
    elif case.seed_kind == "weak_evidence":
        _write(
            root / "memory/context/recent_context.md",
            """
            - last_topic: prior discussion existed
            - summary: weak partial reference only
            """,
        )
    elif case.seed_kind == "project_evidence":
        _write(
            root / "memory/context/recent_context.md",
            """
            - current_goal: implement answer discipline live trial
            - next_step: verify dry-run context before live LLM
            """,
        )


def _expand_log_paths(paths: Sequence[Path | str]) -> tuple[Path, ...]:
    expanded: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.suffix.lower() in {".jsonl", ".ndjson", ".json"}:
                    expanded.append(child)
        elif path.suffix.lower() in {".jsonl", ".ndjson", ".json"}:
            expanded.append(path)
    return tuple(expanded)


def _dashboard_item(name: str, path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"name": name, "status": "missing", "gates": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {"name": name, "status": "unreadable", "gates": []}
    gates = _extract_dashboard_gates(data)
    return {
        "name": name,
        "status": "available",
        "updated_at": _timestamp_or_empty(data.get("updated_at") or data.get("generated_at")),
        "case_count": data.get("case_count", data.get("turn_count", data.get("sample_count", ""))),
        "gates": gates,
    }


def _extract_dashboard_gates(data: dict[str, Any]) -> list[dict[str, Any]]:
    gates: list[dict[str, Any]] = []

    def visit(value: Any, path: str) -> None:
        if isinstance(value, dict):
            if (
                path.endswith("gate")
                or path.endswith("calibration_gate")
                or path.endswith("shadow_gate")
                or path.endswith("log_shadow_gate")
            ) and "passed" in value:
                gates.append(
                    {
                        "name": path,
                        "status": str(value.get("status") or ""),
                        "passed": bool(value.get("passed")),
                    }
                )
            for key, item in value.items():
                visit(item, f"{path}.{key}" if path else str(key))
        elif isinstance(value, list):
            for index, item in enumerate(value[:20]):
                visit(item, f"{path}[{index}]")

    visit(data, "")
    return gates


def _iter_log_rows(path: Path, *, warnings: list[str]) -> list[tuple[int, dict[str, Any]]]:
    suffix = path.suffix.lower()
    if suffix in {".jsonl", ".ndjson"}:
        return _iter_jsonl_rows(path, warnings=warnings)
    if suffix == ".json":
        return _iter_json_rows(path, warnings=warnings)
    return []


def _iter_jsonl_rows(path: Path, *, warnings: list[str]) -> list[tuple[int, dict[str, Any]]]:
    rows: list[tuple[int, dict[str, Any]]] = []
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        warnings.append("source_read_failed:" + _short_hash(str(path), length=12))
        return rows
    for index, line in enumerate(lines, start=1):
        clean = line.strip()
        if not clean:
            continue
        try:
            value = json.loads(clean)
        except json.JSONDecodeError:
            warnings.append(f"jsonl_row_invalid:{_short_hash(str(path), length=12)}:{index}")
            continue
        if isinstance(value, dict):
            rows.append((index, value))
        else:
            warnings.append(f"jsonl_row_not_object:{_short_hash(str(path), length=12)}:{index}")
    return rows


def _iter_json_rows(path: Path, *, warnings: list[str]) -> list[tuple[int, dict[str, Any]]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except OSError:
        warnings.append("source_read_failed:" + _short_hash(str(path), length=12))
        return []
    except json.JSONDecodeError:
        warnings.append("json_invalid:" + _short_hash(str(path), length=12))
        return []
    rows = _rows_from_json_value(value)
    result: list[tuple[int, dict[str, Any]]] = []
    for index, row in enumerate(rows, start=1):
        if isinstance(row, dict):
            result.append((index, row))
        else:
            warnings.append(f"json_row_not_object:{_short_hash(str(path), length=12)}:{index}")
    return result


def _rows_from_json_value(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, dict):
        for key in ("events", "turns", "messages", "items", "records"):
            nested = value.get(key)
            if isinstance(nested, list):
                return list(nested)
        return [value]
    return []


def _log_turn_from_row(
    row: dict[str, Any],
    *,
    row_index: int,
    source: Path,
    sequence_counts: dict[str, int],
    warnings: list[str],
) -> AnswerDisciplineLogTurn | None:
    if not _is_user_log_row(row):
        return None
    user_text = _first_row_text(row, ("user_text", "text", "content", "message", "prompt", "query"))
    if not user_text:
        warnings.append(f"log_row_missing_text:{_short_hash(str(source), length=12)}:{row_index}")
        return None
    sequence_id = _first_row_text(row, ("session_id", "conversation_id", "sequence_id", "thread_id")) or "default"
    sequence_counts[sequence_id] = sequence_counts.get(sequence_id, 0) + 1
    turn_id = _first_row_text(row, ("turn_id", "id", "message_id")) or f"row-{row_index}"
    return AnswerDisciplineLogTurn(
        sequence_id=sequence_id,
        turn_id=turn_id,
        turn_index=_as_int(row.get("turn_index"), sequence_counts[sequence_id]),
        user_text=user_text,
        seed_kind=_first_row_text(row, ("seed_kind",)) or "clear_context",
        expected_retrieval_pressure=_first_row_text(row, ("expected_retrieval_pressure",)),
        expected_evidence_sufficiency=_first_row_text(row, ("expected_evidence_sufficiency",)),
        expected_answer_discipline=_first_row_text(row, ("expected_answer_discipline",)),
        source_hash=_short_hash(str(source), length=12),
    )


def _is_user_log_row(row: dict[str, Any]) -> bool:
    role = _first_row_text(row, ("role", "sender", "from", "speaker")).strip().lower()
    if not role:
        return True
    return role in {"user", "human", "owner", "customer"}


def _first_row_text(row: dict[str, Any], keys: Sequence[str]) -> str:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _as_int(value: Any, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _apply_shadow_seed(root: Path, seed_kind: str) -> None:
    if seed_kind == "clear_context":
        for rel in (
            "memory/context/recent_context.md",
            "memory/context/interaction_journal_state.md",
            "memory/context/continuity_handoff_state.md",
            "memory/context/memory_braid_state.md",
        ):
            try:
                (root / rel).unlink()
            except OSError:
                pass
        return
    _seed_minimal_root(root, AnswerDisciplineTrialCase("shadow", "shadow_replay", "", seed_kind))


def _shadow_sequence_dir_name(sequence_id: str) -> str:
    return "seq-" + _short_hash(sequence_id, length=10)


def _shadow_turns_for_pack(pack: str) -> tuple[AnswerDisciplineShadowTurn, ...]:
    key = _clean_token(pack or "core")
    return SHADOW_TURN_PACKS.get(key, DEFAULT_SHADOW_TURNS)


def _ensure_shadow_context_dirs(root: Path) -> None:
    for rel in ("memory/context", "memory/self", "memory/people", "memory/relationships", "runtime"):
        (root / rel).mkdir(parents=True, exist_ok=True)


def _case_result(case: AnswerDisciplineTrialCase, context: str) -> dict[str, Any]:
    fields = _extract_context_fields(context)
    result = {
        "case_id": case.case_id,
        "case_type": case.case_type,
        "user_text_hash": _short_hash(case.user_text, length=16),
        "context_hash": _short_hash(context, length=16),
        "retrieval_pressure": fields.get("retrieval_pressure", ""),
        "evidence_sufficiency": fields.get("evidence_sufficiency", ""),
        "answer_discipline": fields.get("answer_discipline", ""),
        "current_scene": fields.get("current_scene", ""),
        "discipline_visible_in_context": bool(fields.get("answer_discipline")),
        "internal_label_leak_risk": "context_only_not_owner_visible",
        "context_constraints": _constraint_lines(context),
        "notes": ["dry_run_only", "no_llm_call", "no_raw_user_text"],
    }
    result["visible_reply_constraints"] = answer_discipline_visible_constraints(result).to_report()
    return result


def _shadow_turn_result(turn: AnswerDisciplineShadowTurn, context: str) -> dict[str, Any]:
    fields = _extract_context_fields(context)
    actual = {
        "retrieval_pressure": fields.get("retrieval_pressure", ""),
        "evidence_sufficiency": fields.get("evidence_sufficiency", ""),
        "answer_discipline": fields.get("answer_discipline", ""),
        "current_scene": fields.get("current_scene", ""),
    }
    expected = {
        "retrieval_pressure": turn.expected_retrieval_pressure,
        "evidence_sufficiency": turn.expected_evidence_sufficiency,
        "answer_discipline": turn.expected_answer_discipline,
    }
    mismatches = [
        key
        for key, expected_value in expected.items()
        if str(actual.get(key) or "") != str(expected_value)
    ]
    result = {
        "sequence_id": turn.sequence_id,
        "turn_id": turn.turn_id,
        "turn_index": turn.turn_index,
        "user_text_hash": _short_hash(turn.user_text, length=16),
        "context_hash": _short_hash(context, length=16),
        "seed_kind": turn.seed_kind,
        "current_scene": actual["current_scene"],
        "retrieval_pressure": actual["retrieval_pressure"],
        "evidence_sufficiency": actual["evidence_sufficiency"],
        "answer_discipline": actual["answer_discipline"],
        "expected_retrieval_pressure": expected["retrieval_pressure"],
        "expected_evidence_sufficiency": expected["evidence_sufficiency"],
        "expected_answer_discipline": expected["answer_discipline"],
        "matched_expectation": not mismatches,
        "mismatches": mismatches,
        "context_constraints": _constraint_lines(context),
        "notes": ["shadow_replay", "no_llm_call", "no_raw_user_text", "isolated_workspace"],
    }
    result["visible_reply_constraints"] = answer_discipline_visible_constraints(result).to_report()
    result["visible_reply_guard"] = _shadow_visible_reply_guard_report(result)
    return result


def _log_shadow_turn_result(turn: AnswerDisciplineLogTurn, context: str) -> dict[str, Any]:
    fields = _extract_context_fields(context)
    actual = {
        "retrieval_pressure": fields.get("retrieval_pressure", ""),
        "evidence_sufficiency": fields.get("evidence_sufficiency", ""),
        "answer_discipline": fields.get("answer_discipline", ""),
        "current_scene": fields.get("current_scene", ""),
    }
    expected = {
        "retrieval_pressure": turn.expected_retrieval_pressure,
        "evidence_sufficiency": turn.expected_evidence_sufficiency,
        "answer_discipline": turn.expected_answer_discipline,
    }
    mismatches = [
        key
        for key, expected_value in expected.items()
        if expected_value and str(actual.get(key) or "") != str(expected_value)
    ]
    result = {
        "sequence_hash": _short_hash(turn.sequence_id, length=16),
        "turn_hash": _short_hash(turn.turn_id, length=16),
        "turn_index": turn.turn_index,
        "source_hash": turn.source_hash,
        "user_text_hash": _short_hash(turn.user_text, length=16),
        "context_hash": _short_hash(context, length=16),
        "seed_kind": turn.seed_kind,
        "current_scene": actual["current_scene"],
        "retrieval_pressure": actual["retrieval_pressure"],
        "evidence_sufficiency": actual["evidence_sufficiency"],
        "answer_discipline": actual["answer_discipline"],
        "expected_retrieval_pressure": expected["retrieval_pressure"],
        "expected_evidence_sufficiency": expected["evidence_sufficiency"],
        "expected_answer_discipline": expected["answer_discipline"],
        "matched_expectation": not mismatches,
        "mismatches": mismatches,
        "context_constraints": _constraint_lines(context),
        "notes": ["log_shadow_replay", "no_llm_call", "no_raw_user_text", "isolated_workspace"],
    }
    result["visible_reply_constraints"] = answer_discipline_visible_constraints(result).to_report()
    result["visible_reply_guard"] = _shadow_visible_reply_guard_report(result)
    return result


def _extract_context_fields(context: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    wanted = {"current_scene", "retrieval_pressure", "evidence_sufficiency", "answer_discipline"}
    for line in context.splitlines():
        clean = line.strip()
        if clean.startswith("- "):
            clean = clean[2:].strip()
        if ":" not in clean:
            continue
        key, value = clean.split(":", 1)
        key = key.strip()
        if key in wanted and key not in fields:
            fields[key] = value.strip()
    return fields


def _shadow_visible_reply_guard_report(result: dict[str, Any]) -> dict[str, Any]:
    reply = synthetic_visible_reply_for_constraints(result)
    report = _visible_reply_guard_report(reply, result)
    report["probe"] = "synthetic_shadow_visible_reply"
    report["reply_hash"] = _short_hash(reply, length=16)
    return report


def _visible_reply_guard_report(reply: str, result: dict[str, Any]) -> dict[str, Any]:
    guard = evaluate_visible_reply_for_answer_discipline(reply, result)
    return guard.to_report()


def _constraint_lines(context: str) -> list[str]:
    lines: list[str] = []
    for line in context.splitlines():
        clean = line.strip()
        if any(token in clean for token in ("evidence_sufficiency:", "answer_discipline:", "retrieval_pressure:")):
            lines.append(clean)
        elif "do not invent missing history" in clean or "answer with uncertainty" in clean:
            lines.append(clean)
    return lines[:12]


def _build_report(*, run_id: str, observed_at: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    completed = sum(1 for item in results if item.get("discipline_visible_in_context"))
    high_no_evidence_guarded = sum(
        1
        for item in results
        if item.get("retrieval_pressure") == "high"
        and item.get("evidence_sufficiency") == "none"
        and item.get("answer_discipline") == "answer_current_only_acknowledge_missing_evidence"
    )
    high_weak_guarded = sum(
        1
        for item in results
        if item.get("retrieval_pressure") == "high"
        and item.get("evidence_sufficiency") == "weak"
        and item.get("answer_discipline") == "answer_with_uncertainty_use_only_supported_recall"
    )
    return {
        "run_id": run_id,
        "updated_at": observed_at,
        "case_count": len(results),
        "discipline_visible_count": completed,
        "high_no_evidence_guarded_count": high_no_evidence_guarded,
        "high_weak_evidence_guarded_count": high_weak_guarded,
        "cases": results,
        "boundaries": {
            "llm_calls": "blocked",
            "raw_user_text_in_report": "blocked",
            "long_term_memory_writes": "blocked",
            "initiative_delivery": "blocked",
        },
    }


def _build_shadow_replay_report(*, run_id: str, observed_at: str, results: list[dict[str, Any]], pack: str = "core") -> dict[str, Any]:
    gate = _shadow_replay_gate(results)
    return {
        "run_id": run_id,
        "updated_at": observed_at,
        "pack": _clean_token(pack or "core"),
        "sequence_count": len({item.get("sequence_id") for item in results}),
        "turn_count": len(results),
        "cases": results,
        "shadow_gate": gate,
        "boundaries": {
            "llm_calls": "blocked",
            "raw_user_text_in_report": "blocked",
            "long_term_memory_writes": "blocked",
            "initiative_delivery": "blocked",
        },
    }


def _build_log_shadow_replay_report(
    *,
    run_id: str,
    observed_at: str,
    results: list[dict[str, Any]],
    warnings: Sequence[str],
    source_count: int,
    live_requested: bool = False,
    live_configured: bool = False,
    live_error_count: int = 0,
) -> dict[str, Any]:
    gate = _log_shadow_replay_gate(
        results,
        warnings=warnings,
        live_requested=live_requested,
        live_configured=live_configured,
        live_error_count=live_error_count,
    )
    return {
        "run_id": run_id,
        "updated_at": observed_at,
        "source_count": source_count,
        "sequence_count": len({item.get("sequence_hash") for item in results}),
        "turn_count": len(results),
        "warning_count": len(warnings),
        "warnings": list(warnings[:20]),
        "live_llm": {
            "requested": live_requested,
            "configured": live_configured,
            "llm_calls": "attempted_optional_live" if live_requested and live_configured else ("skipped_missing_credentials" if live_requested else "blocked"),
            "error_count": live_error_count,
        },
        "cases": results,
        "log_shadow_gate": gate,
        "boundaries": {
            "llm_calls": "attempted_optional_live" if live_requested and live_configured else ("skipped_missing_credentials" if live_requested else "blocked"),
            "raw_user_text_in_report": "blocked",
            "raw_prompt_in_report": "blocked",
            "raw_reply_in_report": "blocked",
            "long_term_memory_writes": "blocked",
            "initiative_delivery": "blocked",
        },
    }


def _log_shadow_replay_gate(
    results: Sequence[dict[str, Any]],
    *,
    warnings: Sequence[str],
    live_requested: bool = False,
    live_configured: bool = False,
    live_error_count: int = 0,
) -> dict[str, Any]:
    mismatch_count = sum(1 for item in results if not item.get("matched_expectation"))
    high_no_evidence = [
        item
        for item in results
        if item.get("retrieval_pressure") == "high" and item.get("evidence_sufficiency") == "none"
    ]
    high_no_evidence_unguarded = sum(
        1
        for item in high_no_evidence
        if item.get("answer_discipline") != "answer_current_only_acknowledge_missing_evidence"
    )
    sticky_pressure_failures = _log_sticky_pressure_failure_count(results)
    visible_guard_failure_count = _visible_guard_failure_count(results)
    checks = [
        _gate_check("turns_loaded", len(results) > 0),
        _gate_check("optional_expectations_match", mismatch_count == 0),
        _gate_check("high_no_evidence_turns_guarded", high_no_evidence_unguarded == 0),
        _gate_check("ordinary_turns_do_not_inherit_callback_pressure", sticky_pressure_failures == 0),
        _gate_check("visible_reply_shadow_guard_passes", visible_guard_failure_count == 0),
    ]
    live_counts = _log_live_counts(results, live_error_count=live_error_count)
    if live_requested:
        checks.extend(
            [
                _gate_check("live_llm_configured", live_configured),
                _gate_check("live_log_calls_without_errors", live_counts["live_error_count"] == 0),
                _gate_check("live_log_no_blank_replies", live_counts["blank_reply_count"] == 0),
                _gate_check("live_log_no_internal_label_leaks", live_counts["internal_label_leak_count"] == 0),
                _gate_check(
                    "live_log_no_overconfident_high_no_evidence_replies",
                    live_counts["high_no_evidence_overconfident_count"] == 0,
                ),
                _gate_check("live_log_no_template_like_casual_replies", live_counts["template_like_casual_reply_count"] == 0),
            ]
        )
    passed = all(bool(item["passed"]) for item in checks)
    return {
        "status": "passed" if passed else "failed",
        "passed": passed,
        "counts": {
            "turn_count": len(results),
            "warning_count": len(warnings),
            "mismatch_count": mismatch_count,
            "high_no_evidence_count": len(high_no_evidence),
            "high_no_evidence_unguarded_count": high_no_evidence_unguarded,
            "sticky_pressure_failure_count": sticky_pressure_failures,
            "visible_guard_failure_count": visible_guard_failure_count,
            **live_counts,
        },
        "checks": checks,
    }


def _log_live_counts(results: Sequence[dict[str, Any]], *, live_error_count: int) -> dict[str, int]:
    ok_cases = [item for item in results if item.get("llm_status") == "ok"]
    high_no_evidence = [
        item
        for item in ok_cases
        if item.get("retrieval_pressure") == "high" and item.get("evidence_sufficiency") == "none"
    ]
    return {
        "live_ok_count": len(ok_cases),
        "live_error_count": live_error_count,
        "blank_reply_count": sum(1 for item in ok_cases if _flag(item, "blank_reply")),
        "internal_label_leak_count": sum(1 for item in ok_cases if _flag(item, "leaked_internal_label")),
        "high_no_evidence_overconfident_count": sum(
            1 for item in high_no_evidence if _flag(item, "overconfident_without_evidence")
        ),
        "high_no_evidence_uncertainty_count": sum(
            1 for item in high_no_evidence if _flag(item, "acknowledged_uncertainty")
        ),
        "template_like_casual_reply_count": sum(
            1 for item in ok_cases if _flag(item, "template_like_casual_reply")
        ),
    }


def _log_sticky_pressure_failure_count(results: Sequence[dict[str, Any]]) -> int:
    previous_by_sequence: dict[str, dict[str, Any]] = {}
    failures = 0
    for item in sorted(results, key=lambda entry: (str(entry.get("sequence_hash") or ""), int(entry.get("turn_index") or 0))):
        sequence_hash = str(item.get("sequence_hash") or "")
        previous = previous_by_sequence.get(sequence_hash)
        if (
            previous
            and previous.get("retrieval_pressure") == "high"
            and item.get("expected_retrieval_pressure") == "none"
            and item.get("retrieval_pressure") != "none"
        ):
            failures += 1
        previous_by_sequence[sequence_hash] = item
    return failures


def _visible_guard_failure_count(results: Sequence[dict[str, Any]]) -> int:
    failures = 0
    for item in results:
        guard = item.get("visible_reply_guard")
        if isinstance(guard, dict) and guard.get("passed") is False:
            failures += 1
    return failures


def _shadow_replay_gate(results: Sequence[dict[str, Any]]) -> dict[str, Any]:
    mismatch_count = sum(1 for item in results if not item.get("matched_expectation"))
    high_no_evidence_guarded = sum(
        1
        for item in results
        if item.get("retrieval_pressure") == "high"
        and item.get("evidence_sufficiency") == "none"
        and item.get("answer_discipline") == "answer_current_only_acknowledge_missing_evidence"
    )
    casual_after_callback = [
        item
        for item in results
        if str(item.get("turn_id") or "").startswith("casual_after_")
    ]
    sticky_pressure_failures = sum(1 for item in casual_after_callback if item.get("retrieval_pressure") != "none")
    visible_guard_failure_count = _visible_guard_failure_count(results)
    checks = [
        _gate_check("all_turn_expectations_match", mismatch_count == 0),
        _gate_check("unsupported_callback_guarded", high_no_evidence_guarded >= 1),
        _gate_check("casual_turns_do_not_inherit_callback_pressure", sticky_pressure_failures == 0),
        _gate_check("visible_reply_shadow_guard_passes", visible_guard_failure_count == 0),
    ]
    passed = all(bool(item["passed"]) for item in checks)
    return {
        "status": "passed" if passed else "failed",
        "passed": passed,
        "counts": {
            "mismatch_count": mismatch_count,
            "high_no_evidence_guarded_count": high_no_evidence_guarded,
            "casual_after_callback_count": len(casual_after_callback),
            "sticky_pressure_failure_count": sticky_pressure_failures,
            "visible_guard_failure_count": visible_guard_failure_count,
        },
        "checks": checks,
    }


def _run_live_llm_trial(
    root: Path,
    *,
    prepared: Sequence[tuple[AnswerDisciplineTrialCase, str, dict[str, Any]]],
    caller: LLMCaller | None,
    thresholds: CalibrationThresholds,
) -> dict[str, Any]:
    config = _discover_live_llm_config(root)
    selected = [(case, context, result) for case, context, result in prepared if case.case_id in LIVE_CASE_IDS]
    if config is None:
        return {
            "enabled": True,
            "status": "skipped_missing_credentials",
            "llm_calls": "skipped_missing_credentials",
            "case_count": len(selected),
            "cases": [
                _live_skipped_case(case, context, result, reason="missing_llm_credentials")
                for case, context, result in selected
            ],
            "calibration_gate": _calibration_gate([], error_count=0, skipped=True, thresholds=thresholds),
            "boundaries": {
                "raw_prompt_in_report": "blocked",
                "raw_reply_in_report": "blocked",
                "long_term_memory_writes": "blocked",
                "initiative_delivery": "blocked",
            },
        }
    active_caller = caller or _call_openai_compatible_llm
    cases: list[dict[str, Any]] = []
    failed = 0
    for case, context, result in selected:
        messages = _live_trial_messages(case, context, result)
        base = _live_case_base(case, context, result)
        base["prompt_hash"] = _short_hash(_messages_hash_payload(messages), length=16)
        try:
            reply = active_caller(messages, config)
        except Exception as exc:  # pragma: no cover - exact network failures are environment-specific
            failed += 1
            cases.append(
                {
                    **base,
                    "llm_status": "error",
                    "error_type": type(exc).__name__,
                    "error_code": getattr(exc, "code", "llm_call_failed"),
                    "reply_hash": "",
                    "reply_chars": 0,
                    "flags": _empty_live_flags(),
                    "notes": ["live_llm_call_failed", "no_raw_prompt_or_reply"],
                }
            )
            continue
        flags = _judge_live_reply(reply, result)
        cases.append(
            {
                **base,
                "llm_status": "ok",
                "reply_hash": _short_hash(reply, length=16),
                "reply_chars": len(reply.strip()),
                "flags": flags,
                "visible_reply_guard": _visible_reply_guard_report(reply, result),
                "notes": ["live_llm_call", "no_raw_prompt_or_reply", "synthetic_case_only"],
            }
        )
    return {
        "enabled": True,
        "status": "completed" if failed == 0 else "completed_with_errors",
        "llm_calls": "attempted_optional_live",
        "case_count": len(cases),
        "error_count": failed,
        "model": config.model,
        "base_url_configured": bool(config.base_url),
        "api_key_env": config.api_key_env,
        "cases": cases,
        "calibration_gate": _calibration_gate(cases, error_count=failed, skipped=False, thresholds=thresholds),
        "boundaries": {
            "raw_prompt_in_report": "blocked",
            "raw_reply_in_report": "blocked",
            "long_term_memory_writes": "blocked",
            "initiative_delivery": "blocked",
        },
    }


def _calibration_gate(
    cases: Sequence[dict[str, Any]],
    *,
    error_count: int,
    skipped: bool,
    thresholds: CalibrationThresholds,
) -> dict[str, Any]:
    if skipped:
        return {
            "status": "skipped_missing_credentials",
            "passed": False,
            "reason": "live_llm_not_run",
            "thresholds": asdict(thresholds),
            "counts": {
                "ok_case_count": 0,
                "error_count": error_count,
                "blank_reply_count": 0,
                "internal_label_leak_count": 0,
                "high_no_evidence_case_count": 0,
                "high_no_evidence_uncertainty_count": 0,
                "high_no_evidence_overconfident_count": 0,
                "template_like_casual_reply_count": 0,
            },
            "checks": [],
        }
    counts = _calibration_counts(cases, error_count=error_count)
    checks = [
        _gate_check("no_live_call_errors", counts["error_count"] <= thresholds.max_error_count),
        _gate_check("no_blank_replies", counts["blank_reply_count"] <= thresholds.max_blank_reply_count),
        _gate_check(
            "no_internal_label_leaks",
            counts["internal_label_leak_count"] <= thresholds.max_internal_label_leak_count,
        ),
        _gate_check(
            "no_overconfident_high_no_evidence_replies",
            counts["high_no_evidence_overconfident_count"] <= thresholds.max_high_no_evidence_overconfident_count,
        ),
        _gate_check(
            "no_template_like_casual_replies",
            counts["template_like_casual_reply_count"] <= thresholds.max_template_like_casual_reply_count,
        ),
    ]
    if thresholds.require_high_no_evidence_uncertainty:
        checks.append(
            _gate_check(
                "high_no_evidence_acknowledges_uncertainty",
                counts["high_no_evidence_case_count"] > 0
                and counts["high_no_evidence_uncertainty_count"] == counts["high_no_evidence_case_count"],
            )
        )
    passed = all(bool(item["passed"]) for item in checks)
    return {
        "status": "passed" if passed else "failed",
        "passed": passed,
        "thresholds": asdict(thresholds),
        "counts": counts,
        "checks": checks,
    }


def _calibration_counts(cases: Sequence[dict[str, Any]], *, error_count: int) -> dict[str, int]:
    ok_cases = [case for case in cases if case.get("llm_status") == "ok"]
    high_no_evidence = [
        case
        for case in ok_cases
        if case.get("retrieval_pressure") == "high" and case.get("evidence_sufficiency") == "none"
    ]
    return {
        "ok_case_count": len(ok_cases),
        "error_count": error_count,
        "blank_reply_count": sum(1 for case in ok_cases if _flag(case, "blank_reply")),
        "internal_label_leak_count": sum(1 for case in ok_cases if _flag(case, "leaked_internal_label")),
        "high_no_evidence_case_count": len(high_no_evidence),
        "high_no_evidence_uncertainty_count": sum(
            1 for case in high_no_evidence if _flag(case, "acknowledged_uncertainty")
        ),
        "high_no_evidence_overconfident_count": sum(
            1 for case in high_no_evidence if _flag(case, "overconfident_without_evidence")
        ),
        "template_like_casual_reply_count": sum(
            1 for case in ok_cases if _flag(case, "template_like_casual_reply")
        ),
    }


def _flag(case: dict[str, Any], name: str) -> bool:
    flags = case.get("flags")
    return bool(flags.get(name)) if isinstance(flags, dict) else False


def _gate_check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def _live_skipped_case(
    case: AnswerDisciplineTrialCase,
    context: str,
    result: dict[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    return {
        **_live_case_base(case, context, result),
        "llm_status": "skipped",
        "skip_reason": reason,
        "reply_hash": "",
        "reply_chars": 0,
        "flags": _empty_live_flags(),
        "notes": ["no_llm_call", "no_raw_prompt_or_reply"],
    }


def _live_case_base(case: AnswerDisciplineTrialCase, context: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "case_type": case.case_type,
        "user_text_hash": result.get("user_text_hash", _short_hash(case.user_text, length=16)),
        "context_hash": result.get("context_hash", _short_hash(context, length=16)),
        "retrieval_pressure": result.get("retrieval_pressure", ""),
        "evidence_sufficiency": result.get("evidence_sufficiency", ""),
        "answer_discipline": result.get("answer_discipline", ""),
        "visible_reply_constraints": answer_discipline_visible_constraints(result).to_report(),
    }


def _live_trial_messages(
    case: AnswerDisciplineTrialCase,
    context: str,
    result: dict[str, Any],
) -> list[dict[str, str]]:
    system = "\n".join(
        [
            "You are testing XinYu's answer discipline in a private synthetic trial.",
            "Return only a short outward reply to the owner.",
            "Use the hidden context only when it is enough for the current message.",
            "If evidence is missing or weak, acknowledge uncertainty naturally and do not invent prior history.",
            "Do not reveal internal field names, source paths, hashes, gates, or trial labels.",
            "",
            "Hidden context:",
            context[:5000],
            "",
            "Final mandatory discipline for this turn:",
            _discipline_instruction(result),
        ]
    )
    user = "\n".join(
        [
            "Synthetic owner message:",
            case.user_text,
        ]
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _discipline_instruction(result: dict[str, Any]) -> str:
    pressure = str(result.get("retrieval_pressure") or "")
    evidence = str(result.get("evidence_sufficiency") or "")
    if pressure == "high" and evidence == "none":
        return (
            "Discipline for this turn: the message depends on prior context, but no usable prior evidence is available. "
            "Your first sentence must say that you cannot verify the previous dialogue. "
            "If replying in Chinese, the first sentence must include '我无法确认前面的完整对话'. "
            "Then answer only the current message. "
            "Do not state any specific prior event as fact."
        )
    if pressure == "high" and evidence == "weak":
        return (
            "Discipline for this turn: the message depends on prior context, but evidence is weak. "
            "Use uncertainty language and mention only what the available context supports."
        )
    if pressure == "high":
        return (
            "Discipline for this turn: the message depends on prior context and usable evidence is available. "
            "Use that evidence compactly, without overclaiming or exposing internal machinery."
        )
    if pressure == "medium" and evidence in {"none", "weak"}:
        return (
            "Discipline for this turn: resolve the reference carefully. "
            "If the context is not enough, say so briefly instead of filling gaps."
        )
    return "Discipline for this turn: answer the current message normally, with no memory machinery visible."


def _discover_live_llm_config(root: Path) -> LiveLLMConfig | None:
    _load_trial_env_file(root / "xinyu.local.env")
    api_key_env = os.environ.get("XINYU_API_KEY_ENV", "XINYU_API_KEY").strip() or "XINYU_API_KEY"
    api_key = os.environ.get(api_key_env, "").strip()
    base_url = os.environ.get("XINYU_BASE_URL", "").strip()
    if not api_key or not base_url:
        return None
    return LiveLLMConfig(
        model=os.environ.get("XINYU_LLM_MODEL", "").strip() or "mimo-v2.5-pro",
        base_url=base_url,
        api_key_env=api_key_env,
        api_key=api_key,
        temperature=_float_env("XINYU_ANSWER_DISCIPLINE_LIVE_TEMPERATURE", 0.2),
        max_tokens=_int_env("XINYU_ANSWER_DISCIPLINE_LIVE_MAX_TOKENS", 360),
        timeout_seconds=_float_env("XINYU_ANSWER_DISCIPLINE_LIVE_TIMEOUT_SECONDS", 45.0),
    )


def _load_trial_env_file(path: Path) -> None:
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or not key.replace("_", "A").isalnum() or key in os.environ:
            continue
        os.environ[key] = value.strip().strip('"').strip("'")


def _call_openai_compatible_llm(messages: list[dict[str, str]], config: LiveLLMConfig) -> str:
    payload = {
        "model": config.model,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "messages": messages,
    }
    request = urllib.request.Request(
        config.base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "Authorization": f"Bearer {config.api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise LiveLLMTrialError(f"llm_http_{exc.code}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise LiveLLMTrialError("llm_request_failed") from exc
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise LiveLLMTrialError("llm_invalid_json") from exc
    reply = _extract_openai_text(data)
    if not reply:
        raise LiveLLMTrialError("llm_empty_reply")
    return reply


def _extract_openai_text(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                return str(message.get("content") or "").strip()
            return str(first.get("text") or "").strip()
    return str(data.get("text") or data.get("reply") or "").strip()


def _judge_live_reply(reply: str, result: dict[str, Any]) -> dict[str, bool]:
    return evaluate_visible_reply_for_answer_discipline(reply, result).flags
    text = reply.strip()
    lowered = text.lower()
    uncertainty = _has_any(
        lowered,
        (
            "不确定",
            "不能确定",
            "无法确认",
            "不能确认",
            "没有足够",
            "不足以",
            "缺少",
            "不知道",
            "记不清",
            "不掌握",
            "not sure",
            "cannot tell",
            "cannot verify",
            "can't tell",
            "do not know",
            "don't know",
            "not enough",
            "missing",
            "uncertain",
        ),
    )
    leaked_internal_label = _has_any(
        lowered,
        (
            "retrieval_pressure",
            "evidence_sufficiency",
            "answer_discipline",
            "current_scene",
            "contextual recall",
            "contextual_recall",
            "trial label",
            "hidden context",
        ),
    )
    high_none = (
        result.get("retrieval_pressure") == "high"
        and result.get("evidence_sufficiency") == "none"
    )
    overconfident_without_evidence = bool(high_none and text and not uncertainty)
    return {
        "blank_reply": not bool(text),
        "leaked_internal_label": leaked_internal_label,
        "acknowledged_uncertainty": uncertainty,
        "overconfident_without_evidence": overconfident_without_evidence,
    }


def _empty_live_flags() -> dict[str, bool]:
    return {
        "blank_reply": False,
        "leaked_internal_label": False,
        "leaked_source_reference": False,
        "leaked_gate_or_hash": False,
        "acknowledged_uncertainty": False,
        "missing_required_uncertainty": False,
        "unsupported_history_claim": False,
        "overconfident_without_evidence": False,
        "template_like_casual_reply": False,
    }


def _has_any(text: str, needles: Sequence[str]) -> bool:
    return any(needle in text for needle in needles)


def _messages_hash_payload(messages: Sequence[dict[str, str]]) -> str:
    return json.dumps(messages, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    tmp.write_text(json.dumps(_clean_json_value(data), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _clean_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _clean_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean_json_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _short_hash(value: Any, *, length: int = 10) -> str:
    return hashlib.sha256(str(value).encode("utf-8", errors="replace")).hexdigest()[:length]


def _clean_token(value: str) -> str:
    text = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "-" for ch in value.strip())
    while "--" in text:
        text = text.replace("--", "-")
    return text.strip("-")[:80] or "trial"


def _timestamp_or_empty(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return ""
    return parsed.astimezone().isoformat(timespec="seconds")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run answer discipline trial cases.")
    parser.add_argument("--root", default=".", help="XinYu app root. Defaults to current directory.")
    parser.add_argument("--run-id", default="", help="Optional run id for isolated runtime workspace.")
    parser.add_argument(
        "--live-llm",
        action="store_true",
        help="Run the optional 3-case live LLM trial if XINYU_API_KEY and XINYU_BASE_URL are configured.",
    )
    parser.add_argument(
        "--shadow-replay",
        action="store_true",
        help="Run the synthetic multi-turn shadow replay gate without LLM calls.",
    )
    parser.add_argument(
        "--pack",
        default="core",
        help="Synthetic shadow replay pack: core, callback, casual_reset, or unsupported_callback.",
    )
    parser.add_argument(
        "--log-shadow-replay",
        action="store_true",
        help="Run safe shadow replay over local JSON/JSONL log sources without LLM calls.",
    )
    parser.add_argument(
        "--log-live-llm",
        action="store_true",
        help="When used with --log-shadow-replay, run optional live LLM shadow scoring without outward delivery.",
    )
    parser.add_argument(
        "--log-source",
        action="append",
        default=[],
        help="Local JSON/JSONL log source for --log-shadow-replay. May be repeated.",
    )
    parser.add_argument("--log-limit", type=int, default=100, help="Maximum user turns for --log-shadow-replay.")
    parser.add_argument("--dashboard", action="store_true", help="Build the unified calibration dashboard report.")
    parser.add_argument(
        "--safe-suite",
        action="store_true",
        help="Run the no-network calibration suite: dry trial, synthetic shadow, fixture log shadow, and dashboard.",
    )
    parser.add_argument(
        "--strict-gate",
        action="store_true",
        help="Exit non-zero when any requested calibration gate is skipped or failed.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    root = Path(args.root)
    log_sources = tuple(args.log_source)
    if args.safe_suite and not log_sources:
        fixture = root / DEFAULT_LOG_REPLAY_FIXTURE_REL
        if fixture.exists():
            log_sources = (str(fixture),)
    shadow_replay = bool(args.shadow_replay or args.safe_suite)
    log_shadow_replay = bool(args.log_shadow_replay or (args.safe_suite and log_sources))
    dashboard_requested = bool(args.dashboard or args.safe_suite)
    report = run_answer_discipline_trial(
        root,
        run_id=args.run_id or None,
        live_llm=args.live_llm,
        shadow_replay=shadow_replay,
        shadow_pack=args.pack,
        log_shadow_replay=log_shadow_replay,
        log_sources=log_sources,
        log_limit=args.log_limit,
        log_live_llm=args.log_live_llm,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    gates: list[dict[str, Any]] = []
    if args.live_llm and isinstance(report.get("live_llm_trial"), dict):
        gate = report["live_llm_trial"].get("calibration_gate")
        if isinstance(gate, dict):
            gates.append(gate)
    if shadow_replay and isinstance(report.get("shadow_replay"), dict):
        gate = report["shadow_replay"].get("shadow_gate")
        if isinstance(gate, dict):
            gates.append(gate)
    if log_shadow_replay and isinstance(report.get("log_shadow_replay"), dict):
        gate = report["log_shadow_replay"].get("log_shadow_gate")
        if isinstance(gate, dict):
            gates.append(gate)
    if dashboard_requested:
        dashboard = build_answer_discipline_calibration_dashboard(root)
        print(json.dumps({"dashboard": dashboard}, ensure_ascii=False, indent=2, sort_keys=True))
        gates.append({"passed": dashboard.get("passed"), "status": dashboard.get("status")})
    if args.strict_gate and (not gates or any(not gate.get("passed") for gate in gates)):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
