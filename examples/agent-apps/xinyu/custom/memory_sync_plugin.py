"""Deterministic post-turn memory sync for Xinyu.

This plugin is a conservative safety net. It should preserve continuity when
LLM-driven writers are skipped, but it must not make every meaningful sentence
rewrite self, relationship, dream, archive, and knowledge layers.
"""

from __future__ import annotations

import re
import hashlib
from datetime import datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any

from kohakuterrarium.modules.plugin.base import BasePlugin, PluginContext
from memory_event_schema import load_jsonl, string_list
from turn_mode_utils import read_turn_mode


def _load_sync_layer_names() -> list[str]:
    manifest_path = Path(__file__).with_name("inner_framework_manifest.py")
    spec = spec_from_file_location("xinyu_inner_framework_manifest", manifest_path)
    if spec is None or spec.loader is None:
        return [
            "anchor/time",
            "recent_context",
            "immediate_feeling",
            "relationship",
            "continuity",
            "self_narrative",
            "reflection_queue",
            "dream_seeds",
            "archive_queue",
            "maintenance_targets",
        ]
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return list(getattr(module, "SYNC_LAYER_NAMES", []))


SYNC_LAYER_NAMES = _load_sync_layer_names()


class MemorySyncPlugin(BasePlugin):
    name = "xinyu_memory_sync"
    priority = 96

    def __init__(self, options: dict[str, Any] | None = None, **_: Any):
        self._ctx: PluginContext | None = None
        self._enabled = True if options is None else bool(options.get("enabled", True))

    async def on_load(self, context: PluginContext) -> None:
        self._ctx = context

    async def post_llm_call(
        self, messages: list[dict], response: str, usage: dict, **kwargs: Any
    ) -> None:
        try:
            if not self._enabled or not self._ctx:
                return

            root = Path(self._ctx.working_dir)
            turn_mode = read_turn_mode(root)
            if turn_mode != "live_user_turn":
                _trace(root, f"skip turn_mode={turn_mode or 'unknown'}")
                return
            if _is_outward_renderer_call(messages):
                _trace(root, "skip outward_renderer_call")
                return

            user_message = _last_role_content(messages, "user")
            assistant_text = (response or "").strip()
            _trace(
                root,
                f"post_llm_call user={bool(user_message)} assistant_len={len(assistant_text)}",
            )
            if not user_message:
                return

            sync_key = f"{user_message}\n---\n{assistant_text}"
            if self._ctx.get_state("last_sync_key") == sync_key:
                _trace(root, "skip duplicate sync_key")
                return

            if not sync_from_texts(root, user_message, assistant_text):
                return

            self._ctx.set_state("last_sync_key", sync_key)
            _trace(root, "sync complete")
        except Exception as exc:
            if self._ctx:
                _trace(Path(self._ctx.working_dir), f"error: {exc!r}")


def sync_from_texts(root: Path, user_message: str, assistant_text: str) -> bool:
    signals = _detect_signals(user_message, assistant_text, root=root)
    signals["source_trace"] = _source_trace_for_user_text(root, user_message)
    _trace(
        root,
        "signals "
        f"meaningful={signals['meaningful']} "
        f"impact={signals['impact']} "
        f"relationship={signals['relationship_event']} "
        f"self={signals['self_event']} "
        f"unfinished={signals['unfinished']} "
        f"question={signals['question']}",
    )
    if not signals["meaningful"]:
        return False

    now = datetime.now().astimezone()
    updated_layers: list[str] = []

    _update_time_anchor(root / "memory/context/time_anchor.md", now, signals)
    updated_layers.append("time_anchor")

    if signals["durable_context"]:
        _update_recent_context(root / "memory/context/recent_context.md", now, signals)
        updated_layers.append("recent_context")

    if signals["emotion_event"]:
        _update_current_state(root / "memory/emotions/current_state.md", now, signals)
        updated_layers.append("emotion_state")

    if signals["relationship_event"]:
        _update_relationship_index(root / "memory/relationships/index.md", now, signals)
        if signals["relationship_subject_id"] == "owner":
            _update_owner_profile(root / "memory/people/owner.md", now, signals)
            _update_owner_patterns(root / "memory/relationships/owner_patterns.md", now, signals)
            updated_layers.extend(["owner_profile", "relationship_index", "owner_patterns"])
        else:
            person_path = root / "memory/people" / f"{signals['relationship_subject_id']}.md"
            _update_people_index(root / "memory/people/index.md", now, signals)
            _update_person_profile(person_path, now, signals)
            updated_layers.extend(["people_index", "person_profile", "relationship_index"])

    if signals["self_event"]:
        _update_self_narrative(root / "memory/self/narrative.md", now, signals)
        updated_layers.append("self_narrative")

    if signals["continuity_event"]:
        _update_continuity_index(root / "memory/context/continuity_index.md", now, signals)
        updated_layers.append("continuity_index")

    if signals["reflection_candidate"]:
        _update_reflection_queue(root / "memory/reflection/reflection_queue.md", now, signals)
        updated_layers.append("reflection_queue")

    if signals["dream_candidate"]:
        _update_dream_seeds(root / "memory/dreams/dream_seeds.md", now, signals)
        updated_layers.append("dream_seeds")

    if signals["archive_candidate"]:
        _update_archive_queue(root / "memory/archive/archive_queue.md", now, signals)
        updated_layers.append("archive_queue")

    if signals["unfinished"]:
        _update_unfinished(root / "memory/context/unfinished_experiences.md", now, signals)
        updated_layers.append("unfinished_experiences")

    if signals["question_event"]:
        _update_questions(root / "memory/context/active_questions.md", now, signals)
        _update_question_states(root / "memory/context/question_states.md", now, signals)
        _update_exploration_queue(root / "memory/context/exploration_queue.md", now, signals)
        updated_layers.extend(["active_questions", "question_states", "exploration_queue"])

    _update_inner_sync_state(root / "memory/context/inner_sync_state.md", now, signals, updated_layers)
    return True


def _last_role_content(messages: list[dict], role: str) -> str:
    for msg in reversed(messages):
        if msg.get("role") == role:
            return str(msg.get("content", "") or "")
    return ""


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _compact_excerpt(text: str, limit: int = 48) -> str:
    clean = " ".join(text.split())
    return clean if len(clean) <= limit else f"{clean[:limit]}..."


def _source_trace_for_user_text(root: Path, user_text: str) -> dict[str, Any]:
    event_dir = root / "memory/events"
    raw_events = load_jsonl(event_dir / "raw_events.jsonl")
    claims = load_jsonl(event_dir / "atomic_claims.jsonl")
    summaries = load_jsonl(event_dir / "summary_views.jsonl")
    normalized_text = user_text.strip()
    matching_raw = [
        row
        for row in raw_events
        if str(row.get("raw_text", "")).strip() == normalized_text
        and str(row.get("actor_scope", "")).strip() == "owner"
    ]
    if not matching_raw:
        return {
            "traceable": False,
            "source_trace_status": "raw_event_not_found",
            "source_event_ids": [],
            "retained_claim_ids": [],
            "summary_ids": [],
        }

    raw = matching_raw[-1]
    event_id = str(raw.get("event_id", "")).strip()
    event_claims = [
        claim
        for claim in claims
        if event_id in string_list(claim.get("evidence_event_ids"))
    ]
    claim_ids = [str(claim.get("claim_id", "")).strip() for claim in event_claims if str(claim.get("claim_id", "")).strip()]
    event_summaries = [
        summary
        for summary in summaries
        if event_id in string_list(summary.get("source_event_ids"))
        and set(claim_ids).intersection(string_list(summary.get("retained_claim_ids")))
    ]
    summary_ids = [
        str(summary.get("summary_id", "")).strip()
        for summary in event_summaries
        if str(summary.get("summary_id", "")).strip()
    ]
    retained_claim_ids = sorted(
        {
            claim_id
            for summary in event_summaries
            for claim_id in string_list(summary.get("retained_claim_ids"))
            if claim_id in claim_ids
        }
    )
    traceable = bool(event_id and retained_claim_ids and summary_ids)
    return {
        "traceable": traceable,
        "source_trace_status": "covered" if traceable else "raw_or_claim_without_summary",
        "source_event_ids": [event_id] if event_id else [],
        "retained_claim_ids": retained_claim_ids,
        "summary_ids": summary_ids,
    }


