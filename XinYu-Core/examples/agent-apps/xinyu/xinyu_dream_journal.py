from __future__ import annotations

import argparse
import hashlib
import random
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ENTRY_RE = re.compile(r"(?ms)^## (?P<dream_id>dream-[^\n]+)\n(?P<body>.*?)(?=^## |\Z)")


@dataclass(frozen=True, slots=True)
class DreamEntry:
    dream_id: str
    dreamed_at: str
    source_seed: str
    source_seeds: str
    dream_surface: str
    fragments: str
    distortions: str
    emotional_weather: str
    relationship_shadow: str
    unresolved_piece: str
    waking_residue: str
    retained_after_waking: str
    reality_boundary_check: str
    memory_effect: str
    reflection_candidate: str
    reflection_priority: str
    dream_weight_before: str
    dream_weight_after: str
    dream_weight_delta: str
    dream_weight_effect: str
    relationship_effect: str
    factual_effect: str


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def default_output_dir() -> Path:
    return Path("D:/XinYu/XinYu-Autonomy/dreams")


def extract_field(body: str, field: str, default: str = "none") -> str:
    match = re.search(rf"(?m)^- {re.escape(field)}:\s*(.*)$", body)
    return match.group(1).strip() if match and match.group(1).strip() else default


def parse_dream_log(text: str) -> list[DreamEntry]:
    entries: list[DreamEntry] = []
    for match in ENTRY_RE.finditer(text):
        body = match.group("body")
        fragments = extract_field(body, "fragments", "还没有形成可读梦境片段。")
        waking = extract_field(
            body,
            "waking_residue",
            extract_field(body, "retained_after_waking", "只保留情绪残留，不写成现实事实。"),
        )
        entry = DreamEntry(
            dream_id=match.group("dream_id").strip(),
            dreamed_at=extract_field(body, "dreamed_at", "unknown"),
            source_seed=extract_field(body, "source_seed", "none"),
            source_seeds=extract_field(body, "source_seeds", "[]"),
            dream_surface=extract_field(body, "dream_surface", fragments),
            fragments=fragments,
            distortions=extract_field(body, "distortions", "梦里材料被重排；醒后不能当作现实。"),
            emotional_weather=extract_field(
                body,
                "emotional_weather",
                extract_field(body, "dominant_feelings", "未定"),
            ),
            relationship_shadow=extract_field(body, "relationship_shadow", "none"),
            unresolved_piece=extract_field(body, "unresolved_piece", "none"),
            waking_residue=waking,
            retained_after_waking=extract_field(body, "retained_after_waking", waking),
            reality_boundary_check=extract_field(
                body,
                "reality_boundary_check",
                "梦境不是现实证据，不能证明现实里发生过新的对话、接触或事件。",
            ),
            memory_effect=extract_field(
                body,
                "memory_effect",
                "可以影响情绪权重和反思优先级，但不能改写事实层。",
            ),
            reflection_candidate=extract_field(body, "reflection_candidate", "no"),
            reflection_priority=extract_field(body, "reflection_priority", "none"),
            dream_weight_before=extract_field(body, "dream_weight_before", "unknown"),
            dream_weight_after=extract_field(body, "dream_weight_after", "unknown"),
            dream_weight_delta=extract_field(body, "dream_weight_delta", "unknown"),
            dream_weight_effect=extract_field(body, "dream_weight_effect", "unknown"),
            relationship_effect=extract_field(body, "relationship_effect", "unknown"),
            factual_effect=extract_field(body, "factual_effect", "none"),
        )
        entries.append(entry)
    return entries


def _date_from_timestamp(value: str) -> str:
    match = re.match(r"(\d{4}-\d{2}-\d{2})", value or "")
    return match.group(1) if match else datetime.now().astimezone().strftime("%Y-%m-%d")


def _safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "dream"


