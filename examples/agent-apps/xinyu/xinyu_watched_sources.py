from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx


WATCH_CONFIG_REL = Path("memory/context/watch_sources.md")
STATE_REL = Path("memory/context/watched_source_state.md")
TRACE_REL = Path("runtime/watched_source_trace.jsonl")

ALLOWED_SCHEMES = {"http", "https"}
DEFAULT_CADENCE_SECONDS = 1800
DEFAULT_MAX_ITEMS = 8
DEFAULT_TIMEOUT_SECONDS = 12.0

AI_TOPIC_KEYWORDS = (
    "ai",
    "aigc",
    "llm",
    "gpt",
    "chatgpt",
    "openai",
    "codex",
    "claude",
    "gemini",
    "copilot",
    "cursor",
    "deepseek",
    "qwen",
    "kimi",
    "llama",
    "ollama",
    "mcp",
    "api",
    "prompt",
    "token",
    "agent",
    "agents",
    "rag",
    "tool use",
    "tool-use",
    "人工智能",
    "大模型",
    "模型",
    "智能体",
    "agentic",
    "提示词",
    "上下文",
    "推理",
    "多模态",
    "向量",
    "嵌入",
    "工具调用",
)

_FIELD_RE = re.compile(r"(?m)^\s*-\s*([A-Za-z0-9_]+):\s*(.*?)\s*$")
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bauthorization\s*:\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bapi[_-]?key\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\btoken\s*[:=]\s*[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bsk-[a-z0-9_-]{12,}"),
)


