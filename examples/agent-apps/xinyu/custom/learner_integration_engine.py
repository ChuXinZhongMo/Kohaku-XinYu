from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def append_lines_to_section(text: str, heading: str, lines: list[str]) -> str:
    if heading not in text:
        return text.rstrip() + f"\n\n{heading}\n" + "\n".join(lines)
    pattern = rf"(?ms)^({re.escape(heading)}\n)(.*?)(?=^## |\Z)"
    match = re.search(pattern, text)
    if not match:
        return text.rstrip() + f"\n\n{heading}\n" + "\n".join(lines)
    body = match.group(2).rstrip()
    addition = ("\n" if body else "") + "\n".join(lines)
    replacement = match.group(1) + body + addition + "\n\n"
    return text[: match.start()] + replacement + text[match.end():]


def extract_value(text: str, field: str, default: str = "unknown") -> str:
    pattern = re.compile(rf"^- {re.escape(field)}:\s*(.+)$", re.M)
    match = pattern.search(text)
    return match.group(1).strip() if match else default


from xinyu_state_io import extract_value as extract_value, read_text as read_text, write_text as write_text


def split_materials(text: str) -> list[dict[str, str]]:
    parts = re.split(r"(?m)^## (material-\d{4}-\d{2}-\d{2}-\d{3})\n", text)
    materials: list[dict[str, str]] = []
    if len(parts) < 3:
        return materials
    for i in range(1, len(parts), 2):
        material_id = parts[i].strip()
        body = parts[i + 1]
        item = {
            "material_id": material_id,
            "question_id": "none",
            "url": "none",
            "source_type": "unknown",
            "reliability": "unknown",
            "integration_scope": "hold",
            "status": "hold",
            "comparison_status": "not_compared",
            "evidence_hosts": "0",
            "claim": "none",
            "extraction_status": "unknown",
        }
        for line in body.splitlines():
            stripped = line.strip()
            for key in [
                "question_id",
                "url",
                "source_type",
                "reliability",
                "integration_scope",
                "status",
                "comparison_status",
                "evidence_hosts",
                "claim",
                "extraction_status",
            ]:
                prefix = f"- {key}: "
                if stripped.startswith(prefix):
                    item[key] = stripped.removeprefix(prefix).strip()
        materials.append(item)
    return materials


def ready_materials(materials: list[dict[str, str]]) -> list[dict[str, str]]:
    allowed_reliability = {"medium_ready", "high_ready", "verified", "curated"}
    allowed_scope = {"knowledge_only", "question_answer", "conceptual_only"}
    # Single-source material can stay staged, but it should not become learned
    # knowledge until another independent source or curated review supports it.
    allowed_comparison = {"corroborated", "limited_independence", "curated"}
    return [
        item for item in materials
        if item["status"] == "ready"
        and item["reliability"] in allowed_reliability
        and item["integration_scope"] in allowed_scope
        and item.get("comparison_status") in allowed_comparison
        and not claim_looks_garbled(item.get("claim", ""))
        and not claim_is_placeholder(item.get("claim", ""))
        and not claim_is_too_thin(item.get("claim", ""))
        and item.get("extraction_status") != "unreadable"
    ]


def material_is_ready_except_claim_quality(item: dict[str, str]) -> bool:
    allowed_reliability = {"medium_ready", "high_ready", "verified", "curated"}
    allowed_scope = {"knowledge_only", "question_answer", "conceptual_only"}
    allowed_comparison = {"corroborated", "limited_independence", "curated"}
    return (
        item["status"] == "ready"
        and item["reliability"] in allowed_reliability
        and item["integration_scope"] in allowed_scope
        and item.get("comparison_status") in allowed_comparison
    )