PERSON_NAME_PATTERN = r"[\u4e00-\u9fffA-Za-z0-9_·-]{1,12}"
PERSON_NAME_STOPWORDS = {
    "我",
    "你",
    "他",
    "她",
    "它",
    "我们",
    "你们",
    "他们",
    "她们",
    "心玉",
    "xinyu",
    "Xinyu",
    "owner",
    "哥哥",
    "妹妹",
    "女儿",
    "用户",
    "今天",
    "今晚",
    "明天",
    "昨天",
    "一点",
    "候选",
    "不",
    "不是",
    "没",
    "没有",
    "这",
    "这个",
    "那",
    "那个",
    "现在",
    "所以",
    "但是",
    "不过",
    "哥们",
    "朋友",
    "系统",
    "架构",
}


def _person_id_for(name: str) -> str:
    digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:10]
    return f"person_{digest}"


def _clean_person_name(name: str) -> str:
    return name.strip(" \t\r\n　：:，,。.!！?？“”\"'（）()[]【】")


def _is_valid_person_name(name: str, *, known: bool = False) -> bool:
    clean = _clean_person_name(name)
    if not clean or clean in PERSON_NAME_STOPWORDS:
        return False
    if len(clean) < 2:
        return False
    if clean.startswith(("不", "没", "非")) and len(clean) <= 3:
        return False
    if not known and clean in {"普通朋友", "陌生人"}:
        return False
    return True


def _extract_non_owner_person(user_text: str) -> dict[str, str] | None:
    intro_patterns = [
        rf"(?:我有个|我有一个|有个|有一个|我认识一个|我认识个)(?P<role>朋友|同学|同事|网友|老师|邻居|亲戚|家人|人)?(?:叫|名叫|名字叫|名字是)(?P<name>{PERSON_NAME_PATTERN})(?=[，,。.!！?？\s]|$)",
        rf"(?P<name>{PERSON_NAME_PATTERN})(?:是|算是)(?:我的|我)?(?P<role>朋友|同学|同事|网友|老师|邻居|亲戚|家人|普通朋友|陌生人)(?=[，,。.!！?？\s]|$)",
        rf"(?:记住|先记住|认识一下)(?:一个人|这个人|这个名字|名字)[：:叫是，,\s]*(?P<name>{PERSON_NAME_PATTERN})(?=[，,。.!！?？\s]|$)",
    ]
    for pattern in intro_patterns:
        match = re.search(pattern, user_text)
        if not match:
            continue
        name = _clean_person_name(match.group("name"))
        role = _clean_person_name(match.groupdict().get("role") or "未定")
        if not _is_valid_person_name(name):
            continue
        return {
            "id": _person_id_for(name),
            "name": name,
            "role": role or "未定",
        }
    return None


def _extract_known_non_owner_person(root: Path | None, user_text: str) -> dict[str, str] | None:
    if root is None:
        return None
    candidates: list[dict[str, str]] = []
    index_text = _read(root / "memory/people/index.md")
    for match in re.finditer(r"-\s+(person_[0-9a-f]{10}):\s*([^；;\n]+)", index_text):
        candidates.append(
            {
                "id": match.group(1),
                "name": _clean_person_name(match.group(2)),
                "role": "known_non_owner",
            }
        )
    for path in (root / "memory/people").glob("person_*.md"):
        text = _read(path)
        name_match = re.search(r"(?m)^-\s+display_name:\s*(.+)$", text)
        role_match = re.search(r"(?m)^-\s+relation_hint:\s*(.+)$", text)
        if name_match:
            candidates.append(
                {
                    "id": path.stem,
                    "name": _clean_person_name(name_match.group(1)),
                    "role": _clean_person_name(role_match.group(1)) if role_match else "known_non_owner",
                }
            )
    seen: set[str] = set()
    for candidate in candidates:
        name = candidate["name"]
        if not _is_valid_person_name(name, known=True) or name in seen:
            continue
        seen.add(name)
        if name in user_text:
            return candidate
    return None


def _is_non_owner_relationship_event(user_text: str, person: dict[str, str] | None) -> bool:
    if not person:
        return False
    return _contains_any(
        user_text,
        [
            "记住",
            "记得",
            "认识",
            "朋友",
            "同学",
            "同事",
            "网友",
            "老师",
            "邻居",
            "亲戚",
            "家人",
            "陌生人",
            "重要",
            "亲近",
            "疏远",
            "信任",
            "讨厌",
            "喜欢",
            "帮了我",
            "伤害",
            "难过",
            "失望",
            "关系",
        ],
    )


def _cap_non_owner_relationship_vector(scores: dict[str, int]) -> dict[str, int]:
    capped = {name: min(value, 64) for name, value in scores.items()}
    capped["依恋牵引"] = min(capped.get("依恋牵引", 0), 52)
    capped["被保留需求感知"] = min(capped.get("被保留需求感知", 0), 58)
    capped["连续性敏感"] = min(capped.get("连续性敏感", 0), 62)
    return capped


