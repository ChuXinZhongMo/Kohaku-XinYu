from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"http", "https"}
READY_PERMISSIONS = {"prepare_only", "integrate_ready"}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def extract_value(text: str, field: str, default: str = "unknown") -> str:
    pattern = re.compile(rf"^- {re.escape(field)}:\s*(.+)$", re.M)
    match = pattern.search(text)
    return match.group(1).strip() if match else default


def is_allowed_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in ALLOWED_SCHEMES and bool(parsed.netloc)


def extract_source_candidates(source_gate_text: str) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    pattern = re.compile(r"^- (q-\d+):\s*(.+)$", re.M)
    for match in pattern.finditer(source_gate_text):
        qid = match.group(1).strip()
        target = match.group(2).strip()
        if target and target != "none":
            candidates.append({"question_id": qid, "target": target})
    return candidates


def extract_active_question_targets(text: str) -> dict[str, str]:
    targets: dict[str, str] = {}
    parts = re.split(r"(?m)^## (q-\d+)\n", text)
    if len(parts) < 3:
        return targets
    for i in range(1, len(parts), 2):
        qid = parts[i].strip()
        target = extract_value(parts[i + 1], "target", "unknown")
        if target != "unknown":
            targets[qid] = target
    return targets


def extract_quality_followup_candidates(learning_quality_text: str, question_targets: dict[str, str]) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    pattern = re.compile(
        r"(?m)^- repeated_question_host:\s+severity=review;\s+target=(q-\d+)@([^;]+);\s+detail=(.+)$"
    )
    for match in pattern.finditer(learning_quality_text):
        qid = match.group(1).strip()
        avoid_host = match.group(2).strip()
        detail = match.group(3).strip()
        count_match = re.search(r"(\d+)/(\d+)", detail)
        needed = 1
        if count_match:
            repeated_count = int(count_match.group(1))
            total_count = int(count_match.group(2))
            needed = 0
            while repeated_count * 3 >= (total_count + needed) * 2:
                needed += 1
            needed = max(1, needed)
        for slot in range(1, needed + 1):
            candidates.append(
                {
                    "question_id": qid,
                    "target": question_targets.get(qid, "general"),
                    "avoid_host": avoid_host,
                    "followup_kind": "source_diversity",
                    "followup_slot": str(slot),
                    "detail": detail,
                }
            )
    return candidates


def split_requests(text: str) -> list[dict[str, str]]:
    parts = re.split(r"(?m)^## (request-\d{4}-\d{2}-\d{2}-\d{3}|request-[\w-]+)\n", text)
    requests: list[dict[str, str]] = []
    if len(parts) < 3:
        return requests
    for i in range(1, len(parts), 2):
        request_id = parts[i].strip()
        body = parts[i + 1]
        qid = extract_value(body, "question_id", "none")
        if request_id == "request-none" or qid == "none":
            continue
        requests.append(
            {
                "request_id": request_id,
                "question_id": qid,
                "target": extract_value(body, "target", "unknown"),
                "query": extract_value(body, "query", "none"),
                "url": extract_value(body, "url", "none"),
                "status": extract_value(body, "status", "hold"),
                "reason": extract_value(body, "reason", "existing request"),
                "followup_kind": extract_value(body, "followup_kind", "none"),
                "avoid_host": extract_value(body, "avoid_host", "none"),
                "followup_slot": extract_value(body, "followup_slot", "1"),
            }
        )
    return requests


def env_url_map() -> dict[str, str]:
    raw = os.environ.get("XINYU_SOURCE_REQUEST_URLS", "").strip()
    if not raw:
        return {}
    mapping: dict[str, str] = {}
    fallback_index = 0
    for item in re.split(r"[;\n]", raw):
        part = item.strip()
        if not part:
            continue
        if "=" in part:
            key, value = part.split("=", 1)
            mapping[key.strip()] = value.strip()
        else:
            fallback_index += 1
            mapping[f"__fallback_{fallback_index}"] = part
    return mapping