def claim_looks_garbled(claim: str) -> bool:
    sample = claim.strip()[:2000]
    mojibake_markers = sum(
        sample.count(marker)
        for marker in ("\u951f\u65a4\u62f7", "\u951f\u65a4", "\u65a4\u62f7", "\ufffd\ufffd", "\ufffd\ufffd\ufffd")
    )
    chars = [char for char in sample if not char.isspace()]
    if len(chars) < 24:
        return False
    control_or_replacement = sum(
        1
        for char in chars
        if char == "\ufffd" or unicodedata.category(char) in {"Cc", "Cf", "Cs"}
    )
    private_use = sum(1 for char in chars if 0xE000 <= ord(char) <= 0xF8FF or unicodedata.category(char) == "Co")
    rare_cjk = sum(
        1
        for char in chars
        if 0x3400 <= ord(char) <= 0x4DBF or 0x20000 <= ord(char) <= 0x2FA1F
    )
    uncommon_latin = sum(1 for char in chars if 0x1D00 <= ord(char) <= 0x1EFF or 0xA720 <= ord(char) <= 0xABFF)
    total = len(chars)
    if mojibake_markers >= 2 and (mojibake_markers * 3) / total > 0.01:
        return True
    if control_or_replacement and control_or_replacement / total > 0.004:
        return True
    if private_use and private_use / total > 0.003:
        return True
    if total >= 80 and (rare_cjk + uncommon_latin + private_use + control_or_replacement) / total > 0.18:
        return True
    return False


def claim_is_placeholder(claim: str) -> bool:
    normalized = re.sub(r"\s+", " ", claim.strip().lower())
    return normalized.startswith("owner/local material copied from ") or normalized.startswith("downloaded ")


def claim_is_too_thin(claim: str) -> bool:
    tokens = [token for token in re.findall(r"[a-z0-9]+", claim.lower()) if len(token) > 2]
    return len(tokens) < 8


def integrated_source_material_ids(text: str) -> set[str]:
    return set(re.findall(r"(?m)^- source_material:\s*(material-\d{4}-\d{2}-\d{2}-\d{3})\s*$", text))


def next_learned_id(text: str, date_part: str) -> str:
    pattern = re.compile(rf"(?m)^## learned-{re.escape(date_part)}-(\d{{3}})$")
    numbers = [int(match.group(1)) for match in pattern.finditer(text)]
    return f"learned-{date_part}-{max(numbers, default=0) + 1:03d}"


def append_general_knowledge(path: Path, integrated_at: str, item: dict[str, str]) -> bool:
    text = read_text(path).rstrip()
    if f"- source_material: {item['material_id']}" in text:
        return False
    learned_id = next_learned_id(text, integrated_at[:10])
    addition = (
        f"\n\n## {learned_id}\n"
        f"- learned_at: {integrated_at}\n"
        f"- source_material: {item['material_id']}\n"
        f"- question_id: {item['question_id']}\n"
        f"- source_type: {item['source_type']}\n"
        f"- reliability: {item['reliability']}\n"
        f"- comparison_status: {item.get('comparison_status', 'not_compared')}\n"
        f"- evidence_hosts: {item.get('evidence_hosts', '0')}\n"
        f"- claim: {item['claim']}\n"
        "- integration_scope: knowledge_only\n"
        "- boundary: updates knowledge and question progress only; does not rewrite self or relationship memory\n"
    )
    write_text(path, text + addition + "\n")
    return True


def append_source_notes(path: Path, integrated_at: str, integrated: list[dict[str, str]]) -> None:
    text = read_text(path).rstrip()
    lines = []
    for item in integrated:
        marker = f"- {item['material_id']}:"
        if marker in text:
            continue
        lines.append(
            f"- {item['material_id']}: integrated for {item['question_id']} at {integrated_at}; "
            f"source_type={item['source_type']}; reliability={item['reliability']}; "
            f"comparison={item.get('comparison_status', 'not_compared')}; "
            f"evidence_hosts={item.get('evidence_hosts', '0')}; scope=knowledge_only"
        )
    if not lines:
        return
    text = append_lines_to_section(text, "## Learner Integrated Sources", lines)
    write_text(path, text.rstrip() + "\n")


def update_question_states(path: Path, integrated_at: str, integrated: list[dict[str, str]]) -> None:
    text = read_text(path)
    for item in integrated:
        qid = item["question_id"]
        if qid == "none":
            continue
        pattern = rf"(### {re.escape(qid)}\n)(.*?)(?=\n### |\n## |\Z)"
        match = re.search(pattern, text, flags=re.S)
        replacement_body = (
            "- state: partially_answered\n"
            f"- reason: learner integration used {item['material_id']} as knowledge-only material; identity and relationship layers remain protected.\n"
            f"- updated_at: {integrated_at}\n"
        )
        if match:
            text = text[: match.start(2)] + replacement_body + text[match.end(2) :]
    write_text(path, text.rstrip() + "\n")


