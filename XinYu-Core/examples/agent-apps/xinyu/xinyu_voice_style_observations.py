from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

PUBLIC_REFERENCE_SOURCES: tuple[dict[str, str], ...] = (
    {
        "name": "Chinese-Dialogue-Dataset",
        "url": "https://github.com/YouTaoBaBa/Chinese-Dialogue-Dataset",
        "note": "中文开放对话数据集汇总，包含 NaturalConv、LCCC、豆瓣多轮等。",
    },
    {
        "name": "CDial-GPT / LCCC",
        "url": "https://github.com/thu-coai/CDial-GPT",
        "note": "LCCC 来源包含微博、贴吧、豆瓣、字幕、小黄鸡等短文本对话；公开 README 给出样例。",
    },
    {
        "name": "DDmkTCCorpus",
        "url": "https://github.com/TinyTalks/DDmkTCCorpus",
        "note": "历时弹幕文本评论语料库，强调 B 站弹幕短文本属性。",
    },
    {
        "name": "bilibili_comments_crawl",
        "url": "https://github.com/FunnySaltyFish/bilibili_comments_crawl",
        "note": "基于 B 站评论区构建对话链，README 和 example_data 提供公开样例。",
    },
)

PUBLIC_CORPUS_FINDINGS: tuple[dict[str, Any], ...] = (
    {
        "name": "NaturalConv",
        "scale": "19.9K conversations / 400K utterances / average 20.1 turns",
        "style_signal": "多轮话题推进，不是一次性完整说明；适合学习上下文承接。",
    },
    {
        "name": "LCCC-base",
        "scale": "3,354,232 single-turn sessions + 3,466,274 multi-turn sessions; avg 6.79/8.32 words per utterance",
        "style_signal": "短文本对话平均词数很低，主动消息不应长篇解释。",
    },
    {
        "name": "LCCC-large",
        "scale": "7,273,804 single-turn sessions + 4,733,955 multi-turn sessions; avg 7.45/8.14 words per utterance",
        "style_signal": "微博/贴吧/豆瓣等混合来源更接近日常短回复。",
    },
    {
        "name": "Tieba Corpus in LCCC",
        "scale": "2.32M sessions",
        "style_signal": "贴吧回复常见省略、吐槽、顺着上文接一句。",
    },
    {
        "name": "Douban Conversation Corpus in LCCC",
        "scale": "0.5M sessions",
        "style_signal": "豆瓣多轮对话有更明显的上下文连续性。",
    },
    {
        "name": "DDmkTCCorpus",
        "scale": "2017-2020 Bilibili videos over 1M views; danmaku text corpus",
        "style_signal": "弹幕极短、强上下文、常省略主语。",
    },
    {
        "name": "bilibili_comments_crawl",
        "scale": "comment-tree paths with minimum dialog length filtering",
        "style_signal": "评论区对话是树状接话，不是客服式问答。",
    },
)