def run_watched_source_check(
    root: Path,
    *,
    checked_at: str | None = None,
    force: bool = False,
    min_interval_seconds: int | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    root = root.resolve()
    checked_at = checked_at or _now_iso()
    sources = _load_sources(root)
    if not sources:
        result = _result(
            checked_at=checked_at,
            status="no_sources",
            notes=["watch_sources_config_missing_or_empty"],
        )
        _append_trace(root, result)
        return result

    source = sources[0]
    cadence = _source_int(source, "cadence_seconds", DEFAULT_CADENCE_SECONDS)
    if min_interval_seconds is not None:
        cadence = max(cadence, int(min_interval_seconds))
    previous_state = _read(root / STATE_REL)
    if not force and _same_source(previous_state, source):
        age = _seconds_between(checked_at, _extract_value(previous_state, "checked_at", ""))
        if age is not None and age < cadence:
            result = _result(
                checked_at=checked_at,
                status="skipped_cooldown",
                source=source,
                feed_url=_feed_url_for(source),
                scanned_items=_extract_int(previous_state, "scanned_items", 0),
                matched_items=_extract_int(previous_state, "matched_items", 0),
                ignored_items=_extract_int(previous_state, "ignored_items", 0),
                fetched_items=_extract_int(previous_state, "fetched_items", 0),
                new_items=0,
                latest_title=_extract_value(previous_state, "latest_title", "none"),
                latest_url=_extract_value(previous_state, "latest_url", "none"),
                notes=[f"cooldown_active:{int(age)}/{cadence}"],
            )
            _append_trace(root, result)
            return result

    feed_url = _feed_url_for(source)
    fetch = _fetch_feed_or_page(source, feed_url=feed_url, timeout_seconds=timeout_seconds)
    previous_keys = set(re.findall(r"(?m)^\s*-\s*item_key:\s*(\S+)\s*$", previous_state))
    scanned_items = fetch["items"]
    matched_items, ignored_items = _filter_items(source, scanned_items)
    items = matched_items[: _source_int(source, "max_items", DEFAULT_MAX_ITEMS)]
    new_items = sum(1 for item in items if item["item_key"] not in previous_keys)
    latest = items[0] if items else {}
    status = "fetched" if fetch["ok"] else "error"
    if fetch["ok"] and not scanned_items:
        status = "empty"
    elif fetch["ok"] and scanned_items and not items:
        status = "no_relevant_items"
    result = _result(
        checked_at=checked_at,
        status=status,
        source=source,
        feed_url=feed_url,
        fetch_url=fetch["fetch_url"],
        fetch_status_code=fetch["status_code"],
        scanned_items=len(scanned_items),
        matched_items=len(matched_items),
        ignored_items=ignored_items,
        fetched_items=len(items),
        new_items=new_items,
        latest_title=latest.get("title", "none"),
        latest_url=latest.get("url", "none"),
        items=items,
        notes=fetch["notes"],
    )
    _write(root / STATE_REL, _render_state(result))
    _append_trace(root, result)
    return result


def _load_sources(root: Path) -> list[dict[str, str]]:
    text = _read(root / WATCH_CONFIG_REL)
    if not text:
        return []
    parts = re.split(r"(?m)^##\s+([A-Za-z0-9_-]+)\s*$", text)
    sources: list[dict[str, str]] = []
    for index in range(1, len(parts), 2):
        source_id = _clean_token(parts[index])
        body = parts[index + 1]
        fields = {"source_id": source_id}
        for match in _FIELD_RE.finditer(body):
            fields[match.group(1)] = _one_line(match.group(2), limit=500)
        if fields.get("enabled", "true").lower() not in {"true", "yes", "1", "enabled"}:
            continue
        url = fields.get("url", "")
        if not _allowed_public_url(url):
            continue
        fields["url"] = url
        fields.setdefault("read_only", "true")
        fields.setdefault("no_posting", "true")
        fields.setdefault("site_policy", "read_only_no_posting")
        fields.setdefault("ignore_non_matching", "false")
        sources.append(fields)
    return sources


def _feed_url_for(source: dict[str, str]) -> str:
    explicit = source.get("feed_url") or source.get("rss_url") or ""
    if explicit and _allowed_public_url(explicit):
        return explicit
    url = source.get("url", "")
    parsed = urlparse(url)
    if parsed.path.rstrip("/").endswith("/latest"):
        return url.rstrip("/") + ".rss"
    return url


def _fetch_feed_or_page(source: dict[str, str], *, feed_url: str, timeout_seconds: float) -> dict[str, Any]:
    fetch_url = feed_url
    first = _fetch_text(fetch_url, timeout_seconds=timeout_seconds)
    items: list[dict[str, str]] = []
    notes = list(first["notes"])
    if first["ok"]:
        items = _parse_rss_items(first["text"], str(first["final_url"]))
        if not items:
            items = _parse_html_items(first["text"], str(first["final_url"]))
    if not first["ok"] or not items:
        source_url = source.get("url", "")
        if source_url and source_url != fetch_url:
            second = _fetch_text(source_url, timeout_seconds=timeout_seconds)
            notes.extend(second["notes"])
            if second["ok"]:
                html_items = _parse_html_items(second["text"], str(second["final_url"]))
                if html_items:
                    first = second
                    fetch_url = source_url
                    items = html_items
    return {
        "ok": bool(first["ok"]),
        "fetch_url": fetch_url,
        "status_code": first["status_code"],
        "items": items,
        "notes": sorted(set(_clean_note(note) for note in notes if _clean_note(note))),
    }


def _fetch_text(url: str, *, timeout_seconds: float) -> dict[str, Any]:
    if not _allowed_public_url(url):
        return {
            "ok": False,
            "final_url": url,
            "status_code": 0,
            "text": "",
            "notes": ["url_blocked"],
        }
    headers = {
        "User-Agent": "XinyuWatchedSource/0.1 read-only",
        "Accept": "application/rss+xml, application/xml, text/html;q=0.9, */*;q=0.8",
    }
    try:
        with httpx.Client(timeout=timeout_seconds, follow_redirects=True, headers=headers) as client:
            response = client.get(url)
        ok = 200 <= response.status_code < 400
        return {
            "ok": ok,
            "final_url": str(response.url),
            "status_code": response.status_code,
            "text": response.text,
            "notes": [f"fetch_status:{response.status_code}"],
        }
    except Exception as exc:
        return {
            "ok": False,
            "final_url": url,
            "status_code": 0,
            "text": "",
            "notes": [f"fetch_error:{type(exc).__name__}"],
        }


def _parse_rss_items(raw: str, base_url: str) -> list[dict[str, str]]:
    try:
        document = ET.fromstring(raw)
    except ET.ParseError:
        return []
    items: list[dict[str, str]] = []
    for node in document.findall(".//channel/item"):
        title = _one_line(_xml_text(node, "title"), limit=180)
        link = _one_line(_xml_text(node, "link"), limit=500)
        if link:
            link = urljoin(base_url, link)
        if not title or not _allowed_public_url(link):
            continue
        summary = _strip_html(_xml_text(node, "description"), limit=260)
        category = _one_line(_xml_text(node, "category"), limit=80, default="none")
        published = _normalize_date(_xml_text(node, "pubDate"))
        items.append(_item(title=title, url=link, category=category, published_at=published, summary=summary))
    return _dedupe_items(items)


def _parse_html_items(raw: str, base_url: str) -> list[dict[str, str]]:
    anchors = re.finditer(
        r"<a\b[^>]+href=[\"']([^\"']*/t/[^\"']+)[\"'][^>]*>(.*?)</a>",
        raw,
        flags=re.I | re.S,
    )
    items: list[dict[str, str]] = []
    for match in anchors:
        url = urljoin(base_url, html.unescape(match.group(1)))
        title = _strip_html(match.group(2), limit=180)
        if not title or not _allowed_public_url(url):
            continue
        items.append(_item(title=title, url=url, category="none", published_at="unknown", summary="html topic link"))
        if len(items) >= DEFAULT_MAX_ITEMS:
            break
    return _dedupe_items(items)


def _item(*, title: str, url: str, category: str, published_at: str, summary: str) -> dict[str, str]:
    key = hashlib.sha256(f"{url}|{title}".encode("utf-8", errors="replace")).hexdigest()[:16]
    return {
        "item_key": key,
        "title": _one_line(title, limit=180),
        "url": _one_line(url, limit=500),
        "category": _one_line(category, limit=80, default="none"),
        "published_at": _one_line(published_at, limit=80, default="unknown"),
        "summary": _one_line(summary, limit=260, default="none"),
    }


def _dedupe_items(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    deduped: list[dict[str, str]] = []
    for item in items:
        key = item["item_key"]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _filter_items(source: dict[str, str], items: list[dict[str, str]]) -> tuple[list[dict[str, str]], int]:
    keywords = _relevance_keywords(source)
    filter_enabled = (
        bool(keywords)
        or source.get("topic_filter", "none").lower() in {"ai", "llm", "ai_related"}
        or source.get("ignore_non_matching", "false").lower() in {"1", "true", "yes", "enabled"}
    )
    if not filter_enabled:
        return list(items), 0
    matched: list[dict[str, str]] = []
    for item in items:
        haystack = " ".join(
            [
                str(item.get("title", "")),
                str(item.get("category", "")),
                str(item.get("summary", "")),
            ]
        ).lower()
        if any(_keyword_in_text(keyword, haystack) for keyword in keywords):
            matched.append(item)
    return matched, max(0, len(items) - len(matched))


def _relevance_keywords(source: dict[str, str]) -> tuple[str, ...]:
    keywords: list[str] = []
    if source.get("topic_filter", "none").lower() in {"ai", "llm", "ai_related"}:
        keywords.extend(AI_TOPIC_KEYWORDS)
    for key in ("include_keywords", "ai_filter_keywords", "relevance_keywords"):
        keywords.extend(_source_list(source.get(key, "")))
    clean: list[str] = []
    seen: set[str] = set()
    for item in keywords:
        keyword = item.strip().lower()
        if keyword and keyword not in seen:
            seen.add(keyword)
            clean.append(keyword)
    return tuple(clean)


def _source_list(value: str) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in re.split(r"[|,;，；、]+", value) if part.strip()]


def _keyword_in_text(keyword: str, text: str) -> bool:
    if not keyword:
        return False
    if keyword.isascii() and keyword.replace("_", "").isalnum() and len(keyword) <= 3:
        return re.search(rf"(?<![a-z0-9-]){re.escape(keyword)}(?![a-z0-9])", text) is not None
    return keyword in text


def _xml_text(node: ET.Element, name: str) -> str:
    child = node.find(name)
    return "" if child is None or child.text is None else child.text


def _strip_html(value: str, *, limit: int) -> str:
    text = re.sub(r"<script\b.*?</script>", " ", value or "", flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return _one_line(text, limit=limit, default="none")


def _normalize_date(value: str) -> str:
    value = _one_line(value, limit=120, default="")
    if not value:
        return "unknown"
    try:
        parsed = parsedate_to_datetime(value)
        return parsed.astimezone().isoformat()
    except (TypeError, ValueError, OSError):
        return value


def _render_state(result: dict[str, Any]) -> str:
    items = result.get("items")
    item_blocks: list[str] = []
    if isinstance(items, list) and items:
        for index, item in enumerate(items, 1):
            if not isinstance(item, dict):
                continue
            item_blocks.append(
                f"### item-{index}\n"
                f"- item_key: {_one_line(item.get('item_key'))}\n"
                f"- title: {_one_line(item.get('title'))}\n"
                f"- url: {_one_line(item.get('url'), limit=500)}\n"
                f"- category: {_one_line(item.get('category'))}\n"
                f"- published_at: {_one_line(item.get('published_at'))}\n"
                f"- summary: {_one_line(item.get('summary'), limit=260)}\n"
            )
    else:
        item_blocks.append("### item-none\n- item_key: none\n- title: none\n- url: none\n")
    notes = "\n".join(f"- {_one_line(note, limit=160)}" for note in result.get("notes", [])) or "- none"
    return f"""---
title: Watched Source State
memory_type: watched_source_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: xinyu_watched_sources
updated_at: {_one_line(result['checked_at'])}
status: active
tags: [watched-source, read-only, web]
---

# Watched Source State

## Last Check
- checked_at: {_one_line(result['checked_at'])}
- status: {_one_line(result['status'])}
- source_id: {_one_line(result['source_id'])}
- source_url: {_one_line(result['source_url'], limit=500)}
- feed_url: {_one_line(result['feed_url'], limit=500)}
- fetch_url: {_one_line(result['fetch_url'], limit=500)}
- fetch_status_code: {_one_line(result['fetch_status_code'])}
- filter_topic: {_one_line(result['filter_topic'])}
- relevance_filter: {_one_line(result['relevance_filter'])}
- learning_scope: {_one_line(result['learning_scope'], limit=180)}
- scanned_items: {_one_line(result['scanned_items'])}
- matched_items: {_one_line(result['matched_items'])}
- ignored_items: {_one_line(result['ignored_items'])}
- fetched_items: {_one_line(result['fetched_items'])}
- new_items: {_one_line(result['new_items'])}
- latest_title: {_one_line(result['latest_title'], limit=180)}
- latest_url: {_one_line(result['latest_url'], limit=500)}

## Boundaries
- read_only: true
- no_posting: true
- no_ai_generated_forum_content: true
- no_stable_memory_write: true
- no_qq_message_from_watcher: true
- site_policy: {_one_line(result['site_policy'], limit=160)}
- use: recent public topic awareness only; do not treat titles as verified facts.
- candidate_learning_only: true
- learning_gate_required: true
- ignored_policy: non-matching topics stay out of prompt-visible watched items.

## Latest Items
{''.join(item_blocks).rstrip()}

## Notes
{notes}
"""


def _result(
    *,
    checked_at: str,
    status: str,
    source: dict[str, str] | None = None,
    feed_url: str = "none",
    fetch_url: str = "none",
    fetch_status_code: int | str = 0,
    scanned_items: int = 0,
    matched_items: int = 0,
    ignored_items: int = 0,
    fetched_items: int = 0,
    new_items: int = 0,
    latest_title: str = "none",
    latest_url: str = "none",
    items: list[dict[str, str]] | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    source = source or {}
    return {
        "accepted": True,
        "checked_at": checked_at,
        "status": status,
        "source_id": source.get("source_id", "none"),
        "source_url": source.get("url", "none"),
        "feed_url": feed_url,
        "fetch_url": fetch_url,
        "fetch_status_code": str(fetch_status_code),
        "filter_topic": source.get("topic_filter", "none"),
        "relevance_filter": "ai_keywords" if _relevance_keywords(source) else "none",
        "learning_scope": source.get("learning_scope", "candidate_topics_only"),
        "scanned_items": int(scanned_items),
        "matched_items": int(matched_items),
        "ignored_items": int(ignored_items),
        "fetched_items": int(fetched_items),
        "new_items": int(new_items),
        "latest_title": _one_line(latest_title, limit=180, default="none"),
        "latest_url": _one_line(latest_url, limit=500, default="none"),
        "site_policy": source.get("site_policy", "read_only_no_posting"),
        "items": items or [],
        "notes": sorted(set(_clean_note(note) for note in (notes or []) if _clean_note(note))),
    }


def _append_trace(root: Path, result: dict[str, Any]) -> None:
    payload = {
        "checked_at": result["checked_at"],
        "status": result["status"],
        "source_id": result["source_id"],
        "source_url": result["source_url"],
        "scanned_items": result["scanned_items"],
        "matched_items": result["matched_items"],
        "ignored_items": result["ignored_items"],
        "fetched_items": result["fetched_items"],
        "new_items": result["new_items"],
        "latest_title": result["latest_title"],
        "notes": result["notes"][:8],
    }
    path = root / TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _same_source(previous_state: str, source: dict[str, str]) -> bool:
    return (
        bool(previous_state)
        and _extract_value(previous_state, "source_id", "none") == source.get("source_id", "none")
        and _extract_value(previous_state, "source_url", "none") == source.get("url", "none")
    )


def _source_int(source: dict[str, str], key: str, default: int) -> int:
    try:
        return max(0, int(source.get(key, str(default))))
    except ValueError:
        return default


def _extract_int(text: str, field: str, default: int) -> int:
    try:
        return int(_extract_value(text, field, str(default)))
    except ValueError:
        return default


def _extract_value(text: str, field: str, default: str = "none") -> str:
    for match in _FIELD_RE.finditer(text or ""):
        if match.group(1) == field:
            return _one_line(match.group(2), limit=500, default=default)
    return default


def _seconds_since(value: str) -> float | None:
    value = _one_line(value, limit=120, default="")
    if not value:
        return None
    try:
        return max(0.0, time.time() - datetime.fromisoformat(value).timestamp())
    except ValueError:
        return None


def _seconds_between(later: str, earlier: str) -> float | None:
    later = _one_line(later, limit=120, default="")
    earlier = _one_line(earlier, limit=120, default="")
    if not later or not earlier:
        return None
    try:
        return max(0.0, datetime.fromisoformat(later).timestamp() - datetime.fromisoformat(earlier).timestamp())
    except ValueError:
        return None


def _allowed_public_url(url: str) -> bool:
    parsed = urlparse((url or "").strip())
    return parsed.scheme in ALLOWED_SCHEMES and bool(parsed.netloc)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _clean_token(value: Any) -> str:
    text = _one_line(value, limit=80).lower().replace(" ", "_")
    text = re.sub(r"[^a-z0-9_-]+", "_", text).strip("_")
    return text or "source"


def _clean_note(value: Any) -> str:
    return _clean_token(value)[:120]


def _one_line(value: Any, *, limit: int = 240, default: str = "none") -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.replace("\r\n", "\n").replace("\r", "\n").split()).strip()
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("<secret>", text)
    if not text:
        return default
    if len(text) > limit:
        text = text[: max(0, limit - 3)].rstrip() + "..."
    return text


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Run XinYu watched source check.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run_watched_source_check(args.root, force=args.force)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("Watched source check:", result["status"])
        print("source:", result["source_id"])
        print("fetched_items:", result["fetched_items"])
        print("new_items:", result["new_items"])
        print("latest_title:", result["latest_title"])
    return 0 if result.get("accepted") else 1


if __name__ == "__main__":
    raise SystemExit(main())
