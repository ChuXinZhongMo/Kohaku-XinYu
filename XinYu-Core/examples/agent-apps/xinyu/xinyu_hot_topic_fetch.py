"""On-demand public hot-topic fetch for live chat.

When the user asks about current/public hot topics and world_now_pulse has no
usable clue, fetch a small set of owner-allowlisted public pages (read-only HTTP),
write browse-action + DOM artifacts so world_now_pulse can read them, and
optionally enqueue a short oral follow-up to QQ outbox.

Never invents personal biography. Never browses hosts outside the grant allowlist.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from xinyu_private_ecosystem_grants import browser_grant, load_grants
from xinyu_qq_outbox import enqueue_qq_outbox_message, enqueue_owner_qq_outbox_message
from xinyu_world_now_pulse import (
    _host_label,
    _strip_html,
    collect_hot_items,
    collect_hot_notes,
    extract_linked_items,
    refresh_hot_pulse_cache,
)


ENV_ENABLED = "XINYU_HOT_TOPIC_AUTO_FETCH"
ENV_COOLDOWN = "XINYU_HOT_TOPIC_FETCH_COOLDOWN_SECONDS"
BROWSER_ACTIONS_REL = Path("runtime/private_ecosystem/browser_actions.jsonl")
ARTIFACTS_REL = Path("runtime/private_ecosystem/browser_artifacts")
STATE_REL = Path("runtime/private_ecosystem/hot_topic_fetch_state.json")
DEFAULT_COOLDOWN_SECONDS = 180
MAX_FETCH = 2
MAX_BYTES = 900_000
# HTML pages like GitHub trending can exceed 600KB; allow larger for link extraction.
MAX_HTML_BYTES = 1_500_000

# Prefer Chinese public hot boards first; tech boards as backup.
_PREFERRED_HOST_ORDER = (
    "s.weibo.com",
    "zhihu.com",
    "cls.cn",
    "thepaper.cn",
    "36kr.com",
    "ithome.com",
    "sspai.com",
    "news.ycombinator.com",
    "github.com",
)

# AI / model / agent news sources preferred when the user asks about AI.
_AI_PREFERRED_HOST_ORDER = (
    "news.ycombinator.com",
    "github.com",
    "36kr.com",
    "ithome.com",
    "sspai.com",
    "producthunt.com",
    "thepaper.cn",
    "zhihu.com",
    "cls.cn",
    "s.weibo.com",
)

# Paper-first sources when user asks about latest papers / arXiv.
_PAPER_PREFERRED_HOST_ORDER = (
    "arxiv.org",
    "huggingface.co",
    "news.ycombinator.com",
    "github.com",
    "36kr.com",
    "sspai.com",
    "ithome.com",
    "zhihu.com",
)

# Extra allowlist seeds for AI news (only used if grant allowlist already
# contains the host family or owner later adds them). Keep public/read-only.
_AI_DEFAULT_URL_CANDIDATES = (
    "https://news.ycombinator.com/",
    "https://github.com/trending",
    "https://36kr.com/",
    "https://www.ithome.com/",
    "https://sspai.com/",
    "https://www.producthunt.com/",
)

_PAPER_DEFAULT_URL_CANDIDATES = (
    "https://arxiv.org/list/cs.AI/recent",
    "https://arxiv.org/list/cs.CL/recent",
    "https://arxiv.org/list/cs.LG/recent",
    "https://huggingface.co/papers",
)

_HOT_TOPIC_MARKERS = (
    "热搜",
    "热点",
    "热榜",
    "刷到",
    "最近啥",
    "最近有啥",
    "最近发生",
    "今天啥",
    "今天有啥",
    "最新消息",
    "新闻",
    "八卦",
    "出啥事",
    "啥瓜",
    "瓜",
    "trending",
    "hot search",
    "what's trending",
    "what is trending",
)

# AI-specific public news / release asks (subset of hot topics).
_AI_NEWS_MARKERS = (
    "ai资讯",
    "AI资讯",
    "ai新闻",
    "AI新闻",
    "ai热点",
    "AI热点",
    "ai圈",
    "AI圈",
    "大模型",
    "最新模型",
    "模型发布",
    "开源模型",
    "chatgpt",
    "ChatGPT",
    "claude",
    "Claude",
    "gemini",
    "Gemini",
    "openai",
    "OpenAI",
    "anthropic",
    "grok",
    "Grok",
    "llm",
    "LLM",
    "agent",
    "Agent",
    "智能体",
    "机器学习",
    "深度学习",
    "生成式",
    "aigc",
    "AIGC",
    "huggingface",
    "HuggingFace",
    "hugging face",
    "arxiv",
    "arXiv",
    "论文",
    "模型更新",
    "ai动态",
    "AI动态",
    "ai 最新",
    "AI 最新",
    "最新ai",
    "最新AI",
    "ai消息",
    "AI消息",
    # Common typos / speech-to-text near-misses for 资讯
    "ai咨询",
    "AI咨询",
    "ai諮询",
    "AI諮询",
    "ai咨讯",
    "AI咨讯",
    "ai资讯",
    "看ai",
    "看AI",
    "查ai",
    "查AI",
)

# Paper / arXiv / daily-papers style asks (subset of AI news).
_AI_PAPER_MARKERS = (
    "最新论文",
    "ai论文",
    "AI论文",
    "大模型论文",
    "论文资讯",
    "论文动态",
    "论文更新",
    "论文推荐",
    "看论文",
    "读论文",
    "刷论文",
    "每日论文",
    "daily paper",
    "daily papers",
    "arxiv",
    "arXiv",
    "ArXiv",
    "预印本",
    "preprint",
    "preprints",
    "cs.AI",
    "cs.CL",
    "cs.LG",
    "hf papers",
    "huggingface papers",
    "HuggingFace papers",
    "paper",
    "papers",
)

_ALREADY_KNOWS_MARKERS = (
    "我知道",
    "我刷到",
    "我刚看",
    "我看到",
    "热搜上",
    "热榜上",
    "新闻说",
)


def hot_topic_auto_fetch_enabled() -> bool:
    raw = os.environ.get(ENV_ENABLED, "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _cooldown_seconds() -> int:
    try:
        return max(30, min(3600, int(os.environ.get(ENV_COOLDOWN, DEFAULT_COOLDOWN_SECONDS))))
    except (TypeError, ValueError):
        return DEFAULT_COOLDOWN_SECONDS


def _safe_str(value: Any) -> str:
    return "" if value is None else str(value)


def _now() -> datetime:
    return datetime.now().astimezone()


def _now_iso() -> str:
    return _now().isoformat(timespec="seconds")


def user_asks_hot_topic(user_text: str) -> bool:
    text = re.sub(r"\s+", "", _safe_str(user_text))
    if not text:
        return False
    raw = _safe_str(user_text)
    if any(marker.replace(" ", "") in text or marker in raw for marker in _HOT_TOPIC_MARKERS):
        return True
    return user_asks_ai_news(user_text)


def user_asks_ai_news(user_text: str) -> bool:
    """True when the user is asking about AI / model / agent public news."""
    raw = _safe_str(user_text)
    if not raw.strip():
        return False
    if user_asks_ai_papers(user_text):
        return True
    compact = re.sub(r"\s+", "", raw)
    lowered = raw.lower()
    for marker in _AI_NEWS_MARKERS:
        m = _safe_str(marker)
        if not m:
            continue
        if m.lower() in lowered or m.replace(" ", "") in compact:
            return True
    # Pattern: 最近/今天 + AI/大模型/模型
    if re.search(r"(最近|今天|这几天|有啥|什么|看看|看看最新|最新).{0,10}(AI|ai|大模型|模型|智能体)", compact):
        return True
    if re.search(
        r"(AI|ai|大模型|模型|智能体).{0,10}(新闻|资讯|咨询|咨讯|热点|动态|更新|发布|消息)",
        compact,
    ):
        return True
    return False


def user_asks_ai_papers(user_text: str) -> bool:
    """True when the user wants latest AI / ML papers (arXiv, HF papers, etc.)."""
    raw = _safe_str(user_text)
    if not raw.strip():
        return False
    compact = re.sub(r"\s+", "", raw)
    lowered = raw.lower()
    for marker in _AI_PAPER_MARKERS:
        m = _safe_str(marker)
        if not m:
            continue
        if m.lower() in lowered or m.replace(" ", "") in compact:
            return True
    # 最近/今天 + 论文；论文 + 资讯/推荐/更新
    if re.search(r"(最近|今天|这几天|有啥|什么|最新).{0,10}(论文|arxiv|预印本)", compact, re.I):
        return True
    if re.search(r"(论文|arxiv|预印本).{0,10}(新闻|资讯|热点|动态|更新|推荐|消息|列表)", compact, re.I):
        return True
    if re.search(r"(cs\.(AI|CL|LG)|machinelearning|nlp).{0,8}(paper|论文)", compact, re.I):
        return True
    return False

def reply_already_has_hot_claim(reply: str) -> bool:
    text = _safe_str(reply)
    if not text:
        return False
    if any(m in text for m in _ALREADY_KNOWS_MARKERS):
        return True
    # Concrete "刷到X上在聊" style already delivered.
    if "刷到" in text and ("在聊" in text or "热" in text):
        return True
    return False


def pulse_has_concrete_hot_clue(root: Path) -> bool:
    notes = collect_hot_notes(root, limit=2)
    if not notes:
        return False
    # Placeholder notes do not count as knowledge.
    return any("暂无" not in n and "没抓到" not in n for n in notes)


def _read_state(root: Path) -> dict[str, Any]:
    path = root / STATE_REL
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_state(root: Path, data: dict[str, Any]) -> None:
    path = root / STATE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _cooldown_active(root: Path) -> bool:
    state = _read_state(root)
    last = _safe_str(state.get("last_fetch_at"))
    if not last:
        return False
    try:
        ts = datetime.fromisoformat(last.replace("Z", "+00:00"))
    except ValueError:
        return False
    if ts.tzinfo is None:
        ts = ts.astimezone()
    return _now() - ts < timedelta(seconds=_cooldown_seconds())


def _normalize_item_url(url: str) -> str:
    text = _safe_str(url).strip()
    if not text:
        return ""
    # Strip tracking query noise for stable dedupe.
    text = re.sub(r"[?#].*$", "", text)
    return text.rstrip("/").lower()


def _item_fingerprint(item: dict[str, Any]) -> str:
    url = _normalize_item_url(_safe_str(item.get("url")))
    title = re.sub(r"\s+", " ", _safe_str(item.get("title")).strip().lower())
    if url:
        return f"url:{url}"
    if title:
        return "title:" + hashlib.sha1(title.encode("utf-8", errors="replace")).hexdigest()[:16]
    return ""


def _load_pushed_fingerprints(root: Path) -> set[str]:
    state = _read_state(root)
    raw = state.get("pushed_item_fps")
    if not isinstance(raw, list):
        return set()
    out: set[str] = set()
    for row in raw:
        if isinstance(row, str) and row.strip():
            out.add(row.strip())
        elif isinstance(row, dict):
            fp = _safe_str(row.get("fp")).strip()
            if fp:
                out.add(fp)
    return out


def _save_pushed_fingerprints(root: Path, fps: set[str], *, keep: int = 200) -> None:
    state = _read_state(root)
    # Keep insertion-ish order by sorting for stability; cap size.
    ordered = sorted(fps)[-max(20, keep) :]
    state["pushed_item_fps"] = ordered
    state["pushed_item_fps_updated_at"] = _now_iso()
    _write_state(root, state)


def filter_unpushed_items(root: Path, items: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Split items into (fresh, already_pushed)."""
    pushed = _load_pushed_fingerprints(root)
    fresh: list[dict[str, str]] = []
    dupes: list[dict[str, str]] = []
    seen_local: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        fp = _item_fingerprint(item)
        if not fp:
            continue
        if fp in pushed or fp in seen_local:
            dupes.append(item)
            continue
        seen_local.add(fp)
        fresh.append(item)
    return fresh, dupes


