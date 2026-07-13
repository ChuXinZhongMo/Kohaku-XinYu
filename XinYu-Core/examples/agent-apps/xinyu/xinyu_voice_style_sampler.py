from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_voice_style_observations import PUBLIC_CORPUS_FINDINGS, PUBLIC_EXAMPLES
from xinyu_voice_style_sampler_store import write_voice_style_sample_report_text

BANNED_SAMPLE_PATTERNS: tuple[str, ...] = (
    "傻逼",
    "你妈",
    "滚",
    "去死",
    "操你",
    "艹",
    "nmsl",
    "sb",
    "身份证",
    "手机号",
    "银行卡",
    "token",
    "api_key",
)

DEICTIC_MARKERS: tuple[str, ...] = ("这个", "那个", "这", "那", "刚才", "前面", "后面", "现在", "后来")
CONTINUATION_MARKERS: tuple[str, ...] = ("还", "也", "就", "又", "再", "继续", "后来", "然后", "所以")
QUESTION_MARKERS: tuple[str, ...] = ("吗", "呢", "？", "?", "怎么", "为什么", "真的假的", "还有人吗", "还在吗")
PARTICLE_ENDINGS: tuple[str, ...] = ("啊", "吧", "呢", "嘛", "哈", "哦", "了", "啦", "呗")

SCENE_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("接上文/考古", ("考古", "原来", "现在", "前面", "后来", "翻到", "评论提醒")),
    ("确认/追问", ("吗", "？", "怎么", "为什么", "真的假的", "还有人", "还在")),
    ("附和/同感", ("我也", "+1", "一样", "同", "你不是一个人")),
    ("惊讶/吐槽", ("惊", "离谱", "不是吧", "这也行", "哈哈", "笑", "救命")),
    ("继续/收束", ("后来", "所以", "继续", "还", "现在")),
)


def collect_public_style_samples(raw_samples: tuple[str, ...] = PUBLIC_EXAMPLES) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_samples:
        text = normalize_public_sample(raw)
        if not text or text in seen:
            continue
        seen.add(text)
        if not is_safe_public_style_sample(text):
            continue
        samples.append(
            {
                "text": text,
                "visible_chars": len(text),
                "length_bucket": length_bucket(text),
                "is_question_like": is_question_like(text),
                "starts_first_person": text.startswith("我"),
                "has_deictic_marker": any(marker in text for marker in DEICTIC_MARKERS),
                "has_continuation_marker": any(marker in text for marker in CONTINUATION_MARKERS),
                "ends_with_particle": text.endswith(PARTICLE_ENDINGS),
                "scene_tags": classify_scene_tags(text),
            }
        )
    return samples


def analyse_style_samples(samples: list[dict[str, Any]]) -> dict[str, Any]:
    bucket_counts = Counter(sample["length_bucket"] for sample in samples)
    scene_counts: Counter[str] = Counter()
    ending_counts: Counter[str] = Counter()
    starter_counts: Counter[str] = Counter()
    for sample in samples:
        text = sample["text"]
        ending_counts[text[-1:]] += 1
        starter_counts[text[:2]] += 1
        for tag in sample["scene_tags"]:
            scene_counts[tag] += 1
    total = max(1, len(samples))
    return {
        "sample_count": len(samples),
        "corpus_finding_count": len(PUBLIC_CORPUS_FINDINGS),
        "length_buckets": dict(bucket_counts),
        "question_like_count": sum(1 for sample in samples if sample["is_question_like"]),
        "first_person_start_count": sum(1 for sample in samples if sample["starts_first_person"]),
        "deictic_marker_count": sum(1 for sample in samples if sample["has_deictic_marker"]),
        "continuation_marker_count": sum(1 for sample in samples if sample["has_continuation_marker"]),
        "particle_ending_count": sum(1 for sample in samples if sample["ends_with_particle"]),
        "scene_counts": dict(scene_counts.most_common()),
        "common_starters": starter_counts.most_common(16),
        "common_endings": ending_counts.most_common(16),
        "short_ratio": round(bucket_counts.get("short", 0) / total, 3),
        "contextual_ratio": round(
            sum(1 for sample in samples if sample["has_deictic_marker"] or sample["has_continuation_marker"]) / total,
            3,
        ),
    }


def proactive_scene_templates(scene: str, topic: str) -> tuple[str, ...]:
    topic = normalize_proactive_topic(topic)
    if scene == "接上文/考古":
        return ("刚才那个还弄吗", f"{topic}还接吗", f"{topic}接着？")
    if scene == "确认/追问":
        return (f"{topic}还要吗", "这个还要吗", f"{topic}还看吗")
    if scene == "继续/收束":
        return (f"{topic}我接着？", "那我接着？", f"{topic}继续吗")
    if scene == "附和/同感":
        return (f"{topic}我也觉得怪", "这块我也有点在意", f"{topic}我也卡着")
    if scene == "不打扰":
        return ("那我先不吵你", "我先收着", "那我先放一会儿")
    return (f"{topic}还接吗", "刚才那个还弄吗", "我继续吗")


def infer_proactive_scene(text: str) -> str:
    compact = str(text or "")
    if any(marker in compact for marker in ("不打扰", "先不", "晚点", "不用现在")):
        return "不打扰"
    if any(marker in compact for marker in ("继续", "接着", "接上", "收束", "跑一遍", "弄完")):
        return "继续/收束"
    if any(marker in compact for marker in ("确认", "检查", "是不是", "是否", "要不要", "吗", "？", "?")):
        return "确认/追问"
    if any(marker in compact for marker in ("也觉得", "我也", "一样", "同感", "怪")):
        return "附和/同感"
    if any(marker in compact for marker in ("刚才", "前面", "之前", "那条", "那块", "这块")):
        return "接上文/考古"
    return "接上文/考古"