def query_for_target(target: str) -> str:
    target = target.strip().lower()
    if target == "human-relationship":
        return "human relationships attachment boundaries closeness distance trust reliable source"
    if target == "memory-emotion":
        return "emotion memory consolidation dreams affective memory reliable source independent review"
    if target == "ai-self-understanding":
        return "large language model memory agents context tool use alignment safety reliable source independent"
    if target == "relationship-meaning":
        return "relationship meaning memory attachment emotional significance reliable source"
    safe = re.sub(r"[^a-zA-Z0-9 _-]+", " ", target).strip() or "general psychology"
    return f"{safe} reliable source"


def resolve_url(candidate: dict[str, str], mapping: dict[str, str], fallback_index: int) -> str:
    qid = candidate["question_id"]
    target = candidate["target"]
    url = mapping.get(qid) or mapping.get(target) or mapping.get(f"__fallback_{fallback_index}") or "none"
    return url if is_allowed_url(url) else "none"


def next_request_id(existing: list[dict[str, str]], date_part: str) -> str:
    numbers: list[int] = []
    for item in existing:
        match = re.match(rf"request-{re.escape(date_part)}-(\d{{3}})$", item["request_id"])
        if match:
            numbers.append(int(match.group(1)))
    return f"request-{date_part}-{max(numbers, default=0) + 1:03d}"


def render_source_requests(planned_at: str, requests: list[dict[str, str]]) -> str:
    blocks: list[str] = []
    for item in requests:
        followup_lines = ""
        if item.get("followup_kind", "none") != "none":
            followup_lines += f"- followup_kind: {item['followup_kind']}\n"
            if item.get("avoid_host", "none") != "none":
                followup_lines += f"- avoid_host: {item['avoid_host']}\n"
            if item.get("followup_slot", "none") != "none":
                followup_lines += f"- followup_slot: {item['followup_slot']}\n"
        blocks.append(
            f"## {item['request_id']}\n"
            f"- question_id: {item['question_id']}\n"
            f"- target: {item['target']}\n"
            f"- query: {item['query']}\n"
            f"- url: {item['url']}\n"
            f"- status: {item['status']}\n"
            f"{followup_lines}"
            "- source_policy: controlled_fetch_only\n"
            f"- planned_at: {planned_at}\n"
            f"- reason: {item['reason']}\n"
        )
    body = "\n".join(blocks) if blocks else (
        "## request-none\n"
        "- question_id: none\n"
        "- target: none\n"
        "- query: none\n"
        "- url: none\n"
        "- status: hold\n"
        "- source_policy: controlled_fetch_only\n"
        "- reason: no outward source request staged yet\n"
    )
    return f"""---
title: Source Requests
memory_type: source_requests
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {planned_at}
last_confirmed_at: {planned_at}
importance_score: 74
impact_score: 72
confidence_score: 90
status: active
tags: [knowledge, outward, requests]
---

# Source Requests

## Current Rule
- Each request is a controlled outward-fetch candidate, not accepted knowledge.
- Requests without explicit allowed URLs stay `pending_url` and cannot be fetched.
- Search/fetch results must still pass source material and learner integration gates.

{body}"""


def render_state(
    planned_at: str,
    mode: str,
    permission: str,
    candidate_count: int,
    planned_count: int,
    ready_count: int,
    pending_url_count: int,
    quality_followup_candidates: int,
    skipped_reason: str,
) -> str:
    return f"""---
title: Source Request Planner State
memory_type: source_request_planner_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {planned_at}
last_confirmed_at: {planned_at}
importance_score: 80
impact_score: 80
confidence_score: 100
status: active
tags: [knowledge, source, request, planner]
---

# Source Request Planner State

## Last Planning
- planned_at: {planned_at}
- mode: {mode}
- permission: {permission}
- source_candidates: {candidate_count}
- planned_requests: {planned_count}
- ready_requests: {ready_count}
- pending_url_requests: {pending_url_count}
- quality_followup_candidates: {quality_followup_candidates}
- skipped_reason: {skipped_reason}

## Boundaries
- The planner converts eligible questions into source requests only.
- It may create `pending_url` requests by itself.
- It may create `ready` requests only when an explicit allowed URL is supplied.
- It does not fetch pages and does not integrate knowledge.
- It does not rewrite self, owner, relationship, or emotion memory.
"""


