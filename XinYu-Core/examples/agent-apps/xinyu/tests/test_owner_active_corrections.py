from __future__ import annotations

import json
from datetime import datetime, timedelta

import xinyu_owner_active_corrections as oac


def _tail(*pairs: tuple[str, str]) -> list[dict[str, str]]:
    return [{"role": role, "content": content} for role, content in pairs]


def test_extract_picks_corrections_and_ignores_chat_and_questions() -> None:
    tail = _tail(
        ("user", "晚上好"),
        ("assistant", "晚上好"),
        ("user", "别老用'在'开头"),
        ("user", "为什么老是有前缀 在？"),  # bare question, no imperative -> ignored
        ("assistant", "好"),
        ("user", "以后尽量少说那种英文"),
    )
    lines = oac.extract_correction_lines(tail, latest_user_text="这句太模板了")
    assert "别老用'在'开头" in lines
    assert "以后尽量少说那种英文" in lines
    assert "这句太模板了" in lines
    assert "晚上好" not in lines
    assert all("为什么老是有前缀" not in line for line in lines)


def test_extract_dedupes_repeated_requests() -> None:
    tail = _tail(("user", "别道歉"), ("user", "别道歉。"))
    assert oac.extract_correction_lines(tail) == ["别道歉"]


def test_ingest_dedupes_bumps_hits_and_persists(tmp_path) -> None:
    oac.ingest(tmp_path, ["别老用在开头"], now_iso="2026-06-12T10:00:00+08:00")
    data = oac.ingest(tmp_path, ["别老用在开头。"], now_iso="2026-06-12T11:00:00+08:00")
    assert len(data["entries"]) == 1
    assert data["entries"][0]["hits"] == 2
    on_disk = json.loads((tmp_path / oac.LEDGER_REL).read_text(encoding="utf-8"))
    assert on_disk["entries"][0]["hits"] == 2


def test_ingest_decays_old_and_caps_size(tmp_path) -> None:
    old = (datetime.now().astimezone() - timedelta(days=oac.TTL_DAYS + 2)).isoformat()
    oac.ingest(tmp_path, ["别用太正式的说法"], now_iso=old)
    fresh = [f"以后第{i}条要求别忘" for i in range(oac.MAX_ENTRIES + 3)]
    oac.ingest(tmp_path, fresh)
    requests = oac.active_corrections(tmp_path)
    assert len(requests) == oac.MAX_ENTRIES
    assert "别用太正式的说法" not in requests  # decayed out


def test_build_block_renders_standing_rules(tmp_path) -> None:
    block = oac.build_owner_active_corrections_block(
        tmp_path,
        dialogue_tail=_tail(("user", "别这么模板")),
        latest_user_text="以后别加'在'开头",
    )
    assert "owner standing requests sidecar:" in block
    assert "别这么模板" in block
    assert "以后别加'在'开头" in block
    assert "do not say 记住了" in block.replace("，", ",")


def test_build_block_empty_when_no_corrections(tmp_path) -> None:
    assert oac.build_owner_active_corrections_block(
        tmp_path,
        dialogue_tail=_tail(("user", "晚上好"), ("assistant", "晚上好")),
        latest_user_text="今天天气不错",
    ) == ""


def test_build_block_persists_across_turns(tmp_path) -> None:
    # turn 1: owner gives a correction
    oac.build_owner_active_corrections_block(
        tmp_path,
        dialogue_tail=_tail(("user", "别老用在开头")),
        latest_user_text="",
    )
    # turn 2: ordinary chat, correction must still be restated from the ledger
    block = oac.build_owner_active_corrections_block(
        tmp_path,
        dialogue_tail=_tail(("user", "嗯好的")),
        latest_user_text="今天干嘛了",
    )
    assert "别老用在开头" in block