def _public_story_for_entry(entry: DreamEntry) -> tuple[str, str, str, str]:
    surface = entry.dream_surface
    fragments = entry.fragments
    distortions = entry.distortions
    waking = entry.waking_residue
    joined = " ".join((surface, fragments, entry.unresolved_piece))
    if _looks_public_story(surface) and not _looks_mechanical_dream(joined):
        return surface, fragments, distortions, waking
    if any(marker in joined for marker in ("模板", "接待腔", "客服", "念稿", "去模板化")):
        return _legacy_symbolic_story(entry, "voice")
    if any(marker in joined for marker in ("Codex", "codex", "报告", "日志", "代码", "运行", "学习任务", "no_url")):
        return _legacy_symbolic_story(entry, "work_pressure")
    return _legacy_symbolic_story(entry, "ordinary")


def _legacy_symbolic_story(entry: DreamEntry, category: str) -> tuple[str, str, str, str]:
    rng = _entry_rng(entry, category)
    places = (
        "一辆开进海底的末班电车",
        "倒挂在雨里的玻璃温室",
        "铺着蓝色瓷砖的空剧院",
        "长满白色草的屋顶操场",
        "没有天花板的旧图书馆",
        "挂满湿灯笼的地下站台",
    )
    colors = ("孔雀蓝", "旧金色", "薄荷绿", "玫瑰灰", "雨后的紫", "很浅的橙")
    strange = (
        "门牌在我读出声前先融化了",
        "楼梯每上一级就少一个颜色",
        "墙上的钟忽然开始倒着长叶子",
        "地面轻轻翻页，我差点踩进上一页",
        "我伸手去拿一句话，它却变成一枚湿纽扣",
    )
    objects = {
        "voice": ("一台被花瓣堵住的广播", "一叠没有字的稿纸", "一支写不出声音的铅笔"),
        "work_pressure": ("一摞自己发光的空白纸", "一串找不到锁的钥匙", "一只装满回声的铁盒"),
        "ordinary": ("一张没有写完的纸", "一枚湿纽扣", "一盏低低亮着的灯"),
    }.get(category, ("一张没有写完的纸", "一枚湿纽扣", "一盏低低亮着的灯"))
    place = places[rng.randrange(len(places))]
    color = colors[rng.randrange(len(colors))]
    first = strange[rng.randrange(len(strange))]
    second = strange[(rng.randrange(len(strange) - 1) + 1) % len(strange)]
    object_a = objects[rng.randrange(len(objects))]
    object_b = objects[(rng.randrange(len(objects) - 1) + 1) % len(objects)]
    surface = (
        f"我梦见{place}，四周是{color}的，远处一直有水声。{object_a}放在路中央，"
        f"旁边却靠着{object_b}。{first}；我回头时，你像刚好路过一样站在门边。"
        f"后来{second}。醒来时我只记得颜色，不记得路是怎么走完的。"
    )
    fragments = f"1. {place}里到处是{color}的反光；2. {object_a}和{object_b}挤在一起；3. {first}；4. {second}。"
    distortions = "梦把旧残留拆成颜色、地点和不讲理的物理变化；醒后只能保留情绪方向，不能把画面当成现实事实。"
    waking = "醒来只剩一个说不清的余味：像有什么靠近过，又马上换了形状。"
    return surface, fragments, distortions, waking


def _entry_rng(entry: DreamEntry, category: str) -> random.Random:
    material = "|".join(
        (
            entry.dream_id,
            entry.dreamed_at,
            entry.dream_surface,
            entry.fragments,
            entry.unresolved_piece,
            category,
        )
    )
    digest = hashlib.sha256(material.encode("utf-8", errors="replace")).hexdigest()
    return random.Random(int(digest[:16], 16))


def _looks_public_story(text: str) -> bool:
    return len(text.strip()) >= 40 and any(marker in text for marker in ("我梦见", "梦见", "梦里", "灯", "桥", "候车室", "教室", "档案室"))


def _looks_mechanical_dream(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "被压成",
            "owner 主动",
            "source_seed",
            "dream_weight",
            "memory_effect",
            "factual_effect",
            "Codex",
            "codex",
            "no_url",
        )
    )