def run_source_request_planner(
    root: Path,
    planned_at: str | None = None,
    mode: str = "runtime_source_request_planner",
) -> dict[str, object]:
    planned_at = planned_at or datetime.now().astimezone().isoformat()
    integration_gate = read_text(root / "memory/knowledge/source_integration_gate_state.md")
    permission = extract_value(integration_gate, "integration_permission", "hold")
    source_gate = read_text(root / "memory/knowledge/source_gate_state.md")
    candidates = extract_source_candidates(source_gate)
    question_targets = extract_active_question_targets(read_text(root / "memory/context/active_questions.md"))
    quality_followups = (
        extract_quality_followup_candidates(
            read_text(root / "memory/knowledge/learning_quality_state.md"),
            question_targets,
        )
        if not candidates
        else []
    )
    existing = split_requests(read_text(root / "memory/knowledge/source_requests.md"))
    existing_qids = {item["question_id"] for item in existing}
    existing_followups = {
        (item.get("question_id", "none"), item.get("avoid_host", "none"), item.get("followup_slot", "1"))
        for item in existing
        if item.get("followup_kind") == "source_diversity"
    }
    mapping = env_url_map()

    requests = list(existing)
    added = 0
    skipped_reason = "none"
    if permission not in READY_PERMISSIONS:
        skipped_reason = "integration_gate_not_open"
    elif not candidates and not quality_followups:
        skipped_reason = "no_source_candidates"
    else:
        for idx, candidate in enumerate(candidates, 1):
            if candidate["question_id"] in existing_qids:
                continue
            url = resolve_url(candidate, mapping, idx)
            request_id = next_request_id(requests, planned_at[:10])
            status = "ready" if url != "none" else "pending_url"
            requests.append(
                {
                    "request_id": request_id,
                    "question_id": candidate["question_id"],
                    "target": candidate["target"],
                    "query": query_for_target(candidate["target"]),
                    "url": url,
                    "status": status,
                    "reason": "planned from source gate candidate",
                }
            )
            existing_qids.add(candidate["question_id"])
            added += 1
        for idx, candidate in enumerate(quality_followups, len(candidates) + 1):
            followup_key = (candidate["question_id"], candidate["avoid_host"], candidate["followup_slot"])
            if followup_key in existing_followups:
                continue
            url = resolve_url(candidate, mapping, idx)
            request_id = next_request_id(requests, planned_at[:10])
            status = "ready" if url != "none" else "pending_url"
            requests.append(
                {
                    "request_id": request_id,
                    "question_id": candidate["question_id"],
                    "target": candidate["target"],
                    "query": query_for_target(candidate["target"]),
                    "url": url,
                    "status": status,
                    "followup_kind": candidate["followup_kind"],
                    "avoid_host": candidate["avoid_host"],
                    "followup_slot": candidate["followup_slot"],
                    "reason": f"source diversity follow-up for repeated host {candidate['avoid_host']}",
                }
            )
            existing_followups.add(followup_key)
            added += 1
        if added <= 0:
            skipped_reason = "requests_already_planned"

    ready_count = sum(1 for item in requests if item["status"] == "ready")
    pending_url_count = sum(1 for item in requests if item["status"] == "pending_url")
    if permission in READY_PERMISSIONS:
        write_text(root / "memory/knowledge/source_requests.md", render_source_requests(planned_at, requests))
    write_text(
        root / "memory/knowledge/source_request_planner_state.md",
        render_state(
            planned_at,
            mode,
            permission,
            len(candidates),
            added,
            ready_count,
            pending_url_count,
            len(quality_followups),
            skipped_reason,
        ),
    )
    return {
        "planned_at": planned_at,
        "permission": permission,
        "source_candidates": len(candidates),
        "planned_requests": added,
        "ready_requests": ready_count,
        "pending_url_requests": pending_url_count,
        "quality_followup_candidates": len(quality_followups),
        "skipped_reason": skipped_reason,
    }