def normalize_proactive_topic(topic: str) -> str:
    value = re.sub(r"\s+", " ", str(topic or "")).strip(" ，,：:。.?？")
    return value or "这个"


def derive_proactive_constraints(analysis: dict[str, Any]) -> list[str]:
    constraints = [
        "主动消息默认短句；优先 4-14 个可见字，超过 24 字要有明确原因。",
        "能指回上下文时，用“刚才那个/那块/那条/那几句”压缩，不复述完整工程名。",
        "问句可以不完整，但必须能被最近上下文解释。",
        "避免连续第一人称开头；真实短回复里第一人称不是默认入口。",
        "可以用轻量语气词收尾，但不要把公网评论腔照搬成卖萌。",
        "拒绝客服/系统词：请确认、当前检测到、是否需要我、我将为你。",
    ]
    if analysis.get("contextual_ratio", 0) < 0.25:
        constraints.append("样本上下文指代比例还偏低，下一轮优先补评论链/多轮对话而不是孤立句子。")
    return constraints


def write_style_sample_report(root: Path, *, updated_at: str | None = None) -> Path:
    root = root.resolve()
    updated_at = updated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    samples = collect_public_style_samples()
    analysis = analyse_style_samples(samples)
    constraints = derive_proactive_constraints(analysis)
    lines = [
        "# Voice Style Sample Report",
        "",
        f"updated_at: {updated_at}",
        "status: public_aggregate_style_sampling_only",
        "stable_persona_write: blocked",
        "owner_memory_write: blocked",
        "raw_private_body_retained: false",
        "",
        "## Corpus basis",
    ]
    for finding in PUBLIC_CORPUS_FINDINGS:
        lines.append(f"- {finding['name']}: {finding['scale']} — {finding['style_signal']}")
    lines.extend(
        [
            "",
            "## Sample analysis",
            f"- sample_count: {analysis['sample_count']}",
            f"- length_buckets: {json.dumps(analysis['length_buckets'], ensure_ascii=False, sort_keys=True)}",
            f"- short_ratio: {analysis['short_ratio']}",
            f"- contextual_ratio: {analysis['contextual_ratio']}",
            f"- question_like_count: {analysis['question_like_count']}",
            f"- first_person_start_count: {analysis['first_person_start_count']}",
            f"- deictic_marker_count: {analysis['deictic_marker_count']}",
            f"- continuation_marker_count: {analysis['continuation_marker_count']}",
            f"- particle_ending_count: {analysis['particle_ending_count']}",
            f"- scene_counts: {json.dumps(analysis['scene_counts'], ensure_ascii=False, sort_keys=True)}",
            f"- common_starters: {json.dumps(analysis['common_starters'], ensure_ascii=False)}",
            f"- common_endings: {json.dumps(analysis['common_endings'], ensure_ascii=False)}",
            "",
            "## Derived proactive constraints",
        ]
    )
    lines.extend(f"- {constraint}" for constraint in constraints)
    lines.extend(["", "## Safe sampled pattern examples"])
    for sample in samples[:32]:
        lines.append(
            f"- `{sample['text']}` — len={sample['visible_chars']}; "
            f"bucket={sample['length_bucket']}; tags={','.join(sample['scene_tags']) or 'none'}"
        )
    lines.extend(
        [
            "",
            "## Boundaries",
            "- This report samples public style signals only; it is not permission to copy public users into owner-private speech.",
            "- Do not write stable persona or owner memory from this report.",
            "- Keep proactive delivery gates, owner-private routing, cooldown and dedupe unchanged.",
        ]
    )
    return write_voice_style_sample_report_text(root, "\n".join(lines).rstrip() + "\n")


def normalize_public_sample(text: Any) -> str:
    value = str(text or "")
    value = re.sub(r"回复\s*@[^:：]{1,30}[:：]", "", value)
    value = re.sub(r"\[[^\]]{1,24}\]", "", value)
    value = re.sub(r"[\r\n\t]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:80]


def is_safe_public_style_sample(text: str) -> bool:
    compact = text.lower().replace(" ", "")
    if len(text) < 1 or len(text) > 80:
        return False
    return not any(pattern in compact for pattern in BANNED_SAMPLE_PATTERNS)


def length_bucket(text: str) -> str:
    length = len(text)
    if length <= 8:
        return "short"
    if length <= 18:
        return "medium"
    if length <= 32:
        return "long"
    return "too_long"


def is_question_like(text: str) -> bool:
    return text.rstrip().endswith(("?", "？")) or any(marker in text for marker in QUESTION_MARKERS)


def classify_scene_tags(text: str) -> list[str]:
    tags: list[str] = []
    for tag, markers in SCENE_PATTERNS:
        if any(marker in text for marker in markers):
            tags.append(tag)
    return tags


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sample public Chinese short-dialogue style signals for XinYu.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--updated-at", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    path = write_style_sample_report(args.root, updated_at=args.updated_at)
    samples = collect_public_style_samples()
    result = {"accepted": True, "path": str(path), "analysis": analyse_style_samples(samples)}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"wrote: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
