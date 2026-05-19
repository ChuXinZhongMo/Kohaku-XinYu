from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from source_protocol_utils import (
    is_allowed_source_url,
    next_dated_id,
    split_search_results,
    split_source_requests,
)
from xinyu_storage_paths import knowledge_file_path

split_requests = split_source_requests


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _knowledge(root: Path, filename: str) -> Path:
    return knowledge_file_path(root, filename)


def is_allowed_url(url: str) -> bool:
    return is_allowed_source_url(url)


def source_type_for_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.endswith(".gov") or host.endswith(".edu"):
        return "public_institutional_source"
    if "wikipedia.org" in host:
        return "public_reference_source"
    return "public_web_source" if host else "unknown_source"


def candidate_reliability(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.endswith(".gov") or host.endswith(".edu"):
        return "high_candidate"
    if host:
        return "medium_candidate"
    return "unknown"


def env_result_map() -> dict[str, list[dict[str, str]]]:
    raw = os.environ.get("XINYU_SOURCE_SEARCH_RESULTS", "").strip()
    if not raw:
        return {}
    mapping: dict[str, list[dict[str, str]]] = {}
    fallback_index = 0
    for item in re.split(r"[;\n]", raw):
        part = item.strip()
        if not part:
            continue
        key = ""
        rest = part
        if "=" in part:
            key, rest = part.split("=", 1)
            key = key.strip()
        else:
            fallback_index += 1
            key = f"__fallback_{fallback_index}"
        pieces = [piece.strip() for piece in rest.split("|", 2)]
        url = pieces[0] if pieces else "none"
        title = pieces[1] if len(pieces) > 1 else "provided search result"
        snippet = pieces[2] if len(pieces) > 2 else "provided by controlled search result input"
        if not is_allowed_url(url):
            continue
        mapping.setdefault(key, []).append({"url": url, "title": title, "snippet": snippet})
    return mapping


def choose_results(request: dict[str, str], mapping: dict[str, list[dict[str, str]]], fallback_index: int) -> list[dict[str, str]]:
    keys = [request["request_id"], request["question_id"], request["target"], f"__fallback_{fallback_index}"]
    for key in keys:
        items = mapping.get(key)
        if items:
            return items[:3]
    return []


def split_existing_results(text: str) -> list[dict[str, str]]:
    return split_search_results(text)


def next_result_id(existing: list[dict[str, str]], date_part: str) -> str:
    return next_dated_id(existing, id_field="result_id", prefix="result", date_part=date_part)


def render_results(resolved_at: str, results: list[dict[str, str]]) -> str:
    blocks: list[str] = []
    for item in results:
        blocks.append(
            f"## {item['result_id']}\n"
            f"- request_id: {item['request_id']}\n"
            f"- question_id: {item['question_id']}\n"
            f"- target: {item['target']}\n"
            f"- query: {item['query']}\n"
            f"- url: {item['url']}\n"
            f"- title: {item['title']}\n"
            f"- snippet: {item['snippet']}\n"
            f"- source_type: {item['source_type']}\n"
            f"- reliability: {item['reliability']}\n"
            "- status: candidate\n"
            f"- resolved_at: {resolved_at}\n"
        )
    body = "\n".join(blocks) if blocks else (
        "## result-none\n"
        "- request_id: none\n"
        "- question_id: none\n"
        "- url: none\n"
        "- status: hold\n"
    )
    return f"""---
title: Source Search Results
memory_type: source_search_results
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {resolved_at}
last_confirmed_at: {resolved_at}
importance_score: 74
impact_score: 72
confidence_score: 90
status: active
tags: [knowledge, source, search, results]
---

# Source Search Results

## Current Rule
- Search results are candidate URLs only.
- A candidate URL must pass `search_result_gate` before becoming a ready source request.
- Search snippets are never accepted as learned knowledge.

{body}"""


def render_state(resolved_at: str, mode: str, pending_requests: int, resolved_results: int, skipped_reason: str) -> str:
    return f"""---
title: Source Search Resolver State
memory_type: source_search_resolver_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {resolved_at}
last_confirmed_at: {resolved_at}
importance_score: 80
impact_score: 80
confidence_score: 100
status: active
tags: [knowledge, source, search, resolver]
---

# Source Search Resolver State

## Last Resolution
- resolved_at: {resolved_at}
- mode: {mode}
- pending_requests: {pending_requests}
- resolved_results: {resolved_results}
- skipped_reason: {skipped_reason}

## Boundaries
- The resolver converts `pending_url` requests into candidate URLs only.
- It currently uses controlled provided search results, not broad autonomous web search.
- It does not fetch pages, integrate knowledge, or rewrite self/relationship/emotion memory.
"""


def run_source_search_resolver(
    root: Path,
    resolved_at: str | None = None,
    mode: str = "runtime_source_search_resolver",
) -> dict[str, object]:
    resolved_at = resolved_at or datetime.now().astimezone().isoformat()
    requests = split_requests(read_text(_knowledge(root, "source_requests.md")))
    pending = [item for item in requests if item.get("status") == "pending_url"]
    existing_results = split_existing_results(read_text(_knowledge(root, "source_search_results.md")))
    existing_keys = {(item.get("request_id"), item.get("url")) for item in existing_results}
    mapping = env_result_map()

    results = list(existing_results)
    added = 0
    skipped_reason = "none"
    if not pending:
        skipped_reason = "no_pending_url_requests"
    elif not mapping:
        skipped_reason = "no_controlled_search_results"
    else:
        for idx, request in enumerate(pending, 1):
            for result in choose_results(request, mapping, idx):
                key = (request["request_id"], result["url"])
                if key in existing_keys:
                    continue
                result_id = next_result_id(results, resolved_at[:10])
                results.append(
                    {
                        "result_id": result_id,
                        "request_id": request["request_id"],
                        "question_id": request["question_id"],
                        "target": request["target"],
                        "query": request["query"],
                        "url": result["url"],
                        "title": result["title"],
                        "snippet": result["snippet"],
                        "source_type": source_type_for_url(result["url"]),
                        "reliability": candidate_reliability(result["url"]),
                    }
                )
                existing_keys.add(key)
                added += 1
        if added <= 0:
            skipped_reason = "results_already_resolved"

    write_text(_knowledge(root, "source_search_results.md"), render_results(resolved_at, results))
    write_text(
        _knowledge(root, "source_search_resolver_state.md"),
        render_state(resolved_at, mode, len(pending), added, skipped_reason),
    )
    return {
        "resolved_at": resolved_at,
        "pending_requests": len(pending),
        "resolved_results": added,
        "total_results": len(results),
        "skipped_reason": skipped_reason,
    }
