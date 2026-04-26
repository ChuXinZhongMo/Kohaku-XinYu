from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


READY_STATUSES = {"ready"}
READY_RELIABILITY = {"medium_ready", "high_ready", "verified", "curated"}
FINAL_READY_COMPARISONS = {"corroborated", "limited_independence", "curated"}
NEGATORS = {"not", "no", "never", "cannot", "cant", "without", "false", "deny", "denies"}
HOLD_STATUSES = {"conflict_hold", "semantic_mismatch_hold"}
MIN_SEMANTIC_OVERLAP = 0.06
MIN_SHARED_SUPPORT_TOKENS = 2
GENERIC_SUPPORT_TOKENS = {
    "article",
    "human",
    "humans",
    "people",
    "relationship",
    "relationships",
    "source",
    "study",
    "question",
}
STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "because",
    "being",
    "between",
    "could",
    "from",
    "have",
    "into",
    "that",
    "their",
    "there",
    "these",
    "this",
    "when",
    "with",
    "would",
}
MIN_QUESTION_OVERLAP = 0.50
MIN_SHARED_QUESTION_TOKENS = 2


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


def host_of(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host or "unknown"


def split_material_blocks(text: str) -> tuple[str, list[dict[str, object]]]:
    parts = re.split(r"(?m)^## (material-\d{4}-\d{2}-\d{2}-\d{3}|material-[\w-]+)\n", text)
    preface = parts[0].rstrip()
    materials: list[dict[str, object]] = []
    if len(parts) < 3:
        return preface, materials
    for i in range(1, len(parts), 2):
        material_id = parts[i].strip()
        body = parts[i + 1].rstrip()
        fields: dict[str, str] = {}
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped.startswith("- ") or ": " not in stripped:
                continue
            key, value = stripped[2:].split(": ", 1)
            fields[key.strip()] = value.strip()
        materials.append({"material_id": material_id, "body": body, "fields": fields})
    return preface, materials


def split_question_refs(text: str) -> dict[str, str]:
    refs: dict[str, str] = {}
    parts = re.split(r"(?m)^## (q-\d+)\n", text)
    if len(parts) < 3:
        return refs
    for i in range(1, len(parts), 2):
        qid = parts[i].strip()
        body = parts[i + 1]
        question = extract_value(body, "question", "")
        if question:
            refs[qid] = question
    return refs


def set_field(body: str, key: str, value: str) -> str:
    lines = body.splitlines()
    found = False
    rendered: list[str] = []
    prefix = f"- {key}: "
    for line in lines:
        if line.startswith(prefix):
            if not found:
                rendered.append(f"{prefix}{value}")
                found = True
            continue
        rendered.append(line)
    if not found:
        rendered.append(f"{prefix}{value}")
    return "\n".join(rendered).rstrip()


def apply_updates(material: dict[str, object], updates: dict[str, str]) -> None:
    body = str(material["body"])
    fields = dict(material["fields"])
    for key, value in updates.items():
        body = set_field(body, key, value)
        fields[key] = value
    material["body"] = body
    material["fields"] = fields


def render_materials(compared_at: str, preface: str, materials: list[dict[str, object]]) -> str:
    text = preface
    text = re.sub(r"(?m)^updated_at:\s*.+$", f"updated_at: {compared_at}", text)
    text = re.sub(r"(?m)^last_confirmed_at:\s*.+$", f"last_confirmed_at: {compared_at}", text)
    blocks = []
    for material in materials:
        blocks.append(f"## {material['material_id']}\n{str(material['body']).rstrip()}")
    if blocks:
        text = text.rstrip() + "\n\n" + "\n\n".join(blocks)
    return text.rstrip() + "\n"


def tokens_for_claim(claim: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", claim.lower()) if len(token) > 3 and token not in STOPWORDS]


def support_tokens_for_claim(claim: str) -> set[str]:
    return {token for token in tokens_for_claim(claim) if token not in GENERIC_SUPPORT_TOKENS}


def token_polarities(claim: str) -> dict[str, set[int]]:
    raw_tokens = re.findall(r"[a-z0-9]+", claim.lower())
    polarities: dict[str, set[int]] = defaultdict(set)
    for idx, token in enumerate(raw_tokens):
        if len(token) <= 3 or token in STOPWORDS:
            continue
        window = raw_tokens[max(0, idx - 3):idx]
        polarity = -1 if any(item in NEGATORS for item in window) else 1
        polarities[token].add(polarity)
    return polarities


def content_overlap(left: str, right: str) -> float:
    left_tokens = set(tokens_for_claim(left))
    right_tokens = set(tokens_for_claim(right))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)


def semantic_overlap(left: str, right: str) -> tuple[float, set[str]]:
    left_tokens = support_tokens_for_claim(left)
    right_tokens = support_tokens_for_claim(right)
    if not left_tokens or not right_tokens:
        return 0.0, set()
    shared = left_tokens & right_tokens
    overlap = len(shared) / max(len(left_tokens | right_tokens), 1)
    return overlap, shared


def question_for_material(material: dict[str, object], question_refs: dict[str, str]) -> str:
    fields = dict(material["fields"])
    return (
        fields.get("source_question")
        or fields.get("question")
        or question_refs.get(fields.get("question_id", "none"), "")
    )


def question_relation(left: dict[str, object], right: dict[str, object], question_refs: dict[str, str]) -> tuple[str, float, list[str]]:
    left_question = question_for_material(left, question_refs)
    right_question = question_for_material(right, question_refs)
    if not left_question or not right_question:
        return "same_question", 1.0, []
    overlap, shared = semantic_overlap(left_question, right_question)
    if overlap >= MIN_QUESTION_OVERLAP and len(shared) >= MIN_SHARED_QUESTION_TOKENS:
        return "same_question", overlap, sorted(shared)
    if overlap > 0.0 or bool(set(tokens_for_claim(left_question)) & set(tokens_for_claim(right_question))):
        return "adjacent_question", overlap, sorted(shared)
    return "unrelated_question", overlap, sorted(shared)


def material_question_alignment(material: dict[str, object], question_refs: dict[str, str]) -> tuple[str, float, list[str]]:
    fields = dict(material["fields"])
    canonical_question = question_refs.get(fields.get("question_id", "none"), "")
    source_question = question_for_material(material, question_refs)
    if not canonical_question or not source_question:
        return "same_question", 1.0, []
    overlap, shared = semantic_overlap(canonical_question, source_question)
    if overlap >= MIN_QUESTION_OVERLAP and len(shared) >= MIN_SHARED_QUESTION_TOKENS:
        return "same_question", overlap, sorted(shared)
    if overlap > 0.0 or bool(set(tokens_for_claim(canonical_question)) & set(tokens_for_claim(source_question))):
        return "adjacent_question", overlap, sorted(shared)
    return "unrelated_question", overlap, sorted(shared)


def semantic_support_pairs(group: list[dict[str, object]], question_refs: dict[str, str]) -> list[dict[str, object]]:
    pairs: list[dict[str, object]] = []
    for idx, left in enumerate(group):
        left_fields = dict(left["fields"])
        for right in group[idx + 1:]:
            right_fields = dict(right["fields"])
            overlap, shared = semantic_overlap(left_fields.get("claim", ""), right_fields.get("claim", ""))
            if overlap >= MIN_SEMANTIC_OVERLAP and len(shared) >= MIN_SHARED_SUPPORT_TOKENS:
                q_relation, q_overlap, q_shared = question_relation(left, right, question_refs)
                pairs.append(
                    {
                        "left": str(left["material_id"]),
                        "right": str(right["material_id"]),
                        "overlap": overlap,
                        "shared_tokens": sorted(shared),
                        "question_relation": q_relation,
                        "question_overlap": f"{q_overlap:.3f}",
                        "shared_question_tokens": q_shared,
                        "hosts": {
                            host_of(left_fields.get("url", "none")),
                            host_of(right_fields.get("url", "none")),
                        },
                    }
                )
    return pairs


def independent_semantic_support_pairs(
    support_pairs: list[dict[str, object]],
    relation: str = "same_question",
) -> list[dict[str, object]]:
    independent: list[dict[str, object]] = []
    for pair in support_pairs:
        if pair.get("question_relation") != relation:
            continue
        hosts = {str(host) for host in pair.get("hosts", set()) if str(host) != "unknown"}
        if len(hosts) >= 2:
            independent.append(pair)
    return independent


def claims_conflict(left: str, right: str) -> bool:
    overlap = content_overlap(left, right)
    if overlap < 0.16:
        return False
    left_polarities = token_polarities(left)
    right_polarities = token_polarities(right)
    for token in set(left_polarities) & set(right_polarities):
        if -1 in left_polarities[token] and 1 in right_polarities[token]:
            return True
        if 1 in left_polarities[token] and -1 in right_polarities[token]:
            return True
    return False


def next_comparison_id(existing_text: str, date_part: str) -> str:
    pattern = re.compile(rf"compare-{re.escape(date_part)}-(\d{{3}})")
    numbers = [int(match.group(1)) for match in pattern.finditer(existing_text)]
    return f"compare-{date_part}-{max(numbers, default=0) + 1:03d}"


def ready_materials(materials: list[dict[str, object]]) -> list[dict[str, object]]:
    ready: list[dict[str, object]] = []
    for material in materials:
        fields = dict(material["fields"])
        if fields.get("status") in READY_STATUSES and fields.get("reliability") in READY_RELIABILITY:
            ready.append(material)
    return ready


def group_needs_comparison(group: list[dict[str, object]]) -> bool:
    for material in group:
        fields = dict(material["fields"])
        comparison_status = fields.get("comparison_status", "not_compared")
        if comparison_status not in FINAL_READY_COMPARISONS:
            return True
    return False


def compare_group(
    group_id: str,
    compared_at: str,
    group: list[dict[str, object]],
    question_refs: dict[str, str],
) -> dict[str, object]:
    hosts = {host_of(dict(item["fields"]).get("url", "none")) for item in group}
    conflict_pairs: list[tuple[str, str]] = []
    support_pairs = semantic_support_pairs(group, question_refs)
    independent_support_pairs = independent_semantic_support_pairs(support_pairs, "same_question")
    adjacent_support_pairs = independent_semantic_support_pairs(support_pairs, "adjacent_question")
    max_semantic_overlap = max((float(item["overlap"]) for item in support_pairs), default=0.0)
    alignments = [material_question_alignment(item, question_refs)[0] for item in group]
    if any(item == "unrelated_question" for item in alignments):
        question_alignment_status = "mixed_or_unrelated_question"
    elif any(item == "adjacent_question" for item in alignments):
        question_alignment_status = "adjacent_question"
    else:
        question_alignment_status = "same_question"
    for idx, left in enumerate(group):
        left_fields = dict(left["fields"])
        for right in group[idx + 1:]:
            right_fields = dict(right["fields"])
            if claims_conflict(left_fields.get("claim", ""), right_fields.get("claim", "")):
                conflict_pairs.append((str(left["material_id"]), str(right["material_id"])))

    evidence_hosts = len({host for host in hosts if host != "unknown"})
    if conflict_pairs:
        status = "conflict_hold"
        updates = {
            "status": "hold",
            "integration_scope": "hold_conflict",
            "comparison_status": status,
            "comparison_group": group_id,
            "evidence_hosts": str(evidence_hosts),
            "comparison_checked_at": compared_at,
            "comparison_reason": "source claims conflict; learner integration blocked until reviewed",
            "question_alignment_status": question_alignment_status,
        }
    elif len(group) >= 2 and not support_pairs:
        status = "semantic_mismatch_hold"
        updates = {
            "status": "hold",
            "integration_scope": "hold_semantic_review",
            "comparison_status": status,
            "comparison_group": group_id,
            "evidence_hosts": str(evidence_hosts),
            "comparison_checked_at": compared_at,
            "comparison_reason": "multiple sources exist, but claims do not show enough same-question support",
            "question_alignment_status": question_alignment_status,
        }
    elif evidence_hosts >= 2 and independent_support_pairs:
        status = "corroborated"
        updates = {
            "status": "ready",
            "reliability": "verified",
            "comparison_status": status,
            "comparison_group": group_id,
            "evidence_hosts": str(evidence_hosts),
            "comparison_checked_at": compared_at,
            "comparison_reason": "two or more independent hosts show same-question semantic support",
            "question_alignment_status": "same_question",
        }
    elif evidence_hosts >= 2 and adjacent_support_pairs:
        status = "limited_independence"
        updates = {
            "status": "ready",
            "comparison_status": status,
            "comparison_group": group_id,
            "evidence_hosts": str(evidence_hosts),
            "comparison_checked_at": compared_at,
            "comparison_reason": "independent hosts show adjacent-question support only; not enough for corroborated",
            "question_alignment_status": "adjacent_question",
        }
    elif evidence_hosts >= 2:
        status = "semantic_mismatch_hold"
        updates = {
            "status": "hold",
            "integration_scope": "hold_semantic_review",
            "comparison_status": status,
            "comparison_group": group_id,
            "evidence_hosts": str(evidence_hosts),
            "comparison_checked_at": compared_at,
            "comparison_reason": "independent hosts exist, but cross-host same-question support is insufficient",
            "question_alignment_status": question_alignment_status,
        }
    elif len(group) >= 2:
        status = "limited_independence"
        updates = {
            "status": "ready",
            "comparison_status": status,
            "comparison_group": group_id,
            "evidence_hosts": str(evidence_hosts),
            "comparison_checked_at": compared_at,
            "comparison_reason": "multiple materials exist, but host independence is limited",
            "question_alignment_status": question_alignment_status,
        }
    else:
        status = "single_source"
        updates = {
            "status": "ready",
            "comparison_status": status,
            "comparison_group": group_id,
            "evidence_hosts": str(evidence_hosts),
            "comparison_checked_at": compared_at,
            "comparison_reason": "single source only; keep learner boundary explicit",
            "question_alignment_status": question_alignment_status,
        }

    for material in group:
        apply_updates(material, updates)

    return {
        "group_id": group_id,
        "question_id": dict(group[0]["fields"]).get("question_id", "none"),
        "status": status,
        "materials": len(group),
        "evidence_hosts": evidence_hosts,
        "conflict_pairs": conflict_pairs,
        "semantic_support_pairs": len(support_pairs),
        "independent_semantic_support_pairs": len(independent_support_pairs),
        "adjacent_semantic_support_pairs": len(adjacent_support_pairs),
        "question_alignment_status": question_alignment_status,
        "max_semantic_overlap": f"{max_semantic_overlap:.3f}",
    }


def render_state(
    compared_at: str,
    mode: str,
    ready_count: int,
    group_results: list[dict[str, object]],
    skipped_reason: str,
) -> str:
    groups_block = "\n".join(
        f"- {item['group_id']}: question_id={item['question_id']}; status={item['status']}; "
        f"materials={item['materials']}; evidence_hosts={item['evidence_hosts']}; "
        f"question_alignment={item.get('question_alignment_status', 'unknown')}"
        for item in group_results
    ) or "- none"
    corroborated = sum(int(item["materials"]) for item in group_results if item["status"] == "corroborated")
    conflict = sum(int(item["materials"]) for item in group_results if item["status"] == "conflict_hold")
    single = sum(int(item["materials"]) for item in group_results if item["status"] == "single_source")
    limited = sum(int(item["materials"]) for item in group_results if item["status"] == "limited_independence")
    semantic_mismatch = sum(int(item["materials"]) for item in group_results if item["status"] == "semantic_mismatch_hold")
    adjacent_question = sum(
        int(item["materials"])
        for item in group_results
        if item.get("question_alignment_status") == "adjacent_question"
    )
    question_mismatch = sum(
        int(item["materials"])
        for item in group_results
        if item.get("question_alignment_status") == "mixed_or_unrelated_question"
    )
    return f"""---
title: Source Comparison State
memory_type: source_comparison_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {compared_at}
last_confirmed_at: {compared_at}
importance_score: 82
impact_score: 82
confidence_score: 100
status: active
tags: [knowledge, source, comparison]
---

# Source Comparison State

## Last Comparison
- compared_at: {compared_at}
- mode: {mode}
- ready_materials: {ready_count}
- compared_groups: {len(group_results)}
- corroborated_materials: {corroborated}
- conflict_materials: {conflict}
- single_source_materials: {single}
- limited_independence_materials: {limited}
- semantic_mismatch_materials: {semantic_mismatch}
- adjacent_question_materials: {adjacent_question}
- question_mismatch_materials: {question_mismatch}
- skipped_reason: {skipped_reason}

## Groups
{groups_block}

## Boundaries
- Source comparison marks source material confidence before learner integration.
- Conflicted or semantically mismatched materials are moved to hold and must not be learned automatically.
- Corroboration upgrades knowledge-source confidence only; it does not rewrite self, owner, relationship, or emotion memory.
"""


def append_source_notes(root: Path, compared_at: str, group_results: list[dict[str, object]]) -> None:
    hold_groups = [item for item in group_results if item["status"] in HOLD_STATUSES]
    if not hold_groups:
        return
    path = root / "memory/knowledge/source_notes.md"
    text = read_text(path).rstrip()
    lines: list[str] = []
    for item in hold_groups:
        marker = f"- {item['group_id']}:"
        if marker in text:
            continue
        pairs = item.get("conflict_pairs", [])
        pair_text = ", ".join(f"{left}<>{right}" for left, right in pairs) if pairs else "unknown"
        hold_kind = "conflict_hold" if item["status"] == "conflict_hold" else "semantic_mismatch_hold"
        lines.append(
            f"- {item['group_id']}: {hold_kind} for {item['question_id']} at {compared_at}; "
            f"materials={item['materials']}; evidence_hosts={item['evidence_hosts']}; pairs={pair_text}"
        )
    if not lines:
        return
    text = append_lines_to_section(text, "## Source Comparison Holds", lines)
    write_text(path, text.rstrip() + "\n")


def update_question_states(root: Path, compared_at: str, group_results: list[dict[str, object]]) -> None:
    hold_groups = [item for item in group_results if item["status"] in HOLD_STATUSES]
    if not hold_groups:
        return
    path = root / "memory/context/question_states.md"
    text = read_text(path)
    for item in hold_groups:
        qid = str(item["question_id"])
        if qid == "none":
            continue
        if item["status"] == "conflict_hold":
            state = "blocked_by_source_conflict"
            reason = f"source comparison {item['group_id']} found conflicting materials; hold learning and seek clarification."
        else:
            state = "blocked_by_semantic_mismatch"
            reason = f"source comparison {item['group_id']} found multiple materials without enough same-question support; hold learning and refine sourcing."
        pattern = rf"(### {re.escape(qid)}\n)(.*?)(?=\n### |\n## |\Z)"
        replacement_body = (
            f"- state: {state}\n"
            f"- reason: {reason}\n"
            f"- updated_at: {compared_at}\n"
        )
        match = re.search(pattern, text, flags=re.S)
        if match:
            text = text[: match.start(2)] + replacement_body + text[match.end(2) :]
        else:
            if "## Current Question Entries" not in text:
                text = text.rstrip() + "\n\n## Current Question Entries\n"
            text = text.rstrip() + f"\n### {qid}\n{replacement_body}"
    write_text(path, text.rstrip() + "\n")


def update_exploration_queue(root: Path, compared_at: str, group_results: list[dict[str, object]]) -> None:
    hold_groups = [item for item in group_results if item["status"] in HOLD_STATUSES]
    if not hold_groups:
        return
    path = root / "memory/context/exploration_queue.md"
    text = read_text(path)
    conflict_by_qid = {str(item["question_id"]): item for item in hold_groups if item["question_id"] != "none"}
    parts = re.split(r"(?m)^## (item-\d{4}-\d{2}-\d{2}-\d{3}|item-[\w-]+)\n", text)
    matched: set[str] = set()
    if len(parts) >= 3:
        rendered = [parts[0].rstrip()]
        for i in range(1, len(parts), 2):
            item_id = parts[i]
            body = parts[i + 1].rstrip()
            qid = extract_value(body, "question_id", "none")
            conflict = conflict_by_qid.get(qid)
            if conflict:
                status_value = "blocked_by_source_conflict" if conflict["status"] == "conflict_hold" else "blocked_by_semantic_mismatch"
                stage_value = "source_conflict_review" if conflict["status"] == "conflict_hold" else "source_semantic_review"
                action_value = (
                    "compare sources again or ask for clarification before learning"
                    if conflict["status"] == "conflict_hold"
                    else "refine source query and require same-question support before learning"
                )
                matched.add(qid)
                lines = []
                status_seen = False
                stage_seen = False
                action_seen = False
                for line in body.splitlines():
                    if line.startswith("- status: "):
                        lines.append(f"- status: {status_value}")
                        status_seen = True
                    elif line.startswith("- exploration_stage: "):
                        lines.append(f"- exploration_stage: {stage_value}")
                        stage_seen = True
                    elif line.startswith("- next_action: "):
                        lines.append(f"- next_action: {action_value}")
                        action_seen = True
                    else:
                        lines.append(line)
                if not status_seen:
                    lines.append(f"- status: {status_value}")
                if not stage_seen:
                    lines.append(f"- exploration_stage: {stage_value}")
                if not action_seen:
                    lines.append(f"- next_action: {action_value}")
                if not any(line.startswith("- source_conflict_group: ") for line in lines):
                    lines.append(f"- source_conflict_group: {conflict['group_id']}")
                if not any(line.startswith("- source_conflict_at: ") for line in lines):
                    lines.append(f"- source_conflict_at: {compared_at}")
                body = "\n".join(lines)
            rendered.append(f"\n\n## {item_id}\n{body}")
        text = "".join(rendered).rstrip()
    for qid, conflict in conflict_by_qid.items():
        if qid in matched:
            continue
        semantic_mismatch = conflict["status"] == "semantic_mismatch_hold"
        item_id = f"item-{compared_at[:10]}-source-{'semantic' if semantic_mismatch else 'conflict'}-{qid}"
        text = text.rstrip() + (
            f"\n\n## {item_id}\n"
            f"- question_id: {qid}\n"
            f"- status: {'blocked_by_semantic_mismatch' if semantic_mismatch else 'blocked_by_source_conflict'}\n"
            f"- exploration_stage: {'source_semantic_review' if semantic_mismatch else 'source_conflict_review'}\n"
            f"- target: {'source semantic support' if semantic_mismatch else 'source conflict'}\n"
            f"- reason: source comparison {conflict['group_id']} found {'insufficient same-question support' if semantic_mismatch else 'conflicting material'}\n"
            f"- next_action: {'refine source query and require same-question support before learning' if semantic_mismatch else 'compare sources again or ask for clarification before learning'}\n"
            f"- source_conflict_group: {conflict['group_id']}\n"
            f"- source_conflict_at: {compared_at}\n"
        )
    write_text(path, text.rstrip() + "\n")


def run_source_comparison(
    root: Path,
    compared_at: str | None = None,
    mode: str = "runtime_source_comparison",
) -> dict[str, object]:
    compared_at = compared_at or datetime.now().astimezone().isoformat()
    path = root / "memory/knowledge/source_materials.md"
    original = read_text(path)
    preface, materials = split_material_blocks(original)
    active_questions_path = root / "memory/context/active_questions.md"
    question_refs = split_question_refs(read_text(active_questions_path)) if active_questions_path.exists() else {}
    ready = ready_materials(materials)
    existing_state = read_text(root / "memory/knowledge/source_comparison_state.md")

    skipped_reason = "none"
    group_results: list[dict[str, object]] = []
    if not ready:
        skipped_reason = "no_ready_materials"
    else:
        grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
        for material in ready:
            fields = dict(material["fields"])
            grouped[fields.get("question_id", "none")].append(material)
        for question_id, group in grouped.items():
            if question_id == "none":
                continue
            if not group_needs_comparison(group):
                continue
            group_id = next_comparison_id(existing_state + "\n" + original, compared_at[:10])
            result = compare_group(group_id, compared_at, group, question_refs)
            existing_state += f"\n{group_id}"
            group_results.append(result)
        if not group_results:
            skipped_reason = "no_materials_need_comparison"
        else:
            write_text(path, render_materials(compared_at, preface, materials))
            append_source_notes(root, compared_at, group_results)
            update_question_states(root, compared_at, group_results)
            update_exploration_queue(root, compared_at, group_results)

    write_text(
        root / "memory/knowledge/source_comparison_state.md",
        render_state(compared_at, mode, len(ready), group_results, skipped_reason),
    )
    return {
        "compared_at": compared_at,
        "ready_materials": len(ready),
        "compared_groups": len(group_results),
        "corroborated_materials": sum(int(item["materials"]) for item in group_results if item["status"] == "corroborated"),
        "conflict_materials": sum(int(item["materials"]) for item in group_results if item["status"] == "conflict_hold"),
        "single_source_materials": sum(int(item["materials"]) for item in group_results if item["status"] == "single_source"),
        "limited_independence_materials": sum(int(item["materials"]) for item in group_results if item["status"] == "limited_independence"),
        "semantic_mismatch_materials": sum(int(item["materials"]) for item in group_results if item["status"] == "semantic_mismatch_hold"),
        "adjacent_question_materials": sum(
            int(item["materials"])
            for item in group_results
            if item.get("question_alignment_status") == "adjacent_question"
        ),
        "question_mismatch_materials": sum(
            int(item["materials"])
            for item in group_results
            if item.get("question_alignment_status") == "mixed_or_unrelated_question"
        ),
        "skipped_reason": skipped_reason,
    }
