from __future__ import annotations

import argparse
import hashlib
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_dialogue_archive import (
    GROUP_SCOPE,
    OWNER_PRIVATE_SCOPE,
    list_memory_candidates,
    resolve_dialogue_scope,
    store_memory_candidate,
    store_temporal_trace_from_candidate,
)
from xinyu_text_variants import readable_markers


VOICE_CORRECTION_MARKERS = readable_markers(
    "不像你",
    "太客服",
    "太 GPT",
    "太GPT",
    "GPT味",
    "AI味",
    "别这样说",
    "不要解释那么多",
    "没什么变化",
    "没变化",
    "助手腔",
    "默认助手",
    "机械",
    "模板",
)

OWNER_PREFERENCE_MARKERS = readable_markers(
    "以后",
    "记住",
    "我喜欢",
    "我不喜欢",
    "我希望",
    "我更想",
    "不要",
    "别",
    "优先",
    "默认",
)

RELATIONSHIP_MARKERS = readable_markers(
    "靠近",
    "失望",
    "难过",
    "受伤",
    "在乎",
    "信任",
    "疏远",
    "回来",
    "白做",
    "敷衍",
    "关系",
    "生气",
)

PROJECT_MARKERS = readable_markers(
    "Codex",
    "OCR",
    "runtime",
    "bridge",
    "QQ gateway",
    "NapCat",
    "smoke",
    "测试",
    "实现",
    "修复",
    "通过",
    "失败",
    "上下文",
    "长期记忆",
    "SQLite",
    "FTS",
)

CODEX_MARKERS = readable_markers("Codex", "codex", "辅助脑", "委托", "报告")


@dataclass(frozen=True)
class CandidateSpec:
    candidate_type: str
    target_gate: str
    target_memory_layer: str
    reason: str
    confidence_score: int
    text: str


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    if value is None:
        return default
    return bool(value)


def candidate_extraction_enabled() -> bool:
    return _as_bool(os.environ.get("XINYU_DIALOGUE_CANDIDATE_EXTRACTION_ENABLED"), default=True)


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker and marker in text for marker in markers)


def _matched(text: str, markers: tuple[str, ...], *, limit: int = 6) -> list[str]:
    return [marker for marker in markers if marker and marker in text][:limit]


def _trim(text: str, limit: int = 240) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 3)].rstrip() + "..."


def _candidate_id(candidate_type: str, text: str, source_message_ids: list[int]) -> str:
    seed = f"{candidate_type}|{','.join(str(item) for item in source_message_ids)}|{text[:260]}"
    return "memcand-" + hashlib.sha256(seed.encode("utf-8", errors="replace")).hexdigest()[:18]


def _candidate_text(user_text: str, assistant_reply: str, *, prefix: str = "") -> str:
    parts = []
    if prefix:
        parts.append(prefix)
    parts.append(f"owner_turn: {_trim(user_text, 180)}")
    if assistant_reply.strip():
        parts.append(f"visible_reply: {_trim(assistant_reply, 180)}")
    return "\n".join(parts)


def _visible_turn_kind(visible_turn: Any | None) -> str:
    return _safe_str(getattr(visible_turn, "turn_kind", "")).strip()


def build_candidate_specs(
    *,
    payload: dict[str, Any] | None,
    user_text: str,
    assistant_reply: str,
    visible_turn: Any | None = None,
) -> list[CandidateSpec]:
    scope = resolve_dialogue_scope(payload)
    owner_private = scope.scope == OWNER_PRIVATE_SCOPE
    group_scope = scope.scope == GROUP_SCOPE
    combined = f"{user_text}\n{assistant_reply}"
    specs: list[CandidateSpec] = []

    if owner_private and _contains_any(user_text, VOICE_CORRECTION_MARKERS):
        markers = ", ".join(_matched(user_text, VOICE_CORRECTION_MARKERS)) or "voice_pressure"
        specs.append(
            CandidateSpec(
                candidate_type="voice_correction",
                target_gate="voice_calibration_review",
                target_memory_layer="memory/self/voice_calibration_log.md",
                reason=f"owner-private voice/style correction markers: {markers}",
                confidence_score=72,
                text=_candidate_text(user_text, assistant_reply, prefix="voice correction candidate; stable voice rewrite blocked"),
            )
        )

    preference_hit = _contains_any(user_text, OWNER_PREFERENCE_MARKERS)
    if owner_private and preference_hit and not _contains_any(user_text, VOICE_CORRECTION_MARKERS):
        markers = ", ".join(_matched(user_text, OWNER_PREFERENCE_MARKERS)) or "owner_preference"
        specs.append(
            CandidateSpec(
                candidate_type="owner_preference",
                target_gate="owner_memory_review",
                target_memory_layer="memory/people/owner.md",
                reason=f"possible owner preference; review for repetition and stability: {markers}",
                confidence_score=58,
                text=_candidate_text(user_text, assistant_reply, prefix="owner preference candidate; temporary mood must not become stable"),
            )
        )

    if owner_private and _contains_any(combined, RELATIONSHIP_MARKERS):
        markers = ", ".join(_matched(combined, RELATIONSHIP_MARKERS)) or "relationship_signal"
        specs.append(
            CandidateSpec(
                candidate_type="relationship_signal",
                target_gate="relationship_emotion_review",
                target_memory_layer="memory/relationships/index.md",
                reason=f"owner-private relationship or emotional residue markers: {markers}",
                confidence_score=54,
                text=_candidate_text(user_text, assistant_reply, prefix="relationship signal candidate; not a fixed owner label"),
            )
        )

    project_hit = _contains_any(combined, PROJECT_MARKERS) or _visible_turn_kind(visible_turn) == "technical_work"
    if project_hit:
        markers = ", ".join(_matched(combined, PROJECT_MARKERS)) or _visible_turn_kind(visible_turn) or "project_continuity"
        layer = "memory/context/recent_context.md"
        reason = f"project/runtime continuity signal: {markers}"
        if group_scope:
            reason += "; group-scoped and not owner relationship memory"
        specs.append(
            CandidateSpec(
                candidate_type="project_fact",
                target_gate="recent_context_project_review",
                target_memory_layer=layer,
                reason=reason,
                confidence_score=62 if owner_private else 46,
                text=_candidate_text(user_text, assistant_reply, prefix="project fact candidate; keep separate from relationship memory"),
            )
        )

    if _contains_any(combined, CODEX_MARKERS):
        specs.append(
            CandidateSpec(
                candidate_type="codex_result",
                target_gate="codex_project_archive_review",
                target_memory_layer="memory/context/recent_context.md",
                reason="Codex delegation/result signal; not source-learning unless learning gates pass",
                confidence_score=64 if owner_private else 48,
                text=_candidate_text(user_text, assistant_reply, prefix="Codex result candidate; learning gate still authoritative"),
            )
        )

    return specs


