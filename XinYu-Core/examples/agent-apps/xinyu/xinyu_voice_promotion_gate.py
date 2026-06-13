from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from xinyu_text_variants import readable_markers
from xinyu_voice_calibration_store import read_voice_calibration_text
from xinyu_voice_calibration_store import voice_calibration_log_path
from xinyu_voice_calibration_store import voice_profile_review_state_path
from xinyu_voice_calibration_store import write_voice_calibration_text


CLUSTERS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    (
        "gpt_like_smoothness",
        readable_markers(
            "gpt",
            "GPT",
            "AI味",
            "太顺",
            "落下来",
            "接待腔",
            "模板",
        ),
        "Reduce polished assistant fallback. Prefer contextual QQ wording without fixed example lines.",
    ),
    (
        "wording_local_chinese",
        readable_markers(
            "用词",
            "中文互联网",
            "端着",
            "写作文",
        ),
        "Reduce translated/report wording. Let words come from owner-private Chinese chat instead of product analysis.",
    ),
    (
        "not_human_or_template",
        readable_markers(
            "不像人",
            "不自然",
            "机械",
            "模板",
        ),
        "When pressured, use an imperfect small line instead of a complete self-explanation.",
    ),
    (
        "relationship_pressure_not_product",
        readable_markers(
            "白做",
            "红温",
            "敷衍",
            "反馈",
        ),
        "Treat owner correction as relationship pressure, not product feedback or support handling.",
    ),
)

AFFECTED_SMOKES = (
    "tests/smoke/voice/voice_learning_smoke.py",
    "tests/smoke/voice/chinese_voice_guard_smoke.py",
    "tests/smoke/voice/integration/real_conversation_quality_smoke.py",
)


def read_text(path: Path) -> str:
    return read_voice_calibration_text(path)


def write_text(path: Path, text: str) -> None:
    write_voice_calibration_text(path, text)


def _timestamp_or_now_iso(value: object) -> str:
    parsed = _parse_iso(value)
    if parsed is None:
        return datetime.now().astimezone().isoformat()
    return parsed.astimezone().isoformat()


def _parse_iso(value: object) -> datetime | None:
    text = "" if value is None else str(value).strip()
    if not text or text == "none":
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def extract_value(text: str, field: str, default: str = "unknown") -> str:
    match = re.search(rf"(?m)^- {re.escape(field)}:\s*(.+)$", text)
    return match.group(1).strip() if match else default