PUBLIC_EXAMPLES: tuple[str, ...] = (
    "貌似没人来",
    "兄弟你还在吗！(=・ω・=)",
    "嗯?(〜￣△￣)〜",
    "哇前辈确认存活！大佬!",
    "：）",
    "可怜的二楼(=・ω・=)",
    "一楼了",
    "原来的一楼去哪里[蛆音娘_吃惊]",
    "下去了(｀・ω・´)",
    "我划了一万一( •̥́ ˍ •̀ू )",
    "+1(〜￣△￣)〜",
    "你你你..你是怎么找到这里来的Σ(ﾟдﾟ;)",
    "现在你都六级了，我才五级[大哭]",
    "你也六级了",
    "话说2楼这位前辈还活着，8号还投了稿",
    "？？",
    "原来你的微博还在更新",
    "考古学家到此一游(｀・ω・´)",
    "考古考古学家[doge][doge][doge]",
    "2020了呢~",
    "也是来考古的嘛。[doge]",
    "评论提醒就来看看",
    "好早之前了救命，时间流逝太快了。[拥抱]",
    "都在考古呢",
    "你不是一个人(･∀･)",
    "你号怎么没了[无语]",
    "被封了还行",
    "我们现在在考古你呢",
    "我这一年了算是考古你嘛",
    "现在又变成我考古你们了233[小电视_赞]",
    "发生了什么，大佬被封禁了[热词系列_知识增加]",
    "惊了",
    "我也[热词系列_知识增加]",
    "被删掉的番剧??好像b站以前有缘之空的……",
    "对的，评分还很高，好像有9.8分",
    "额⊙∀⊙！",
    "同上网搜w",
    "同道中人，同道中人",
    "这么老的评论都能翻牌[笑哭]b站当时连番剧评分系统都没呢哪来的评分啊兄[doge]",
    "我一样，宿舍四个人，只叮我，b型血",
    "b血加一，一个屋里人家能骑着被子我得从头到脚裹严实",
    "我是176cm，55kg的肌肉女",
    "我特讨厌吃甜食，爱喝水不喝饮料，不吃肉，只吃鱼和蔬菜，血糖正常。[OK]",
    "火锅我在重庆成都吃了七八顿火锅",
    "哈哈哈哈！那我的嘴巴可能要烂掉！",
    "你谈过恋爱么",
    "谈过，哎，别提了，伤心..",
    "看原版英文电影学纯正英语",
    "大爱老友记反复看了好多次了",
    "一样光盘都快被我看花了",
    "那你现在的英语应该不错了",
    "我今天腿都废了，你们过节，我搬砖",
    "辛苦啊，圣诞节还去赚大钱了加油",
    "毕竟是没男朋友的人，什么节都是一样的",
    "这居然是北京不是哈尔滨。",
    "哈尔滨的天气好像比北京好点",
    "我以为是马云的广告。",
    "最后一件太美了",
    "你可拉到吧",
    "别学我说话",
    "我说话就是你不行。",
    "不，是逼你动口是吧",
    "为什么乡民总是欺负国高中生呢QQ",
    "如果以为选好科系就会变成比尔盖兹那不如退学吧",
    "前排，鲁迷们都起床了吧",
    "标题说助攻，但是看了那球，真是活生生的讽刺了",
    "看来你很爱钱",
    "噢是吗？那么你也差不多了",
    "这个会不会聚划算",
    "暂时没有哦",
    "后期会不会有",
    "不一定哦亲多多关注我们哦",
    "一楼",
    "二楼",
    "三楼",
    "我也抢三楼",
    "你抢失败了哈哈",
    "怎么无情嘲笑",
    "哈哈哈哈，有点离谱",
    "有点慢哈",
    "9月9",
    "考古",
    "我来自2023年，只是埋一个时间胶囊",
    "考古，这个视频都要成骨灰了",
    "运营商校园广告大PK，太欢乐了！哈哈哈。",
    "你喜欢吗？",
    "这会不会太离谱了",
    "还有人吗",
    "前面的还在吗",
    "这个也能翻到？",
    "所以现在还算数吗",
    "那后来呢",
    "真的假的啊",
    "不是吧",
    "这也行？",
)

FORBIDDEN_PROACTIVE_PATTERNS: tuple[str, ...] = (
    "我想问你一件小事",
    "我想把这点先给你看",
    "根据当前状态",
    "建议你",
    "是否需要我",
    "请确认",
    "当前检测到",
    "我将为你",
)

OBSERVATION_RULES: tuple[str, ...] = (
    "主动消息优先像熟人接话，不像通知、报告或客服询问。",
    "能靠上下文理解时，压缩 topic：那个、那条、那块、那张、刚才那个。",
    "短问句优先，通常 4-14 个汉字；工程词只在必要时保留。",
    "可以省主语，不必每句都以“我”开头。",
    "允许轻微不完整，但不能让 owner 看不懂正在指哪件事。",
    "保留边界：不复制公网原句到 owner 私聊，不引入脏话/攻击/隐私内容。",
)

CONTEXTUAL_TOPIC_REWRITES: tuple[tuple[str, str], ...] = (
    (r".*主动消息.*句子.*", "那几句"),
    (r".*生活事件.*主动消息.*闭环.*", "刚才那条链"),
    (r".*生活事件.*链路.*", "刚才那条链"),
    (r".*主动直发.*", "直发那块"),
    (r".*表达层.*契约.*", "表现那块"),
    (r".*expression.*contract.*", "表现那块"),
    (r".*人格状态卡.*Desktop.*", "Desktop 那张卡"),
    (r".*Desktop.*人格状态卡.*", "Desktop 那张卡"),
    (r".*QQ.*outbox.*", "QQ 那条"),
    (r".*自我整理.*", "自我整理那块"),
)


def analyse_public_examples(examples: tuple[str, ...] = PUBLIC_EXAMPLES) -> dict[str, Any]:
    cleaned = [_strip_markup(example) for example in examples if _strip_markup(example)]
    lengths = [len(example) for example in cleaned]
    starters = Counter(example[:2] for example in cleaned if len(example) >= 2)
    endings = Counter(example[-1:] for example in cleaned if example)
    question_count = sum(1 for example in examples if example.rstrip().endswith(("?", "？")) or "吗" in example)
    first_person_count = sum(1 for example in cleaned if example.startswith("我"))
    short_reply_count = sum(1 for length in lengths if length <= 8)
    medium_reply_count = sum(1 for length in lengths if 9 <= length <= 18)
    long_reply_count = sum(1 for length in lengths if length > 18)
    particle_count = sum(1 for example in cleaned if example.endswith(("啊", "吧", "呢", "嘛", "哈", "哦", "了")))
    return {
        "example_count": len(examples),
        "corpus_finding_count": len(PUBLIC_CORPUS_FINDINGS),
        "average_visible_chars": round(sum(lengths) / max(1, len(lengths)), 2),
        "max_visible_chars": max(lengths or [0]),
        "short_reply_count": short_reply_count,
        "medium_reply_count": medium_reply_count,
        "long_reply_count": long_reply_count,
        "question_like_count": question_count,
        "first_person_start_count": first_person_count,
        "particle_ending_count": particle_count,
        "common_starters": starters.most_common(16),
        "common_endings": endings.most_common(12),
    }