def update_active_questions(path: Path, integrated_at: str, integrated: list[dict[str, str]]) -> None:
    integrated_qids = {item["question_id"] for item in integrated if item["question_id"] != "none"}
    if not integrated_qids or not path.exists():
        return
    text = read_text(path)
    original = text
    text = re.sub(r"(?m)^updated_at:\s*.+$", f"updated_at: {integrated_at}", text)
    text = re.sub(r"(?m)^last_confirmed_at:\s*.+$", f"last_confirmed_at: {integrated_at}", text)
    for qid in sorted(integrated_qids):
        pattern = rf"(?ms)^(## {re.escape(qid)}\n)(.*?)(?=^## q-\d+\n|^# |\Z)"
        match = re.search(pattern, text)
        if not match:
            continue
        lines = match.group(2).rstrip().splitlines()
        rendered: list[str] = []
        status_seen = False
        next_action_seen = False
        learner_seen = False
        for line in lines:
            if line.startswith("- status: "):
                rendered.append("- status: partially_answered")
                status_seen = True
            elif line.startswith("- next_action: "):
                rendered.append("- next_action: learned as knowledge_only; keep out of fresh exploration unless explicitly reopened")
                next_action_seen = True
            elif line.startswith("- learner_integrated_at: "):
                rendered.append(f"- learner_integrated_at: {integrated_at}")
                learner_seen = True
            else:
                rendered.append(line)
        if not status_seen:
            rendered.append("- status: partially_answered")
        if not next_action_seen:
            rendered.append("- next_action: learned as knowledge_only; keep out of fresh exploration unless explicitly reopened")
        if not learner_seen:
            rendered.append(f"- learner_integrated_at: {integrated_at}")
        replacement = match.group(1) + "\n".join(rendered).rstrip() + "\n\n"
        text = text[: match.start()] + replacement + text[match.end():]
    if text != original:
        write_text(path, text.rstrip() + "\n")


def update_exploration_queue(path: Path, integrated_at: str, integrated: list[dict[str, str]]) -> None:
    text = read_text(path)
    integrated_qids = {item["question_id"] for item in integrated if item["question_id"] != "none"}
    if not integrated_qids:
        return
    parts = re.split(r"(?m)^## (item-\d{4}-\d{2}-\d{2}-\d{3})\n", text)
    if len(parts) < 3:
        return
    rendered = [parts[0].rstrip()]
    for i in range(1, len(parts), 2):
        item_id = parts[i]
        body = parts[i + 1].rstrip()
        question_id = extract_value(body, "question_id", "none")
        if question_id in integrated_qids:
            lines = []
            status_seen = False
            stage_seen = False
            for line in body.splitlines():
                if line.startswith("- status: "):
                    lines.append("- status: partially_answered")
                    status_seen = True
                elif line.startswith("- exploration_stage: "):
                    lines.append("- exploration_stage: learner_integrated")
                    stage_seen = True
                else:
                    lines.append(line)
            if not status_seen:
                lines.append("- status: partially_answered")
            if not stage_seen:
                lines.append("- exploration_stage: learner_integrated")
            if not any(line.startswith("- learner_integrated_at: ") for line in lines):
                lines.append(f"- learner_integrated_at: {integrated_at}")
            body = "\n".join(lines)
        rendered.append(f"\n\n## {item_id}\n{body}")
    write_text(path, "".join(rendered).rstrip() + "\n")