def mark_items_pushed(root: Path, items: list[dict[str, str]]) -> list[str]:
    pushed = _load_pushed_fingerprints(root)
    added: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        fp = _item_fingerprint(item)
        if not fp or fp in pushed:
            continue
        pushed.add(fp)
        added.append(fp)
    if added:
        _save_pushed_fingerprints(root, pushed)
    return added


def content_dedupe_key(topic_tag: str, items: list[dict[str, str]], *, line: str = "") -> str:
    """Stable outbox dedupe key from content, not wall-clock minutes."""
    fps = []
    for item in items[:6]:
        fp = _item_fingerprint(item)
        if fp:
            fps.append(fp)
    if not fps and line:
        fps.append("line:" + hashlib.sha1(line.encode("utf-8", errors="replace")).hexdigest()[:16])
    if not fps:
        fps.append("empty")
    digest = hashlib.sha1("|".join(fps).encode("utf-8", errors="replace")).hexdigest()[:20]
    return f"{topic_tag}:{digest}"


def _allowlisted_urls(
    root: Path,
    *,
    prefer_ai: bool = False,
    prefer_papers: bool = False,
) -> list[str]:
    grants = load_grants(root)
    section = browser_grant(grants)
    if not bool(section.get("enabled")):
        return []
    raw = section.get("allowed_urls")
    if not isinstance(raw, list):
        return []
    urls = [str(item).strip() for item in raw if str(item).strip()]
    if prefer_papers:
        order = _PAPER_PREFERRED_HOST_ORDER
    elif prefer_ai:
        order = _AI_PREFERRED_HOST_ORDER
    else:
        order = _PREFERRED_HOST_ORDER

    def rank(url: str) -> tuple[int, int, str]:
        host = (urlparse(url).hostname or "").lower()
        path = (urlparse(url).path or "").lower()
        host_rank = 100
        for idx, preferred in enumerate(order):
            if host == preferred or host.endswith("." + preferred):
                host_rank = idx
                break
        # Within paper mode, prefer arxiv list pages and HF papers over generic roots.
        path_boost = 0
        if prefer_papers:
            if "arxiv.org" in host and "/list/" in path:
                path_boost = -2
            elif "huggingface.co" in host and "paper" in path:
                path_boost = -1
            elif host in {"github.com", "www.github.com"} and "trending" not in path:
                path_boost = 3
        return (host_rank, path_boost, url)

    return sorted(urls, key=rank)


