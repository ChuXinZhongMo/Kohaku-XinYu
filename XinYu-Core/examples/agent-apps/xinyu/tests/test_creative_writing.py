from __future__ import annotations

import json
from pathlib import Path

from xinyu_creative_writing import (
    CHAPTER_CARDS_REL,
    CHAPTERS_REL,
    CHARACTERS_REL,
    CREATIVE_FACTORY_STATE_REL,
    CREATIVE_ENGINEERING_MODE,
    EDITORIAL_REVIEWS_REL,
    FORESHADOW_LEDGER_REL,
    LOCAL_REFERENCE_DIGEST_REL,
    LOCAL_REFERENCE_INDEX_REL,
    MIN_PLATFORM_CHARS,
    NOVEL_MODE,
    OUTLINE_REL,
    OPENING_REWRITE_BRIEF_REL,
    PACING_RULES_REL,
    PROFILE_REL,
    PUBLICATION_CHAPTERS_REL,
    PUBLICATION_LOG_REL,
    PUBLICATION_STATE_REL,
    READER_MODEL_REL,
    REFERENCE_COLLECTION_LOG_REL,
    REFERENCE_DIGEST_REL,
    REFERENCE_EXTRACTS_REL,
    REFERENCE_PERMISSIONS_REL,
    SOURCE_MAP_REL,
    STORY_BIBLE_REL,
    XINYU_NARRATIVE_FILTER_REL,
    GENRE_BENCHMARK_REL,
    STATE_REL,
    TRACE_REL,
    collect_creative_reference_materials,
    refactor_existing_chapters_for_publication,
    read_creative_writing_state,
    run_creative_writing_maintenance,
)


def _chapters(root: Path) -> list[Path]:
    return sorted((root / CHAPTERS_REL).glob("*/chapter-*.md"))


def _publication_chapters(root: Path) -> list[Path]:
    return sorted((root / PUBLICATION_CHAPTERS_REL).glob("chapter-*.md"))


def _body_chars(path: Path) -> int:
    return len("".join(path.read_text(encoding="utf-8").split()))