def render_state(
    integrated_at: str,
    mode: str,
    permission: str,
    integrated: list[dict[str, str]],
    ready_count: int,
    total_integrated_materials: int,
    already_integrated_ready_materials: int,
    pending_ready_materials: int,
    blocked_unreadable_materials: int,
    held_unreadable_materials: int,
    skipped_reason: str,
) -> str:
    ids = "\n".join(f"- {item['material_id']}" for item in integrated) or "- none"
    return f"""---
title: Learner Integration State
memory_type: learner_integration_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {integrated_at}
last_confirmed_at: {integrated_at}
importance_score: 82
impact_score: 82
confidence_score: 100
status: active
tags: [knowledge, learner, integration]
---

# Learner Integration State

## Last Integration
- integrated_at: {integrated_at}
- mode: {mode}
- permission: {permission}
- integrated_materials: {len(integrated)}
- newly_integrated_materials: {len(integrated)}
- ready_materials: {ready_count}
- total_integrated_materials: {total_integrated_materials}
- already_integrated_ready_materials: {already_integrated_ready_materials}
- pending_ready_materials: {pending_ready_materials}
- blocked_unreadable_materials: {blocked_unreadable_materials}
- held_unreadable_materials: {held_unreadable_materials}
- skipped_reason: {skipped_reason}

## Last Integrated Material Ids
{ids}

## Boundaries
- Learner integration may update knowledge and question states.
- Learner integration only accepts material already marked by source comparison or curated review.
- It may not directly rewrite self/core, self/narrative, owner, or relationship files.
- If a source affects identity or relationship meaning, send it back to reflection first.
"""


def run_learner_integration(
    root: Path,
    integrated_at: str | None = None,
    mode: str = "runtime_learner_integration",
) -> dict[str, object]:
    integrated_at = integrated_at or datetime.now().astimezone().isoformat()
    gate_text = read_text(root / "memory/knowledge/source_integration_gate_state.md")
    permission = extract_value(gate_text, "integration_permission", "hold")
    materials = split_materials(read_text(root / "memory/knowledge/source_materials.md"))
    ready = ready_materials(materials)
    blocked_unreadable = [
        item for item in materials
        if material_is_ready_except_claim_quality(item)
        and (
            claim_looks_garbled(item.get("claim", ""))
            or claim_is_placeholder(item.get("claim", ""))
            or claim_is_too_thin(item.get("claim", ""))
            or item.get("extraction_status") == "unreadable"
        )
    ]
    held_unreadable = [
        item for item in materials
        if item.get("status") != "ready"
        and (
            item.get("extraction_status") == "unreadable"
            or claim_looks_garbled(item.get("claim", ""))
            or claim_is_placeholder(item.get("claim", ""))
            or claim_is_too_thin(item.get("claim", ""))
        )
    ]
    general_path = root / "memory/knowledge/general.md"

    integrated: list[dict[str, str]] = []
    skipped_reason = "none"
    if permission not in {"prepare_only", "integrate_ready"}:
        skipped_reason = "integration_gate_not_open"
    elif not ready:
        skipped_reason = "unreadable_claim_quality_hold" if blocked_unreadable else "no_ready_materials"
    else:
        for item in ready:
            if append_general_knowledge(general_path, integrated_at, item):
                integrated.append(item)
        append_source_notes(root / "memory/knowledge/source_notes.md", integrated_at, integrated)
        update_question_states(root / "memory/context/question_states.md", integrated_at, integrated)
        update_active_questions(root / "memory/context/active_questions.md", integrated_at, integrated)
        update_exploration_queue(root / "memory/context/exploration_queue.md", integrated_at, integrated)
        if not integrated:
            skipped_reason = "materials_already_integrated"

    integrated_ids = integrated_source_material_ids(read_text(general_path))
    ready_ids = {item["material_id"] for item in ready}
    already_integrated_ready = ready_ids & integrated_ids
    pending_ready = ready_ids - integrated_ids

    write_text(
        root / "memory/knowledge/learner_integration_state.md",
        render_state(
            integrated_at,
            mode,
            permission,
            integrated,
            len(ready),
            len(integrated_ids),
            len(already_integrated_ready),
            len(pending_ready),
            len(blocked_unreadable),
            len(held_unreadable),
            skipped_reason,
        ),
    )
    return {
        "integrated_at": integrated_at,
        "permission": permission,
        "ready_materials": len(ready),
        "integrated_materials": len(integrated),
        "newly_integrated_materials": len(integrated),
        "total_integrated_materials": len(integrated_ids),
        "already_integrated_ready_materials": len(already_integrated_ready),
        "pending_ready_materials": len(pending_ready),
        "blocked_unreadable_materials": len(blocked_unreadable),
        "held_unreadable_materials": len(held_unreadable),
        "integrated_ids": [item["material_id"] for item in integrated],
        "skipped_reason": skipped_reason,
    }
