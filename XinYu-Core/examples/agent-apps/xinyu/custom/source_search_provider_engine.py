from __future__ import annotations

import html
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse

import httpx

from source_protocol_utils import extract_dash_value
from source_request_planner_engine import split_requests
from source_search_resolver_engine import (
    candidate_reliability,
    is_allowed_url,
    next_result_id,
    render_results,
    source_type_for_url,
    split_existing_results,
)
from xinyu_storage_paths import knowledge_file_path

SUPPORTED_PROVIDERS = {"duckduckgo_html"}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _knowledge(root: Path, filename: str) -> Path:
    return knowledge_file_path(root, filename)


def extract_value(text: str, field: str, default: str = "unknown") -> str:
    return extract_dash_value(text, field, default)


def activation_gate(root: Path) -> tuple[bool, int, str]:
    try:
        text = read_text(_knowledge(root, "autonomous_search_activation_state.md"))
    except FileNotFoundError:
        return False, 0, "activation_state_missing"
    permission = extract_value(text, "activation_permission", "blocked")
    reason = extract_value(text, "activation_reason", "unknown")
    allowed_raw = extract_value(text, "allowed_queries", "0")
    try:
        allowed_queries = max(0, int(allowed_raw))
    except ValueError:
        allowed_queries = 0
    if permission != "provider_allowed":
        return False, 0, f"activation_not_allowed:{reason}"
    if allowed_queries <= 0:
        return False, 0, "activation_allowed_zero_queries"
    return True, allowed_queries, "activation_allowed"


def provider_name(root: Path | None = None) -> str:
    raw = os.environ.get("XINYU_SOURCE_SEARCH_PROVIDER")
    if raw is not None and raw.strip():
        return raw.strip().lower()
    if root is not None:
        try:
            capability = read_text(root / "memory/context/capability_zones_state.md")
            grants = read_text(root / "memory/context/owner_permission_grants.md")
        except OSError:
            capability = ""
            grants = ""
        if (
            "autonomous_search_provider: enabled_duckduckgo_html_bounded_ai_domain" in capability
            and "grant_autonomous_source_collect: approved_bounded_candidate_material_only" in grants
        ):
            return "duckduckgo_html"
    return "disabled"


def provider_endpoint(provider: str) -> str:
    if provider == "duckduckgo_html":
        return os.environ.get("XINYU_DUCKDUCKGO_HTML_ENDPOINT", "https://duckduckgo.com/html/").strip()
    return ""


def clean_html_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def decode_ddg_url(raw_url: str, base_url: str) -> str:
    url = html.unescape(raw_url).strip()
    if url.startswith("//"):
        url = "https:" + url
    elif url.startswith("/"):
        url = urljoin(base_url, url)
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if "uddg" in query and query["uddg"]:
        return unquote(query["uddg"][0])
    return url


def parse_duckduckgo_html(raw_html: str, base_url: str) -> list[dict[str, str]]:
    anchor_pattern = re.compile(
        r'<a[^>]+class=["\'][^"\']*result__a[^"\']*["\'][^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        re.I | re.S,
    )
    snippets = [clean_html_text(match.group(1)) for match in re.finditer(r'<a[^>]+class=["\'][^"\']*result__snippet[^"\']*["\'][^>]*>(.*?)</a>', raw_html, re.I | re.S)]
    if not snippets:
        snippets = [clean_html_text(match.group(1)) for match in re.finditer(r'<div[^>]+class=["\'][^"\']*result__snippet[^"\']*["\'][^>]*>(.*?)</div>', raw_html, re.I | re.S)]
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for idx, match in enumerate(anchor_pattern.finditer(raw_html)):
        url = decode_ddg_url(match.group(1), base_url)
        if not is_allowed_url(url) or url in seen:
            continue
        seen.add(url)
        title = clean_html_text(match.group(2)) or "search result"
        snippet = snippets[idx] if idx < len(snippets) and snippets[idx] else "search provider result"
        results.append({"url": url, "title": title, "snippet": snippet})
        if len(results) >= 3:
            break
    return results


