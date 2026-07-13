from __future__ import annotations

import json
from pathlib import Path

from xinyu_owner_private_share import evaluate_and_maybe_queue, privacy_filter

QQ_OUTBOX_QUEUE = Path("memory/context/qq_outbox_queue.json")


def _owner_config(tmp_path: Path, user_id: str = "1001") -> None:
    path = tmp_path / "xinyu_qq_gateway.config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"owner_user_ids": [user_id]}), encoding="utf-8")


def _grants(**share) -> dict:
    base = {
        "enabled": True,
        "paused": False,
        "daily_limit": 8,
        "cooldown_minutes": 30,
        "max_message_chars": 800,
        "quiet_hours": "00:00-06:00",
    }
    base.update(share)
    return {"owner_private_autonomous_share": base}


def _candidate(**over) -> dict:
    base = {
        "kind": "self_reflection",
        "summary": "I spent a little while in my own space.",
        "dedupe_key": "k1",
    }
    base.update(over)
    return base


def _queue_items(tmp_path: Path) -> list:
    path = tmp_path / QQ_OUTBOX_QUEUE
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, dict):
        return data.get("items", []) or data.get("queue", [])
    return data if isinstance(data, list) else []


def test_share_blocks_without_grant(tmp_path: Path) -> None:
    _owner_config(tmp_path)
    result = evaluate_and_maybe_queue(
        tmp_path,
        candidate=_candidate(),
        grants=_grants(enabled=False),
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    assert result["allowed"] is False
    assert "share_grant_disabled" in result["blocks"]
    assert result["queued"] is False
    assert not (tmp_path / QQ_OUTBOX_QUEUE).exists()


def test_share_queues_exactly_one_with_grant_and_dedupes(tmp_path: Path) -> None:
    _owner_config(tmp_path)
    first = evaluate_and_maybe_queue(
        tmp_path,
        candidate=_candidate(),
        grants=_grants(),
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    assert first["queued"] is True
    assert first["delivery_level"] == "send_owner_private"
    assert len(_queue_items(tmp_path)) == 1

    # Same dedupe key -> suppressed, still exactly one message.
    second = evaluate_and_maybe_queue(
        tmp_path,
        candidate=_candidate(),
        grants=_grants(),
        evaluated_at="2026-06-02T11:00:00+08:00",
    )
    assert second["queued"] is False
    assert "duplicate_finding" in second["blocks"]
    assert len(_queue_items(tmp_path)) == 1


def test_share_cooldown_blocks_repeated_messages(tmp_path: Path) -> None:
    _owner_config(tmp_path)
    evaluate_and_maybe_queue(
        tmp_path,
        candidate=_candidate(dedupe_key="a"),
        grants=_grants(cooldown_minutes=30),
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    second = evaluate_and_maybe_queue(
        tmp_path,
        candidate=_candidate(dedupe_key="b"),
        grants=_grants(cooldown_minutes=30),
        evaluated_at="2026-06-02T10:10:00+08:00",
    )
    assert second["queued"] is False
    assert "cooldown_active" in second["blocks"]
    assert second["cooldown_remaining_minutes"] == 20


def test_share_daily_limit_blocks_overflow(tmp_path: Path) -> None:
    _owner_config(tmp_path)
    evaluate_and_maybe_queue(
        tmp_path,
        candidate=_candidate(dedupe_key="a"),
        grants=_grants(daily_limit=1, cooldown_minutes=0),
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    second = evaluate_and_maybe_queue(
        tmp_path,
        candidate=_candidate(dedupe_key="b"),
        grants=_grants(daily_limit=1, cooldown_minutes=0),
        evaluated_at="2026-06-02T10:05:00+08:00",
    )
    assert second["queued"] is False
    assert "daily_budget_exhausted" in second["blocks"]


def test_share_quiet_hours_blocks_unless_override(tmp_path: Path) -> None:
    _owner_config(tmp_path)
    blocked = evaluate_and_maybe_queue(
        tmp_path,
        candidate=_candidate(dedupe_key="q1"),
        grants=_grants(),
        evaluated_at="2026-06-02T02:00:00+08:00",
    )
    assert blocked["queued"] is False
    assert "quiet_hours" in blocked["blocks"]

    overridden = evaluate_and_maybe_queue(
        tmp_path,
        candidate=_candidate(dedupe_key="q2"),
        grants=_grants(quiet_hours_override=True),
        evaluated_at="2026-06-02T02:30:00+08:00",
    )
    assert "quiet_hours" not in overridden["blocks"]
    assert overridden["queued"] is True


def test_share_blocks_group_and_non_owner_channel(tmp_path: Path) -> None:
    _owner_config(tmp_path)
    result = evaluate_and_maybe_queue(
        tmp_path,
        candidate=_candidate(channel="group"),
        grants=_grants(),
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    assert result["queued"] is False
    assert "non_owner_channel_blocked" in result["blocks"]
    assert not (tmp_path / QQ_OUTBOX_QUEUE).exists()


def test_share_blocks_when_owner_target_missing(tmp_path: Path) -> None:
    # No owner config written.
    result = evaluate_and_maybe_queue(
        tmp_path,
        candidate=_candidate(),
        grants=_grants(),
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    assert result["queued"] is False
    assert "owner_target_missing" in result["blocks"]


def test_share_redacts_secrets_and_paths(tmp_path: Path) -> None:
    _owner_config(tmp_path)
    candidate = _candidate(
        dedupe_key="redact",
        summary="found token=abc123456789def at C:\\Users\\Atimea\\secret.txt id 123456789012",
    )
    result = evaluate_and_maybe_queue(
        tmp_path,
        candidate=candidate,
        grants=_grants(),
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    assert result["queued"] is True
    assert result["privacy_flags"]  # at least one redaction happened
    raw = (tmp_path / QQ_OUTBOX_QUEUE).read_text(encoding="utf-8-sig")
    assert "abc123456789def" not in raw
    assert "secret.txt" not in raw
    assert "123456789012" not in raw


def test_share_allows_browse_observation_kind(tmp_path: Path) -> None:
    """Private-browser read-only observations must not die on share_kind_not_allowed."""
    _owner_config(tmp_path)
    result = evaluate_and_maybe_queue(
        tmp_path,
        candidate=_candidate(
            kind="browse_observation",
            summary="GitHub trending had a neat Rust toolkit.",
            dedupe_key="browse-1",
        ),
        grants=_grants(),
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    assert "share_kind_not_allowed" not in result["blocks"]
    assert result["queued"] is True
    assert result["delivery_level"] == "send_owner_private"


def test_privacy_filter_unit() -> None:
    clean, flags, hard = privacy_filter("token=abcdef123456 path /home/me/x id 999999999999")
    assert "<secret>" in clean
    assert "<local_path>" in clean
    assert "<id>" in clean
    assert "secret_redacted" in flags
    assert hard is False