def write_voice_style_observations(root: Path, *, updated_at: str | None = None) -> Path:
    root = root.resolve()
    updated_at = updated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    analysis = analyse_public_examples()
    path = root / "memory/self/voice_style_observations.md"
    lines = [
        "# Voice Style Observations",
        "",
        f"updated_at: {updated_at}",
        "status: public_reference_only",
        "stable_persona_write: blocked",
        "owner_memory_write: blocked",
        "raw_private_body_retained: false",
        "",
        "## Public reference sources",
    ]
    for source in PUBLIC_REFERENCE_SOURCES:
        lines.append(f"- {source['name']}: {source['url']} — {source['note']}")
    lines.extend(["", "## Corpus-level findings"])
    for finding in PUBLIC_CORPUS_FINDINGS:
        lines.append(f"- {finding['name']}: {finding['scale']} — {finding['style_signal']}")
    lines.extend(
        [
            "",
            "## Aggregate observations",
            f"- example_count: {analysis['example_count']}",
            f"- corpus_finding_count: {analysis['corpus_finding_count']}",
            f"- average_visible_chars: {analysis['average_visible_chars']}",
            f"- max_visible_chars: {analysis['max_visible_chars']}",
            f"- short_reply_count: {analysis['short_reply_count']}",
            f"- medium_reply_count: {analysis['medium_reply_count']}",
            f"- long_reply_count: {analysis['long_reply_count']}",
            f"- question_like_count: {analysis['question_like_count']}",
            f"- first_person_start_count: {analysis['first_person_start_count']}",
            f"- particle_ending_count: {analysis['particle_ending_count']}",
            f"- common_starters: {json.dumps(analysis['common_starters'], ensure_ascii=False)}",
            f"- common_endings: {json.dumps(analysis['common_endings'], ensure_ascii=False)}",
            "",
            "## Rules for XinYu proactive owner-private speech",
        ]
    )
    lines.extend(f"- {rule}" for rule in OBSERVATION_RULES)
    lines.extend(["", "## Forbidden visible proactive patterns"])
    lines.extend(f"- {pattern}" for pattern in FORBIDDEN_PROACTIVE_PATTERNS)
    lines.extend(["", "## Contextual topic rewrites"])
    for pattern, replacement in CONTEXTUAL_TOPIC_REWRITES:
        lines.append(f"- `{pattern}` -> `{replacement}`")
    lines.extend(
        [
            "",
            "## Notes",
            "- These examples are public short-text references used only to derive aggregate style constraints.",
            "- Do not paste public users' personal content into XinYu's private messages.",
            "- Do not use this file as permission to write stable persona or owner memory.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def proactive_style_guard(text: str) -> dict[str, Any]:
    visible = _strip_markup(str(text or "")).strip()
    forbidden = [pattern for pattern in FORBIDDEN_PROACTIVE_PATTERNS if pattern in visible]
    return {
        "accepted": bool(visible) and not forbidden and len(visible) <= 42,
        "visible_chars": len(visible),
        "forbidden_patterns": forbidden,
        "too_long": len(visible) > 42,
        "notes": _guard_notes(visible, forbidden),
    }


def _guard_notes(visible: str, forbidden: list[str]) -> list[str]:
    notes: list[str] = []
    if not visible:
        notes.append("empty_visible_text")
    if forbidden:
        notes.append("forbidden_template_pattern")
    if len(visible) > 42:
        notes.append("too_long_for_proactive_short_text")
    return notes


def _strip_markup(text: str) -> str:
    text = re.sub(r"\[[^\]]{1,24}\]", "", text)
    text = re.sub(r"[\(（][=・ω´｀￣△▽∀⊙ﾟд;≧∇ノ〜\\/\s]+[\)）]", "", text)
    return re.sub(r"\s+", "", text).strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write public-reference voice style observations for XinYu.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--updated-at", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    path = write_voice_style_observations(args.root, updated_at=args.updated_at)
    result = {"accepted": True, "path": str(path), "analysis": analyse_public_examples()}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"wrote: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