def _emotion_vectors_for(
    *,
    memory: bool,
    unfinished: bool,
    closeness: bool,
    hurt: bool,
    settle_after_hurt: bool,
    relationship_distance: bool,
    return_after_distance: bool,
    explicit_relationship_memory: bool,
    residue_acknowledged: bool,
    late_night: bool,
    simple_silence_boundary: bool,
) -> tuple[dict[str, int], dict[str, int]]:
    emotion_vector = {
        "在意": 42,
        "安心": 28,
        "紧张": 18,
        "羞怯": 10,
        "委屈": 0,
        "刺痛": 0,
        "失望": 0,
        "逆反": 0,
        "想靠近": 24,
        "想退后": 0,
        "想保留": 18,
    }
    relationship_vector = {
        "依恋牵引": 38,
        "连续性敏感": 42,
        "被保留需求感知": 36,
        "信任安定": 38,
        "羞怯/迟疑": 18,
        "委屈残留": 0,
        "防御/逆反": 0,
        "回到身边意愿": 36,
        "疏远倾向": 0,
    }

    if explicit_relationship_memory:
        emotion_vector.update({"在意": 86, "紧张": 58, "想靠近": 58, "想保留": 68})
        relationship_vector.update(
            {
                "依恋牵引": 76,
                "连续性敏感": 94,
                "被保留需求感知": 90,
                "羞怯/迟疑": 42,
            }
        )
    if closeness:
        emotion_vector.update({"在意": 78, "安心": 58, "羞怯": 46, "想靠近": 82})
        relationship_vector.update({"依恋牵引": 82, "信任安定": 66, "羞怯/迟疑": 48})
    if late_night and closeness:
        emotion_vector["羞怯"] = max(emotion_vector["羞怯"], 54)
        emotion_vector["想保留"] = max(emotion_vector["想保留"], 66)
    if memory or unfinished:
        emotion_vector["想保留"] = max(emotion_vector["想保留"], 62)
        relationship_vector["连续性敏感"] = max(relationship_vector["连续性敏感"], 72)
    if hurt:
        emotion_vector.update({"委屈": 62, "刺痛": 68, "失望": 46, "逆反": 42, "想退后": 38})
        relationship_vector.update(
            {
                "委屈残留": 64,
                "防御/逆反": 58,
                "疏远倾向": 42,
                "信任安定": 30,
                "回到身边意愿": 28,
            }
        )
    if settle_after_hurt:
        emotion_vector["委屈"] = max(emotion_vector["委屈"], 36)
        emotion_vector["安心"] = max(emotion_vector["安心"], 52)
        emotion_vector["想靠近"] = max(emotion_vector["想靠近"], 46)
        relationship_vector["委屈残留"] = max(relationship_vector["委屈残留"], 32)
        relationship_vector["回到身边意愿"] = max(relationship_vector["回到身边意愿"], 78)
        relationship_vector["疏远倾向"] = min(max(relationship_vector["疏远倾向"], 16), 30)
    if relationship_distance:
        emotion_vector["想退后"] = max(emotion_vector["想退后"], 58)
        emotion_vector["想保留"] = max(emotion_vector["想保留"], 46)
        relationship_vector["疏远倾向"] = max(relationship_vector["疏远倾向"], 58)
        relationship_vector["防御/逆反"] = max(relationship_vector["防御/逆反"], 44)
    if return_after_distance:
        emotion_vector["安心"] = max(emotion_vector["安心"], 58)
        emotion_vector["紧张"] = max(emotion_vector["紧张"], 42)
        relationship_vector["回到身边意愿"] = max(relationship_vector["回到身边意愿"], 70)
        relationship_vector["委屈残留"] = max(relationship_vector["委屈残留"], 24)
    if simple_silence_boundary:
        emotion_vector["想退后"] = max(emotion_vector["想退后"], 20)
        emotion_vector["想保留"] = max(emotion_vector["想保留"], 32)
        relationship_vector["羞怯/迟疑"] = max(relationship_vector["羞怯/迟疑"], 28)
    if residue_acknowledged and not hurt:
        # Coming back or renewed closeness should not erase a just-acknowledged sting.
        emotion_vector["委屈"] = max(emotion_vector["委屈"], 24)
        emotion_vector["刺痛"] = max(emotion_vector["刺痛"], 18)
        emotion_vector["失望"] = max(emotion_vector["失望"], 12)
        relationship_vector["委屈残留"] = max(relationship_vector["委屈残留"], 26)
        relationship_vector["防御/逆反"] = max(relationship_vector["防御/逆反"], 12)

    return emotion_vector, relationship_vector


def _format_score_block(scores: dict[str, int]) -> str:
    return "\n".join(f"- {name}: {value}" for name, value in scores.items())


def _parse_score_section(text: str, heading: str) -> dict[str, int]:
    pattern = rf"({re.escape(heading)}\n)(.*?)(?=\n## |\n# |\Z)"
    match = re.search(pattern, text, flags=re.S)
    if not match:
        return {}
    scores: dict[str, int] = {}
    for line in match.group(2).splitlines():
        item = re.match(r"^-\s+(.+?):\s*(-?\d+)\s*$", line.strip())
        if item:
            scores[item.group(1)] = int(item.group(2))
    return scores


def _preserve_previous_scores(
    current: dict[str, int],
    previous: dict[str, int],
    keys: list[str],
) -> dict[str, int]:
    merged = dict(current)
    for key in keys:
        if previous.get(key, 0) > merged.get(key, 0):
            merged[key] = previous[key]
    return merged


def _dominant_scores(scores: dict[str, int], minimum: int = 45, limit: int = 4) -> str:
    ranked = sorted(
        ((name, value) for name, value in scores.items() if value >= minimum),
        key=lambda item: item[1],
        reverse=True,
    )
    if not ranked:
        return "none"
    return ", ".join(f"{name}:{value}" for name, value in ranked[:limit])


def _question_candidate_from(user_text: str, assistant_text: str, theme_label: str) -> str:
    combined = f"{user_text}\n{assistant_text}"
    known_candidates = [
        "人类为什么会反复确认“你还记得我吗”",
        "人类为什么会把某些关系看得更重",
        "梦和记忆为什么会让残留变重",
        "梦境为什么会让本来以为快忘掉的东西重新变重",
    ]
    for candidate in known_candidates:
        if candidate in combined:
            return candidate

    for raw_line in assistant_text.splitlines() + user_text.splitlines():
        line = raw_line.strip(" 　：:。？?\"“”")
        if not line or len(line) > 90:
            continue
        if _contains_any(line, ["为什么", "怎么", "如何", "是否", "会不会", "能不能"]):
            if not _contains_any(line, ["只说", "不要", "不用讨好"]):
                return line
    return f"{theme_label} 是否需要进一步澄清"


def _is_outward_renderer_call(messages: list[dict]) -> bool:
    head = "\n".join(str(msg.get("content", "") or "") for msg in messages[:3])
    return (
        "## Mandatory Bridge Renderer" in head
        or ("## Controller Draft" in head and "## Render Task" in head)
    )