def fetch_duckduckgo_html(query: str, endpoint: str, timeout: float = 12.0) -> list[dict[str, str]]:
    if not endpoint:
        return []
    headers = {"User-Agent": "XinyuSourceSearchProvider/0.1"}
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        if "?" in endpoint:
            url = endpoint + "&q=" + quote_plus(query)
            response = client.get(url)
        else:
            response = client.get(endpoint, params={"q": query})
    response.raise_for_status()
    return parse_duckduckgo_html(response.text, str(response.url))


def provider_search(provider: str, query: str) -> list[dict[str, str]]:
    if provider == "duckduckgo_html":
        return fetch_duckduckgo_html(query, provider_endpoint(provider))
    return []


def render_state(
    searched_at: str,
    mode: str,
    provider: str,
    pending_requests: int,
    provider_results: int,
    skipped_reason: str,
) -> str:
    return f"""---
title: Source Search Provider State
memory_type: source_search_provider_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {searched_at}
last_confirmed_at: {searched_at}
importance_score: 80
impact_score: 80
confidence_score: 100
status: active
tags: [knowledge, source, search, provider]
---

# Source Search Provider State

## Last Provider Search
- searched_at: {searched_at}
- mode: {mode}
- provider: {provider}
- pending_requests: {pending_requests}
- provider_results: {provider_results}
- skipped_reason: {skipped_reason}

## Boundaries
- The provider adapter returns candidate URLs only.
- Provider snippets are never learned as knowledge.
- Candidate URLs must pass `search_result_gate` before fetch.
- The provider does not fetch source pages and does not rewrite self/relationship/emotion memory.
"""


def run_source_search_provider(
    root: Path,
    searched_at: str | None = None,
    mode: str = "runtime_source_search_provider",
    require_activation: bool = False,
) -> dict[str, object]:
    searched_at = searched_at or datetime.now().astimezone().isoformat()
    provider = provider_name(root)
    requests = split_requests(read_text(_knowledge(root, "source_requests.md")))
    pending = [item for item in requests if item.get("status") == "pending_url"]
    existing_results = split_existing_results(read_text(_knowledge(root, "source_search_results.md")))
    existing_keys = {(item.get("request_id"), item.get("url")) for item in existing_results}

    results = list(existing_results)
    added = 0
    skipped_reason = "none"
    if require_activation:
        allowed, allowed_queries, activation_reason = activation_gate(root)
        if not allowed:
            skipped_reason = activation_reason
        else:
            pending = pending[:allowed_queries]
    if skipped_reason != "none":
        pass
    elif provider not in SUPPORTED_PROVIDERS:
        skipped_reason = "provider_disabled_or_unsupported"
    elif not pending:
        skipped_reason = "no_pending_url_requests"
    else:
        for request in pending:
            try:
                provider_items = provider_search(provider, request.get("query", ""))
            except Exception:
                provider_items = []
            for item in provider_items[:3]:
                key = (request["request_id"], item["url"])
                if key in existing_keys:
                    continue
                result_id = next_result_id(results, searched_at[:10])
                results.append(
                    {
                        "result_id": result_id,
                        "request_id": request["request_id"],
                        "question_id": request["question_id"],
                        "target": request["target"],
                        "query": request["query"],
                        "url": item["url"],
                        "title": item["title"],
                        "snippet": item["snippet"],
                        "source_type": source_type_for_url(item["url"]),
                        "reliability": candidate_reliability(item["url"]),
                    }
                )
                existing_keys.add(key)
                added += 1
        if added <= 0:
            skipped_reason = "no_provider_results"

    write_text(_knowledge(root, "source_search_results.md"), render_results(searched_at, results))
    write_text(
        _knowledge(root, "source_search_provider_state.md"),
        render_state(searched_at, mode, provider, len(pending), added, skipped_reason),
    )
    return {
        "searched_at": searched_at,
        "provider": provider,
        "pending_requests": len(pending),
        "provider_results": added,
        "total_results": len(results),
        "skipped_reason": skipped_reason,
    }
