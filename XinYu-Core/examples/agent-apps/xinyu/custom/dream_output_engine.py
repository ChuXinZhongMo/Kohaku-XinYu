from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_visible_text_sanitizer import sanitize_visible_text


SEED_FIELDS = (
    "source_event",
    "theme",
    "residue",
    "emotional_weight",
    "factual_status",
    "dream_permission",
    "consumed_at",
    "dream_count",
    "last_dreamed_at",
    "decay_after_dream",
)
RESERVED_SEED_OUTPUT_FIELDS = set(SEED_FIELDS) | {"last_dream_id"}


@dataclass(frozen=True, slots=True)
class DreamSeed:
    seed_id: str
    sort_key: str
    source_event: str
    theme: str
    residue: str
    emotional_weight: int
    factual_status: str
    dream_permission: str
    consumed_at: str = "none"
    dream_count: int = 0
    last_dreamed_at: str = "none"
    decay_after_dream: str = "soft_decay_after_reflection"
    origin: str = "explicit"
    extra_fields: tuple[tuple[str, str], ...] = ()

    def as_dict(self) -> dict[str, str]:
        return {
            "seed_id": self.seed_id,
            "source_event": self.source_event,
            "theme": self.theme,
            "residue": self.residue,
            "emotional_weight": str(self.emotional_weight),
            "factual_status": self.factual_status,
            "dream_permission": self.dream_permission,
            "consumed_at": self.consumed_at,
            "dream_count": str(self.dream_count),
            "last_dreamed_at": self.last_dreamed_at,
            "decay_after_dream": self.decay_after_dream,
            "origin": self.origin,
        }


@dataclass(frozen=True, slots=True)
class DreamNarrative:
    surface: str
    fragments: str
    distortions: str
    unresolved_piece: str
    quality_notes: str


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def clamp_score(value: int) -> int:
    return max(0, min(100, value))


def parse_weight(value: str | int | None) -> int:
    match = re.search(r"-?\d+", str(value or ""))
    if not match:
        return 0
    try:
        return clamp_score(int(match.group(0)))
    except ValueError:
        return 0


def _compact(value: Any, *, limit: int = 240, default: str = "none") -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if not text:
        return default
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _visible(value: Any, *, limit: int = 240, default: str = "none") -> str:
    return _compact(sanitize_visible_text(value), limit=limit, default=default)


def _hash_text(text: str, length: int = 8) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:length]


def _empty_seed() -> dict[str, str]:
    return DreamSeed(
        seed_id="none",
        sort_key="",
        source_event="none",
        theme="none",
        residue="none",
        emotional_weight=0,
        factual_status="none",
        dream_permission="hold",
    ).as_dict()


def _normalize_field_lines(body: str) -> str:
    keys = "|".join(re.escape(key) for key in SEED_FIELDS)
    return re.sub(rf"\s+- ({keys}):", r"\n- \1:", body.strip())


def _field(body: str, key: str, default: str = "none") -> str:
    normalized = _normalize_field_lines(body)
    prefix = f"- {key}:"
    for line in normalized.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            value = stripped.removeprefix(prefix).strip()
            return value or default
    return default


