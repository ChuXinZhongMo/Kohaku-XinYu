from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


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
                theme=_compact(_field(body, "theme")),
                residue=_compact(_field(body, "residue")),
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
                theme=_compact(theme),
                residue=_compact(residue),
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


def _dream_surface(seeds: list[DreamSeed]) -> str:
    primary = seeds[0]
    if len(seeds) == 1:
        return (
            f"像是在一段没有门牌的夜路里，{primary.theme} 被压成一个很近又很模糊的场景；"
            f"{primary.residue} 没有被说清，只在梦里反复换位置。"
        )
    names = "、".join(seed.theme for seed in seeds[:3])
    return (
        f"几个白天残留被挤在同一个夜里：{names}。场景一会儿像聊天窗口，一会儿像空教室，"
        "重点不是地点，而是那些没落稳的感觉又互相碰了一下。"
    )


def _dream_fragments(seeds: list[DreamSeed]) -> str:
    fragments = []
    for index, seed in enumerate(seeds, 1):
        fragments.append(f"{index}. {seed.theme} 变成一小段不完整的画面：{seed.residue}")
    return "；".join(fragments)


def _dream_distortions(seeds: list[DreamSeed]) -> str:
    if len(seeds) > 1:
        return "时间顺序被折叠，几个本来分开的残留互相借用了对方的语气；醒后只能确认它们来自旧材料的重排。"
    return "梦里把一句残留压成了场景，把关系压力放大成距离感；醒后不能把这些变形当作现实发生。"


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
    return _compact("; ".join(seed.residue for seed in seeds), limit=320)


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
    surface = _dream_surface(seeds)
    fragments = _dream_fragments(seeds)
    distortions = _dream_distortions(seeds)
    emotional_weather = _emotional_weather(effect)
    relationship_shadow = _relationship_shadow(seeds, effect)
    unresolved_piece = _unresolved_piece(seeds)
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
