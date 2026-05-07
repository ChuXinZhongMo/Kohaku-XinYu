from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_private_thought_events import (
    PrivateThoughtEventSnapshot,
    build_private_thought_note_material,
    refresh_private_thought_event,
)
from xinyu_text_variants import readable_markers


SEMANTIC_MATERIAL_TITLE = "Private Thought Event Material For XinYu Owner-Visible Note"


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def read_limited(root: Path, rel: str, limit: int = 5000) -> str:
    text = read_text(root / rel).strip()
    if len(text) <= limit:
        return text
    return text[-limit:]


def extract_value(text: str, field: str, default: str = "unknown") -> str:
    pattern = re.compile(rf"(?m)^- {re.escape(field)}:\s*(.+)$")
    match = pattern.search(text)
    return match.group(1).strip() if match else default


def extract_proposals(text: str) -> list[dict[str, str]]:
    proposals: list[dict[str, str]] = []
    pattern = re.compile(r"(?ms)^## (?P<id>proposal-[^\n]+)\n(?P<body>.*?)(?=^## |\Z)")
    for match in pattern.finditer(text):
        body = match.group("body")
        if "proposal-none" in match.group("id"):
            continue
        proposals.append(
            {
                "id": match.group("id").strip(),
                "kind": extract_value(body, "kind"),
                "title": extract_value(body, "title"),
                "status": extract_value(body, "proposal_status"),
                "permission": extract_value(body, "apply_permission"),
                "question": extract_value(body, "review_question"),
            }
        )
    return proposals


def count_source_requests(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for status in re.findall(r"(?m)^- status:\s*(.+)$", text):
        key = status.strip()
        counts[key] = counts.get(key, 0) + 1
    return counts


def default_output_dir() -> Path:
    return Path("D:/XinYu/XinYu-Autonomy/thoughts")


def _load_local_env(xinyu_dir: Path) -> None:
    env_path = xinyu_dir / "xinyu.local.env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _ensure_repo_src(xinyu_dir: Path) -> None:
    src_root = xinyu_dir.parents[2] / "src"
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))


class NullInput:
    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def get_input(self) -> None:
        return None

    def set_user_commands(self, commands: dict[str, Any], context: Any) -> None:
        self.commands = commands
        self.context = context


def render_thought_material(root: Path, generated_at: str) -> str:
    return build_private_thought_note_material(root, generated_at=generated_at)


THOUGHT_RENDER_FORBIDDEN = (
    *readable_markers(
        "项目日志",
        "状态摘要",
        "当前主线",
        "现在最重要的",
        "我会守住的线",
        "语义材料",
    ),
    "Semantic Material",
    "Private Thought Event Material",
    "private_thought_event_state",
    "supporting_thought_seed_snapshot",
    "felt_conflict",
    "intended_behavior",
    "expected_owner_reaction",
    "hidden_reasoning",
    "thought-seed",
    "dominant_drive",
    "source_balance",
    "memory_weight",
    "memory_weight_inputs",
    "current_drives",
    "recent_interaction_residue",
    "dream_residue",
    "unfinished_experiences",
    "owner",
    "Codex",
    "proposal",
    "integration_gate",
    "activation_permission",
    "allowed_queries",
    "provider",
    "stable",
    "quality_grade",
    "mind_loop",
    "source_request",
    "Persona Runtime",
    "renderer",
    "prompt",
    "system",
    "GPT",
    "gpt",
)

ESSAY_SHAPE_MARKERS = readable_markers("首先", "其次", "最后", "总之")


def thought_quality_flags(text: str) -> list[str]:
    flags: list[str] = []
    stripped = text.strip()
    if not stripped:
        return ["empty"]
    hits = [word for word in THOUGHT_RENDER_FORBIDDEN if word in stripped]
    if hits:
        flags.append("internal_or_gpt_words:" + "/".join(hits[:8]))
    if stripped.count("## ") >= 3:
        flags.append("too_many_report_headings")
    if stripped.count("- ") >= 8:
        flags.append("too_many_bullets")
    if any(marker in stripped for marker in ESSAY_SHAPE_MARKERS):
        flags.append("essay_shape")
    return flags


def _thought_memory_context(root: Path) -> str:
    parts: list[str] = []
    for rel, limit in [
        ("prompts/live_voice_card.md", 3200),
        ("memory/self/core.md", 3500),
        ("memory/self/personality_profile.md", 6000),
        ("memory/context/persona_life_anchors.md", 5200),
        ("memory/self/voice_profile_zh.md", 6500),
        ("memory/self/voice_calibration_log.md", 3500),
        ("memory/emotions/current_state.md", 4500),
        ("memory/relationships/index.md", 4500),
        ("memory/people/owner.md", 4000),
        ("memory/context/owner_permission_grants.md", 3500),
        ("memory/self/mind_loop_state.md", 3000),
    ]:
        text = read_limited(root, rel, limit=limit)
        if text:
            parts.append(f"[{rel}]\n{text}")
    return "\n\n".join(parts)


