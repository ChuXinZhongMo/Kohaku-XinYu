from __future__ import annotations

import os
import re
import html as html_lib
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import html2text
import httpx

ALLOWED_SCHEMES = {"http", "https"}
READY_PERMISSIONS = {"prepare_only", "integrate_ready"}
DEFAULT_MAX_FETCH_URLS = 6


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def extract_value(text: str, field: str, default: str = "unknown") -> str:
    pattern = re.compile(rf"^- {re.escape(field)}:\s*(.+)$", re.M)
    match = pattern.search(text)
    return match.group(1).strip() if match else default


def extract_source_candidates(source_gate_text: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    pattern = re.compile(r"^- (q-\d+):\s*(.+)$", re.M)
    for match in pattern.finditer(source_gate_text):
        pairs.append((match.group(1), match.group(2).strip()))
    return pairs


def extract_request_urls(request_text: str, *, ai_only: bool = False) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    parts = re.split(r"(?m)^## (request-\d{4}-\d{2}-\d{2}-\d{3}|request-[\w-]+)\n", request_text)
    if len(parts) < 3:
        return results
    for i in range(1, len(parts), 2):
        body = parts[i + 1]
        qid = extract_value(body, "question_id", "none")
        target = extract_value(body, "target", "unknown")
        url = extract_value(body, "url", "none")
        status = extract_value(body, "status", "hold")
        if ai_only and target != "ai-self-understanding":
            continue
        if status == "ready" and url not in {"", "none"}:
            results.append((qid, url))
    return results


def env_urls() -> list[tuple[str, str]]:
    raw = os.environ.get("XINYU_OUTWARD_SOURCE_URLS", "").strip()
    if not raw:
        return []
    return [("none", item.strip()) for item in re.split(r"[;\n]", raw) if item.strip()]


def existing_material_urls(root: Path) -> set[str]:
    try:
        text = read_text(root / "memory/knowledge/source_materials.md")
    except FileNotFoundError:
        return set()
    return set(re.findall(r"(?m)^- url:\s*(\S+)\s*$", text))


def prioritize_unstaged_urls(root: Path, request_pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    existing_urls = existing_material_urls(root)
    unseen = [(qid, url) for qid, url in request_pairs if url not in existing_urls]
    seen = [(qid, url) for qid, url in request_pairs if url in existing_urls]
    return unseen + seen


def max_fetch_urls() -> int:
    raw = os.environ.get("XINYU_OUTWARD_SOURCE_MAX_FETCH", "").strip()
    if not raw:
        return DEFAULT_MAX_FETCH_URLS
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_MAX_FETCH_URLS


def is_allowed_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in ALLOWED_SCHEMES and bool(parsed.netloc)


def clean_text(raw: str, content_type: str) -> str:
    if "html" in content_type.lower() or "<html" in raw[:500].lower():
        converter = html2text.HTML2Text()
        converter.ignore_links = False
        converter.ignore_images = True
        converter.body_width = 0
        text = converter.handle(raw)
    else:
        text = raw
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_html_fragment(raw: str) -> str:
    text = re.sub(r"<script\b.*?</script>", " ", raw, flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    text = re.sub(r"\[[^\]]{1,20}\]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _first_html_match(raw: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.I | re.S)
        if match:
            value = clean_html_fragment(match.group(1))
            if value:
                return value
    return ""


def extract_html_claim(raw: str, fallback_text: str) -> str:
    title = _first_html_match(
        raw,
        [
            r'<meta[^>]+name=["\']citation_title["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
            r"<h1[^>]*>(.*?)</h1>",
        ],
    )
    abstract = _first_html_match(
        raw,
        [
            r'<meta[^>]+name=["\']citation_abstract["\'][^>]+content=["\']([^"\']+)["\']',
            r'<section[^>]+class=["\'][^"\']*abstract[^"\']*["\'][^>]*>(.*?)</section>',
            r'<div[^>]+class=["\'][^"\']*abstract[^"\']*["\'][^>]*>(.*?)</div>',
            r'<section[^>]+id=["\']abstract["\'][^>]*>(.*?)</section>',
        ],
    )
    abstract = re.sub(r"^Abstract\s+", "", abstract, flags=re.I).strip()
    description = _first_html_match(
        raw,
        [
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+name=["\']twitter:description["\'][^>]+content=["\']([^"\']+)["\']',
        ],
    )

    parts = [part for part in [title, abstract or description] if part]
    if parts:
        return " ".join(parts)[:620].replace("|", "/")
    return fallback_text[:420].replace("|", "/") if fallback_text else "no readable text extracted"


def extract_claim(raw: str, content_type: str, cleaned_text: str) -> str:
    if "html" in content_type.lower() or "<html" in raw[:500].lower():
        return extract_html_claim(raw, cleaned_text)
    return cleaned_text[:420].replace("|", "/") if cleaned_text else "no readable text extracted"


def classify_source_type(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.endswith(".gov") or host.endswith(".edu"):
        return "public_institutional_source"
    if "wikipedia.org" in host:
        return "public_reference_source"
    if host:
        return "public_web_source"
    return "unknown_source"


def classify_reliability(url: str, status_code: int, text: str) -> str:
    host = urlparse(url).netloc.lower()
    if status_code >= 400 or len(text) < 80:
        return "unknown"
    if host.endswith(".gov") or host.endswith(".edu"):
        return "high_ready"
    return "medium_ready"


def next_material_id(existing_text: str, date_part: str) -> str:
    pattern = re.compile(rf"(?m)^## material-{re.escape(date_part)}-(\d{{3}})$")
    numbers = [int(match.group(1)) for match in pattern.finditer(existing_text)]
    return f"material-{date_part}-{max(numbers, default=0) + 1:03d}"


def append_source_materials(root: Path, fetched_at: str, staged: list[dict[str, str]]) -> list[str]:
    path = root / "memory/knowledge/source_materials.md"
    text = read_text(path).rstrip()
    material_ids: list[str] = []
    for item in staged:
        if f"- url: {item['url']}" in text:
            continue
        material_id = next_material_id(text, fetched_at[:10])
        material_ids.append(material_id)
        addition = (
            f"\n\n## {material_id}\n"
            f"- question_id: {item['question_id']}\n"
            f"- url: {item['url']}\n"
            f"- source_type: {item['source_type']}\n"
            f"- reliability: {item['reliability']}\n"
            "- integration_scope: knowledge_only\n"
            f"- status: {'ready' if item['reliability'] in {'medium_ready', 'high_ready'} else 'hold'}\n"
            f"- fetched_at: {fetched_at}\n"
            f"- claim: {item['claim']}\n"
        )
        text += addition
    write_text(path, text.rstrip() + "\n")
    return material_ids


def fetch_url(url: str, timeout: float = 12.0) -> dict[str, str]:
    if not is_allowed_url(url):
        return {
            "url": url,
            "status": "blocked",
            "status_code": "0",
            "text": "",
            "claim": "blocked URL scheme or missing host",
            "source_type": "unknown_source",
            "reliability": "unknown",
        }
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent": "XinyuSourceFetcher/0.1"}) as client:
            response = client.get(url)
        content_type = response.headers.get("content-type", "")
        text = clean_text(response.text, content_type)
        claim = extract_claim(response.text, content_type, text)
        reliability = classify_reliability(str(response.url), response.status_code, text)
        return {
            "url": str(response.url),
            "status": "fetched",
            "status_code": str(response.status_code),
            "text": text,
            "claim": claim,
            "source_type": classify_source_type(str(response.url)),
            "reliability": reliability,
        }
    except Exception as exc:
        return {
            "url": url,
            "status": "error",
            "status_code": "0",
            "text": "",
            "claim": f"fetch error: {type(exc).__name__}",
            "source_type": "unknown_source",
            "reliability": "unknown",
        }


def render_state(
    fetched_at: str,
    mode: str,
    permission: str,
    fetched: list[dict[str, str]],
    material_ids: list[str],
    skipped_reason: str,
) -> str:
    fetched_block = "\n".join(
        f"- {item['url']} -> {item['status']} / {item['reliability']}" for item in fetched
    ) or "- none"
    material_block = "\n".join(f"- {item}" for item in material_ids) or "- none"
    return f"""---
title: Outward Source State
memory_type: outward_source_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {fetched_at}
last_confirmed_at: {fetched_at}
importance_score: 80
impact_score: 80
confidence_score: 100
status: active
tags: [knowledge, outward, source, state]
---

# Outward Source State

## Last Fetch
- fetched_at: {fetched_at}
- mode: {mode}
- permission: {permission}
- fetched_sources: {len(fetched)}
- staged_materials: {len(material_ids)}
- skipped_reason: {skipped_reason}

## Fetched Sources
{fetched_block}

## Staged Material Ids
{material_block}

## Boundaries
- Outward source fetch stages source material only.
- It does not write knowledge/general directly.
- It does not rewrite self, owner, relationship, emotion, dream, or archive layers.
"""


def run_outward_source(
    root: Path,
    fetched_at: str | None = None,
    mode: str = "runtime_outward_source",
    urls: list[str] | None = None,
) -> dict[str, object]:
    fetched_at = fetched_at or datetime.now().astimezone().isoformat()
    integration_gate = read_text(root / "memory/knowledge/source_integration_gate_state.md")
    permission = extract_value(integration_gate, "integration_permission", "hold")
    gate_reason = extract_value(integration_gate, "gate_reason", "unknown")
    ai_only = gate_reason == "owner_approved_ai_ready_followthrough"
    source_gate = read_text(root / "memory/knowledge/source_gate_state.md")
    candidates = extract_source_candidates(source_gate)
    default_qid = candidates[0][0] if candidates else "none"

    request_pairs = [(default_qid, url) for url in (urls or [])]
    if not request_pairs:
        request_pairs = extract_request_urls(read_text(root / "memory/knowledge/source_requests.md"), ai_only=ai_only)
    if not request_pairs:
        request_pairs = env_urls()
    request_pairs = [(qid if qid != "none" else default_qid, url) for qid, url in request_pairs]
    request_pairs = prioritize_unstaged_urls(root, request_pairs)

    fetched: list[dict[str, str]] = []
    staged: list[dict[str, str]] = []
    material_ids: list[str] = []
    skipped_reason = "none"

    if permission not in READY_PERMISSIONS:
        skipped_reason = "integration_gate_not_open"
    elif not request_pairs:
        skipped_reason = "no_source_urls"
    else:
        for qid, url in request_pairs[:max_fetch_urls()]:
            result = fetch_url(url)
            fetched.append(result)
            if result["status"] == "fetched" and result["reliability"] in {"medium_ready", "high_ready"}:
                staged.append({
                    "question_id": qid,
                    "url": result["url"],
                    "source_type": result["source_type"],
                    "reliability": result["reliability"],
                    "claim": result["claim"],
                })
        if staged:
            material_ids = append_source_materials(root, fetched_at, staged)
        elif fetched:
            skipped_reason = "no_reliable_fetches"

    write_text(
        root / "memory/knowledge/outward_source_state.md",
        render_state(fetched_at, mode, permission, fetched, material_ids, skipped_reason),
    )
    return {
        "fetched_at": fetched_at,
        "permission": permission,
        "fetched_sources": len(fetched),
        "staged_materials": len(material_ids),
        "material_ids": material_ids,
        "skipped_reason": skipped_reason,
    }