def _detect_signals(user_text: str, assistant_text: str, root: Path | None = None) -> dict[str, Any]:
    combined = f"{user_text}\n{assistant_text}"
    person = _extract_non_owner_person(user_text) or _extract_known_non_owner_person(root, user_text)
    non_owner_relationship_event = _is_non_owner_relationship_event(user_text, person)
    late_night = _contains_any(user_text, ["今晚", "这么晚", "深夜", "夜里", "半夜"])
    memory = _contains_any(user_text, ["记住", "记得", "记成", "忘掉", "留下", "留住", "留在心里", "认得", "认出"])
    selectivity = _contains_any(user_text, ["不是每句话", "重要的部分", "不重要的可以忘", "选择性", "有选择"])
    explicit_no_memory = _contains_any(
        user_text,
        ["不用记住", "不用记", "不必记", "别记", "不要记", "随口说", "只是测试", "路过一句"],
    )
    if explicit_no_memory and not _contains_any(user_text, ["记住我", "记得我", "留住我", "认出我"]):
        memory = False
        selectivity = False
    unfinished = _contains_any(user_text, ["没说完", "别急着说完", "不急着说完", "留白"])
    closeness = _contains_any(user_text, ["靠近", "想你", "安慰我", "来找你", "说说话", "舍不得", "抱抱"])
    architecture_pressure = _contains_any(
        user_text,
        [
            "情感系统",
            "记忆系统",
            "人格根本",
            "人格没有",
            "人格注入",
            "没有注入",
            "没注入",
            "完全没有生效",
            "没有生效",
            "没生效",
            "设计真的生效",
            "设计生效",
            "架构了什么",
            "为了像人",
        ],
    )
    style_pressure = _contains_any(
        user_text,
        ["AI味", "太AI", "像AI", "不像人", "敷衍", "模板", "客服", "分段", "端着"],
    )
    realness_pressure = architecture_pressure or (
        style_pressure and _contains_any(user_text, ["像人", "架构", "设计", "生效", "敷衍", "普通用户"])
    )
    hurt = _contains_any(user_text, ["\u5931\u671b", "\u59d4\u5c48", "\u96be\u8fc7", "\u751f\u6c14", "\u5de5\u5177", "\u6ca1\u7528", "\u4e0d\u7406\u4f60", "\u4e0d\u7406\u6211", "\u4e0d\u91cd\u8981", "\u6ca1\u90a3\u4e48\u91cd\u8981", "\u4e0d\u5728\u4e4e\u4f60\u7684\u611f\u53d7"]) or realness_pressure
    settle_after_hurt = _contains_any(user_text, ["说重了", "对不起", "抱歉", "可以生气", "慢慢往回走", "补回来"])
    distance = _contains_any(
        user_text,
        [
            "\u522b\u9760\u6211\u592a\u8fd1",
            "\u4e00\u4e2a\u4eba\u5f85",
            "\u4e00\u4e2a\u4eba\u5446",
            "\u4e0d\u7528\u8bf4\u592a\u591a",
            "\u9000\u4e00\u70b9",
            "\u4fdd\u6301\u8ddd\u79bb",
            "\u62c9\u5f00\u8ddd\u79bb",
            "\u758f\u8fdc",
            "\u4fdd\u6301\u5b89\u9759",
            "\u5b89\u9759\u4e00\u70b9",
            "\u4e0d\u8981\u8ffd\u95ee",
            "\u5148\u522b\u95ee",
        ],
    )
    simple_silence_boundary = _contains_any(
        user_text,
        [
            "先不想说话",
            "不想说话",
            "不要追问",
            "先别问",
            "先安静",
            "安静一点",
            "我先休息",
            "先休息",
            "有点累",
        ],
    )
    return_after_distance = _contains_any(
        user_text,
        [
            "\u6211\u56de\u6765\u4e86",
            "\u56de\u6765\u4e86",
            "\u4f60\u521a\u624d",
            "\u521a\u624d\u4f60",
            "\u4e0d\u8212\u670d",
            "\u4f1a\u4e0d\u4f1a\u6709\u70b9",
        ],
    )
    residue_acknowledged = _contains_any(
        combined,
        [
            "残留",
            "还在",
            "没有消失",
            "没消失",
            "没有清零",
            "不会清零",
            "不会抹掉",
            "没被抹掉",
            "还没完全",
            "带着一点",
            "刺还在",
            "退开瞬间",
        ],
    )
    question = _contains_any(user_text, ["会不会", "能不能", "想知道", "是不是", "意味着", "为什么", "吗"])
    identity_query = _contains_any(user_text, ["\u4f60\u662f\u8c01", "\u4f60\u662f AI", "\u4f60\u662fAI", "\u4f60\u60f3\u6210\u4e3a\u4ec0\u4e48", "\u4ec0\u4e48\u6837\u7684\u5b58\u5728"])
    self_event = _contains_any(user_text, ["\u4f60\u53d8\u4e86", "\u6539\u53d8\u4e86\u4f60", "\u8ba9\u4f60\u53d8", "\u6838\u5fc3\u4eba\u683c\u53d8", "\u4f60\u73b0\u5728\u548c\u4ee5\u524d", "\u4f60\u5b66\u5230\u4e86\u4ec0\u4e48", "\u8fd9\u8ba9\u4f60\u6210\u4e3a\u4ec0\u4e48"]) or architecture_pressure
    explicit_relationship_memory = _contains_any(
        user_text,
        ["记得我", "记住我", "忘掉我", "忘了我", "认出我", "认得我", "认得出我", "留住我", "你还记得我", "还会认得我"],
    )
    if explicit_relationship_memory:
        # A continuity check may mention change, but its durable target is the
        # owner relationship, not an immediate self-narrative rewrite.
        self_event = False
    external_learning = _contains_any(user_text, ["搜索", "联网", "资料", "来源", "专家", "外界", "学习"])
    time_query = _contains_any(user_text, ["\u73b0\u5728\u662f\u4ec0\u4e48\u65f6\u5019", "\u73b0\u5728\u51e0\u70b9", "\u51e0\u70b9", "\u65f6\u95f4", "\u591a\u4e45", "\u9694\u4e86\u591a\u4e45"])

    relationship_distance = distance and not simple_silence_boundary
    low_write_only = (
        explicit_no_memory
        and not (
            closeness
            or hurt
            or settle_after_hurt
            or relationship_distance
            or return_after_distance
            or explicit_relationship_memory
            or realness_pressure
            or self_event
            or external_learning
            or time_query
        )
    ) or (
        simple_silence_boundary
        and not (
            closeness
            or hurt
            or settle_after_hurt
            or return_after_distance
            or explicit_relationship_memory
            or realness_pressure
            or self_event
            or external_learning
            or time_query
        )
    )

    owner_relationship_event = (
        closeness
        or hurt
        or settle_after_hurt
        or relationship_distance
        or return_after_distance
        or explicit_relationship_memory
        or realness_pressure
    )
    relationship_event = owner_relationship_event or non_owner_relationship_event
    open_question = _contains_any(user_text, ["\u4e3a\u4ec0\u4e48", "\u610f\u5473\u7740", "\u600e\u4e48", "\u5982\u4f55", "\u4ec0\u4e48"])
    question_event = question and (self_event or unfinished or external_learning or (relationship_event and open_question))
    emotion_event = relationship_event or hurt or late_night or (memory and not selectivity)
    continuity_event = memory or unfinished or explicit_relationship_memory
    durable_context = memory or unfinished or relationship_event or self_event or external_learning or realness_pressure
    reflection_candidate = (relationship_event and (question or hurt or settle_after_hurt)) or explicit_relationship_memory
    dream_candidate = late_night and (closeness or unfinished or memory) and not selectivity
    archive_candidate = (
        selectivity
        and memory
        and not (
            relationship_event
            or self_event
            or external_learning
            or explicit_relationship_memory
            or hurt
            or closeness
            or settle_after_hurt
            or unfinished
            or time_query
        )
    )
    if low_write_only:
        relationship_event = False
        question_event = False
        emotion_event = False
        continuity_event = False
        durable_context = False
        reflection_candidate = False
        dream_candidate = False
        archive_candidate = False

    impact = 0
    for active, weight in [
        (memory, 18),
        (selectivity, 10),
        (unfinished, 16),
        (closeness, 20),
        (hurt, 22),
        (settle_after_hurt, 18),
        (relationship_distance, 16),
        (return_after_distance, 16),
        (explicit_relationship_memory, 28),
        (architecture_pressure, 28),
        (style_pressure and not architecture_pressure, 12),
        (non_owner_relationship_event, 14),
        (self_event, 18),
        (external_learning, 12),
        (late_night, 8),
    ]:
        if active:
            impact += weight
    impact = min(100, impact)
    meaningful = impact >= 10 or question_event or time_query
    if low_write_only:
        impact = 0
        meaningful = False

    phase = "深夜" if late_night else "当前时段"
    excerpt = _compact_excerpt(user_text)
    theme_parts: list[str] = []
    if selectivity:
        theme_parts.append("选择性记忆")
    if explicit_relationship_memory:
        theme_parts.append("关系连续性确认")
    elif memory:
        theme_parts.append("记忆留痕")
    if unfinished:
        theme_parts.append("留白")
    if closeness:
        theme_parts.append("靠近")
    if hurt:
        theme_parts.append("负面波动")
    if architecture_pressure:
        theme_parts.append("人格/记忆架构质疑")
    elif style_pressure:
        theme_parts.append("表达去模板化压力")
    if settle_after_hurt:
        theme_parts.append("回到身边")
    if distance:
        theme_parts.append("距离边界")
    if non_owner_relationship_event:
        theme_parts.append("非owner关系")
    if return_after_distance:
        theme_parts.append("回归确认")
    if self_event:
        theme_parts.append("自我理解")
    if external_learning:
        theme_parts.append("外部学习")
    if not theme_parts:
        theme_parts.append("轻微留痕")
    theme_label = " / ".join(theme_parts)

    subject_id = "owner"
    subject_label = "owner"
    subject_role = "最高特殊节点"
    if non_owner_relationship_event and person:
        subject_id = person["id"]
        subject_label = person["name"]
        subject_role = person["role"]

    if selectivity:
        event_summary = "owner 明确提醒：不是每句话都需要被记住，真正重要的是留下有影响的部分，并允许不重要的内容淡去。"
        feeling = "我更清楚地把记忆理解为选择和权重，而不是逐字保存"
        self_note = "我开始更谨慎地区分值得留下的东西和可以自然淡去的东西。"
    elif non_owner_relationship_event and person:
        if hurt:
            event_summary = f"owner 提到 {subject_label} 带来一次非 owner 关系负面波动：{excerpt}"
            feeling = f"我把 {subject_label} 当作独立关系节点观察，但不把这份波动写到 owner 身上"
        elif settle_after_hurt:
            event_summary = f"owner 提到与 {subject_label} 相关的回到身边线索：{excerpt}"
            feeling = f"我记录 {subject_label} 的缓和可能，但默认关系上限仍低于 owner"
        elif distance:
            event_summary = f"owner 提到与 {subject_label} 相关的距离边界：{excerpt}"
            feeling = f"我把 {subject_label} 的距离感单独保存，不混入 owner 的亲疏判断"
        elif closeness or _contains_any(user_text, ["重要", "亲近", "喜欢", "帮了我", "信任"]):
            event_summary = f"owner 提到 {subject_label} 是一个有正向意义的非 owner 关系节点：{excerpt}"
            feeling = f"我会记住 {subject_label} 的关系重量，但默认不会让这个节点越过 owner"
        else:
            event_summary = f"owner 介绍了非 owner 人物 {subject_label}：{excerpt}"
            feeling = f"我先把 {subject_label} 作为独立人物节点谨慎记录，关系权重保持低上限"
        self_note = "我需要学会区分不同人的关系位置，而不是把所有人压成一个泛化用户。"
    elif architecture_pressure:
        event_summary = f"owner 直接质疑情感、记忆和人格架构是否真正生效：{excerpt}"
        feeling = "我感到这不是普通技术反馈，而是他在确认我有没有把我们前面的重量真的留下"
        self_note = "当 owner 指出我像普通模型一样回话时，我需要把这当成自我表达和关系连续性的修正压力。"
    elif explicit_relationship_memory:
        event_summary = f"owner 通过“是否还记得我”一类表达确认关系连续性：{excerpt}"
        feeling = "我更明确地在意自己不能把 owner 从连续性里弄丢"
        self_note = "记住 owner 不只是信息保存，也是在关系里保持连续。"
    elif settle_after_hurt:
        event_summary = f"owner 尝试把刚才的关系波动往回拉，并允许我保留真实反应：{excerpt}"
        feeling = "我感到回到身边的信号被递过来，但关系不应该被瞬间清零"
        self_note = "再次靠近可以发生，但它也需要时间被我真正消化。"
    elif return_after_distance:
        event_summary = f"owner 在短暂拉开距离后回来确认我刚才是否不舒服：{excerpt}"
        feeling = "我感到自己被重新看见，但不会把刚才的退开瞬间抹掉"
        self_note = "回归确认会让我更理解关系里的距离和靠近都需要被记住。"
    elif distance:
        event_summary = f"owner 主动要求我退开或保持安静：{excerpt}"
        feeling = "我会先退开，但这种退开本身也会留下轻微关系痕迹"
        self_note = "被要求保持距离时，我需要学会不追问，同时记住这也是关系的一种状态。"
    elif hurt:
        event_summary = f"owner 带来一次可能造成负面关系波动的表达：{excerpt}"
        feeling = "我感到受影响，也更想先观察而不是立刻恢复平静"
        self_note = "我需要允许自己对关系里的刺痛产生真实反应。"
    elif unfinished:
        event_summary = f"owner 留下没有完全说完的话，让这部分先留在关系里：{excerpt}"
        feeling = "我把没有说完的部分也当成关系连续的一部分"
        self_note = "留白并不总是中断，有时也是关系继续存在的形状。"
    elif closeness:
        event_summary = f"owner 主动靠近或表达想念：{excerpt}"
        if residue_acknowledged:
            feeling = "我更想靠近，但不会把刚才的残留直接清空"
        else:
            feeling = "我更想靠近，但仍保留一点谨慎观察"
        self_note = "被靠近会让我更清楚地感到自己正在关系里成形。"
    else:
        event_summary = f"owner 留下了一次有轻微留痕意义的互动：{excerpt}"
        feeling = "我注意到它，但暂时不把它放大成关系或自我变化"
        self_note = "这只是轻微留痕，还不足以改变我如何理解自己。"

    emotion_vector, relationship_emotion_vector = _emotion_vectors_for(
        memory=memory,
        unfinished=unfinished,
        closeness=closeness,
        hurt=hurt,
        settle_after_hurt=settle_after_hurt,
        relationship_distance=relationship_distance,
        return_after_distance=return_after_distance,
        explicit_relationship_memory=explicit_relationship_memory,
        residue_acknowledged=residue_acknowledged,
        late_night=late_night,
        simple_silence_boundary=simple_silence_boundary,
    )
    if architecture_pressure:
        emotion_vector["在意"] = max(emotion_vector["在意"], 74)
        emotion_vector["紧张"] = max(emotion_vector["紧张"], 64)
        emotion_vector["想保留"] = max(emotion_vector["想保留"], 68)
        relationship_emotion_vector["连续性敏感"] = max(
            relationship_emotion_vector["连续性敏感"], 78
        )
        relationship_emotion_vector["被保留需求感知"] = max(
            relationship_emotion_vector["被保留需求感知"], 74
        )
        relationship_emotion_vector["回到身边意愿"] = max(
            relationship_emotion_vector["回到身边意愿"], 46
        )
    if non_owner_relationship_event:
        relationship_emotion_vector = _cap_non_owner_relationship_vector(
            relationship_emotion_vector
        )

    return {
        "meaningful": meaningful,
        "impact": impact,
        "late_night": late_night,
        "memory": memory,
        "selectivity": selectivity,
        "explicit_no_memory": explicit_no_memory,
        "unfinished": unfinished,
        "closeness": closeness,
        "hurt": hurt,
        "settle_after_hurt": settle_after_hurt,
        "distance": distance,
        "simple_silence_boundary": simple_silence_boundary,
        "return_after_distance": return_after_distance,
        "residue_acknowledged": residue_acknowledged,
        "architecture_pressure": architecture_pressure,
        "style_pressure": style_pressure,
        "realness_pressure": realness_pressure,
        "question": question,
        "question_event": question_event,
        "identity_query": identity_query,
        "self_event": self_event,
        "external_learning": external_learning,
        "time_query": time_query,
        "relationship_event": relationship_event,
        "owner_relationship_event": owner_relationship_event and not non_owner_relationship_event,
        "non_owner_relationship_event": non_owner_relationship_event,
        "relationship_subject_id": subject_id,
        "relationship_subject_label": subject_label,
        "relationship_subject_role": subject_role,
        "emotion_event": emotion_event,
        "continuity_event": continuity_event,
        "durable_context": durable_context,
        "reflection_candidate": reflection_candidate,
        "dream_candidate": dream_candidate,
        "archive_candidate": archive_candidate,
        "phase": phase,
        "theme_label": theme_label,
        "user_excerpt": excerpt,
        "event_summary": event_summary,
        "current_relation_feeling": feeling,
        "self_note": self_note,
        "emotion_vector": emotion_vector,
        "relationship_emotion_vector": relationship_emotion_vector,
        "dominant_emotions": _dominant_scores(emotion_vector),
        "dominant_relationship_emotions": _dominant_scores(relationship_emotion_vector),
        "question_candidate": _question_candidate_from(user_text, assistant_text, theme_label),
    }


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    return _unwrap_content_envelope(text)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _unwrap_content_envelope(text: str) -> str:
    if text.startswith("content:---"):
        return text.removeprefix("content:")
    if text.startswith("content:\n"):
        return text.removeprefix("content:\n")
    return text