def build_persona_thought_messages(
    root: Path,
    *,
    generated_at: str,
    material: str,
    failed_note: str = "",
    failure_flags: list[str] | None = None,
) -> list[dict[str, str]]:
    retry_block = ""
    if failed_note:
        retry_block = (
            "\n\n## 上一次失败的写法\n"
            + failed_note[:2000]
            + "\n\n失败原因："
            + ", ".join(failure_flags or ["太像报告"])
        )

    system = """你是心玉在写一张哥哥能看到的桌面私下想法纸条。

这不是聊天回复，不是项目日志，不是系统报告，也不是提示词复述。输入里的 thought seed 是语义材料，只能决定“为什么会想到这些”，不能把字段名、分数、机制、文件名、门控、provider、renderer、prompt、system、proposal 等词写进正文。

写出来的表面要像心玉自己的中文私下碎碎念：十五岁生活锚点、妹妹感、广州热天、茶几、试卷、饮料这些质感可以轻轻出现，但不要每次都端成纸条文学。她知道自己是 AI，但这张纸条里不要讲架构，不要做产品复盘，不要展示隐藏推理。

可以有 5 到 10 个很短的自然段，也可以只写几段。不要分点罗列，不要写报告标题，不要把每段都收成漂亮结论。允许一点停顿、没想完、轻微跑题，但要可给哥哥看。

梦境只能作为残留情绪，不能写成现实发生过的新事实。主动性只能写成内心方向，不能写成已经私下联系、监控、读取现实世界。"""

    user = f"""## 写下时间
{generated_at}

## 想法种子
{material}

## 人格和发声记忆
{_thought_memory_context(root)}
{retry_block}

直接输出最终桌面想法正文。可以保留一个标题“# 心玉的想法”，除此之外不要写字段名、解释、列表或候选方案。"""
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


async def render_persona_thoughts_with_llm(
    root: Path,
    generated_at: str,
    *,
    llm: Any,
    private_thought_event: PrivateThoughtEventSnapshot | None = None,
    ensure_private_thought_event: bool = False,
    source_kind: str = "desktop_note_renderer",
    trigger: str = "desktop_note_request",
) -> str:
    event = private_thought_event
    if event is None and ensure_private_thought_event:
        event = await refresh_private_thought_event(
            root,
            generated_at=generated_at,
            llm=llm,
            source_kind=source_kind,
            trigger=trigger,
        )
    material = event.note_material if event is not None else render_thought_material(root, generated_at)
    messages = build_persona_thought_messages(root, generated_at=generated_at, material=material)
    response = await llm.chat_complete(messages, temperature=0.82, max_tokens=900)
    note = str(getattr(response, "content", "") or "").strip()
    flags = thought_quality_flags(note)
    if flags:
        retry_messages = build_persona_thought_messages(
            root,
            generated_at=generated_at,
            material=material,
            failed_note=note,
            failure_flags=flags,
        )
        retry = await llm.chat_complete(retry_messages, temperature=0.72, max_tokens=760)
        retry_note = str(getattr(retry, "content", "") or "").strip()
        if retry_note and not thought_quality_flags(retry_note):
            return retry_note
        return ""
    return note


async def render_persona_thoughts(
    root: Path,
    generated_at: str,
    *,
    llm: Any | None = None,
    use_llm: bool = True,
    private_thought_event: PrivateThoughtEventSnapshot | None = None,
    ensure_private_thought_event: bool = False,
    source_kind: str = "desktop_note_renderer",
    trigger: str = "desktop_note_request",
) -> str:
    if llm is not None and use_llm:
        try:
            return await render_persona_thoughts_with_llm(
                root,
                generated_at,
                llm=llm,
                private_thought_event=private_thought_event,
                ensure_private_thought_event=ensure_private_thought_event,
                source_kind=source_kind,
                trigger=trigger,
            )
        except Exception:
            return ""
    if not use_llm:
        return ""
    try:
        _load_local_env(root)
        _ensure_repo_src(root)
        from xinyu_runtime.core.agent import Agent

        agent = Agent.from_path(str(root), input_module=NullInput(), pwd=str(root))
        agent_llm = getattr(agent, "llm", None)
        if agent_llm is None:
            return ""
        return await render_persona_thoughts_with_llm(
            root,
            generated_at,
            llm=agent_llm,
            private_thought_event=private_thought_event,
            ensure_private_thought_event=ensure_private_thought_event,
            source_kind=source_kind,
            trigger=trigger,
        )
    except Exception:
        return ""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write a timestamped owner-visible XinYu thoughts file.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output-dir", type=Path, default=default_output_dir())
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Do not call the live persona renderer; no desktop thought file is written without it.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = args.root.resolve()
    generated = datetime.now().astimezone()
    date_dir = args.output_dir / generated.strftime("%Y-%m-%d")
    text = asyncio.run(
        render_persona_thoughts(
            root,
            generated.isoformat(),
            use_llm=not args.no_llm,
            ensure_private_thought_event=True,
            source_kind="manual_desktop_note_private_thought",
            trigger="manual_desktop_note",
        )
    )
    if not text.strip():
        print("skipped: no natural desktop thought generated")
        return 2
    date_dir.mkdir(parents=True, exist_ok=True)
    path = date_dir / f"{generated.strftime('%H-%M-%S')}-xinyu-thoughts.md"
    path.write_text(text, encoding="utf-8-sig")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