def _pick_fetch_urls(
    root: Path,
    *,
    limit: int = MAX_FETCH,
    prefer_ai: bool = False,
    prefer_papers: bool = False,
) -> list[str]:
    urls = _allowlisted_urls(root, prefer_ai=prefer_ai, prefer_papers=prefer_papers)
    # Skip pure github root if better hot boards exist.
    preferred: list[str] = []
    for url in urls:
        host = (urlparse(url).hostname or "").lower()
        path = (urlparse(url).path or "").lower()
        if host in {"github.com", "www.github.com"} and "trending" not in url and preferred:
            continue
        # For AI news / papers, skip pure social gossip boards when tech boards exist.
        if (prefer_ai or prefer_papers) and host in {"s.weibo.com", "weibo.com"} and any(
            "36kr" in u
            or "ithome" in u
            or "ycombinator" in u
            or "github.com/trending" in u
            or "arxiv.org" in u
            or "huggingface.co" in u
            for u in urls
        ):
            continue
        # Paper mode: skip non-paper generic roots when arxiv/HF papers exist.
        if prefer_papers:
            has_paper_src = any(
                "arxiv.org" in u or "huggingface.co/papers" in u or "huggingface.co/paper" in u for u in urls
            )
            if has_paper_src and host in {"producthunt.com", "www.producthunt.com"}:
                continue
            if has_paper_src and host in {"github.com", "www.github.com"} and "trending" not in path:
                continue
        preferred.append(url)
        if len(preferred) >= limit:
            break
    return preferred[:limit]

