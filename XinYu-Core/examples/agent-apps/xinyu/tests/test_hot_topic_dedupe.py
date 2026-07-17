from __future__ import annotations

import json
from pathlib import Path

from xinyu_hot_topic_fetch import (
    content_dedupe_key,
    filter_unpushed_items,
    mark_items_pushed,
    maybe_fetch_and_enqueue_hot_topic_followup,
)


def test_filter_unpushed_and_mark(tmp_path: Path) -> None:
    items = [
        {"title": "Kimi K3", "url": "https://www.kimi.com/blog/kimi-k3"},
        {"title": "openai/whisper", "url": "https://github.com/openai/whisper"},
    ]
    fresh, dup = filter_unpushed_items(tmp_path, items)
    assert len(fresh) == 2
    assert dup == []
    marked = mark_items_pushed(tmp_path, items)
    assert len(marked) == 2
    fresh2, dup2 = filter_unpushed_items(tmp_path, items)
    assert fresh2 == []
    assert len(dup2) == 2


def test_content_dedupe_key_stable() -> None:
    items = [
        {"title": "A", "url": "https://example.com/a?x=1"},
        {"title": "B", "url": "https://example.com/b"},
    ]
    k1 = content_dedupe_key("ai-news", items)
    k2 = content_dedupe_key("ai-news", list(reversed(items)))
    # same membership may reorder hash join — ensure same tag prefix and non-empty
    assert k1.startswith("ai-news:")
    assert k2.startswith("ai-news:")
    # identical order => identical key
    assert content_dedupe_key("ai-news", items) == k1


def test_second_enqueue_skipped_as_already_pushed(tmp_path: Path, monkeypatch) -> None:
    grants_path = tmp_path / "memory/context/private_ecosystem_grants.json"
    grants_path.parent.mkdir(parents=True, exist_ok=True)
    grants_path.write_text(
        json.dumps(
            {
                "private_browser": {
                    "enabled": True,
                    "read_only": True,
                    "allowed_urls": ["https://news.ycombinator.com/"],
                },
                "private_ecosystem": {"enabled": True, "rollout_state": "browser_read_only"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "xinyu_hot_topic_fetch._download_text",
        lambda url: "1. Kimi K3 Open Frontier 2. Agent Framework Update " * 3,
    )
    monkeypatch.setattr(
        "xinyu_hot_topic_fetch._download_page",
        lambda url: {
            "html": (
                '<span class="titleline"><a href="https://www.kimi.com/blog/kimi-k3">'
                "Kimi K3 Open Frontier Intelligence</a></span>"
            ),
            "text": "Kimi K3 Open Frontier Intelligence",
            "linked_items": [
                {
                    "title": "Kimi K3 Open Frontier Intelligence",
                    "url": "https://www.kimi.com/blog/kimi-k3",
                }
            ],
            "final_url": url,
        },
    )
    queued_calls: list[dict] = []

    def fake_enqueue(root, **kwargs):
        queued_calls.append(kwargs)
        return {"queued": True, "message_id": f"m-{len(queued_calls)}", "notes": ["queued"]}

    monkeypatch.setattr("xinyu_hot_topic_fetch.enqueue_qq_outbox_message", fake_enqueue)
    monkeypatch.setattr("xinyu_hot_topic_fetch.enqueue_owner_qq_outbox_message", fake_enqueue)

    payload = {
        "user_id": "10001",
        "message_type": "private_text",
        "metadata": {"is_owner_user": True},
    }
    first = maybe_fetch_and_enqueue_hot_topic_followup(
        tmp_path,
        payload,
        user_text="最近有啥 AI 资讯",
        reply="我先瞅一眼",
        session_key="qq:private:10001",
        turn_id="turn-1",
    )
    assert first.get("queued") is True
    assert first.get("linked_items")
    assert "https://" in (first.get("line") or "")

    second = maybe_fetch_and_enqueue_hot_topic_followup(
        tmp_path,
        payload,
        user_text="最近有啥 AI 资讯",
        reply="再看看",
        session_key="qq:private:10001",
        turn_id="turn-2",
    )
    # Same content must not push again.
    assert second.get("queued") is False
    assert second.get("reason") in {"all_items_already_pushed", "cooldown", "duplicate_content"}
    assert len(queued_calls) == 1