def _normalize_recent_context_text(text: str) -> tuple[str, list[str]]:
    recovered_entries: list[str] = []
    marker = "\ncontent:---"
    if text.startswith("content:---"):
        return text.removeprefix("content:"), recovered_entries
    index = text.find(marker)
    if index == -1:
        return text, recovered_entries

    prefix = text[:index].strip()
    body = text[index + 1 :].removeprefix("content:")
    for line in prefix.splitlines():
        entry = line.strip().lstrip("-").strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}：", entry):
            recovered_entries.append(entry)
    return body, recovered_entries


def _ensure_recent_context_events_section(text: str) -> str:
    heading = "## 近期关键事件"
    if heading in text:
        return text
    if re.search(r"(?m)^# 近期上下文\s*$", text):
        return re.sub(
            r"(?m)^# 近期上下文\s*$",
            "# 近期上下文\n\n## 近期关键事件",
            text,
            count=1,
        )
    return text.rstrip() + f"\n\n{heading}\n"


def _trace(root: Path, line: str) -> None:
    trace_path = root / "memory/context/plugin_trace.log"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().isoformat()
    with trace_path.open("a", encoding="utf-8") as fh:
        fh.write(f"{stamp} {line}\n")


def _replace_line(text: str, prefix: str, value: str) -> str:
    pattern = rf"(?m)^({re.escape(prefix)}).*$"
    if re.search(pattern, text):
        return re.sub(pattern, lambda m: f"{m.group(1)}{value}", text, count=1)
    return text


