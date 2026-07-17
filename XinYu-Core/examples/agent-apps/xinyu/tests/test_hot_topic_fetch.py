from __future__ import annotations

import json
from pathlib import Path

from xinyu_hot_topic_fetch import (
    _pick_fetch_urls,
    filter_ai_relevant_items,
    maybe_fetch_and_enqueue_hot_topic_followup,
    oral_hot_followup_line,
    should_auto_fetch_hot_topic,
    user_asks_ai_news,
    user_asks_ai_papers,
    user_asks_hot_topic,
)
from xinyu_world_now_pulse import _extract_headlines, collect_hot_notes, extract_linked_items


def test_user_asks_hot_topic_markers() -> None:
    assert user_asks_hot_topic("最近有啥热搜") is True
    assert user_asks_hot_topic("今天热点是啥") is True
    assert user_asks_hot_topic("你知道最近发生什么了吗") is True
    assert user_asks_hot_topic("作业ddl怎么办") is False


def test_user_asks_ai_news_markers() -> None:
    assert user_asks_ai_news("最近有啥 AI 资讯") is True
    assert user_asks_ai_news("大模型有新发布吗") is True
    assert user_asks_ai_news("OpenAI 又更新啥了") is True
    assert user_asks_ai_news("Claude 新模型消息") is True
    assert user_asks_ai_news("作业ddl怎么办") is False
    # Common typo / near-miss from group chat.
    assert user_asks_ai_news("看看最新的AI咨询") is True
    assert user_asks_hot_topic("@心玉 看看最新的AI咨询") is True
    # AI news also counts as hot-topic ask for the auto-fetch gate.
    assert user_asks_hot_topic("最近 AI 圈有啥热点") is True


def test_user_asks_ai_papers_markers() -> None:
    assert user_asks_ai_papers("最近有啥最新论文") is True
    assert user_asks_ai_papers("arXiv 上有啥新的") is True
    assert user_asks_ai_papers("刷一下 cs.AI 论文") is True
    assert user_asks_ai_papers("HuggingFace papers 今日") is True
    assert user_asks_ai_papers("AI 论文资讯") is True
    assert user_asks_ai_papers("最近有啥 AI 资讯") is False
    assert user_asks_ai_news("最近有啥最新论文") is True
    assert user_asks_hot_topic("推荐几篇新论文") is True