def _download_page(url: str) -> dict[str, Any]:
    """Download page; keep HTML when possible so title+link extraction works.

    Always truncate-friendly: large pages (HN/GitHub) must not hard-fail the scout.
    """
    from urllib.request import Request, urlopen

    request = Request(
        url,
        headers={
            "User-Agent": "XinYuHotTopicFetch/0.3 (+local-agent; read-only)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urlopen(request, timeout=30) as response:
        final_url = response.geturl()
        content_type = response.headers.get("content-type", "application/octet-stream")
        # Soft truncate: never raise on large HTML.
        data = response.read(MAX_HTML_BYTES)
    ctype = (content_type or "").lower()
    raw = data.decode("utf-8", errors="replace")
    is_html = "html" in ctype or raw.lstrip().startswith("<") or "<html" in raw[:300].lower()
    page_url = _safe_str(final_url) or url
    if is_html:
        text = _strip_html(raw)
        items = extract_linked_items(raw, page_url=page_url, limit=6)
        return {
            "html": raw[:MAX_HTML_BYTES],
            "text": text,
            "linked_items": items,
            "final_url": page_url,
        }
    text = re.sub(r"\s+", " ", raw).strip()[:12000]
    items = extract_linked_items(text, page_url=page_url, limit=6)
    return {
        "html": "",
        "text": text,
        "linked_items": items,
        "final_url": page_url,
    }


def _download_text(url: str) -> str:
    """Backward-compatible plain text download (tests may monkeypatch this)."""
    page = _download_page(url)
    return _safe_str(page.get("text"))


def _append_browse_action(
    root: Path,
    *,
    url: str,
    text: str,
    html: str = "",
    linked_items: list[dict[str, str]] | None = None,
) -> str:
    """Write a completed browse action + DOM artifact for world_now_pulse."""
    now = _now_iso()
    digest = hashlib.sha1(f"{url}|{now}".encode("utf-8", errors="replace")).hexdigest()[:16]
    action_id = f"bact-hot-{digest}"
    # JSON artifact carries linked_items (title+url) for oral follow-ups.
    rel = ARTIFACTS_REL / f"{action_id}-dom.json"
    abs_path = root / rel
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "url": url,
        "text": text,
        "html": (html or "")[:200_000],
        "linked_items": list(linked_items or [])[:6],
        "saved_at": now,
        "source": "hot_topic_auto_fetch",
    }
    abs_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    # Also keep a plain-text sibling for older readers.
    txt_rel = ARTIFACTS_REL / f"{action_id}-dom.txt"
    try:
        (root / txt_rel).write_text(text, encoding="utf-8")
    except OSError:
        pass
    row = {
        "action_id": action_id,
        "action_kind": "navigate_readonly",
        "result": "completed",
        "target": {"url": url},
        "dom_snapshot_ref": str(rel).replace("\\", "/"),
        "observed_at": now,
        "source": "hot_topic_auto_fetch",
        "notes": ["hot_topic_auto_fetch"],
        "linked_item_count": len(list(linked_items or [])),
    }
    actions = root / BROWSER_ACTIONS_REL
    actions.parent.mkdir(parents=True, exist_ok=True)
    with actions.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return str(rel).replace("\\", "/")


def fetch_public_hot_pages(
    root: Path,
    *,
    limit: int = MAX_FETCH,
    prefer_ai: bool = False,
    prefer_papers: bool = False,
) -> dict[str, Any]:
    """Fetch allowlisted public pages and refresh hot pulse cache."""
    root = Path(root)
    urls = _pick_fetch_urls(
        root,
        limit=limit,
        prefer_ai=prefer_ai or prefer_papers,
        prefer_papers=prefer_papers,
    )
    if not urls:
        return {"ok": False, "fetched": 0, "notes": ["no_allowlisted_urls"], "hot_notes": []}
    fetched = 0
    errors: list[str] = []
    all_items: list[dict[str, str]] = []
    for url in urls:
        try:
            # Prefer full page download (HTML+links). Tests may patch _download_text only.
            try:
                page = _download_page(url)
            except Exception:
                page = {"text": _download_text(url), "html": "", "linked_items": []}
            text = _safe_str(page.get("text"))
            html = _safe_str(page.get("html"))
            items = list(page.get("linked_items") or [])
            if (not text or len(text) < 40) and not items:
                errors.append(f"thin:{_host_label(url)}")
                continue
            if not items and text:
                items = extract_linked_items(html or text, page_url=url, limit=4)
            _append_browse_action(
                root,
                url=_safe_str(page.get("final_url")) or url,
                text=text,
                html=html,
                linked_items=items,
            )
            for item in items:
                if isinstance(item, dict) and item.get("url"):
                    all_items.append(
                        {
                            "title": _safe_str(item.get("title"))[:96],
                            "url": _safe_str(item.get("url")),
                        }
                    )
            fetched += 1
        except Exception as exc:
            errors.append(f"{_host_label(url)}:{type(exc).__name__}")
    refresh_hot_pulse_cache(root)
    notes = collect_hot_notes(root, limit=2)
    if not all_items:
        all_items = collect_hot_items(root, limit=6)
    if prefer_ai or prefer_papers:
        all_items = filter_ai_relevant_items(
            all_items,
            prefer_papers=prefer_papers,
            limit=6,
        )
    _write_state(
        root,
        {
            "last_fetch_at": _now_iso(),
            "fetched": fetched,
            "urls": urls,
            "prefer_ai": prefer_ai or prefer_papers,
            "prefer_papers": prefer_papers,
            "errors": errors[:6],
            "hot_notes": notes,
            "linked_items": all_items[:6],
        },
    )
    return {
        "ok": fetched > 0 or bool(notes) or bool(all_items),
        "fetched": fetched,
        "notes": errors,
        "hot_notes": notes,
        "linked_items": all_items[:6],
        "urls": urls,
        "prefer_ai": prefer_ai or prefer_papers,
        "prefer_papers": prefer_papers,
    }

def _is_placeholder_hot_note(note: str) -> bool:
    text = _safe_str(note)
    if not text:
        return True
    if "没抓到具体标题" in text:
        return True
    if "一类公开页" in text and "在聊" not in text:
        return True
    if "暂无" in text:
        return True
    return False


def _clean_hot_note_for_speech(note: str) -> str:
    text = re.sub(r"（[^）]*）", "", _safe_str(note)).strip()
    text = text.replace("最近刷到", "").replace("最近扫过", "").replace("最近看过", "")
    # Drop HN chrome fragments that leaked into titles.
    text = re.sub(
        r"(?i)(?:\d+\s*points? by [^\s,、]+|\d+\s*(?:hours?|minutes?|days?)\s*ago|hide\s*\||\bcomments?\b)",
        " ",
        text,
    )
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"[、,]{2,}", "、", text)
    return text.strip(" ：:、,|")