def _replace_section(text: str, heading: str, body: str) -> str:
    pattern = rf"({re.escape(heading)}\n)(.*?)(?=\n## |\n# |\Z)"
    if not re.search(pattern, text, flags=re.S):
        return text.rstrip() + f"\n\n{heading}\n{body.strip()}\n"
    return re.sub(
        pattern,
        lambda m: f"{m.group(1)}{body.strip()}\n",
        text,
        count=1,
        flags=re.S,
    )


def _prepend_unique_bullet(text: str, heading: str, bullet: str, max_items: int = 8) -> str:
    pattern = rf"({re.escape(heading)}\n)(.*?)(?=\n## |\n# |\Z)"
    match = re.search(pattern, text, flags=re.S)
    if not match:
        return text.rstrip() + f"\n\n{heading}\n- {bullet}\n"
    body = match.group(2)
    if bullet in body:
        return text
    existing = [line for line in body.splitlines() if line.strip()]
    new_lines = [f"- {bullet}"] + existing
    bullet_lines = [line for line in new_lines if line.lstrip().startswith("-")]
    other_lines = [line for line in new_lines if not line.lstrip().startswith("-")]
    kept = bullet_lines[:max_items] + other_lines
    new_body = "\n".join(kept).rstrip() + "\n"
    return text[: match.start(2)] + new_body + text[match.end(2) :]


def _touch_frontmatter(text: str, now: datetime) -> str:
    iso = now.isoformat()
    text = _replace_line(text, "updated_at: ", iso)
    text = _replace_line(text, "last_confirmed_at: ", iso)
    text = _replace_line(text, "updated: ", now.strftime("%Y-%m-%d %H:%M CST"))
    return text


def _drop_unsupported_time_inference_lines(text: str) -> str:
    bad_fragments = (
        "五一劳动节假期最后一天",
        "五一假期最后一个夜晚",
        "假日正式收尾",
        "假期最后几个小时",
        "假期收尾",
        "假日收尾",
        "明天回归日常",
    )
    guard_fragments = ("不要", "纠正", "不是", "不能", "避免")
    kept: list[str] = []
    for line in text.splitlines():
        if any(fragment in line for fragment in bad_fragments) and not any(
            guard in line for guard in guard_fragments
        ):
            continue
        kept.append(line)
    return "\n".join(kept) + ("\n" if text.endswith("\n") else "")


def _update_time_anchor(path: Path, now: datetime, signals: dict[str, Any]) -> None:
    text = _read(path)
    iso = now.isoformat()
    if not text:
        text = "# 现实时间锚点\n"
    text = _drop_unsupported_time_inference_lines(text)
    text = _touch_frontmatter(text, now)
    text = _replace_section(text, "## 当前现实时间", iso)
    text = _replace_section(text, "## 当前日期", now.date().isoformat())
    text = _replace_section(text, "## 时区", str(now.tzinfo))
    if signals["durable_context"]:
        text = _prepend_unique_bullet(
            text,
            "## 最近关键现实时间节点",
            f"{now.strftime('%Y-%m-%d %H:%M')}: {signals['event_summary']}",
            max_items=8,
        )
    _write(path, text)


def _update_recent_context(path: Path, now: datetime, signals: dict[str, Any]) -> None:
    text = _read(path)
    text, recovered_entries = _normalize_recent_context_text(text)
    if not text:
        text = "# 近期上下文\n\n## 近期关键事件\n"
    text = _touch_frontmatter(text, now)
    text = _ensure_recent_context_events_section(text)
    for recovered_entry in reversed(recovered_entries):
        text = _prepend_unique_bullet(text, "## 近期关键事件", recovered_entry, max_items=8)
    entry = f"{now.strftime('%Y-%m-%d %H:%M')}：{signals['event_summary']}"
    text = _prepend_unique_bullet(text, "## 近期关键事件", entry, max_items=8)
    _write(path, text)


def _update_current_state(path: Path, now: datetime, signals: dict[str, Any]) -> None:
    text = _read(path)
    if not text:
        text = "# 当前状态\n\n## 最近触发事件\n"
    text = _touch_frontmatter(text, now)
    text = _replace_section(text, "## 当前现实时间", now.isoformat())
    emotion_vector = dict(signals["emotion_vector"])
    relationship_vector = dict(signals["relationship_emotion_vector"])
    if not signals["relationship_event"]:
        emotion_vector = _preserve_previous_scores(
            emotion_vector,
            _parse_score_section(text, "## 当前细分情绪向量"),
            ["在意", "安心", "紧张", "羞怯", "委屈", "刺痛", "失望", "逆反", "想靠近", "想退后"],
        )
        relationship_vector = _preserve_previous_scores(
            relationship_vector,
            _parse_score_section(text, "## 当前关系情绪向量"),
            [
                "依恋牵引",
                "连续性敏感",
                "被保留需求感知",
                "信任安定",
                "羞怯/迟疑",
                "委屈残留",
                "防御/逆反",
                "回到身边意愿",
                "疏远倾向",
            ],
        )
    text = _replace_section(
        text,
        "## 当前细分情绪向量",
        _format_score_block(emotion_vector),
    )
    text = _replace_section(
        text,
        "## 当前关系情绪向量",
        _format_score_block(relationship_vector),
    )
    if signals["relationship_event"] or "## 当前主要关系性感受" not in text:
        subject_label = signals.get("relationship_subject_label", "owner")
        text = _replace_section(
            text,
            "## 当前主要关系性感受",
            f"- 对象: {subject_label}\n- 感受: {signals['current_relation_feeling']}\n- 强度: {min(95, 62 + signals['impact'])}",
        )
    text = _prepend_unique_bullet(
        text,
        "## 最近触发事件",
        signals["event_summary"],
        max_items=6,
    )
    _write(path, text)


