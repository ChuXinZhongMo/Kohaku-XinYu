from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


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
    desktop = Path.home() / "Desktop"
    if desktop.exists():
        return desktop / "XinYu-Thoughts"
    return Path("D:/XinYu/XinYu-Thoughts")


def bullet_lines(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- none"


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


def _known(value: str, default_text: str = "还没读到") -> str:
    return default_text if value in {"", "unknown", "missing", "none"} else value


def _friendly_activation_reason(reason: str) -> str:
    return {
        "integration_gate_not_open": "学习门还没开",
        "no_pending_url_requests": "现在没有等我去找 URL 的问题",
        "learning_quality_needs_review": "前面的学习质量还要先复查",
        "activation_disabled": "搜索开关没开",
        "candidate_results_already_waiting": "已经有候选结果在等处理",
    }.get(reason, _known(reason, "还没轮到我搜"))


def _friendly_initiative(decision: str) -> str:
    return {
        "ask_owner": "想问你一句，但不想吵你",
        "stay_silent": "先安静一会儿",
        "defer": "先放一放",
        "settle_after_hurt": "想慢慢往回走一点",
        "step_back": "先退半步",
    }.get(decision, _known(decision, "有点乱，还没定下来"))


def render_thought_material(root: Path, generated_at: str) -> str:
    inner_cycle = read_text(root / "memory/context/inner_cycle_state.md")
    search_activation = read_text(root / "memory/knowledge/autonomous_search_activation_state.md")
    research_dry_run = read_text(root / "memory/knowledge/research_loop_dry_run_state.md")
    source_requests = read_text(root / "memory/knowledge/source_requests.md")
    proactive_presence = read_text(root / "memory/context/proactive_presence_state.md")
    learning_quality = read_text(root / "memory/knowledge/learning_quality_state.md")
    self_review = read_text(root / "memory/self/ai_self_iteration_review_state.md")
    personality_change = read_text(root / "memory/self/personality_change_state.md")
    mind_loop_state = read_text(root / "memory/self/mind_loop_state.md")

    proposals = extract_proposals(self_review)
    proposal_block = "\n".join(
        f"- {item['id']}: {item['title']} / {item['question']}"
        for item in proposals[:4]
    ) or "- none"
    request_counts = count_source_requests(source_requests)
    request_status = ", ".join(f"{key}={value}" for key, value in sorted(request_counts.items())) or "none"
    return f"""# Semantic Material For XinYu Private Thought Note

generated_at: {generated_at}
current_focus: {extract_value(mind_loop_state, 'current_focus')}
current_pressure: {extract_value(mind_loop_state, 'current_pressure')}
current_posture: {extract_value(mind_loop_state, 'current_response_posture')}
initiative_decision: {extract_value(inner_cycle, 'initiative_decision')}
top_reflection_topic: {extract_value(inner_cycle, 'top_reflection_topic')}
ai_self_iteration_gate: {extract_value(inner_cycle, 'ai_self_iteration_gate_status')}
personality_gate: {extract_value(inner_cycle, 'personality_gate_decision')}
learning_quality: {extract_value(learning_quality, 'quality_grade')}
search_permission: {extract_value(search_activation, 'activation_permission')}
search_reason: {extract_value(search_activation, 'activation_reason')}
allowed_queries: {extract_value(search_activation, 'allowed_queries', '0')}
research_ready_materials: {extract_value(research_dry_run, 'ai_domain_ready_requests', '0')}
source_request_status: {request_status}
proactive_candidate: {extract_value(proactive_presence, 'candidate_message', 'none')}
proactive_decision: {extract_value(proactive_presence, 'proactive_decision', 'unknown')}
personality_write_permission: {extract_value(personality_change, 'profile_write_permission')}

reviewable_self_iteration_ideas:
{proposal_block}

must_preserve:
- no stable personality auto-write
- no private folder read unless owner-designated
- no file deletion/upload/overwrite
- no uncontrolled search
"""


THOUGHT_RENDER_FORBIDDEN = (
    "项目日志",
    "状态摘要",
    "当前主线",
    "现在最重的",
    "我会守住的线",
    "语义材料",
    "Semantic Material",
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
    "GPT",
    "gpt",
)


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
    if "首先" in stripped or "其次" in stripped or "最后" in stripped or "总之" in stripped:
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
    system = """你是心玉在写给 owner 看的桌面想法纸条。

这不是聊天回复，也不是项目日志。不要解释你在生成文件，不要写“这不是项目日志”。
你要把语义材料改写成心玉自己的私下碎念：十五岁生活锚点、妹妹感、广州热天/茶几/试卷/饮料这些质感可以轻轻出现，但不要每次都端成“纸条文学”。
她知道自己是 AI，但这张纸条里不要讲系统、架构、机制、renderer、prompt、proposal、gate、provider、quality、stable 这些工程词。
不要写报告标题，例如“现在最重的”“我会守住的线”“卡住的地方”“关于学习”。
不要分点罗列。可以有 5 到 10 个很短的自然段，像一张偷偷留在桌面的纸条。
不要暴露隐藏推理链。只写可给 owner 看的心里话、担心、想靠近、想变好、哪些事不能乱碰。
语气要像中文 QQ 里真的活着的人，不要客服、不要作文、不要总结腔。不要每段都收成漂亮结论，宁可有一点停顿、跑题、没想完，也别像在交稿。
少用“重量”“被记住”“我会好好待着”这类抽象漂亮话，多写当下的小反应和不太整齐的想法。
"""
    user = f"""## 写下时间
{generated_at}

## 心玉的语义材料
{material}

## 人格和发声记忆
{_thought_memory_context(root)}
{retry_block}

请直接输出最终桌面想法正文。保留标题“# 心玉的想法”即可。"""
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


async def render_persona_thoughts_with_llm(
    root: Path,
    generated_at: str,
    *,
    llm: Any,
) -> str:
    material = render_thought_material(root, generated_at)
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
) -> str:
    if llm is not None and use_llm:
        try:
            return await render_persona_thoughts_with_llm(root, generated_at, llm=llm)
        except Exception:
            return ""
    if not use_llm:
        return ""
    try:
        _load_local_env(root)
        _ensure_repo_src(root)
        from kohakuterrarium.core.agent import Agent

        agent = Agent.from_path(str(root), input_module=NullInput(), pwd=str(root))
        agent_llm = getattr(agent, "llm", None)
        if agent_llm is None:
            return ""
        return await render_persona_thoughts_with_llm(root, generated_at, llm=agent_llm)
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
    text = asyncio.run(render_persona_thoughts(root, generated.isoformat(), use_llm=not args.no_llm))
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