_AI_RELEVANCE_MARKERS = (
    "ai",
    "ml",
    "llm",
    "agent",
    "model",
    "gpt",
    "claude",
    "gemini",
    "openai",
    "anthropic",
    "kimi",
    "grok",
    "mistral",
    "llama",
    "qwen",
    "deepseek",
    "transformer",
    "neural",
    "diffusion",
    "embedding",
    "inference",
    "training",
    "fine-tune",
    "finetune",
    "rag",
    "arxiv",
    "huggingface",
    "机器学习",
    "深度学习",
    "大模型",
    "智能体",
    "生成式",
    "神经网络",
    "多模态",
)


def filter_ai_relevant_items(
    items: list[dict[str, str]],
    *,
    prefer_papers: bool = False,
    limit: int = 4,
) -> list[dict[str, str]]:
    """Keep Agent/AI-ish items; papers mode prefers arxiv/hf links."""
    scored: list[tuple[int, dict[str, str]]] = []
    for row in items:
        if not isinstance(row, dict):
            continue
        title = _safe_str(row.get("title"))
        url = _safe_str(row.get("url"))
        blob = f"{title} {url}".lower()
        score = 0
        if any(m in blob for m in _AI_RELEVANCE_MARKERS):
            score += 3
        if "arxiv.org" in url or "huggingface.co" in url:
            score += 4 if prefer_papers else 2
        if "github.com" in url and not any(
            bad in url for bad in ("/security/", "/enterprise/", "/solutions/", "/resources/", "/pricing")
        ):
            score += 1
        if prefer_papers and "arxiv.org" not in url and "huggingface.co" not in url:
            score -= 1
        # Penalize obvious non-tech HN noise.
        if any(bad in blob for bad in ("latrine", "concrete lasted", "usb type", "monkey species", "usgs.gov")):
            score -= 3
        if score > 0 and url.startswith("http"):
            scored.append((score, {"title": title[:96], "url": url}))
    scored.sort(key=lambda x: (-x[0], x[1].get("title") or ""))
    # If everything filtered out, fall back to original top items with real http links.
    if not scored:
        out = []
        for row in items:
            if not isinstance(row, dict):
                continue
            url = _safe_str(row.get("url"))
            title = _safe_str(row.get("title"))
            if url.startswith("http") and title:
                out.append({"title": title[:96], "url": url})
            if len(out) >= limit:
                break
        return out
    return [row for _, row in scored[:limit]]