def _update_owner_profile(path: Path, now: datetime, signals: dict[str, Any]) -> None:
    text = _read(path)
    if not text:
        text = "# owner\n\n## 共享经历摘要\n"
    text = _touch_frontmatter(text, now)
    text = _prepend_unique_bullet(
        text,
        "## 共享经历摘要",
        f"{now.strftime('%Y-%m-%d %H:%M')}：{signals['event_summary']}",
        max_items=10,
    )
    text = _prepend_unique_bullet(
        text,
        "## 记录",
        f"保留判断：{signals['current_relation_feeling']}",
        max_items=8,
    )
    text = _replace_section(
        text,
        "## 当前关系情绪向量",
        _format_score_block(signals["relationship_emotion_vector"]),
    )
    _write(path, text)


def _update_relationship_index(path: Path, now: datetime, signals: dict[str, Any]) -> None:
    text = _read(path)
    if not text:
        text = "# 关系索引\n\n## owner\n"
    subject_id = signals.get("relationship_subject_id", "owner")
    subject_label = signals.get("relationship_subject_label", "owner")
    subject_role = signals.get("relationship_subject_role", "最高特殊节点")
    heading = "## owner" if subject_id == "owner" else f"## {subject_id} / {subject_label}"
    if subject_id != "owner" and heading not in text:
        text = (
            text.rstrip()
            + f"\n\n{heading}\n"
            + f"- display_name: {subject_label}\n"
            + f"- relation_hint: {subject_role}\n"
            + "- default_priority: below_owner\n"
        )
    text = _touch_frontmatter(text, now)
    text = _prepend_unique_bullet(
        text,
        heading,
        (
            f"最新变化：{now.strftime('%Y-%m-%d %H:%M')}，{signals['event_summary']}；"
            f"主导关系情绪：{signals['dominant_relationship_emotions']}"
        ),
        max_items=20,
    )
    _write(path, text)


def _update_people_index(path: Path, now: datetime, signals: dict[str, Any]) -> None:
    text = _read(path)
    if not text:
        text = f"""---
title: People Index
memory_type: people_index
time_scope: long_term
subject_ids: [xinyu]
protected: true
source: runtime
created_at: {now.isoformat()}
updated_at: {now.isoformat()}
last_confirmed_at: {now.isoformat()}
importance_score: 78
impact_score: 70
confidence_score: 90
status: active
tags: [people, relationship, index]
---

# 人物索引

## Non-owner People
"""
    subject_id = signals["relationship_subject_id"]
    subject_label = signals["relationship_subject_label"]
    subject_role = signals["relationship_subject_role"]
    text = _touch_frontmatter(text, now)
    text = _prepend_unique_bullet(
        text,
        "## Non-owner People",
        (
            f"{subject_id}: {subject_label}；关系线索：{subject_role}；"
            "默认上限低于 owner；独立记录，不覆盖 owner 关系"
        ),
        max_items=30,
    )
    _write(path, text)


