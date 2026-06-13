from __future__ import annotations

import json
from pathlib import Path

from xinyu_private_ecosystem_grants import save_grants_patch
from xinyu_sticker_pack import maybe_enqueue_sticker_reply


def _seed_semantic_sticker(root: Path) -> None:
    sticker_dir = root / "emotions/stickers/happy"
    sticker_dir.mkdir(parents=True, exist_ok=True)
    (sticker_dir / "happy.png").write_bytes(b"fake png")
    (root / "emotions/stickers/manifest.json").write_text(
        json.dumps(
            {
                "version": 1,
                "stickers": [
                    {
                        "file": "happy/happy.png",
                        "mood": "happy",
                        "keywords": ["haha", "happy"],
                        "auto_send": True,
                        "weight": 2,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _owner_payload() -> dict[str, object]:
    return {
        "message_type": "private_text",
        "user_id": "owner-1",
        "group_id": "",
        "metadata": {"is_owner_user": True},
    }


def test_semantic_auto_sticker_blocks_when_owner_private_share_paused(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XINYU_STICKER_DISABLE_SHARED_ASSET_LIBRARY", "1")
    monkeypatch.setenv("XINYU_LOCAL_SCOPE_DIR", str(tmp_path / "local_scope"))
    monkeypatch.setenv("XINYU_STICKER_AUTO_MIN_SCORE", "1")
    monkeypatch.setenv("XINYU_STICKER_AUTO_RATE", "100")
    _seed_semantic_sticker(tmp_path)
    save_grants_patch(tmp_path, {"owner_private_autonomous_share": {"enabled": True, "paused": True}})

    result = maybe_enqueue_sticker_reply(
        tmp_path,
        _owner_payload(),
        user_text="haha cute",
        reply="happy",
        session_key="qq:private:owner-1",
        turn_id="turn-auto-paused",
    )

    assert result["queued"] is False
    assert result["mode"] == "semantic_auto"
    assert "sticker_skip:owner_private_autonomous_share_paused" in result["notes"]
    assert not (tmp_path / "memory/context/qq_outbox_queue.json").exists()


def test_explicit_sticker_request_still_works_when_owner_private_share_paused(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XINYU_STICKER_DISABLE_SHARED_ASSET_LIBRARY", "1")
    monkeypatch.setenv("XINYU_LOCAL_SCOPE_DIR", str(tmp_path / "local_scope"))
    _seed_semantic_sticker(tmp_path)
    save_grants_patch(tmp_path, {"owner_private_autonomous_share": {"enabled": True, "paused": True}})

    result = maybe_enqueue_sticker_reply(
        tmp_path,
        _owner_payload(),
        user_text="sticker",
        reply="ok",
        session_key="qq:private:owner-1",
        turn_id="turn-explicit-paused",
    )

    assert result["queued"] is True
    assert result["mode"] == "explicit"
    assert (tmp_path / "memory/context/qq_outbox_queue.json").exists()