def oral_hot_followup_line(
    hot_notes: list[str],
    *,
    prefer_ai: bool = False,
    prefer_papers: bool = False,
    linked_items: list[dict[str, str]] | None = None,
) -> str:
    """Short QQ follow-up with concrete titles and clickable links when available."""
    items = [row for row in list(linked_items or []) if isinstance(row, dict)]
    # Prefer structured title+url pairs.
    if items:
        chunks: list[str] = []
        for row in items[:3]:
            title = _clean_hot_note_for_speech(_safe_str(row.get("title")))
            link = _safe_str(row.get("url")).strip()
            if not title or not link.startswith("http"):
                continue
            if len(title) > 48:
                title = title[:47].rstrip() + "…"
            chunks.append(f"{title}\n{link}")
        if chunks:
            body = "\n\n".join(chunks)
            if prefer_papers:
                return f"最新论文线索：\n{body}"
            if prefer_ai:
                return f"AI圈我刚刷到：\n{body}"
            return f"我刚刷到：\n{body}"

    concrete = [n for n in hot_notes if not _is_placeholder_hot_note(n)]
    usable = concrete or list(hot_notes or [])
    if not usable:
        if prefer_papers:
            return "我刚扫了 arXiv/论文页，标题不太清晰，你丢个方向词（对齐/推理/多模态）我再对。"
        if prefer_ai:
            return "我刚扫了眼 AI/科技公开页，标题不太清晰，你丢个关键词我再对。"
        return "我刚扫了一眼公开页，没抓到清晰标题，你先说你看到啥？"
    # Prefer the first concrete note, strip parenthetical disclaimer for speech.
    note = _clean_hot_note_for_speech(usable[0])
    if not note or _is_placeholder_hot_note(note):
        if prefer_papers:
            return "论文页刚扫过，细目标题还糊，你丢个方向我再对。"
        if prefer_ai:
            return "AI/科技页刚扫过，细目还不稳，你丢个关键词我再对。"
        return "我刚扫了一眼，线索有点糊，你说下关键词我再对。"
    # Keep short but preserve any URLs already embedded in the note.
    if len(note) > 220:
        note = note[:219].rstrip() + "…"
    if prefer_papers:
        if "arxiv" in note.lower() or "cs." in note.lower() or "paper" in note.lower() or "http" in note:
            return f"论文页我刚扫到：{note}"
        return f"最新论文线索：{note}"
    if prefer_ai:
        if "在聊" in note or "、" in note or "/" in note or "HN" in note or "GitHub" in note or "http" in note:
            return f"AI圈我刚刷到一点：{note}"
        return f"AI/科技公开页刚扫到：{note}"
    if "在聊" in note or "、" in note or "http" in note:
        return f"我刚刷到一点：{note}"
    return f"我刚扫到公开页在聊：{note}"