def _one_line(text: str, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


@dataclass(frozen=True)
class VoiceEntry:
    entry_id: str
    owner_correction: str
    visible_reply: str
    markers: str

    @property
    def combined(self) -> str:
        return f"{self.owner_correction}\n{self.visible_reply}\n{self.markers}"


@dataclass(frozen=True)
class VoicePromotionCandidate:
    candidate_id: str
    cluster: str
    evidence: tuple[VoiceEntry, ...]
    proposed_pressure: str


def parse_voice_entries(log_text: str) -> list[VoiceEntry]:
    entries: list[VoiceEntry] = []
    matches = list(re.finditer(r"(?m)^## (voice-[0-9]+)\s*$", log_text))
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(log_text)
        block = log_text[start:end]
        entries.append(
            VoiceEntry(
                entry_id=match.group(1),
                owner_correction=extract_value(block, "owner_correction", "unknown"),
                visible_reply=extract_value(block, "latest_visible_reply", "unknown"),
                markers=extract_value(block, "correction_markers", "unknown"),
            )
        )
    return entries


def build_candidates(entries: list[VoiceEntry], *, min_evidence: int = 2) -> list[VoicePromotionCandidate]:
    candidates: list[VoicePromotionCandidate] = []
    for cluster, markers, proposed_pressure in CLUSTERS:
        evidence = [
            entry
            for entry in entries
            if any(marker in entry.combined for marker in markers)
        ]
        if len(evidence) >= min_evidence:
            candidates.append(
                VoicePromotionCandidate(
                    candidate_id=f"voice-profile-{cluster}",
                    cluster=cluster,
                    evidence=tuple(evidence),
                    proposed_pressure=proposed_pressure,
                )
            )
    return candidates


def render_review_state(
    *,
    evaluated_at: str,
    candidates: list[VoicePromotionCandidate],
    entry_count: int,
) -> str:
    review_status = "pending_owner_review" if candidates else "hold_not_enough_repeated_evidence"
    parts = [
        "---",
        "title: XinYu Voice Profile Review State",
        "memory_type: voice_profile_review_state",
        "time_scope: evolving",
        "subject_ids: [xinyu, owner]",
        "protected: true",
        "source: voice_calibration_promotion_gate",
        f"created_at: {_timestamp_or_now_iso('2026-04-27T00:00:00+08:00')}",
        f"updated_at: {_timestamp_or_now_iso(evaluated_at)}",
        "importance_score: 90",
        "impact_score: 92",
        "confidence_score: 84",
        "status: active",
        "tags: [self, voice, calibration, review]",
        "---",
        "",
        "# XinYu Voice Profile Review State",
        "",
        "## Gate Summary",
        f"- evaluated_at: {_timestamp_or_now_iso(evaluated_at)}",
        f"- review_status: {review_status}",
        f"- calibration_entry_count: {entry_count}",
        f"- candidate_count: {len(candidates)}",
        "- stable_profile_write: blocked_until_owner_accepts",
        "- target_file: memory/self/voice_profile_zh.md",
        "- review_rule: repeated owner corrections may create candidates, but this gate never rewrites the stable voice profile.",
        "- affected_smokes: " + ", ".join(AFFECTED_SMOKES),
    ]
    if not candidates:
        parts.extend(["", "## Candidates", "- none"])
        return "\n".join(parts)

    parts.append("")
    parts.append("## Candidates")
    for candidate in candidates:
        entries = candidate.evidence
        source_ids = ", ".join(entry.entry_id for entry in entries[:12])
        examples = " | ".join(
            _one_line(entry.visible_reply, limit=90)
            for entry in entries[:3]
            if entry.visible_reply not in {"unknown", "none", ""}
        ) or "none"
        owner_examples = " | ".join(
            _one_line(entry.owner_correction, limit=90)
            for entry in entries[:3]
            if entry.owner_correction not in {"unknown", "none", ""}
        ) or "none"
        parts.extend(
            [
                "",
                f"### {candidate.candidate_id}",
                f"- candidate_id: {candidate.candidate_id}",
                f"- cluster: {candidate.cluster}",
                f"- evidence_count: {len(entries)}",
                f"- source_entries: {source_ids}",
                "- owner_review_status: pending",
                "- accepted: no",
                "- rejected: no",
                "- stable_profile_write: blocked_until_owner_accepts",
                f"- proposed_profile_pressure: {candidate.proposed_pressure}",
                f"- owner_correction_examples: {owner_examples}",
                f"- bad_visible_reply_examples: {examples}",
                "- rollback_note: delete or reject this candidate; no stable profile file has been changed.",
                "- affected_smokes: " + ", ".join(AFFECTED_SMOKES),
            ]
        )
    return "\n".join(parts)


def build_voice_promotion_review(
    root: Path,
    *,
    evaluated_at: str | None = None,
    min_evidence: int = 2,
) -> dict[str, object]:
    evaluated_at = _timestamp_or_now_iso(evaluated_at)
    log_text = read_text(voice_calibration_log_path(root))
    entries = parse_voice_entries(log_text)
    candidates = build_candidates(entries, min_evidence=min_evidence)
    state = render_review_state(
        evaluated_at=evaluated_at,
        candidates=candidates,
        entry_count=len(entries),
    )
    write_text(voice_profile_review_state_path(root), state)
    return {
        "review_status": "pending_owner_review" if candidates else "hold_not_enough_repeated_evidence",
        "candidate_count": len(candidates),
        "entry_count": len(entries),
        "candidates": [candidate.candidate_id for candidate in candidates],
    }


def main() -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Build review-only voice profile promotion candidates.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--min-evidence", type=int, default=2)
    args = parser.parse_args()
    result = build_voice_promotion_review(args.root.resolve(), min_evidence=args.min_evidence)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