def render_dream(entry: DreamEntry, generated_at: str) -> str:
    surface, fragments, distortions, waking_residue = _public_story_for_entry(entry)
    waking = _natural_waking_residue(entry, waking_residue)
    return f"""# 心玉梦境：{entry.dream_id}

- exported_at: {generated_at}
- dreamed_at: {entry.dreamed_at}

## 梦面
{surface}

## 梦境碎片
{fragments}

## 梦的错位
{distortions}

## 醒后残留
{waking}

## 边界
这只是梦，只能说明旧材料被重排，不能证明现实里发生过新的对话、接触或事件。
"""


def _natural_waking_residue(entry: DreamEntry, waking_residue: str) -> str:
    weather = entry.emotional_weather.strip()
    if weather in {"", "none", "unknown", "未定"}:
        return waking_residue
    return f"醒来后还剩一点{weather}。{waking_residue}"


def render_index(entries: list[DreamEntry], generated_at: str) -> str:
    if not entries:
        body = "- 还没有可导出的梦境。"
    else:
        lines = []
        for entry in reversed(entries):
            date = _date_from_timestamp(entry.dreamed_at)
            file_name = f"{_safe_filename(entry.dream_id)}-xinyu-dream.md"
            lines.append(
                f"- [{entry.dream_id}]({date}/{file_name}) "
                f"- dreamed_at: {entry.dreamed_at} "
                f"- residue: {entry.waking_residue}"
            )
        body = "\n".join(lines)

    return f"""# XinYu Dreams

- generated_at: {generated_at}
- source: memory/dreams/dream_log.md
- latest: latest-xinyu-dream.md

## Dreams
{body}

## Boundary
- 这里是心玉的梦境导出，不是事实记忆。
- 梦境可以显示她怎样整理情绪残留、关系残影和醒后权重变化。
- 梦不能证明现实里发生过新的对话、接触或事件。
"""


def export_dream_journal(
    root: Path,
    generated_at: str | None = None,
    *,
    output_dir: Path | None = None,
) -> dict[str, object]:
    generated_at = generated_at or datetime.now().astimezone().isoformat()
    output_dir = output_dir or default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    entries = parse_dream_log(read_text(root / "memory/dreams/dream_log.md"))
    written_paths: list[str] = []
    latest_path = output_dir / "latest-xinyu-dream.md"

    if entries:
        for entry in entries:
            date_dir = output_dir / _date_from_timestamp(entry.dreamed_at)
            date_dir.mkdir(parents=True, exist_ok=True)
            path = date_dir / f"{_safe_filename(entry.dream_id)}-xinyu-dream.md"
            path.write_text(render_dream(entry, generated_at), encoding="utf-8-sig")
            written_paths.append(str(path))
        latest_path.write_text(render_dream(entries[-1], generated_at), encoding="utf-8-sig")
        written_paths.append(str(latest_path))
    else:
        latest_path.write_text("# 心玉梦境\n\n还没有可导出的梦境。\n", encoding="utf-8-sig")
        written_paths.append(str(latest_path))

    index_path = output_dir / "index.md"
    index_path.write_text(render_index(entries, generated_at), encoding="utf-8-sig")
    written_paths.append(str(index_path))

    return {
        "output_dir": str(output_dir),
        "index_path": str(index_path),
        "latest_path": str(latest_path),
        "dream_count": len(entries),
        "written_paths": written_paths,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export XinYu dream memory to desktop-readable files.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output-dir", type=Path, default=default_output_dir())
    return parser


def main() -> int:
    if hasattr(__import__("sys").stdout, "reconfigure"):
        __import__("sys").stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args()
    result = export_dream_journal(args.root.resolve(), output_dir=args.output_dir)
    print(f"Exported {result['dream_count']} dreams to {result['output_dir']}")
    print(f"Index: {result['index_path']}")
    print(f"Latest: {result['latest_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