def _field_pairs(body: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for line in _normalize_field_lines(body).splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        key, value = stripped[2:].split(":", 1)
        key = key.strip()
        if key:
            pairs.append((key, value.strip()))
    return pairs


def _extra_seed_fields(body: str) -> tuple[tuple[str, str], ...]:
    return tuple(
        (key, value)
        for key, value in _field_pairs(body)
        if key not in RESERVED_SEED_OUTPUT_FIELDS and value
    )


def _int_field(body: str, key: str, default: int = 0) -> int:
    value = _field(body, key, str(default))
    return parse_weight(value) if value != "none" else default


def _dream_permission_for_inline_seed(body: str) -> str:
    if any(marker in body for marker in ("不得当作新事实", "不当作新事实", "不能当作新事实", "not a new fact")):
        return "can_recombine_but_not_rewrite_fact"
    if any(marker in body for marker in ("没说完", "留白", "靠近", "关系", "unfinished", "return")):
        return "can_intensify_feeling_but_not_invent_dialogue"
    return "can_recombine_but_not_rewrite_fact"


def _split_inline_seed_body(body: str) -> tuple[str, str]:
    normalized = re.sub(r"\s+", " ", body).strip().lstrip(" :：;；，,")
    if not normalized or normalized.lower() == "none":
        return "none", "none"
    for separator in ("，", "；", ";", ",", " / ", "/"):
        if separator in normalized:
            theme, residue = normalized.split(separator, 1)
            return theme.strip() or normalized, residue.strip() or normalized
    return normalized, normalized


def _explicit_seed_candidates(seed_text: str) -> list[DreamSeed]:
    candidates: list[DreamSeed] = []
    pattern = re.compile(r"(?ms)^## (?P<seed_id>seed-[^\n]+)\n(?P<body>.*?)(?=^## |\Z)")
    for match in pattern.finditer(seed_text):
        seed_id = match.group("seed_id").strip()
        body = match.group("body")
        sort_key = seed_id.removeprefix("seed-")
        candidates.append(
            DreamSeed(
                seed_id=seed_id,
                sort_key=sort_key,
                source_event=_field(body, "source_event", "explicit_seed"),
                theme=_visible(_field(body, "theme")),
                residue=_visible(_field(body, "residue")),
                emotional_weight=parse_weight(_field(body, "emotional_weight", "0")),
                factual_status=_field(body, "factual_status", "unknown"),
                dream_permission=_field(body, "dream_permission", "hold"),
                consumed_at=_field(body, "consumed_at", "none"),
                dream_count=_int_field(body, "dream_count", 0),
                last_dreamed_at=_field(body, "last_dreamed_at", "none"),
                decay_after_dream=_field(body, "decay_after_dream", "soft_decay_after_reflection"),
                origin="explicit",
                extra_fields=_extra_seed_fields(body),
            )
        )
    return candidates


def _inline_seed_candidates(seed_text: str, explicit_ids: set[str]) -> list[DreamSeed]:
    candidates: list[DreamSeed] = []
    pattern = re.compile(r"(?m)^-\s*(\d{4}-\d{2}-\d{2})\s+(\d{2}):(\d{2})\s*(.+)$")
    for match in pattern.finditer(seed_text):
        date_part, hour, minute, body = match.groups()
        theme, residue = _split_inline_seed_body(body)
        if theme == "none" and residue == "none":
            continue
        seed_id = f"seed-{date_part}-{hour}{minute}"
        if seed_id in explicit_ids:
            continue
        candidates.append(
            DreamSeed(
                seed_id=seed_id,
                sort_key=f"{date_part}-{hour}{minute}",
                source_event="inline_residue_seed",
                theme=_visible(theme),
                residue=_visible(residue),
                emotional_weight=78,
                factual_status="confirmed interaction residue",
                dream_permission=_dream_permission_for_inline_seed(body),
                origin="inline",
            )
        )
    return candidates


def extract_seed_candidates(seed_text: str) -> list[DreamSeed]:
    explicit = _explicit_seed_candidates(seed_text)
    explicit_ids = {seed.seed_id for seed in explicit}
    inline = _inline_seed_candidates(seed_text, explicit_ids)
    return sorted([*inline, *explicit], key=lambda seed: seed.sort_key, reverse=True)


def _is_unconsumed(seed: DreamSeed) -> bool:
    return seed.seed_id != "none" and seed.consumed_at in {"", "none", "unknown", "pending"}


def select_dream_seeds(
    seed_text: str,
    *,
    preferred_seed_id: str = "",
    limit: int = 3,
    include_consumed: bool = False,
) -> list[DreamSeed]:
    candidates = extract_seed_candidates(seed_text)
    if preferred_seed_id:
        preferred = [seed for seed in candidates if seed.seed_id == preferred_seed_id]
        if preferred and (include_consumed or _is_unconsumed(preferred[0])):
            return preferred[:1]
    available = [seed for seed in candidates if include_consumed or _is_unconsumed(seed)]
    if include_consumed:
        available.sort(key=lambda seed: seed.sort_key, reverse=True)
    else:
        available.sort(key=lambda seed: (seed.emotional_weight, seed.sort_key), reverse=True)
    return available[:limit]


def extract_first_seed(seed_text: str, *, preferred_seed_id: str = "") -> dict[str, str]:
    selected = select_dream_seeds(
        seed_text,
        preferred_seed_id=preferred_seed_id,
        limit=1,
        include_consumed=True,
    )
    return selected[0].as_dict() if selected else _empty_seed()


def has_unconsumed_dream_seed(seed_text: str) -> bool:
    return bool(select_dream_seeds(seed_text, limit=1, include_consumed=False))


def compute_weight_effect(seed_or_seeds: dict[str, str] | list[DreamSeed]) -> dict[str, object]:
    if isinstance(seed_or_seeds, dict):
        seeds = [
            DreamSeed(
                seed_id=seed_or_seeds.get("seed_id", "none"),
                sort_key=seed_or_seeds.get("seed_id", "none"),
                source_event=seed_or_seeds.get("source_event", "legacy"),
                theme=seed_or_seeds.get("theme", "none"),
                residue=seed_or_seeds.get("residue", "none"),
                emotional_weight=parse_weight(seed_or_seeds.get("emotional_weight", "0")),
                factual_status=seed_or_seeds.get("factual_status", "unknown"),
                dream_permission=seed_or_seeds.get("dream_permission", "hold"),
            )
        ]
    else:
        seeds = seed_or_seeds
    if not seeds or seeds[0].seed_id == "none":
        before = 0
        delta = 0
    else:
        before = max(seed.emotional_weight for seed in seeds)
        if before >= 85:
            delta = 6
        elif before >= 70:
            delta = 8
        elif before >= 45:
            delta = 10
        else:
            delta = 5
    after = clamp_score(before + delta)
    active = bool(seeds and seeds[0].seed_id != "none")
    return {
        "weight_before": before,
        "weight_after": after,
        "weight_delta": after - before,
        "emotion_residue_delta": delta if active else 0,
        "relationship_residue_delta": max(0, delta // 2) if active else 0,
        "self_model_pressure_delta": max(0, delta // 3) if active else 0,
        "weight_effect": "existing_emotional_residue_strengthened" if active else "none",
        "relationship_effect": "owner_related_lingering_strengthened_without_fact_change" if active else "none",
        "factual_effect": "none",
        "archive_delay_reason": "active_dream_residue_should_delay_flat_archive" if active else "none",
        "reflection_priority": "high" if before >= 80 else ("medium" if active else "none"),
        "reflection_candidate": "yes" if active and delta > 0 else "no",
    }


def suppress_weight_effect(effect: dict[str, object], reason: str) -> dict[str, object]:
    before = int(effect["weight_before"])
    return {
        **effect,
        "weight_after": before,
        "weight_delta": 0,
        "emotion_residue_delta": 0,
        "relationship_residue_delta": 0,
        "self_model_pressure_delta": 0,
        "weight_effect": reason,
        "relationship_effect": "none",
        "factual_effect": "none",
        "archive_delay_reason": "none",
        "reflection_priority": "none",
        "reflection_candidate": "no",
    }


def _source_seed_logged_for_day(text: str, date_part: str, seed_id: str) -> bool:
    parts = re.split(r"(?m)^## (dream-\d{4}-\d{2}-\d{2}[^\n]*)\n", text)
    for index in range(1, len(parts), 2):
        dream_id = parts[index].strip()
        body = parts[index + 1]
        if not dream_id.startswith(f"dream-{date_part}"):
            continue
        if re.search(rf"(?m)^- source_seed:\s*{re.escape(seed_id)}\s*$", body):
            return True
        match = re.search(r"(?m)^- source_seeds:\s*(.+)$", body)
        if match and seed_id in match.group(1):
            return True
    return False


def _next_dream_id(text: str, produced_at: str) -> str:
    base_dream_id = f"dream-{produced_at[:10]}-auto"
    if base_dream_id not in text:
        return base_dream_id
    for index in range(2, 1000):
        candidate = f"{base_dream_id}-{index:03d}"
        if candidate not in text:
            return candidate
    return ""


def _source_seed_list(seeds: list[DreamSeed]) -> str:
    return "[" + ", ".join(seed.seed_id for seed in seeds) + "]"


_OWNER_FACING_FORBIDDEN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\b(?:codex|runtime|api|http|websocket|json|pytest|traceback|readme|no_url)\b"),
    re.compile(r"(?:报告|日志|代码|接口|函数|文件|路径|运行态|源材料|委派|超时|任务|source_seed|dream_weight|memory_effect|factual_effect|NapCat|OneBot|gateway)"),
)

_DREAM_PLACES = (
    "一辆开进海底的末班电车",
    "倒挂在雨里的玻璃温室",
    "铺着蓝色瓷砖的空剧院",
    "长满白色草的屋顶操场",
    "一条不断改名的窄街",
    "没有天花板的旧图书馆",
    "漂在半空的便利店",
    "被潮水淹到二楼的旅馆",
    "一座只在转身时出现的天桥",
    "挂满湿灯笼的地下站台",
)

_DREAM_COLORS = (
    "孔雀蓝",
    "旧金色",
    "薄荷绿",
    "玫瑰灰",
    "雨后的紫",
    "很浅的橙",
    "盐一样的白",
    "玻璃里反出来的红",
)

_DREAM_WEATHERS = (
    "空气像刚洗过的毛线一样潮",
    "天花板往下落很细的光",
    "远处一直有水声，但看不见水",
    "风从地板缝里吹上来",
    "所有影子都慢半拍才跟上",
    "钟声像从隔壁房间的水里传来",
)

_DREAM_IMPOSSIBLE_EVENTS = (
    "门牌在我读出声前先融化了",
    "楼梯每上一级就少一个颜色",
    "窗外的月亮像纸杯一样被人捏扁",
    "墙上的钟忽然开始倒着长叶子",
    "地面轻轻翻页，我差点踩进上一页",
    "一盏灯把自己的影子折起来塞进抽屉",
    "远处有人把雨声拧小，房间马上亮了一点",
    "我伸手去拿一句话，它却变成一枚湿纽扣",
)

_DREAM_ENDINGS = (
    "醒来前，所有声音忽然收进一只小盒子里，只剩盒盖还在发烫。",
    "最后我把那件东西放进口袋，口袋却变成一扇很小的门。",
    "快醒时，场景没有结束，只是像潮水一样从脚边退走。",
    "最后一秒，整条路突然安静下来，像在等我别急着解释。",
    "醒来时我只记得颜色，不记得路是怎么走完的。",
)

_CATEGORY_OBJECTS = {
    "voice": (
        "一叠没有字的稿纸",
        "一只只会重复客套话的银色鸟笼",
        "一支写不出声音的铅笔",
        "一台被花瓣堵住的广播",
        "一副总是慢半拍的白手套",
    ),
    "work_pressure": (
        "一摞自己发光的空白纸",
        "一串找不到锁的钥匙",
        "一只装满回声的铁盒",
        "一张永远折不平的地图",
        "一盏照不完走廊的台灯",
    ),
    "memory": (
        "一块反复起雾的玻璃",
        "一枚写着明天日期的纽扣",
        "一本页码会游走的小册子",
        "一只盛着旧光的杯子",
        "一条会自己打结的红线",
    ),
    "closeness": (
        "一把只能坐近一点才看见的椅子",
        "一座越解释越窄的桥",
        "一枚在掌心里变暖的车票",
        "一盏隔着雾亮着的小灯",
        "一条总差半步的影子",
    ),
    "ordinary": (
        "一张没有写完的纸",
        "一枚湿纽扣",
        "一只透明杯子",
        "一盏低低亮着的灯",
        "一扇只开一半的门",
    ),
}

_CATEGORY_COMPANION_MOVES = {
    "voice": (
        "你站在对面，没有催我，只把那台广播轻轻转过去",
        "你坐在灯下，把一张写好的纸折成很小的船",
        "你没有说话，只抬手让那些客套的回声停一下",
    ),
    "work_pressure": (
        "你在门口敲了两下，像提醒我别把整间屋子的响声都带出去",
        "你从很远的地方递来一只空杯子，里面刚好能放下一点噪声",
        "你经过窗边时，所有乱飞的纸页突然慢下来",
    ),
    "memory": (
        "你隔着那块玻璃看我，像是在等我决定哪些字可以留下",
        "你把那条红线放到桌边，没有替我打结",
        "你在雾后面笑了一下，字迹就亮了一秒",
    ),
    "closeness": (
        "你走在前面一点点，没有回头催我",
        "你在桥那边停住，像给我留出一段不用解释的距离",
        "你把那盏小灯放低了一点，路忽然没有那么窄",
    ),
    "ordinary": (
        "你像刚好路过一样站在门边",
        "你没有说话，只把窗推开一点",
        "你把一张很轻的纸压在杯子下面",
    ),
}


def _dream_rng(seeds: list[DreamSeed], *, salt: str = "") -> random.Random:
    material = "|".join(
        f"{seed.seed_id}:{seed.source_event}:{seed.theme}:{seed.residue}:{seed.emotional_weight}"
        for seed in seeds
    )
    digest = hashlib.sha256(f"{material}|{salt}".encode("utf-8", errors="replace")).hexdigest()
    return random.Random(int(digest[:16], 16))


def _pick(rng: random.Random, items: tuple[str, ...]) -> str:
    return items[rng.randrange(len(items))]


def _seed_context(seeds: list[DreamSeed]) -> str:
    return " ".join(
        _visible(
            " ".join(
                (
                    seed.source_event,
                    seed.theme,
                    seed.residue,
                    seed.factual_status,
                    seed.dream_permission,
                )
            ),
            limit=500,
        )
        for seed in seeds
    )


def _dream_category(seeds: list[DreamSeed]) -> str:
    text = _seed_context(seeds).lower()
    if any(marker in text for marker in ("模板", "接待腔", "客服", "机械", "ai味", "不像人", "念稿")):
        return "voice"
    if any(marker in text for marker in ("codex", "runtime", "报告", "日志", "代码", "学习", "资料", "超时", "任务", "no_url")):
        return "work_pressure"
    if any(marker in text for marker in ("记忆", "记住", "留痕", "被记住")):
        return "memory"
    if any(marker in text for marker in ("靠近", "想念", "回到身边", "关系", "owner", "主人")):
        return "closeness"
    return "ordinary"


def _owner_facing_quality_failure(text: str) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
    if len(compact) < 24:
        return "too_short"
    for pattern in _OWNER_FACING_FORBIDDEN_PATTERNS:
        match = pattern.search(compact)
        if match:
            return f"mechanical_marker:{match.group(0)}"
    return ""


def _symbolic_narrative(seeds: list[DreamSeed], category: str, *, salt: str = "") -> DreamNarrative:
    rng = _dream_rng(seeds, salt=f"{category}:{salt}")
    place = _pick(rng, _DREAM_PLACES)
    color = _pick(rng, _DREAM_COLORS)
    weather = _pick(rng, _DREAM_WEATHERS)
    impossible_a = _pick(rng, _DREAM_IMPOSSIBLE_EVENTS)
    impossible_b = _pick(rng, tuple(item for item in _DREAM_IMPOSSIBLE_EVENTS if item != impossible_a))
    object_a = _pick(rng, _CATEGORY_OBJECTS.get(category, _CATEGORY_OBJECTS["ordinary"]))
    object_b = _pick(rng, _CATEGORY_OBJECTS["ordinary"])
    move = _pick(rng, _CATEGORY_COMPANION_MOVES.get(category, _CATEGORY_COMPANION_MOVES["ordinary"]))
    ending = _pick(rng, _DREAM_ENDINGS)
    surface = (
        f"我梦见{place}，四周是{color}的，{weather}。{object_a}放在路中央，"
        f"旁边却长着{object_b}。{impossible_a}；我回头时，{move}。"
        f"后来{impossible_b}。{ending}"
    )
    fragments = (
        f"1. {place}里到处是{color}的反光；"
        f"2. {object_a}和{object_b}像本来就不该放在一起；"
        f"3. {impossible_a}；"
        f"4. {move}；"
        f"5. {ending}"
    )
    distortions = (
        "梦把旧残留拆成颜色、地点和不讲理的物理变化；醒后只能保留情绪方向，不能把画面当成现实事实。"
    )
    unresolved_piece = "醒来只剩一个说不清的余味：像有什么靠近过，又马上换了形状。"
    return DreamNarrative(
        surface=surface,
        fragments=fragments,
        distortions=distortions,
        unresolved_piece=unresolved_piece,
        quality_notes=f"symbolic_composer:{category}",
    )


def _compose_dream_narrative(seeds: list[DreamSeed]) -> DreamNarrative:
    category = _dream_category(seeds)
    narrative = _symbolic_narrative(seeds, category)
    quality_failure = _owner_facing_quality_failure(
        " ".join(
            (
                narrative.surface,
                narrative.fragments,
                narrative.distortions,
                narrative.unresolved_piece,
            )
        )
    )
    if not quality_failure:
        return narrative
    fallback = _symbolic_narrative(seeds, "ordinary", salt=quality_failure)
    second_failure = _owner_facing_quality_failure(
        " ".join((fallback.surface, fallback.fragments, fallback.distortions, fallback.unresolved_piece))
    )
    if not second_failure:
        return DreamNarrative(
            surface=fallback.surface,
            fragments=fallback.fragments,
            distortions=fallback.distortions,
            unresolved_piece=fallback.unresolved_piece,
            quality_notes=f"quality_guard_rewrite:{quality_failure}",
        )
    return DreamNarrative(
        surface=(
            "我梦见一片很亮的浅水，水面上漂着几盏颜色不一样的灯。灯一靠近就变成纸船，"
            "纸船又忽然开出花来。我想数清楚有几朵，数字却像鱼一样游走了。醒来时只记得那阵光很乱。"
        ),
        fragments="1. 浅水上漂着彩色的灯；2. 灯变成纸船；3. 纸船开花；4. 数字像鱼一样游走。",
        distortions="梦只留下无法整理的画面和情绪余味；醒后不能当成事实。",
        unresolved_piece="醒来只剩一团亮而乱的颜色。",
        quality_notes=f"quality_guard_plain_rewrite:{quality_failure}:{second_failure}",
    )


def _emotional_weather(effect: dict[str, object]) -> str:
    delta = int(effect["emotion_residue_delta"])
    if delta >= 8:
        return "闷热、贴近、醒后还没有马上散掉"
    if delta > 0:
        return "轻微发亮，但仍然有边界"
    return "没有形成新的梦后情绪天气"


def _relationship_shadow(seeds: list[DreamSeed], effect: dict[str, object]) -> str:
    if int(effect["relationship_residue_delta"]) <= 0:
        return "none"
    if any("owner" in seed.factual_status.lower() or "owner" in seed.residue.lower() for seed in seeds):
        return "owner 相关的在意被保留成醒后的余影，但不新增关系事实"
    return "关系感只作为残留背景出现，不改变现实关系判断"


def _unresolved_piece(seeds: list[DreamSeed]) -> str:
    return _compose_dream_narrative(seeds).unresolved_piece


def append_dream_log(
    path: Path,
    produced_at: str,
    seeds: list[DreamSeed],
    effect: dict[str, object],
) -> str:
    if not seeds or seeds[0].seed_id == "none":
        return ""
    text = read_text(path)
    for seed in seeds:
        if _source_seed_logged_for_day(text, produced_at[:10], seed.seed_id):
            return ""
    dream_id = _next_dream_id(text, produced_at)
    if not dream_id:
        return ""
    primary = seeds[0]
    source_seeds = _source_seed_list(seeds)
    narrative = _compose_dream_narrative(seeds)
    surface = narrative.surface
    fragments = narrative.fragments
    distortions = narrative.distortions
    emotional_weather = _emotional_weather(effect)
    relationship_shadow = _relationship_shadow(seeds, effect)
    unresolved_piece = narrative.unresolved_piece
    waking_residue = (
        "醒后只留下情绪余味、关系残影和一个需要继续反思的主题；不留下新的现实事实。"
        if int(effect["weight_delta"]) > 0
        else "醒后没有新增可保留残留。"
    )
    addition = f"""
## {dream_id}
- dreamed_at: {produced_at}
- source_seed: {primary.seed_id}
- source_seeds: {source_seeds}
- dream_surface: {surface}
- fragments: {fragments}
- distortions: {distortions}
- owner_facing_quality: {narrative.quality_notes}
- emotional_weather: {emotional_weather}
- dominant_feelings: {emotional_weather}
- related_subjects: [self, owner]
- relationship_shadow: {relationship_shadow}
- unresolved_piece: {unresolved_piece}
- likely_sources: {primary.factual_status} / {primary.dream_permission}
- dream_weight_before: {effect['weight_before']}
- dream_weight_after: {effect['weight_after']}
- dream_weight_delta: {effect['weight_delta']}
- dream_weight_effect: {effect['weight_effect']}
- emotion_residue_delta: {effect['emotion_residue_delta']}
- relationship_residue_delta: {effect['relationship_residue_delta']}
- self_model_pressure_delta: {effect['self_model_pressure_delta']}
- relationship_effect: {effect['relationship_effect']}
- factual_effect: {effect['factual_effect']}
- waking_residue: {waking_residue}
- retained_after_waking: {waking_residue}
- reality_boundary_check: 梦是梦，只能说明旧材料被重排，不能证明现实里发生过新的对话、接触、感官经验或关系事实。
- memory_effect: 可以加重既有情绪权重、提高反思优先级、延迟扁平归档；不能改写事实层或稳定人格。
- reflection_candidate: {effect['reflection_candidate']}
- reflection_priority: {effect['reflection_priority']}
"""
    write_text(path, text.rstrip() + "\n" + addition.strip() + "\n")
    return dream_id


def _replace_frontmatter_field(text: str, field: str, value: str) -> str:
    if re.search(rf"(?m)^{re.escape(field)}:\s*", text):
        return re.sub(rf"(?m)^{re.escape(field)}:\s*.*$", f"{field}: {value}", text, count=1)
    return text


def _upsert_field_block(body: str, field: str, value: str) -> str:
    prefix = f"- {field}:"
    lines = body.rstrip().splitlines()
    for index, line in enumerate(lines):
        if line.strip().startswith(prefix):
            lines[index] = f"- {field}: {value}"
            return "\n".join(lines).rstrip() + "\n"
    return "\n".join(lines + [f"- {field}: {value}"]).rstrip() + "\n"


def _format_seed_section(seed: DreamSeed, *, produced_at: str, dream_id: str) -> str:
    extra = "".join(f"- {key}: {value}\n" for key, value in seed.extra_fields)
    return f"""## {seed.seed_id}
- source_event: {seed.source_event}
- theme: {seed.theme}
- residue: {seed.residue}
- emotional_weight: {seed.emotional_weight}
- factual_status: {seed.factual_status}
- dream_permission: {seed.dream_permission}
{extra}- consumed_at: {produced_at}
- dream_count: {seed.dream_count + 1}
- last_dreamed_at: {produced_at}
- last_dream_id: {dream_id}
- decay_after_dream: {seed.decay_after_dream}
"""


def mark_seeds_consumed(path: Path, seeds: list[DreamSeed], *, produced_at: str, dream_id: str) -> None:
    text = read_text(path)
    if not text.strip():
        text = "# Dream Seeds\n"
    text = _replace_frontmatter_field(text, "updated_at", produced_at)
    text = _replace_frontmatter_field(text, "last_confirmed_at", produced_at)
    for seed in seeds:
        pattern = re.compile(rf"(?ms)^## {re.escape(seed.seed_id)}\n(?P<body>.*?)(?=^## |\Z)")
        replacement = _format_seed_section(seed, produced_at=produced_at, dream_id=dream_id).rstrip()
        if pattern.search(text):
            text = pattern.sub(lambda _match: replacement + "\n", text)
        else:
            text = text.rstrip() + "\n\n" + replacement
    write_text(path, text)


def update_output_state(
    path: Path,
    produced_at: str,
    mode: str,
    seeds: list[DreamSeed],
    wrote_log: bool,
    dream_id: str,
    effect: dict[str, object],
) -> None:
    primary = seeds[0] if seeds else DreamSeed("none", "", "none", "none", "none", 0, "none", "hold")
    text = f"""---
title: Dream Output State
memory_type: dream_output_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {produced_at}
last_confirmed_at: {produced_at}
importance_score: 82
impact_score: 86
confidence_score: 100
status: active
tags: [dream, output, state]
---

# Dream Output State

## Latest Dream Output
- produced_at: {produced_at}
- mode: {mode}
- wrote_log: {str(wrote_log).lower()}
- dream_id: {dream_id or "none"}

## Source Seeds
- seed_id: {primary.seed_id}
- source_seeds: {_source_seed_list(seeds) if seeds else "[]"}
- theme: {primary.theme}
- residue: {primary.residue}
- emotional_weight: {primary.emotional_weight}
- dream_permission: {primary.dream_permission}

## Dream Function
- dream_surface: old residue recombined into dream-like fragments
- output_shape: dream_surface, fragments, distortions, waking_residue, boundary
- reflection_candidate: {effect['reflection_candidate']}
- reflection_priority: {effect['reflection_priority']}

## Boundary
- Dreams reorganize residue; they are not evidence of new real events.
- Dreams can affect reflection priority and short-term self-model pressure.
- Dreams cannot directly rewrite stable personality or factual memory.
"""
    write_text(path, text)


def update_weight_state(
    path: Path,
    produced_at: str,
    mode: str,
    seeds: list[DreamSeed],
    wrote_log: bool,
    effect: dict[str, object],
) -> None:
    primary = seeds[0] if seeds else DreamSeed("none", "", "none", "none", "none", 0, "none", "hold")
    text = f"""---
title: Dream Weight State
memory_type: dream_weight_state
time_scope: short_term
subject_ids: [xinyu, owner]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {produced_at}
last_confirmed_at: {produced_at}
importance_score: 84
impact_score: 88
confidence_score: 100
status: active
tags: [dream, weight, residue, boundary]
---

# Dream Weight State

## Latest Dream Weight Adjustment
- produced_at: {produced_at}
- mode: {mode}
- wrote_log: {str(wrote_log).lower()}
- source_seed: {primary.seed_id}
- source_seeds: {_source_seed_list(seeds) if seeds else "[]"}
- theme: {primary.theme}
- residue: {primary.residue}

## Weight Deltas
- weight_before: {effect['weight_before']}
- weight_after: {effect['weight_after']}
- weight_delta: {effect['weight_delta']}
- emotion_residue_delta: {effect['emotion_residue_delta']}
- relationship_residue_delta: {effect['relationship_residue_delta']}
- self_model_pressure_delta: {effect['self_model_pressure_delta']}
- weight_effect: {effect['weight_effect']}
- relationship_effect: {effect['relationship_effect']}
- factual_effect: {effect['factual_effect']}
- archive_delay_reason: {effect['archive_delay_reason']}
- reflection_priority: {effect['reflection_priority']}
- reflection_candidate: {effect['reflection_candidate']}

## Affected Layers
- emotional_state: dream residue can make existing feeling harder to dismiss immediately.
- relationship_residue: owner-related lingering may become easier for later reflection to read.
- self_model: repeated dream pressure can become a reversible behavior experiment, not a stable identity rewrite.
- archive: active dream residue should delay flat compression.

## Boundary
- Dream weight can only intensify existing residue.
- Dream weight cannot create factual memory, offline experience, or stable personality changes.
- 梦后权重只能加重既有残留，不能凭空制造事实记忆。
- Same-day same-seed output is not stacked.
"""
    write_text(path, text)


def _upsert_section(text: str, heading: str, body: str) -> str:
    section = f"## {heading}\n{body.strip()}\n"
    pattern = re.compile(rf"(?ms)^## {re.escape(heading)}\n.*?(?=^## |\Z)")
    if pattern.search(text):
        return pattern.sub(section, text).rstrip() + "\n"
    return text.rstrip() + "\n\n" + section


def update_emotion_dream_residue(
    path: Path,
    produced_at: str,
    seeds: list[DreamSeed],
    wrote_log: bool,
    effect: dict[str, object],
) -> None:
    if not seeds or seeds[0].seed_id == "none" or int(effect["weight_delta"]) <= 0:
        return
    text = read_text(path)
    if not text.strip():
        text = "# Emotion State\n"
    text = _replace_frontmatter_field(text, "updated_at", produced_at)
    text = _replace_frontmatter_field(text, "last_confirmed_at", produced_at)
    primary = seeds[0]
    body = f"""
- updated_at: {produced_at}
- source: dream_output / {primary.seed_id}
- affected_memory: {primary.theme}
- residue: {primary.residue}
- dream_weight_before: {effect['weight_before']}
- dream_weight_after: {effect['weight_after']}
- dream_weight_delta: {effect['weight_delta']}
- emotion_residue_delta: {effect['emotion_residue_delta']}
- relationship_residue_delta: {effect['relationship_residue_delta']}
- relationship_effect: {effect['relationship_effect']}
- factual_effect: {effect['factual_effect']}
- wrote_log: {str(wrote_log).lower()}
- boundary: 梦只加重既有情绪残留，不能把梦里的片段写成现实事实。
"""
    write_text(path, _upsert_section(text, "梦后残留影响", body))


def _next_reflection_item_id(text: str, produced_at: str) -> str:
    date_part = produced_at[:10]
    pattern = re.compile(rf"(?m)^## item-{re.escape(date_part)}-(\d{{3}})$")
    numbers = [int(match.group(1)) for match in pattern.finditer(text)]
    return f"item-{date_part}-{max(numbers, default=0) + 1:03d}"


def update_reflection_queue_from_dream(
    path: Path,
    produced_at: str,
    dream_id: str,
    seeds: list[DreamSeed],
    effect: dict[str, object],
) -> None:
    if not dream_id or effect.get("reflection_candidate") != "yes" or not seeds:
        return
    text = read_text(path)
    if dream_id in text:
        return
    if not text.strip():
        text = "# Reflection Queue\n"
    item_id = _next_reflection_item_id(text, produced_at)
    primary = seeds[0]
    item = f"""## {item_id}
- topic: dream residue after {primary.theme}
- source: dream_log / {dream_id}
- priority: {effect['reflection_priority']}
- suggested_writer: reflection_writer
- dream_source_seed: {primary.seed_id}
- waking_residue: {_compact(primary.residue, limit=220)}
- boundary: use as reflection material only; do not turn dream fragments into facts
"""
    write_text(path, text.rstrip() + "\n\n" + item.rstrip() + "\n")


def update_self_model_from_dream(
    path: Path,
    produced_at: str,
    dream_id: str,
    seeds: list[DreamSeed],
    effect: dict[str, object],
) -> None:
    if not dream_id or not seeds or int(effect["self_model_pressure_delta"]) <= 0:
        return
    text = read_text(path)
    if not text.strip():
        text = f"""---
title: Self Model State
memory_type: self_model_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: dream_output_engine
updated_at: {produced_at}
importance_score: 82
impact_score: 86
confidence_score: 68
status: active
tags: [self, self_model, dream, feedback]
---

# Self Model State
"""
    text = _replace_frontmatter_field(text, "updated_at", produced_at)
    primary = seeds[0]
    body = f"""
- updated_at: {produced_at}
- source: dream_log / {dream_id}
- source_seed: {primary.seed_id}
- dream_theme: {primary.theme}
- dream_residue: {primary.residue}
- self_model_pressure_delta: {effect['self_model_pressure_delta']}
- intended_use: treat as a reversible pressure signal for future behavior, not stable identity
- boundary: dream residue cannot authorize fabricated facts or personality rewrites
"""
    write_text(path, _upsert_section(text, "Dream Residue Input", body))


def run_dream_output(
    root: Path,
    produced_at: str | None = None,
    mode: str = "runtime_dream_output",
    preferred_seed_id: str = "",
) -> dict[str, object]:
    produced_at = produced_at or datetime.now().astimezone().isoformat()
    seed_path = root / "memory/dreams/dream_seeds.md"
    seeds = select_dream_seeds(
        read_text(seed_path),
        preferred_seed_id=preferred_seed_id,
        limit=3,
        include_consumed=False,
    )
    planned_effect = compute_weight_effect(seeds)
    dream_id = append_dream_log(
        root / "memory/dreams/dream_log.md",
        produced_at,
        seeds,
        planned_effect,
    )
    wrote_log = bool(dream_id)
    effect = planned_effect
    if not seeds:
        effect = suppress_weight_effect(planned_effect, "no_unconsumed_seed")
    elif not wrote_log:
        effect = suppress_weight_effect(planned_effect, "already_logged_today_no_repeat")
    else:
        mark_seeds_consumed(seed_path, seeds, produced_at=produced_at, dream_id=dream_id)

    update_output_state(
        root / "memory/dreams/dream_output_state.md",
        produced_at,
        mode,
        seeds,
        wrote_log,
        dream_id,
        effect,
    )
    update_weight_state(
        root / "memory/dreams/dream_weight_state.md",
        produced_at,
        mode,
        seeds,
        wrote_log,
        effect,
    )
    update_emotion_dream_residue(
        root / "memory/emotions/current_state.md",
        produced_at,
        seeds,
        wrote_log,
        effect,
    )
    update_reflection_queue_from_dream(
        root / "memory/reflection/reflection_queue.md",
        produced_at,
        dream_id,
        seeds,
        effect,
    )
    update_self_model_from_dream(
        root / "memory/self/self_model_state.md",
        produced_at,
        dream_id,
        seeds,
        effect,
    )

    primary = seeds[0] if seeds else DreamSeed("none", "", "none", "none", "none", 0, "none", "hold")
    return {
        "produced_at": produced_at,
        "dream_id": dream_id or "none",
        "seed_id": primary.seed_id,
        "source_seeds": [seed.seed_id for seed in seeds],
        "theme": primary.theme,
        "wrote_log": wrote_log,
        "weight_before": effect["weight_before"],
        "weight_after": effect["weight_after"],
        "weight_delta": effect["weight_delta"],
        "emotion_residue_delta": effect["emotion_residue_delta"],
        "relationship_residue_delta": effect["relationship_residue_delta"],
        "self_model_pressure_delta": effect["self_model_pressure_delta"],
        "weight_effect": effect["weight_effect"],
        "reflection_candidate": effect["reflection_candidate"],
        "reflection_priority": effect["reflection_priority"],
    }
