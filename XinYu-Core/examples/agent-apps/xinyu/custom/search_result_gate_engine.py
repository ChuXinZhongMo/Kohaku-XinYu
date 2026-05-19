from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from source_request_planner_engine import render_source_requests, split_requests
from source_search_resolver_engine import split_existing_results
from source_protocol_utils import next_dated_id
from xinyu_storage_paths import knowledge_file_path

ACCEPTED_RELIABILITY = {"medium_candidate", "high_candidate"}


def _knowledge(root: Path, filename: str) -> Path:
    return knowledge_file_path(root, filename)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def host_of(url: str) -> str:
    return urlparse(url).netloc.lower() or "unknown"


def next_registry_id(existing_text: str, date_part: str) -> str:
    pattern = re.compile(rf"(?m)^## source-{re.escape(date_part)}-(\d{{3}})$")
    numbers = [int(match.group(1)) for match in pattern.finditer(existing_text)]
    return f"source-{date_part}-{max(numbers, default=0) + 1:03d}"


def next_request_id(existing: list[dict[str, str]], date_part: str) -> str:
    return next_dated_id(existing, id_field="request_id", prefix="request", date_part=date_part)


def append_registry(root: Path, gated_at: str, accepted: list[dict[str, str]]) -> list[str]:
    path = _knowledge(root, "source_registry.md")
    text = read_text(path).rstrip()
    ids: list[str] = []
    if "# Source Registry" not in text:
        text = f"""---
title: Source Registry
memory_type: source_registry
time_scope: long_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {gated_at}
last_confirmed_at: {gated_at}
importance_score: 86
impact_score: 84
confidence_score: 100
status: active
tags: [knowledge, sources, registry]
---

# Source Registry

## Rules
- The registry records candidate source origins and gate decisions.
- Registry entries are not learned claims.
- Identity, owner, relationship, and emotion memory cannot be rewritten from the registry.
""".rstrip()
    for item in accepted:
        if f"- url: {item['url']}" in text:
            continue
        registry_id = next_registry_id(text, gated_at[:10])
        ids.append(registry_id)
        text += (
            f"\n\n## {registry_id}\n"
            f"- request_id: {item['request_id']}\n"
            f"- question_id: {item['question_id']}\n"
            f"- host: {host_of(item['url'])}\n"
            f"- url: {item['url']}\n"
            f"- source_type: {item.get('source_type', 'unknown_source')}\n"
            f"- gate_reliability: {item.get('reliability', 'unknown')}\n"
            "- gate_status: accepted_for_fetch\n"
            f"- gated_at: {gated_at}\n"
        )
    write_text(path, text.rstrip() + "\n")
    return ids


def update_requests_for_accepted(root: Path, gated_at: str, accepted: list[dict[str, str]]) -> int:
    requests = split_requests(read_text(_knowledge(root, "source_requests.md")))
    by_request_id: dict[str, list[dict[str, str]]] = {}
    for item in accepted:
        by_request_id.setdefault(item["request_id"], []).append(item)
    updated = 0
    for request in requests:
        accepted_items = by_request_id.get(request["request_id"], [])
        if not accepted_items or request.get("status") != "pending_url":
            continue
        first = accepted_items[0]
        request["url"] = first["url"]
        request["status"] = "ready"
        request["reason"] = f"accepted by search_result_gate from {first['result_id']}"
        updated += 1
        for extra in accepted_items[1:]:
            request_id = next_request_id(requests, gated_at[:10])
            requests.append(
                {
                    "request_id": request_id,
                    "question_id": request["question_id"],
                    "target": request["target"],
                    "query": request["query"],
                    "url": extra["url"],
                    "status": "ready",
                    "reason": f"accepted by search_result_gate from {extra['result_id']} as additional source",
                }
            )
            updated += 1
    write_text(_knowledge(root, "source_requests.md"), render_source_requests(gated_at, requests))
    return updated


def render_state(gated_at: str, mode: str, candidate_results: int, accepted_results: int, updated_requests: int, skipped_reason: str) -> str:
    return f"""---
title: Search Result Gate State
memory_type: search_result_gate_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {gated_at}
last_confirmed_at: {gated_at}
importance_score: 81
impact_score: 80
confidence_score: 100
status: active
tags: [knowledge, source, search, gate]
---

# Search Result Gate State

## Last Gate
- gated_at: {gated_at}
- mode: {mode}
- candidate_results: {candidate_results}
- accepted_results: {accepted_results}
- updated_requests: {updated_requests}
- skipped_reason: {skipped_reason}

## Boundaries
- The gate may convert a pending request into a ready request.
- It does not fetch the URL and does not learn the source claim.
- It records accepted source origins in the source registry.
- It does not rewrite self, owner, relationship, or emotion memory.
"""


def run_search_result_gate(
    root: Path,
    gated_at: str | None = None,
    mode: str = "runtime_search_result_gate",
) -> dict[str, object]:
    gated_at = gated_at or datetime.now().astimezone().isoformat()
    results = split_existing_results(read_text(_knowledge(root, "source_search_results.md")))
    requests = split_requests(read_text(_knowledge(root, "source_requests.md")))
    pending_request_ids = {
        item["request_id"] for item in requests if item.get("status") == "pending_url"
    }
    candidates = [
        item for item in results
        if item.get("status") == "candidate" and item.get("request_id") in pending_request_ids
    ]
    accepted: list[dict[str, str]] = []
    skipped_reason = "none"
    if not pending_request_ids:
        skipped_reason = "no_pending_url_requests"
    elif not candidates:
        skipped_reason = "no_candidate_results_for_pending_requests"
    else:
        accepted_per_request: dict[str, int] = {}
        for item in candidates:
            if item.get("reliability") not in ACCEPTED_RELIABILITY:
                continue
            request_id = item.get("request_id", "none")
            if request_id == "none":
                continue
            if accepted_per_request.get(request_id, 0) >= 3:
                continue
            accepted.append(item)
            accepted_per_request[request_id] = accepted_per_request.get(request_id, 0) + 1
        if not accepted:
            skipped_reason = "no_accepted_results"
    updated_requests = update_requests_for_accepted(root, gated_at, accepted) if accepted else 0
    registry_ids = append_registry(root, gated_at, accepted) if accepted else []
    write_text(
        _knowledge(root, "search_result_gate_state.md"),
        render_state(gated_at, mode, len(candidates), len(accepted), updated_requests, skipped_reason),
    )
    return {
        "gated_at": gated_at,
        "candidate_results": len(candidates),
        "accepted_results": len(accepted),
        "updated_requests": updated_requests,
        "registry_ids": registry_ids,
        "skipped_reason": skipped_reason,
    }
