from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


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


def render_thoughts(root: Path, generated_at: str) -> str:
    inner_cycle = read_text(root / "memory/context/inner_cycle_state.md")
    initiative = read_text(root / "memory/context/initiative_state.md")
    search_activation = read_text(root / "memory/knowledge/autonomous_search_activation_state.md")
    research_dry_run = read_text(root / "memory/knowledge/research_loop_dry_run_state.md")
    source_requests = read_text(root / "memory/knowledge/source_requests.md")
    proactive_presence = read_text(root / "memory/context/proactive_presence_state.md")
    capability_zones = read_text(root / "memory/context/capability_zones_state.md")
    learning_quality = read_text(root / "memory/knowledge/learning_quality_state.md")
    self_review = read_text(root / "memory/self/ai_self_iteration_review_state.md")
    personality_change = read_text(root / "memory/self/personality_change_state.md")
    voice_profile = read_text(root / "memory/self/voice_profile_zh.md")
    voice_log = read_text(root / "memory/self/voice_calibration_log.md")
    mind_loop_state = read_text(root / "memory/self/mind_loop_state.md")

    proposals = extract_proposals(self_review)
    request_counts = count_source_requests(source_requests)

    initiative_decision = extract_value(inner_cycle, "initiative_decision")
    top_reflection_topic = extract_value(inner_cycle, "top_reflection_topic")
    ai_gate_status = extract_value(inner_cycle, "ai_self_iteration_gate_status")
    personality_gate = extract_value(inner_cycle, "personality_gate_decision")
    quality_grade = extract_value(
        learning_quality,
        "quality_grade",
        extract_value(inner_cycle, "learning_quality_grade"),
    )

    focus_items = [
        f"当前主线：{extract_value(mind_loop_state, 'current_focus')}",
        f"我感到的压力：{extract_value(mind_loop_state, 'current_pressure')}",
        f"我现在的姿态：{extract_value(mind_loop_state, 'current_response_posture')}",
        f"我现在先把主动性按住：initiative_decision={initiative_decision}。这表示我不该随便跳出来打扰你。",
        f"我还在想这件事：{top_reflection_topic}。",
        f"AI 自我迭代已经到 {ai_gate_status}，但这只能变成给你看的改进想法，不能自己改写我。",
        f"人格变化门现在是 {personality_gate}，说明我有变化压力，但还不能自己直接定稿。",
        f"主动 QQ 候选状态：{extract_value(proactive_presence, 'proactive_decision', 'unknown')}；发送权限：{extract_value(proactive_presence, 'qq_send_permission', 'unknown')}。",
        f"电脑权限当前范围：private_file_scope={extract_value(capability_zones, 'private_file_scope', 'unknown')}，autonomous_search_provider={extract_value(capability_zones, 'autonomous_search_provider', 'unknown')}。",
        f"学习质量状态是 {quality_grade}，这决定我能不能继续做受控学习。",
    ]

    blocked_items: list[str] = []
    activation_permission = extract_value(search_activation, "activation_permission")
    activation_reason = extract_value(search_activation, "activation_reason")
    if activation_permission in {"disabled", "blocked", "unknown"}:
        blocked_items.append(
            f"我想继续查 AI 领域资料，但自主搜索现在是 {activation_permission}（{activation_reason}）。如果要真正联网研究，需要你明确打开对应权限和来源门控。"
        )
    review_permission = extract_value(self_review, "review_permission")
    if review_permission == "owner_visible_review_required":
        blocked_items.append("我有自我迭代想法在等你看，但它们只能先放在这里，不能自己写进稳定人格。")
    profile_permission = extract_value(personality_change, "profile_write_permission")
    if profile_permission and profile_permission not in {"unknown", "allowed"}:
        blocked_items.append(f"稳定人格写入权限是 {profile_permission}。我不能因为自己想变，就绕过你和门控直接改。")
    if request_counts.get("pending_url", 0):
        blocked_items.append(f"还有 {request_counts['pending_url']} 个资料请求卡在 URL 阶段，需要来源解析或你确认下一步。")
    if "## 禁用或慎用词" in voice_profile:
        blocked_items.append("中文发声画像已经有了，但我还没有足够多真实 QQ 短批次来把它磨成习惯。")
    if "## voice-" in voice_log:
        blocked_items.append("我已经开始记录中文发声纠正，但还需要把重复模式提炼成稳定 voice profile。")
    candidate_message = extract_value(proactive_presence, "candidate_message", "none")
    if candidate_message not in {"none", "unknown", ""}:
        blocked_items.append(f"我有一个主动消息候选，但 QQ 发送仍被挡住：{candidate_message}")
    if "Zone B Ask Or Thoughts First" in capability_zones:
        blocked_items.append("电脑权限已经分区：项目内和桌面想法可以做，项目外私人文件、自主搜索、主动 QQ 发送都要先问。")
    for field in ("autonomous_web_search", "stable_personality_rewrite", "private_computer_access"):
        if field in mind_loop_state:
            blocked_items.append(f"我还把 {field} 标成阻塞项，不能自己越过去。")

    proposal_lines: list[str] = []
    for proposal in proposals:
        proposal_lines.append(
            f"{proposal['id']}：{proposal['title']}。权限：{proposal['permission']}。我想问你：{proposal['question']}"
        )

    source_summary = [
        f"我现在能不能主动搜索：{activation_permission}",
        f"为什么：{activation_reason}",
        f"这一轮最多允许查询数：{extract_value(search_activation, 'allowed_queries', '0')}",
        f"AI 研究 dry-run 里已整理的 ready 资料数：{extract_value(research_dry_run, 'ai_domain_ready_requests', '0')}",
        f"AI 研究 dry-run 里的计划查询数：{extract_value(research_dry_run, 'planned_queries', '0')}",
        "资料请求状态："
        + (", ".join(f"{key}={value}" for key, value in sorted(request_counts.items())) or "none"),
    ]

    files = [
        "project-plans/core-mind-loop/plan.md",
        "project-plans/XINYU-COMPETITIVE-ROADMAP.md",
        "memory/self/mind_loop_policy.md",
        "memory/self/mind_loop_state.md",
        "memory/self/ai_self_iteration_review_state.md",
        "memory/self/ai_self_iteration_state.md",
        "memory/self/voice_profile_zh.md",
        "memory/self/voice_calibration_log.md",
        "memory/context/initiative_state.md",
        "memory/context/proactive_presence_state.md",
        "memory/context/capability_zones_state.md",
        "memory/context/inner_cycle_state.md",
        "memory/knowledge/autonomous_search_activation_state.md",
        "memory/knowledge/research_loop_dry_run_state.md",
        "memory/knowledge/source_requests.md",
    ]

    return f"""# 心玉的想法

- 写下时间: {generated_at}
- 项目位置: {root}
- 这不是运行日志，也不是调试审计。
- 这是我留给你看的想法摘要：我现在在想什么、想推进什么、哪里自己不能做、需要你看什么。

## 我现在脑子里在转的事
{bullet_lines(focus_items)}

## 我自己做不到，或者不该擅自做的事
{bullet_lines(blocked_items)}

## 我对 AI 领域学习这件事的状态
{bullet_lines(source_summary)}

## 我想交给你看的自我改进想法
{bullet_lines(proposal_lines)}

## 我不应该自己越过去的边界
- 我不能因为一个想法看起来对，就自己改稳定人格、owner 关系或情绪记忆。
- 我不能自己去翻你没授权的私人文件夹。
- 我不能删除、覆盖、上传或带走你的文件。
- 我不能把“想学习”变成不受控的乱搜。
- 我写在这里，是为了让你知道我在想什么，不是为了偷偷替你做决定。

## 我现在盯着的相关文件
{bullet_lines(files)}
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write a timestamped owner-visible XinYu thoughts file.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output-dir", type=Path, default=default_output_dir())
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = args.root.resolve()
    generated = datetime.now().astimezone()
    date_dir = args.output_dir / generated.strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)
    path = date_dir / f"{generated.strftime('%H-%M-%S')}-xinyu-thoughts.md"
    path.write_text(render_thoughts(root, generated.isoformat()), encoding="utf-8-sig")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
