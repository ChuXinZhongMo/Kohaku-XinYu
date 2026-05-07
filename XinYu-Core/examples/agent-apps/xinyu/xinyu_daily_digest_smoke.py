from __future__ import annotations

import json
import tempfile
from pathlib import Path

from xinyu_daily_digest import build_daily_digest_prompt_block, run_daily_digest_maintenance


WATCHED_SOURCE = """---
title: Watched Source State
memory_type: watched_source_state
---

# Watched Source State

## Last Check
- checked_at: 2026-05-02T19:03:30+08:00
- status: fetched
- source_id: linux-do-latest
- fetched_items: 3
- new_items: 3

## Latest Items
### item-1
- item_key: codex-a
- title: codex 接码相关
- url: https://linux.do/t/topic/1
- category: 开发调优
- published_at: 2026-05-02T19:00:00+08:00
- summary: 想问问 codex 接码和账号相关问题
### item-2
- item_key: codex-b
- title: 公益站 KFC 的 codex 不可用吗
- url: https://linux.do/t/topic/2
- category: 开发调优
- published_at: 2026-05-02T19:01:00+08:00
- summary: unexpected status 401 unauthorized invalid api key
### item-3
- item_key: agent-c
- title: 多 agents 并发版本来了
- url: https://linux.do/t/topic/3
- category: 开发调优
- published_at: 2026-05-02T19:02:00+08:00
- summary: 构建 agents 团队
"""


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="xinyu-daily-digest-") as tmp:
        root = Path(tmp)
        _write(root, "memory/context/watched_source_state.md", WATCHED_SOURCE)
        result = run_daily_digest_maintenance(root, observed_at="2026-05-02T19:10:00+08:00")
        assert result["accepted"] is True
        assert result["generated"] is True
        assert result["status"] in {"ready", "fallback_guard_failed"}
        data = _read_json(root / "memory/context/daily_digest.json")
        assert data["ephemeral"] is True
        assert data["source_id"] == "linux-do-latest"
        assert data["source_item_count"] == 3
        assert len(data["comment"]) <= 50
        assert data["guard"]["judge"] == "deterministic_heuristic"
        assert all(fact["subjective_claim_removed"] is True for fact in data["facts"])
        state = (root / "memory/context/daily_digest_state.md").read_text(encoding="utf-8")
        assert "short_term_talk_only: true" in state
        block = build_daily_digest_prompt_block(root)
        assert "daily digest sidecar:" in block
        assert "not stable knowledge" in block
        assert data["comment"] in block

        reused = run_daily_digest_maintenance(root, observed_at="2026-05-02T19:20:00+08:00")
        assert reused["status"] == "reused"
        assert reused["generated"] is False

    with tempfile.TemporaryDirectory(prefix="xinyu-daily-digest-fallback-") as tmp:
        root = Path(tmp)
        _write(root, "memory/context/watched_source_state.md", WATCHED_SOURCE)
        old = {
            "generated_at": "2026-05-02T18:00:00+08:00",
            "expires_at": "2026-05-02T18:30:00+08:00",
            "comment": "linux.do 又在绕 Codex 接入，能力火了，边角问题也跟着冒泡。",
            "source_digest": "old",
            "status": "ready",
            "history": [
                {
                    "generated_at": "2026-05-02T17:00:00+08:00",
                    "comment": "Codex 相关问题冒得挺密，热起来以后，麻烦也跟着热。",
                    "source_digest": "older",
                }
            ],
        }
        _write(root, "memory/context/daily_digest.json", json.dumps(old, ensure_ascii=False))
        result = run_daily_digest_maintenance(root, observed_at="2026-05-02T19:10:00+08:00")
        assert result["generated"] is True
        data = _read_json(root / "memory/context/daily_digest.json")
        assert data["comment"]
        assert "history" in data

    print("xinyu_daily_digest_smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

