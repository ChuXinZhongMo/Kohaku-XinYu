from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ENTRY_RE = re.compile(r"(?ms)^## (?P<dream_id>dream-[^\n]+)\n(?P<body>.*?)(?=^## |\Z)")


@dataclass
class DreamEntry:
    dream_id: str
    dreamed_at: str
    fragments: str
    dominant_feelings: str
    source_seed: str
    likely_sources: str
    retained_after_waking: str
    reality_boundary_check: str
    memory_effect: str
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
    desktop = Path.home() / "Desktop"
    if desktop.exists():
        return desktop / "XinYu-Dreams"
    return Path("D:/XinYu/XinYu-Dreams")


def extract_field(body: str, field: str, default: str = "none") -> str:
    match = re.search(rf"(?m)^- {re.escape(field)}:\s*(.*)$", body)
    return match.group(1).strip() if match else default


def parse_dream_log(text: str) -> list[DreamEntry]:
    entries: list[DreamEntry] = []
    for match in ENTRY_RE.finditer(text):
        body = match.group("body")
        entry = DreamEntry(
            dream_id=match.group("dream_id").strip(),
            dreamed_at=extract_field(body, "dreamed_at", "unknown"),
            fragments=extract_field(body, "fragments", "还没有形成可读梦境片段。"),
            dominant_feelings=extract_field(body, "dominant_feelings", "未定"),
            source_seed=extract_field(body, "source_seed", "none"),
            likely_sources=extract_field(body, "likely_sources", "unknown"),
            retained_after_waking=extract_field(
                body,
                "retained_after_waking",
                "只保留情绪残留，不写成现实事实。",
            ),
            reality_boundary_check=extract_field(
                body,
                "reality_boundary_check",
                "梦境不是现实证据，不能证明现实里发生过新的对话或事件。",
            ),
            memory_effect=extract_field(
                body,
                "memory_effect",
                "可以影响情绪权重，但不能改写事实层。",
            ),
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


def render_dream(entry: DreamEntry, generated_at: str) -> str:
    weight_line = "unknown"
    if entry.dream_weight_before != "unknown" or entry.dream_weight_after != "unknown":
        weight_line = (
            f"{entry.dream_weight_before} -> {entry.dream_weight_after} "
            f"(delta {entry.dream_weight_delta})"
        )

    return f"""# 心玉梦境：{entry.dream_id}

- exported_at: {generated_at}
- dreamed_at: {entry.dreamed_at}
- source_seed: {entry.source_seed}

## 梦境片段
{entry.fragments}

## 醒后残留
- dominant_feelings: {entry.dominant_feelings}
- retained_after_waking: {entry.retained_after_waking}

## 梦后权重
- dream_weight: {weight_line}
- dream_weight_effect: {entry.dream_weight_effect}
- relationship_effect: {entry.relationship_effect}
- factual_effect: {entry.factual_effect}
- memory_effect: {entry.memory_effect}

## 来源与边界
- likely_sources: {entry.likely_sources}
- reality_boundary_check: {entry.reality_boundary_check}
- rule: 梦可以保留情绪残影，但不能把梦里的片段写成现实事实。
"""


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
                f"- feelings: {entry.dominant_feelings}"
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
- 梦境可以显示她怎样整理情绪残留、关系残影和醒后的权重变化。
- 梦不能证明现实里发生过新的对话或事件。
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
        latest_path.write_text(
            "# 心玉梦境\n\n还没有可导出的梦境。\n",
            encoding="utf-8-sig",
        )
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