def extract_memory_candidates(
    root: Path,
    payload: dict[str, Any] | None,
    *,
    user_text: str,
    assistant_reply: str,
    source_message_ids: list[int] | None = None,
    dialogue_tail: list[dict[str, str]] | None = None,
    visible_turn: Any | None = None,
    quality_flags: list[str] | dict[str, Any] | None = None,
) -> dict[str, Any]:
    del dialogue_tail, quality_flags
    if not candidate_extraction_enabled():
        return {"candidate_count": 0, "candidate_ids": [], "notes": ["candidate_extraction_disabled"]}
    specs = build_candidate_specs(
        payload=payload,
        user_text=user_text,
        assistant_reply=assistant_reply,
        visible_turn=visible_turn,
    )
    message_ids = [int(item) for item in (source_message_ids or []) if isinstance(item, int)]
    scope = resolve_dialogue_scope(payload)
    candidate_ids: list[str] = []
    inserted = 0
    traces_inserted = 0
    for spec in specs:
        candidate_id = _candidate_id(spec.candidate_type, spec.text, message_ids)
        if store_memory_candidate(
            root,
            candidate_id=candidate_id,
            candidate_type=spec.candidate_type,
            source_message_ids=message_ids,
            candidate_text=spec.text,
            confidence_score=spec.confidence_score,
            target_gate=spec.target_gate,
            target_memory_layer=spec.target_memory_layer,
            reason=spec.reason,
            review_notes="pending owner/gate review; no stable memory write performed",
            created_at=datetime.now().astimezone().isoformat(),
        ):
            inserted += 1
            candidate_ids.append(candidate_id)
            if store_temporal_trace_from_candidate(
                root,
                candidate_id=candidate_id,
                candidate_type=spec.candidate_type,
                source_message_ids=message_ids,
                candidate_text=spec.text,
                confidence_score=spec.confidence_score,
                target_gate=spec.target_gate,
                target_memory_layer=spec.target_memory_layer,
                reason=spec.reason,
                scope=scope.scope,
            ):
                traces_inserted += 1
    notes = ["memory_candidate_queued"] if inserted else ["memory_candidate_none"]
    if traces_inserted:
        notes.append("temporal_trace_queued")
    if scope.scope == GROUP_SCOPE:
        notes.append("group_scope_owner_relationship_candidates_blocked")
    return {
        "candidate_count": inserted,
        "candidate_ids": candidate_ids,
        "temporal_trace_count": traces_inserted,
        "notes": notes,
    }


def build_candidate_report(root: Path, *, status: str = "pending", limit: int = 50) -> str:
    rows = list_memory_candidates(root, status=status, limit=limit)
    generated_at = datetime.now().astimezone().isoformat()
    lines = [
        "# XinYu Memory Candidate Report",
        "",
        f"- generated_at: {generated_at}",
        f"- status: {status}",
        f"- candidates: {len(rows)}",
        "",
    ]
    if not rows:
        lines.append("- none")
        return "\n".join(lines).rstrip() + "\n"
    for row in rows:
        lines.extend(
            [
                f"## {row.get('candidate_id', 'unknown')}",
                f"- created_at: {row.get('created_at', '')}",
                f"- candidate_type: {row.get('candidate_type', '')}",
                f"- confidence_score: {row.get('confidence_score', '')}",
                f"- target_gate: {row.get('target_gate', '')}",
                f"- target_memory_layer: {row.get('target_memory_layer', '')}",
                f"- reason: {row.get('reason', '')}",
                f"- review_notes: {row.get('review_notes', '')}",
                "",
                _trim(_safe_str(row.get("candidate_text")), 500),
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect XinYu pending memory candidates.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--status", default="pending")
    parser.add_argument("--limit", type=int, default=50)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    print(build_candidate_report(args.root.resolve(), status=args.status, limit=max(1, args.limit)), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