def test_should_auto_fetch_when_no_pulse_clue(tmp_path: Path, monkeypatch) -> None:
    # Grant allowlist
    grants = tmp_path / "memory/context/private_ecosystem_grants.json"
    grants.parent.mkdir(parents=True, exist_ok=True)
    grants.write_text(
        json.dumps(
            {
                "private_browser": {
                    "enabled": True,
                    "read_only": True,
                    "allowed_urls": ["https://www.zhihu.com/hot", "https://s.weibo.com/top/summary"],
                },
                "private_ecosystem": {"enabled": True, "rollout_state": "browser_read_only"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("xinyu_hot_topic_fetch.load_grants", lambda root: json.loads(grants.read_text(encoding="utf-8")))
    monkeypatch.setattr(
        "xinyu_hot_topic_fetch.browser_grant",
        lambda g: g.get("private_browser") or {},
    )
    ok, reason = should_auto_fetch_hot_topic(tmp_path, user_text="最近热搜啥", reply="不知道诶")
    assert ok is True
    assert reason == "eligible"
    ok2, reason2 = should_auto_fetch_hot_topic(
        tmp_path,
        user_text="最近热搜啥",
        reply="我刷到热搜上在聊考试",
    )
    assert ok2 is False
    assert reason2 == "reply_already_claims_hot"


def test_fetch_writes_artifact_and_enqueue(tmp_path: Path, monkeypatch) -> None:
    grants_path = tmp_path / "memory/context/private_ecosystem_grants.json"
    grants_path.parent.mkdir(parents=True, exist_ok=True)
    grants_path.write_text(
        json.dumps(
            {
                "private_browser": {
                    "enabled": True,
                    "read_only": True,
                    "allowed_urls": ["https://www.zhihu.com/hot"],
                },
                "private_ecosystem": {"enabled": True, "rollout_state": "browser_read_only"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "xinyu_hot_topic_fetch._download_text",
        lambda url: "1. 暑期实习好卷 2. 新游戏上线 3. 分数线讨论 " * 3,
    )

    queued: dict = {}

    def fake_enqueue(root, **kwargs):
        queued.update(kwargs)
        return {"queued": True, "message_id": "hot-1", "notes": ["queued"]}

    monkeypatch.setattr("xinyu_hot_topic_fetch.enqueue_qq_outbox_message", fake_enqueue)
    monkeypatch.setattr("xinyu_hot_topic_fetch.enqueue_owner_qq_outbox_message", fake_enqueue)

    result = maybe_fetch_and_enqueue_hot_topic_followup(
        tmp_path,
        {"user_id": "10001", "message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="最近热搜啥",
        reply="我先瞅一眼",
        session_key="qq:private:10001",
        turn_id="turn-hot-1",
    )
    assert result.get("reason") in {"fetched", "eligible"} or result.get("queued") is True
    assert result["queued"] is True
    assert result["fetched"] >= 1, result
    notes = collect_hot_notes(tmp_path, limit=2)
    assert notes
    assert "line" in result and result["line"]
    assert queued.get("source") == "hot_topic_auto_fetch"

def test_oral_hot_followup_line_short() -> None:
    line = oral_hot_followup_line(["最近刷到知乎热榜上在聊：暑期实习好卷、新游戏上线（公共信息，不是亲身经历）"])
    assert "暑期" in line or "知乎" in line or "刷到" in line
    assert "首先" not in line


def test_oral_ai_followup_line() -> None:
    line = oral_hot_followup_line(
        ["最近刷到 HN 上在聊：openai/whisper、新开源模型（公共信息，不是亲身经历）"],
        prefer_ai=True,
    )
    assert "AI" in line or "刷到" in line or "公开" in line
    assert "首先" not in line


def test_oral_line_skips_github_placeholder() -> None:
    line = oral_hot_followup_line(
        [
            "最近扫过 GitHub trending 一类公开页（公共信息，不是亲身经历）",
            "最近刷到HN上在聊：Kimi K3: Open Frontier Intelligence、LM Studio Bionic（公共信息，不是亲身经历）",
        ],
        prefer_ai=True,
    )
    assert "一类公开页" not in line
    assert "Kimi" in line or "LM Studio" in line or "HN" in line


def test_filter_ai_relevant_items_prefers_ai() -> None:
    items = [
        {"title": "Roman Concrete Latrine", "url": "https://example.com/concrete"},
        {"title": "Kimi K3 Open Frontier Intelligence", "url": "https://www.kimi.com/blog/kimi-k3"},
        {"title": "USB Type-C Guide", "url": "https://www.ti.com/usb.pdf"},
        {"title": "openai/whisper", "url": "https://github.com/openai/whisper"},
    ]
    kept = filter_ai_relevant_items(items, prefer_papers=False, limit=3)
    urls = " ".join(i["url"] for i in kept)
    assert "kimi.com" in urls
    assert "openai/whisper" in urls
    assert "concrete" not in urls
    assert "usb.pdf" not in urls


def test_oral_line_includes_links() -> None:
    line = oral_hot_followup_line(
        [],
        prefer_ai=True,
        linked_items=[
            {
                "title": "Kimi K3: Open Frontier Intelligence",
                "url": "https://kimi.com/",
            },
            {
                "title": "openai/whisper",
                "url": "https://github.com/openai/whisper",
            },
        ],
    )
    assert "https://kimi.com/" in line
    assert "https://github.com/openai/whisper" in line
    assert "Kimi" in line


def test_extract_hn_linked_items_from_html() -> None:
    html = """
    <html><body>
    <span class="titleline"><a href="https://kimi.com/">Kimi K3: Open Frontier Intelligence</a></span>
    <span class="titleline"><a href="https://lmstudio.ai/">LM Studio Bionic</a></span>
    </body></html>
    """
    items = extract_linked_items(html, page_url="https://news.ycombinator.com/", limit=3)
    assert items
    assert items[0]["url"].startswith("http")
    assert "Kimi" in items[0]["title"]


def test_extract_github_linked_items_from_html() -> None:
    html = """
    <a href="/openai/whisper">openai/whisper</a>
    <a href="/meta-llama/llama3">meta-llama/llama3</a>
    """
    items = extract_linked_items(html, page_url="https://github.com/trending", limit=3)
    assert any(i["url"] == "https://github.com/openai/whisper" for i in items)


def test_extract_arxiv_linked_items_from_html() -> None:
    html = """
    <a href="/abs/2403.11111">arXiv:2403.11111</a>
    <span class="title">Better Alignment for Agents</span>
    <a href="/abs/2403.22222v1">arXiv:2403.22222</a>
    """
    items = extract_linked_items(html, page_url="https://arxiv.org/list/cs.AI/recent", limit=3)
    assert items
    assert any("arxiv.org/abs/2403.11111" in i["url"] for i in items)


def test_ai_fetch_prefers_tech_hosts(tmp_path: Path, monkeypatch) -> None:
    grants = {
        "private_browser": {
            "enabled": True,
            "read_only": True,
            "allowed_urls": [
                "https://s.weibo.com/top/summary",
                "https://www.zhihu.com/hot",
                "https://36kr.com/",
                "https://news.ycombinator.com/",
                "https://github.com/trending",
            ],
        },
        "private_ecosystem": {"enabled": True, "rollout_state": "browser_read_only"},
    }
    monkeypatch.setattr("xinyu_hot_topic_fetch.load_grants", lambda root: grants)
    monkeypatch.setattr(
        "xinyu_hot_topic_fetch.browser_grant",
        lambda g: g.get("private_browser") or {},
    )
    urls = _pick_fetch_urls(tmp_path, limit=2, prefer_ai=True)
    assert urls
    blob = " ".join(urls)
    assert "weibo" not in blob
    assert ("36kr" in blob) or ("ycombinator" in blob) or ("github.com/trending" in blob)


def test_paper_fetch_prefers_arxiv_hosts(tmp_path: Path, monkeypatch) -> None:
    grants = {
        "private_browser": {
            "enabled": True,
            "read_only": True,
            "allowed_urls": [
                "https://s.weibo.com/top/summary",
                "https://36kr.com/",
                "https://news.ycombinator.com/",
                "https://arxiv.org/list/cs.AI/recent",
                "https://huggingface.co/papers",
                "https://github.com/",
            ],
        },
        "private_ecosystem": {"enabled": True, "rollout_state": "browser_read_only"},
    }
    monkeypatch.setattr("xinyu_hot_topic_fetch.load_grants", lambda root: grants)
    monkeypatch.setattr(
        "xinyu_hot_topic_fetch.browser_grant",
        lambda g: g.get("private_browser") or {},
    )
    urls = _pick_fetch_urls(tmp_path, limit=2, prefer_ai=True, prefer_papers=True)
    assert urls
    blob = " ".join(urls)
    assert "weibo" not in blob
    assert ("arxiv.org" in blob) or ("huggingface.co/papers" in blob)


def test_extract_arxiv_headlines() -> None:
    text = "arXiv:2401.12345 Title: Scaling Laws for Something Cool 2401.99999v2 Another Paper"
    heads = _extract_headlines(text, url="https://arxiv.org/list/cs.AI/recent")
    assert heads
    assert any("2401." in h or "Scaling" in h or "arXiv:" in h for h in heads)


def test_ai_papers_fetch_enqueue(tmp_path: Path, monkeypatch) -> None:
    grants_path = tmp_path / "memory/context/private_ecosystem_grants.json"
    grants_path.parent.mkdir(parents=True, exist_ok=True)
    grants_path.write_text(
        json.dumps(
            {
                "private_browser": {
                    "enabled": True,
                    "read_only": True,
                    "allowed_urls": [
                        "https://arxiv.org/list/cs.AI/recent",
                        "https://huggingface.co/papers",
                        "https://news.ycombinator.com/",
                    ],
                },
                "private_ecosystem": {"enabled": True, "rollout_state": "browser_read_only"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "xinyu_hot_topic_fetch._download_text",
        lambda url: (
            "Title: Better Alignment for Agents 2403.11111 "
            "Title: Multimodal Reasoning at Scale 2403.22222 "
            "arXiv:2403.33333 cs.AI cs.CL "
        )
        * 2,
    )
    queued: dict = {}

    def fake_enqueue(root, **kwargs):
        queued.update(kwargs)
        return {"queued": True, "message_id": "paper-1", "notes": ["queued"]}

    monkeypatch.setattr("xinyu_hot_topic_fetch.enqueue_qq_outbox_message", fake_enqueue)
    monkeypatch.setattr("xinyu_hot_topic_fetch.enqueue_owner_qq_outbox_message", fake_enqueue)

    result = maybe_fetch_and_enqueue_hot_topic_followup(
        tmp_path,
        {"user_id": "10001", "message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="最近有啥最新论文",
        reply="我先瞅一眼",
        session_key="qq:private:10001",
        turn_id="turn-paper-1",
    )
    assert result.get("queued") is True
    assert result.get("prefer_papers") is True
    assert result.get("prefer_ai") is True
    assert result.get("fetched", 0) >= 1
    line = result.get("line") or ""
    assert "论文" in line or "arXiv" in line or "刷到" in line or "扫到" in line
    # Prefer real abs links when HTML/text yields paper ids.
    assert "http" in line or "arXiv:" in line
    assert queued.get("metadata", {}).get("ai_papers_fetch") is True or queued.get("source") == "hot_topic_auto_fetch"


def test_ai_news_fetch_enqueue(tmp_path: Path, monkeypatch) -> None:
    grants_path = tmp_path / "memory/context/private_ecosystem_grants.json"
    grants_path.parent.mkdir(parents=True, exist_ok=True)
    grants_path.write_text(
        json.dumps(
            {
                "private_browser": {
                    "enabled": True,
                    "read_only": True,
                    "allowed_urls": [
                        "https://news.ycombinator.com/",
                        "https://36kr.com/",
                        "https://github.com/trending",
                    ],
                },
                "private_ecosystem": {"enabled": True, "rollout_state": "browser_read_only"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "xinyu_hot_topic_fetch._download_text",
        lambda url: "1. Open source LLM release 2. Agent framework update 3. New multimodal model " * 3,
    )
    queued: dict = {}

    def fake_enqueue(root, **kwargs):
        queued.update(kwargs)
        return {"queued": True, "message_id": "ai-1", "notes": ["queued"]}

    monkeypatch.setattr("xinyu_hot_topic_fetch.enqueue_qq_outbox_message", fake_enqueue)
    monkeypatch.setattr("xinyu_hot_topic_fetch.enqueue_owner_qq_outbox_message", fake_enqueue)

    result = maybe_fetch_and_enqueue_hot_topic_followup(
        tmp_path,
        {"user_id": "10001", "message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="最近有啥 AI 资讯",
        reply="我先瞅一眼",
        session_key="qq:private:10001",
        turn_id="turn-ai-1",
    )
    assert result.get("queued") is True
    assert result.get("prefer_ai") is True
    assert result.get("fetched", 0) >= 1
    assert "AI" in (result.get("line") or "") or "刷到" in (result.get("line") or "")
    assert queued.get("source") == "hot_topic_auto_fetch"