def _paragraphs(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [part.strip() for part in text.split("\n\n") if part.strip() and not part.startswith("#")]


def _assert_pure_chapter(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert not text.startswith("---")
    for marker in (
        "写作札记",
        "draft_stage",
        "project_id",
        "project_title",
        "target_platform_chars",
        "min_platform_chars",
        "平台读者",
        "平台连载",
        "平台后台",
        "发布稿",
        "字数",
        "心玉",
    ):
        assert marker not in text


def test_creative_writing_bootstraps_project_and_writes_three_chapters(tmp_path: Path) -> None:
    result = run_creative_writing_maintenance(
        tmp_path,
        checked_at="2026-05-15T09:00:00+08:00",
        daily_target=3,
    )

    assert result["status"] == "complete"
    assert result["creative_writing_mode"] == NOVEL_MODE
    assert result["creative_hobby_enabled"] is True
    assert result["daily_target_chapters"] == 3
    assert result["chapters_written_this_run"] == 3
    assert result["today_chapters_written"] == 3
    assert result["total_chapters"] == 3
    assert result["publish_ready_chapters"] == 3
    assert result["publish_pending_chapters"] == 0
    assert (tmp_path / PROFILE_REL).exists()
    assert (tmp_path / OUTLINE_REL).exists()
    assert (tmp_path / CHARACTERS_REL).exists()
    assert (tmp_path / STATE_REL).exists()
    assert (tmp_path / STORY_BIBLE_REL).exists()
    assert (tmp_path / FORESHADOW_LEDGER_REL).exists()
    assert (tmp_path / READER_MODEL_REL).exists()
    assert (tmp_path / XINYU_NARRATIVE_FILTER_REL).exists()
    assert (tmp_path / CREATIVE_FACTORY_STATE_REL).exists()
    assert (tmp_path / PUBLICATION_STATE_REL).exists()
    assert (tmp_path / PUBLICATION_LOG_REL).exists()
    assert (tmp_path / CHAPTER_CARDS_REL / "chapter-001.md").exists()
    assert (tmp_path / EDITORIAL_REVIEWS_REL / "chapter-001.md").exists()
    assert (tmp_path / REFERENCE_PERMISSIONS_REL).exists()
    assert (tmp_path / SOURCE_MAP_REL).exists()
    assert (tmp_path / GENRE_BENCHMARK_REL).exists()
    assert (tmp_path / PACING_RULES_REL).exists()
    assert (tmp_path / OPENING_REWRITE_BRIEF_REL).exists()
    outline_text = (tmp_path / OUTLINE_REL).read_text(encoding="utf-8")
    assert "避难系统失控" in outline_text
    assert "十三号基地" in outline_text
    assert "一二五号避难所" in outline_text
    assert "参考层只提供题材信号" in outline_text

    chapter_paths = _chapters(tmp_path)
    assert [path.name for path in chapter_paths] == ["chapter-001.md", "chapter-002.md", "chapter-003.md"]
    first_chapter = chapter_paths[0].read_text(encoding="utf-8")
    assert "# 第 001 章" in first_chapter
    assert "星桥试运行" in first_chapter
    _assert_pure_chapter(chapter_paths[0])
    assert _body_chars(chapter_paths[0]) >= MIN_PLATFORM_CHARS

    publication_paths = _publication_chapters(tmp_path)
    assert [path.name for path in publication_paths] == ["chapter-001.md", "chapter-002.md", "chapter-003.md"]
    _assert_pure_chapter(publication_paths[0])
    assert _body_chars(publication_paths[0]) >= MIN_PLATFORM_CHARS
    log_text = (tmp_path / PUBLICATION_LOG_REL).read_text(encoding="utf-8")
    assert "manual_review_before_upload" in log_text
    assert "| 001 | 避难雨站 |" in log_text
    story_bible = (tmp_path / STORY_BIBLE_REL).read_text(encoding="utf-8")
    assert "Commercial Premise" in story_bible
    assert "Object Continuity" in story_bible
    reader_model = (tmp_path / READER_MODEL_REL).read_text(encoding="utf-8")
    assert "Platinum-Level Gates" in reader_model
    narrative_filter = (tmp_path / XINYU_NARRATIVE_FILTER_REL).read_text(encoding="utf-8")
    assert "不可以写“前一章留下的”" in narrative_filter
    assert "角色不知道自己在小说里" in narrative_filter
    ledger = (tmp_path / FORESHADOW_LEDGER_REL).read_text(encoding="utf-8")
    assert "setup" in ledger
    assert "payoff" in ledger
    factory_state = (tmp_path / CREATIVE_FACTORY_STATE_REL).read_text(encoding="utf-8")
    assert "factory_status: active" in factory_state
    assert "review_pass_chapters" in factory_state
    review_text = (tmp_path / EDITORIAL_REVIEWS_REL / "chapter-001.md").read_text(encoding="utf-8")
    assert "market_score" in review_text
    assert "status: pass" in review_text

    state = read_creative_writing_state(tmp_path)
    assert state["creative_hobby_enabled"] is True
    assert state["creative_writing_mode"] == NOVEL_MODE
    assert state["daily_target_chapters"] == 3
    assert state["today_chapters_written"] == 3
    assert state["total_chapters"] == 3
    assert state["publish_ready_chapters"] == 3
    assert state["min_platform_chars"] == MIN_PLATFORM_CHARS
    assert state["latest_chapter_path"].endswith("chapter-003.md")
    assert state["publication_latest_chapter_path"].endswith("chapter-003.md")
    assert state["creative_factory_status"] == "active"
    assert state["story_bible_path"].endswith("story_bible.md")
    assert state["foreshadow_ledger_path"].endswith("foreshadow_ledger.md")
    assert state["reader_model_path"].endswith("reader_model.md")
    assert state["xinyu_narrative_filter_path"].endswith("xinyu_narrative_filter.md")
    assert state["review_pass_chapters"] >= 3
    assert state["review_pending_chapters"] == 0

    trace_rows = [
        json.loads(line)
        for line in (tmp_path / TRACE_REL).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert trace_rows[-1]["event_kind"] == "creative_writing_maintenance"
    assert trace_rows[-1]["written_chapters"][-1]["path"].endswith("chapter-003.md")
    assert trace_rows[-1]["publication"]["publish_ready_chapters"] == 3


def test_creative_writing_is_idempotent_for_same_day(tmp_path: Path) -> None:
    run_creative_writing_maintenance(
        tmp_path,
        checked_at="2026-05-15T09:00:00+08:00",
        daily_target=3,
    )

    second = run_creative_writing_maintenance(
        tmp_path,
        checked_at="2026-05-15T20:30:00+08:00",
        daily_target=3,
    )

    assert second["status"] == "complete"
    assert second["chapters_written_this_run"] == 0
    assert second["publication"]["publication_written_this_run"] == 0
    assert second["today_chapters_written"] == 3
    assert second["total_chapters"] == 3
    assert len(_chapters(tmp_path)) == 3
    assert len(_publication_chapters(tmp_path)) == 3


def test_creative_writing_continues_global_chapter_numbers_next_day(tmp_path: Path) -> None:
    run_creative_writing_maintenance(
        tmp_path,
        checked_at="2026-05-15T09:00:00+08:00",
        daily_target=2,
    )

    result = run_creative_writing_maintenance(
        tmp_path,
        checked_at="2026-05-16T09:00:00+08:00",
        daily_target=3,
    )

    assert result["chapters_written_this_run"] == 3
    assert result["today_chapters_written"] == 3
    assert result["total_chapters"] == 5
    assert result["publish_ready_chapters"] == 5
    assert [path.name for path in _chapters(tmp_path)] == [
        "chapter-001.md",
        "chapter-002.md",
        "chapter-003.md",
        "chapter-004.md",
        "chapter-005.md",
    ]
    assert result["latest_chapter_path"].endswith("chapter-005.md")


def test_refactor_existing_chapters_rewrites_and_archives_short_versions(tmp_path: Path) -> None:
    run_creative_writing_maintenance(
        tmp_path,
        checked_at="2026-05-15T09:00:00+08:00",
        daily_target=1,
    )
    source = _chapters(tmp_path)[0]
    publish = _publication_chapters(tmp_path)[0]
    source.write_text("# 第 001 章：短版\n\n太短。\n", encoding="utf-8")
    publish.write_text("# 第 001 章：短版\n\n太短。\n", encoding="utf-8")

    result = refactor_existing_chapters_for_publication(
        tmp_path,
        checked_at="2026-05-16T10:00:00+08:00",
        chapter_numbers=[1],
    )

    assert result["rewritten_count"] == 1
    assert result["publish_pending_chapters"] == 0
    assert result["archived_files"]
    _assert_pure_chapter(source)
    _assert_pure_chapter(publish)
    assert _body_chars(source) >= MIN_PLATFORM_CHARS
    assert _body_chars(publish) >= MIN_PLATFORM_CHARS
    archive_root = tmp_path / result["archive_path"]
    assert archive_root.exists()


def test_creative_writing_migrates_legacy_mixed_layout(tmp_path: Path) -> None:
    legacy_chapter = tmp_path / "memory/creative/chapters/2026-05-15/chapter-001.md"
    legacy_publication = tmp_path / "memory/creative/publication/chapters/chapter-001.md"
    legacy_chapter.parent.mkdir(parents=True)
    legacy_publication.parent.mkdir(parents=True)
    legacy_chapter.write_text(
        "---\nproject_id: old\n---\n# 第 001 章：旧稿\n\n太短。\n\n## 写作札记\n- 本章推进\n",
        encoding="utf-8",
    )
    legacy_publication.write_text(
        "# 第 001 章：旧发布\n\n这一章给平台读者看。\n",
        encoding="utf-8",
    )

    result = run_creative_writing_maintenance(
        tmp_path,
        checked_at="2026-05-15T09:00:00+08:00",
        daily_target=1,
    )

    migration = result["legacy_migration"]
    assert migration["migrated"] is True
    assert migration["rewritten_chapters"] == 1
    assert migration["retired_legacy_files"] == 2
    assert not legacy_chapter.exists()
    assert not legacy_publication.exists()
    chapter = tmp_path / CHAPTERS_REL / "2026-05-15/chapter-001.md"
    publish = tmp_path / PUBLICATION_CHAPTERS_REL / "chapter-001.md"
    assert chapter.exists()
    assert publish.exists()
    _assert_pure_chapter(chapter)
    _assert_pure_chapter(publish)
    assert _body_chars(chapter) >= MIN_PLATFORM_CHARS
    assert (tmp_path / migration["archive_path"]).exists()


def test_creative_engineering_mode_does_not_write_chapter_prose(tmp_path: Path) -> None:
    result = run_creative_writing_maintenance(
        tmp_path,
        checked_at="2026-05-15T09:00:00+08:00",
        daily_target=3,
        writing_mode=CREATIVE_ENGINEERING_MODE,
    )

    assert result["status"] == "planning"
    assert result["creative_writing_mode"] == CREATIVE_ENGINEERING_MODE
    assert result["chapters_written_this_run"] == 0
    assert result["engineering_plans_written"] == 3
    assert not _chapters(tmp_path)
    assert (tmp_path / PROFILE_REL).exists()
    assert (tmp_path / OUTLINE_REL).exists()
    assert (tmp_path / REFERENCE_PERMISSIONS_REL).exists()
    assert (tmp_path / SOURCE_MAP_REL).exists()
    permissions = (tmp_path / REFERENCE_PERMISSIONS_REL).read_text(encoding="utf-8")
    assert "search_only" in permissions
    assert "reference_download" in permissions
    assert "copyright_safe_extract" in permissions
    assert "禁止保存章节正文" in permissions
    source_map = (tmp_path / SOURCE_MAP_REL).read_text(encoding="utf-8")
    assert "Project Gutenberg" in source_map
    assert "只保存摘要观察，不保存正文" in source_map
    assert result["reference_collection"]["status"] == "collected"
    assert result["reference_collection"]["raw_chapter_text_saved"] is False
    assert (tmp_path / REFERENCE_DIGEST_REL).exists()
    assert (tmp_path / REFERENCE_EXTRACTS_REL).exists()
    assert (tmp_path / REFERENCE_COLLECTION_LOG_REL).exists()
    digest = (tmp_path / REFERENCE_DIGEST_REL).read_text(encoding="utf-8")
    assert "Creative Engineering Intake" in digest
    assert "raw_chapter_text_saved: false" in digest
    assert "禁止保存章节正文" in digest
    cards = sorted((tmp_path / CHAPTER_CARDS_REL).glob("chapter-*.md"))
    assert [path.name for path in cards] == ["chapter-001.md", "chapter-002.md", "chapter-003.md"]
    card_text = cards[0].read_text(encoding="utf-8")
    assert "## Engineering Plan" in card_text
    assert "## Creative Factory Contract" in card_text
    assert "## Event Chain" in card_text
    assert "novel_layer: consumes_this_card_and_writes_pure_prose" in card_text
    assert "reference_digest_path" in card_text
    state = read_creative_writing_state(tmp_path)
    assert state["creative_writing_mode"] == CREATIVE_ENGINEERING_MODE
    assert state["next_action"] == "creative_engineering_review_only"
    assert state["reference_collection_status"] == "collected"
    assert state["reference_sources_collected"] >= 1


def test_creative_reference_collection_never_saves_chapter_prose(tmp_path: Path) -> None:
    fetched: list[str] = []

    def fake_fetcher(source: dict[str, object]) -> dict[str, object]:
        fetched.append(str(source["source_id"]))
        return {
            "ok": True,
            "status_code": 200,
            "text": (
                "<html><head><title>Public Domain Shelf</title>"
                "<meta name=\"description\" content=\"A safe catalog of public-domain speculative fiction.\" />"
                "</head><body>COPY_ME_NOT_FULL_CHAPTER_PROSE</body></html>"
            ),
            "notes": ["fake_fetch"],
        }

    result = collect_creative_reference_materials(
        tmp_path,
        checked_at="2026-05-16T12:00:00+08:00",
        allow_reference_download=True,
        fetcher=fake_fetcher,
        source_specs=[
            {
                "source_id": "public_domain_test",
                "title": "Public Domain Test",
                "platform": "Example",
                "url": "https://example.org/public",
                "permission": "reference_download",
                "safe_use": "测试公开来源摘要。",
            },
            {
                "source_id": "copyright_platform_test",
                "title": "Copyright Platform Test",
                "platform": "Serial Platform",
                "url": "https://example.org/serial",
                "permission": "copyright_safe_extract",
                "safe_use": "测试平台元数据摘要。",
            },
        ],
    )

    assert fetched == ["public_domain_test"]
    assert result["status"] == "collected"
    assert result["downloaded_sources"] == 1
    assert result["raw_chapter_text_saved"] is False
    assert not (tmp_path / CHAPTERS_REL).exists()
    digest = (tmp_path / REFERENCE_DIGEST_REL).read_text(encoding="utf-8")
    extracts = (tmp_path / REFERENCE_EXTRACTS_REL).read_text(encoding="utf-8")
    log = (tmp_path / REFERENCE_COLLECTION_LOG_REL).read_text(encoding="utf-8")
    combined = "\n".join([digest, extracts, log])
    assert "COPY_ME_NOT_FULL_CHAPTER_PROSE" not in combined
    assert "metadata_summary_structure_only_no_raw_chapter_text" in extracts
    assert "metadata_only_no_chapter_fetch" in extracts


def test_creative_reference_collection_indexes_local_manual_import_metadata_only(tmp_path: Path) -> None:
    local_dir = tmp_path / "local_refs"
    local_dir.mkdir()
    (local_dir / "AI觉醒路-中华清扬.txt").write_text("COPY_ME_NOT_LOCAL_PROSE", encoding="utf-8")
    (local_dir / "13号基地-叶枫211.txt").write_text("ALSO_DO_NOT_COPY", encoding="utf-8")

    result = collect_creative_reference_materials(
        tmp_path,
        checked_at="2026-05-16T13:00:00+08:00",
        source_specs=[
            {
                "source_id": "local_scifi_library",
                "title": "本地科幻小说库",
                "platform": "local_filesystem",
                "local_path": str(local_dir),
                "permission": "manual_import",
                "safe_use": "仅做本地参考元数据索引。",
            }
        ],
    )

    assert result["status"] == "collected"
    assert result["local_reference_files"] == 2
    assert (tmp_path / LOCAL_REFERENCE_INDEX_REL).exists()
    assert (tmp_path / LOCAL_REFERENCE_DIGEST_REL).exists()
    index_text = (tmp_path / LOCAL_REFERENCE_INDEX_REL).read_text(encoding="utf-8")
    digest_text = (tmp_path / LOCAL_REFERENCE_DIGEST_REL).read_text(encoding="utf-8")
    combined = index_text + digest_text
    assert "AI觉醒路" in combined
    assert "中华清扬" in combined
    assert "COPY_ME_NOT_LOCAL_PROSE" not in combined
    assert "ALSO_DO_NOT_COPY" not in combined
    source_specs = [
        {
            "source_id": "local_scifi_library",
            "title": "本地科幻小说库",
            "platform": "local_filesystem",
            "local_path": str(local_dir),
            "permission": "manual_import",
            "safe_use": "仅做本地参考元数据索引。",
        }
    ]
    state_result = run_creative_writing_maintenance(
        tmp_path,
        checked_at="2026-05-16T13:30:00+08:00",
        daily_target=1,
        collect_references=True,
        reference_source_specs=source_specs,
    )
    assert state_result["reference_collection"]["local_reference_files"] == 2
    run_creative_writing_maintenance(
        tmp_path,
        checked_at="2026-05-16T14:00:00+08:00",
        daily_target=1,
        collect_references=False,
    )
    state = read_creative_writing_state(tmp_path)
    assert state["reference_local_files"] == 2
    assert state["reference_local_index_path"].endswith("local_reference_index.jsonl")


def test_creative_reference_state_survives_novel_mode_maintenance(tmp_path: Path) -> None:
    run_creative_writing_maintenance(
        tmp_path,
        checked_at="2026-05-16T08:00:00+08:00",
        daily_target=1,
        collect_references=True,
    )
    before = read_creative_writing_state(tmp_path)
    assert before["reference_collection_status"] == "collected"
    assert before["reference_sources_collected"] >= 1

    run_creative_writing_maintenance(
        tmp_path,
        checked_at="2026-05-16T10:00:00+08:00",
        daily_target=1,
        collect_references=False,
    )

    after = read_creative_writing_state(tmp_path)
    assert after["reference_collection_status"] == "collected"
    assert after["reference_sources_collected"] == before["reference_sources_collected"]


def test_novel_mode_generates_continuous_non_repeating_first_arc(tmp_path: Path) -> None:
    run_creative_writing_maintenance(
        tmp_path,
        checked_at="2026-05-15T09:00:00+08:00",
        daily_target=3,
    )
    run_creative_writing_maintenance(
        tmp_path,
        checked_at="2026-05-16T09:00:00+08:00",
        daily_target=3,
    )

    chapters = _chapters(tmp_path)
    assert [path.name for path in chapters] == [
        "chapter-001.md",
        "chapter-002.md",
        "chapter-003.md",
        "chapter-004.md",
        "chapter-005.md",
        "chapter-006.md",
    ]
    all_paragraphs: list[str] = []
    for path in chapters:
        paragraphs = _paragraphs(path)
        assert len(paragraphs) == len(set(paragraphs))
        assert _body_chars(path) >= MIN_PLATFORM_CHARS
        all_paragraphs.extend(paragraphs)

    assert len(all_paragraphs) == len(set(all_paragraphs))
    chapter_texts = [path.read_text(encoding="utf-8") for path in chapters]
    assert chapter_texts[0].count("动作发生得很慢") <= 1
    assert chapter_texts[0].count("这些细节没有组成解释") <= 1
    assert chapter_texts[0].count("偏差没有马上给出回报") <= 1
    assert "给他们安全感" not in chapter_texts[0]
    assert "而他们现在需要的是" not in chapter_texts[0]
    for stiff_marker in (
        "这不是孤立的异象",
        "没有把第 001 次异常当成谜语",
        "已经把自己收拾得接近正常",
        "这块水痕让",
        "真正危险的不是异常出现",
        "报告太慢",
    ):
        assert stiff_marker not in chapter_texts[0]
    assert "第二枚钥匙" not in chapter_texts[0]
    assert "去找失眠档案馆" in chapter_texts[0]
    assert "方岑" not in chapter_texts[0][:2500]
    assert "阿眠" not in chapter_texts[0][:2500]
    assert "林知遥" in chapter_texts[1]
    for fourth_wall_marker in (
        "前一章",
        "上一章",
        "本章",
        "下一章",
        "章节卡",
        "创作工程层",
        "market_score",
    ):
        assert all(fourth_wall_marker not in text for text in chapter_texts)
    assert "那枚带着雨水气味的蓝色纸签" in chapter_texts[1]
    assert "明天之前找到失眠档案馆" in chapter_texts[2]
    assert "第二枚密钥" in chapter_texts[3]
    assert "六点十七分" in chapter_texts[4]
    assert "一二五号避难所" in chapter_texts[4]
    assert "收件人：星桥" in chapter_texts[5]