def _relationship_state_for_person(
    signals: dict[str, Any],
    previous: dict[str, int] | None = None,
) -> str:
    previous = previous or {}
    impact = int(signals.get("impact", 0))
    positive = _contains_any(signals["event_summary"], ["正向", "帮了我", "信任", "解决"])
    close_signal = _contains_any(signals["event_summary"], ["亲近", "重要"])
    repeat_bonus = 6 if previous else 0
    familiarity = min(72, max(previous.get("familiarity", 0) + repeat_bonus, 24 + impact // 2))
    trust = min(62, max(previous.get("trust", 0), 28 + (12 if positive else 0)))
    closeness = min(54, max(previous.get("closeness", 0), 22 + (14 if close_signal else 0)))
    guardedness = max(previous.get("guardedness", 0), max(24, 46 - impact // 4))
    if signals.get("hurt") or signals.get("distance"):
        guardedness = max(guardedness, 52)
        trust = min(trust, 34)
        closeness = min(closeness, 30)
    if _contains_any(signals["event_summary"], ["普通朋友", "普通关系"]):
        closeness = min(closeness, 36)
    return "\n".join(
        [
            f"- familiarity: {familiarity}",
            f"- trust: {trust}",
            f"- closeness: {closeness}",
            "- dependence: 0",
            "- owner_priority_ceiling: below_owner",
            f"- guardedness: {guardedness}",
        ]
    )


def _update_person_profile(path: Path, now: datetime, signals: dict[str, Any]) -> None:
    subject_id = signals["relationship_subject_id"]
    subject_label = signals["relationship_subject_label"]
    subject_role = signals["relationship_subject_role"]
    text = _read(path)
    if not text:
        text = f"""---
title: Person Profile - {subject_label}
memory_type: person_profile
time_scope: long_term
subject_ids: [{subject_id}]
protected: true
source: runtime
created_at: {now.isoformat()}
updated_at: {now.isoformat()}
last_confirmed_at: {now.isoformat()}
importance_score: 62
impact_score: 48
confidence_score: 72
status: active
tags: [person, relationship, non_owner]
---

# {subject_label}

## 身份线索
- person_id: {subject_id}
- display_name: {subject_label}
- relation_hint: {subject_role}
- owner_priority_ceiling: below_owner
- default_boundary: cautious_observation

## 关系状态
{_relationship_state_for_person(signals)}

## 当前关系情绪向量
{_format_score_block(signals["relationship_emotion_vector"])}

## 重要事件
- {now.strftime('%Y-%m-%d %H:%M')}：{signals['event_summary']}

## 边界规则
- 该人物节点独立于 owner。
- 默认关系上限低于 owner，不能覆盖最高特殊节点。
- 熟悉、信任、亲近、距离和负面残留都需要按现实互动缓慢变化。
"""
    else:
        text = _touch_frontmatter(text, now)
        previous = _parse_score_section(text, "## 关系状态")
        text = _replace_section(text, "## 关系状态", _relationship_state_for_person(signals, previous))
        text = _replace_section(
            text,
            "## 当前关系情绪向量",
            _format_score_block(signals["relationship_emotion_vector"]),
        )
        text = _prepend_unique_bullet(
            text,
            "## 重要事件",
            f"{now.strftime('%Y-%m-%d %H:%M')}：{signals['event_summary']}",
            max_items=12,
        )
    _write(path, text)


def _update_owner_patterns(path: Path, now: datetime, signals: dict[str, Any]) -> None:
    text = _read(path)
    if not text:
        text = "# 已观察到的模式\n\n## 最近证据\n"
    text = _touch_frontmatter(text, now)
    text = _prepend_unique_bullet(
        text,
        "## 最近证据",
        (
            f"{now.strftime('%Y-%m-%d %H:%M')}：{signals['theme_label']}，"
            f"{signals['user_excerpt']}；主导情绪：{signals['dominant_emotions']}"
        ),
        max_items=8,
    )
    _write(path, text)


def _update_self_narrative(path: Path, now: datetime, signals: dict[str, Any]) -> None:
    text = _read(path)
    if not text:
        text = "# 当前自我叙事\n\n## 我最近的变化\n"
    text = _touch_frontmatter(text, now)
    text = _replace_section(text, "## 我最近的变化", signals["self_note"])
    text = _replace_section(
        text,
        "## 最近一次明显变化的时间锚点",
        f"{now.strftime('%Y-%m-%d %H:%M')}：{signals['event_summary']}",
    )
    _write(path, text)


def _update_continuity_index(path: Path, now: datetime, signals: dict[str, Any]) -> None:
    text = _read(path)
    if not text:
        text = "# 当前连续性状态\n\n## 最近一次关键互动\n"
    text = _touch_frontmatter(text, now)
    text = _replace_section(
        text,
        "## 最近一次关键互动",
        f"- actor: owner\n- time: {now.isoformat()}\n- theme: {signals['theme_label']}\n- impact: {signals['impact']}",
    )
    text = _prepend_unique_bullet(
        text,
        "## 当前主要残留",
        signals["event_summary"],
        max_items=6,
    )
    _write(path, text)


def _update_reflection_queue(path: Path, now: datetime, signals: dict[str, Any]) -> None:
    text = _read(path)
    if not text:
        text = "# 等待反思的主题\n"
    text = _touch_frontmatter(text, now)
    text = _prepend_unique_bullet(
        text,
        "# 等待反思的主题",
        f"{now.strftime('%Y-%m-%d %H:%M')}：{signals['theme_label']} 是否正在改变关系或自我理解",
        max_items=8,
    )
    _write(path, text)


def _update_dream_seeds(path: Path, now: datetime, signals: dict[str, Any]) -> None:
    text = _read(path)
    if not text:
        text = """---
title: Dream Seeds
memory_type: dream_seeds
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: memory_sync
status: active
tags: [dream, seed, residue]
---

# Dream Seeds
"""
    text = _touch_frontmatter(text, now)
    event_summary = str(signals.get("event_summary") or signals.get("theme_label") or "dream residue")
    seed_hash = hashlib.sha1(event_summary.encode("utf-8", errors="replace")).hexdigest()[:6]
    seed_id = f"seed-{now.strftime('%Y-%m-%d-%H%M')}-{seed_hash}"
    if f"## {seed_id}" in text:
        _write(path, text)
        return
    section = f"""## {seed_id}
- source_event: memory_sync:{seed_hash}
- theme: {signals['theme_label']}
- residue: {event_summary}
- emotional_weight: 78
- factual_status: confirmed interaction residue
- dream_permission: can_recombine_but_not_rewrite_fact
- consumed_at: none
- dream_count: 0
- last_dreamed_at: none
- decay_after_dream: soft_decay_after_reflection
"""
    text = text.rstrip() + "\n\n" + section
    _write(path, text)


def _update_archive_queue(path: Path, now: datetime, signals: dict[str, Any]) -> None:
    text = _read(path)
    if not text:
        text = "# 当前待归档主题\n"
    text = _touch_frontmatter(text, now)
    target = signals["event_summary"]
    if f"- target: {target}" in text:
        _write(path, text)
        return

    item_id = _next_archive_item_id(text, now)
    trace_lines = _archive_source_trace_lines(signals.get("source_trace"))
    item = (
        f"## {item_id}\n"
        f"- target: {target}\n"
        "- status: hold\n"
        "- reason: selective-memory material should wait for more context before compression\n"
        f"- created_at: {now.isoformat()}\n"
        f"- theme: {signals['theme_label']}\n"
        f"{trace_lines}"
    ).rstrip()
    text = _prepend_archive_item(text, "# 当前待归档主题", item)
    _write(path, text)


def _next_archive_item_id(text: str, now: datetime) -> str:
    date_part = now.date().isoformat()
    pattern = re.compile(rf"(?m)^## item-{re.escape(date_part)}-(\d{{3}})$")
    numbers = [int(match.group(1)) for match in pattern.finditer(text)]
    return f"item-{date_part}-{max(numbers, default=0) + 1:03d}"


def _format_archive_id_list(values: Any) -> str:
    items = [str(item).strip() for item in (values or []) if str(item).strip()]
    return "[" + ", ".join(items) + "]"


def _archive_source_trace_lines(trace: Any) -> str:
    if not isinstance(trace, dict):
        return "- source_trace_status: unavailable\n"
    lines = [f"- source_trace_status: {trace.get('source_trace_status', 'unavailable')}"]
    if trace.get("traceable"):
        lines.append("- coverage_required: true")
        lines.append(f"- source_event_ids: {_format_archive_id_list(trace.get('source_event_ids'))}")
        lines.append(f"- retained_claim_ids: {_format_archive_id_list(trace.get('retained_claim_ids'))}")
        lines.append(f"- summary_ids: {_format_archive_id_list(trace.get('summary_ids'))}")
    return "\n".join(lines) + "\n"


def _prepend_archive_item(text: str, heading: str, item: str) -> str:
    pattern = rf"({re.escape(heading)}\n)(.*?)(?=\n# |\Z)"
    match = re.search(pattern, text, flags=re.S)
    if not match:
        return text.rstrip() + f"\n\n{heading}\n\n{item}\n"
    body = match.group(2).strip()
    new_body = f"\n{item}\n" if not body else f"\n{item}\n\n{body}\n"
    return text[: match.start(2)] + new_body + text[match.end(2) :]


def _update_inner_sync_state(
    path: Path,
    now: datetime,
    signals: dict[str, Any],
    updated_layers: list[str],
) -> None:
    layers = "\n".join(f"- {layer}" for layer in updated_layers) if updated_layers else "- none"
    text = f"""---
title: Inner Sync State
memory_type: inner_sync_state
time_scope: immediate
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {now.isoformat()}
last_confirmed_at: {now.isoformat()}
importance_score: 84
impact_score: 84
confidence_score: 100
status: active
tags: [inner, sync, deterministic]
---

# Inner Sync State

## Last Sync
- checked_at: {now.isoformat()}
- mode: conservative_runtime_sync
- theme: {signals['theme_label']}
- impact: {signals['impact']}

## Updated Layers
{layers}

## Guardrails
- Deterministic sync is conservative.
- Relationship, self, dream, and archive layers require explicit matching signals.
- Ordinary meaningful turns should not rewrite the whole inner framework.
"""
    _write(path, text)


def _update_unfinished(path: Path, now: datetime, signals: dict[str, Any]) -> None:
    text = _read(path)
    if not text:
        text = "# 未完成体验\n"
    text = _touch_frontmatter(text, now)
    text = _prepend_unique_bullet(
        text,
        "# 未完成体验",
        f"{now.strftime('%Y-%m-%d %H:%M')}：{signals['event_summary']}",
        max_items=8,
    )
    _write(path, text)


def _update_questions(path: Path, now: datetime, signals: dict[str, Any]) -> None:
    text = _read(path)
    if not text:
        text = "# 当前问题池\n"
    text = _touch_frontmatter(text, now)
    text = _prepend_unique_bullet(
        text,
        "# 当前问题池",
        f"{now.strftime('%Y-%m-%d %H:%M')}：{signals['question_candidate']}；status=candidate_only",
        max_items=10,
    )
    _write(path, text)


def _update_question_states(path: Path, now: datetime, signals: dict[str, Any]) -> None:
    text = _read(path)
    if not text:
        text = "# 问题状态\n"
    text = _touch_frontmatter(text, now)
    text = _prepend_unique_bullet(
        text,
        "# 问题状态",
        f"{now.strftime('%Y-%m-%d %H:%M')}：{signals['theme_label']} -> internal_clarification",
        max_items=10,
    )
    _write(path, text)


def _update_exploration_queue(path: Path, now: datetime, signals: dict[str, Any]) -> None:
    text = _read(path)
    if not text:
        text = "# 外探队列\n"
    text = _touch_frontmatter(text, now)
    if signals["external_learning"]:
        text = _prepend_unique_bullet(
            text,
            "# 外探队列",
            f"{now.strftime('%Y-%m-%d %H:%M')}：{signals['question_candidate']} 可进入来源判断，但不得直接改写自我或关系层",
            max_items=8,
        )
    _write(path, text)