def should_auto_fetch_hot_topic(
    root: Path,
    *,
    user_text: str,
    reply: str = "",
) -> tuple[bool, str]:
    if not hot_topic_auto_fetch_enabled():
        return False, "disabled"
    if not user_asks_hot_topic(user_text):
        return False, "not_hot_topic_ask"
    if reply_already_has_hot_claim(reply):
        return False, "reply_already_claims_hot"
    # AI-specific asks should still fetch even if a generic hot clue exists,
    # because weibo/zhihu gossip is not the same as model/tech news.
    if pulse_has_concrete_hot_clue(root) and not user_asks_ai_news(user_text):
        return False, "pulse_already_has_clue"
    if _cooldown_active(root):
        return False, "cooldown"
    prefer_papers = user_asks_ai_papers(user_text)
    prefer_ai = prefer_papers or user_asks_ai_news(user_text)
    if not _allowlisted_urls(root, prefer_ai=prefer_ai, prefer_papers=prefer_papers):
        return False, "no_allowlist"
    if prefer_papers:
        return True, "eligible_papers"
    return True, "eligible_ai" if prefer_ai else "eligible"


def maybe_fetch_and_enqueue_hot_topic_followup(
    root: Path,
    payload: dict[str, Any],
    *,
    user_text: str,
    reply: str = "",
    session_key: str = "",
    turn_id: str = "",
) -> dict[str, Any]:
    """Sync entry used by finish sidecars (may be run in a worker thread)."""
    root = Path(root)
    ok, reason = should_auto_fetch_hot_topic(root, user_text=user_text, reply=reply)
    if not ok:
        return {"queued": False, "fetched": 0, "reason": reason, "notes": [reason]}

    prefer_papers = user_asks_ai_papers(user_text) or reason == "eligible_papers"
    prefer_ai = prefer_papers or user_asks_ai_news(user_text) or reason in {
        "eligible_ai",
        "eligible_papers",
    }
    result = fetch_public_hot_pages(
        root,
        limit=MAX_FETCH,
        prefer_ai=prefer_ai,
        prefer_papers=prefer_papers,
    )
    hot_notes = list(result.get("hot_notes") or [])
    linked_items = list(result.get("linked_items") or [])
    if not linked_items:
        linked_items = collect_hot_items(root, limit=4)
    if prefer_ai or prefer_papers:
        linked_items = filter_ai_relevant_items(
            linked_items,
            prefer_papers=prefer_papers,
            limit=6,
        )
    fresh_items, dup_items = filter_unpushed_items(root, linked_items)
    # If we have no structured links at all, fall back to note-only speech once.
    # If we *do* have links but all were already pushed, do not re-announce.
    if linked_items and not fresh_items:
        return {
            "queued": False,
            "fetched": int(result.get("fetched") or 0),
            "reason": "all_items_already_pushed",
            "prefer_ai": prefer_ai,
            "prefer_papers": prefer_papers,
            "hot_notes": hot_notes,
            "linked_items": linked_items[:6],
            "duplicate_items": dup_items[:6],
            "line": "",
            "notes": list(result.get("notes") or []) + ["all_items_already_pushed"],
        }

    line = oral_hot_followup_line(
        hot_notes,
        prefer_ai=prefer_ai,
        prefer_papers=prefer_papers,
        linked_items=fresh_items,
    )
    if not line.strip():
        return {
            "queued": False,
            "fetched": int(result.get("fetched") or 0),
            "reason": "empty_followup_line",
            "prefer_ai": prefer_ai,
            "prefer_papers": prefer_papers,
            "hot_notes": hot_notes,
            "linked_items": fresh_items[:6],
            "duplicate_items": dup_items[:6],
            "line": "",
            "notes": list(result.get("notes") or []) + ["empty_followup_line"],
        }
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    user_id = _safe_str(payload.get("user_id") or metadata.get("user_id")).strip()
    group_id = _safe_str(payload.get("group_id") or metadata.get("group_id")).strip()
    message_type = _safe_str(payload.get("message_type") or metadata.get("message_type")).lower()
    is_group = bool(group_id and group_id not in {"0", "none"}) or "group" in message_type

    if prefer_papers:
        topic_tag = "ai-papers"
    elif prefer_ai:
        topic_tag = "ai-news"
    else:
        topic_tag = "hot-topic"
    # Content-hash dedupe (not wall-clock): same links/line => same key until content changes.
    dedupe = content_dedupe_key(topic_tag, fresh_items, line=line)
    meta = {
        "hot_topic_auto_fetch": True,
        "ai_news_fetch": prefer_ai,
        "ai_papers_fetch": prefer_papers,
        "source_turn_id": turn_id,
        "source_session_id": session_key,
        "hot_notes": hot_notes[:3],
        "linked_items": fresh_items[:4],
        "content_dedupe_key": dedupe,
    }
    if is_group and group_id:
        queued = enqueue_qq_outbox_message(
            root,
            user_id=user_id or "0",
            message=line,
            source="hot_topic_auto_fetch",
            dedupe_key=dedupe,
            group_id=group_id,
            message_kind="group",
            metadata=meta,
        )
    else:
        # Prefer explicit user_id when present; else owner config.
        if user_id and user_id not in {"0", "none"}:
            queued = enqueue_qq_outbox_message(
                root,
                user_id=user_id,
                message=line,
                source="hot_topic_auto_fetch",
                dedupe_key=dedupe,
                message_kind="private",
                metadata=meta,
            )
        else:
            queued = enqueue_owner_qq_outbox_message(
                root,
                message=line,
                source="hot_topic_auto_fetch",
                dedupe_key=dedupe,
                metadata=meta,
            )
    if prefer_papers:
        reason_out = "fetched_papers"
    elif prefer_ai:
        reason_out = "fetched_ai"
    else:
        reason_out = "fetched"
    notes = list(result.get("notes") or []) + list(queued.get("notes") or [])
    if dup_items:
        notes.append(f"skipped_already_pushed:{len(dup_items)}")
    # Only mark fingerprints after a successful queue (or explicit duplicate_dedupe_key).
    queued_ok = bool(queued.get("queued"))
    dup_key_hit = any("duplicate_dedupe_key" in _safe_str(n) for n in (queued.get("notes") or []))
    if queued_ok or dup_key_hit:
        marked = mark_items_pushed(root, fresh_items)
        if marked:
            notes.append(f"marked_pushed:{len(marked)}")
        if dup_key_hit and not queued_ok:
            reason_out = "duplicate_content"
    return {
        "queued": queued_ok,
        "message_id": _safe_str(queued.get("message_id")),
        "fetched": int(result.get("fetched") or 0),
        "reason": reason_out if queued_ok or dup_key_hit else reason_out,
        "prefer_ai": prefer_ai,
        "prefer_papers": prefer_papers,
        "hot_notes": hot_notes,
        "linked_items": fresh_items[:6],
        "duplicate_items": dup_items[:6],
        "line": line if queued_ok else "",
        "dedupe_key": dedupe,
        "notes": notes,
    }


def spawn_hot_topic_followup(
    root: Path,
    payload: dict[str, Any],
    *,
    user_text: str,
    reply: str = "",
    session_key: str = "",
    turn_id: str = "",
) -> dict[str, Any]:
    """Non-blocking wrapper: eligibility check sync, fetch+enqueue in daemon thread."""
    root = Path(root)
    ok, reason = should_auto_fetch_hot_topic(root, user_text=user_text, reply=reply)
    if not ok:
        return {"scheduled": False, "reason": reason, "notes": [reason]}

    def _worker() -> None:
        try:
            maybe_fetch_and_enqueue_hot_topic_followup(
                root,
                payload,
                user_text=user_text,
                reply=reply,
                session_key=session_key,
                turn_id=turn_id,
            )
        except Exception as exc:
            try:
                state = _read_state(root)
                state["last_error"] = f"{type(exc).__name__}:{exc}"[:240]
                state["last_error_at"] = _now_iso()
                _write_state(root, state)
            except Exception:
                pass

    thread = threading.Thread(target=_worker, name="xinyu-hot-topic-fetch", daemon=True)
    thread.start()
    return {"scheduled": True, "reason": "eligible", "notes": ["hot_topic_fetch_thread_started"]}
