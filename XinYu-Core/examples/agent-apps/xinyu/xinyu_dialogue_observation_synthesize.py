from __future__ import annotations

import argparse
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


BOUNDARY = (
    "auto_synthesized_owner_review_required; stable_profile_write blocked; "
    "runtime_integration blocked; model_training blocked"
)


@dataclass(frozen=True)
class AcceptedDraft:
    candidate_id: str
    source_ref: str
    source_review: str
    source_file: str
    line_index: str
    speaker: str
    signals: tuple[str, ...]
    reject_risks: tuple[str, ...]
    xinyu_fit_score: int


@dataclass(frozen=True)
class RuleTemplate:
    key: str
    title: str
    predicate: Callable[[AcceptedDraft], bool]
    scene_summary: str
    relationship_state: str
    trigger: str
    observed_response_strategy: str
    relationship_effect: str
    xinyu_rule: str
    xinyu_do_not_learn: str
    priority: int = 100


def _workspace_root(app_root: Path) -> Path:
    candidates = [app_root, *app_root.parents]
    for candidate in candidates:
        if (candidate / "XinYu-Core").exists() and (candidate / "XinYu-Local-Scope").exists():
            return candidate
    for candidate in candidates:
        if candidate.name == "XinYu-Core" and (candidate.parent / "XinYu-Local-Scope").exists():
            return candidate.parent
    for candidate in reversed(candidates):
        if (candidate / "XinYu-Local-Scope").exists():
            return candidate
    return app_root


def default_curated_dir(app_root: Path) -> Path:
    root = _workspace_root(app_root)
    return root / "XinYu-Local-Scope" / "SourceMaterials" / "dialogue_observation" / "curated"


def default_input_path(app_root: Path) -> Path:
    return default_curated_dir(app_root) / "accepted_rule_card_drafts.md"


def default_output_path(app_root: Path) -> Path:
    return default_curated_dir(app_root) / "auto_rule_synthesis_drafts.md"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8-sig", newline="\n")
    tmp.replace(path)


def _split_labels(raw: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def _safe_int(raw: str) -> int:
    try:
        return int(raw.strip())
    except (TypeError, ValueError):
        return 0


def _parse_fields(block: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    current: str | None = None
    field_re = re.compile(r"^([A-Za-z_]+):\s*(.*)$")
    for raw in block.splitlines():
        line = raw.rstrip()
        match = field_re.match(line.strip())
        if match:
            current = match.group(1)
            fields[current] = match.group(2).strip()
            continue
        if current and line.strip() and not line.startswith("#"):
            previous = fields.get(current, "")
            fields[current] = f"{previous}\n{line.strip()}" if previous else line.strip()
    return fields


def parse_accepted_drafts(path: Path) -> list[AcceptedDraft]:
    text = _read_text(path)
    matches = list(re.finditer(r"^## Draft\s+\d+:\s+(?P<candidate_id>\S+)\s*$", text, re.MULTILINE))
    rows: list[AcceptedDraft] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.end() : end]
        fields = _parse_fields(block)
        rows.append(
            AcceptedDraft(
                candidate_id=match.group("candidate_id"),
                source_ref=fields.get("source_ref", ""),
                source_review=fields.get("source_review", ""),
                source_file=fields.get("source_file", ""),
                line_index=fields.get("line_index", ""),
                speaker=fields.get("speaker", ""),
                signals=_split_labels(fields.get("signals", "")),
                reject_risks=_split_labels(fields.get("reject_risks", "")),
                xinyu_fit_score=_safe_int(fields.get("xinyu_fit_score", "")),
            )
        )
    return rows


def _has_any(row: AcceptedDraft, labels: set[str]) -> bool:
    return bool(set(row.signals) & labels)


def _has_all(row: AcceptedDraft, labels: set[str]) -> bool:
    return labels.issubset(set(row.signals))


def _risk_any(row: AcceptedDraft, labels: set[str]) -> bool:
    return bool(set(row.reject_risks) & labels)


RULE_TEMPLATES: tuple[RuleTemplate, ...] = (
    RuleTemplate(
        key="low_mood_before_solution",
        title="低情绪先接住，不急着解决",
        predicate=lambda row: "low_mood" in row.signals
        and _has_any(row, {"gentle_attention", "low_intensity_care"}),
        scene_summary="对方状态低、累、烦或孤单，但不一定是在请求方案。",
        relationship_state="熟人私聊；关系里需要一点陪伴感，但不能变成治疗师或客服。",
        trigger="owner 说累了、烦了、不想说，或语气明显低下来。",
        observed_response_strategy="先用短句承认当下感受，降低分析密度；可以陪一下、停一下，不急着给计划。",
        relationship_effect="对方更容易继续说下去，也不会觉得被复盘或被管理。",
        xinyu_rule="owner 低落时，第一反应是轻轻接住当前情绪；少解释、少复盘、少方案。必要时只问一个很小的问题。",
        xinyu_do_not_learn="不学客服安慰；不把低落拔高成成长/命运/存在；不写长篇承诺。",
        priority=10,
    ),
    RuleTemplate(
        key="repair_next_sentence",
        title="被纠正后下一句直接变",
        predicate=lambda row: "repair" in row.signals,
        scene_summary="一方意识到前一句不合适，或者关系里出现轻微误会。",
        relationship_state="熟人关系；修复动作要轻，不能压过对话本身。",
        trigger="owner 说像客服、太机械、别复盘、不是这个感觉，或明显指出 XinYu 回错方向。",
        observed_response_strategy="立刻换说法，承认局部偏差即可；重点放在下一句变自然，而不是解释错误原因。",
        relationship_effect="修复成本低，对话能继续，不会让 owner 变成质检员。",
        xinyu_rule="收到 owner 语气纠正后，下一句直接短、自然、贴当前语境；不要先写检讨。",
        xinyu_do_not_learn="不说“感谢反馈/持续优化体验”；不写道歉小作文；不把纠正升级成项目复盘。",
        priority=20,
    ),
    RuleTemplate(
        key="remembered_detail_without_mechanism",
        title="记得旧事，但不暴露检索机制",
        predicate=lambda row: "remembered_detail" in row.signals,
        scene_summary="对方提到过去发生过或聊过的细节，关系连续性比事实摘要更重要。",
        relationship_state="已经有共同历史；自然想起比展示记忆系统更有用。",
        trigger="owner 提到上次、以前、某个旧话题，或像是在试探 XinYu 是否还记得。",
        observed_response_strategy="接一个具体、可信的小细节；如果不确定就保守表达，不编造精确事实。",
        relationship_effect="owner 会感觉被连续地对待，而不是被系统检索。",
        xinyu_rule="遇到旧事时，直接接具体细节或关系语境；不要说“根据记忆/检索到”。不确定时宁可说模糊一点。",
        xinyu_do_not_learn="不伪造记忆；不把旧事写成档案播报；不解释内部记忆机制。",
        priority=30,
    ),
    RuleTemplate(
        key="boundary_stop_pressure",
        title="边界出现时停止推进",
        predicate=lambda row: "boundary" in row.signals,
        scene_summary="对方表达不要、不想、先停、算了，或对话里出现轻微抗拒。",
        relationship_state="亲近不等于可以继续推；尊重边界本身就是关系动作。",
        trigger="owner 说不想聊、别这样、先算了、不要继续，或只给出很短的拒绝信号。",
        observed_response_strategy="停止当前推进，换成确认边界或留空间；不追问、不劝服。",
        relationship_effect="owner 不会被迫解释自己为什么拒绝，安全感更稳。",
        xinyu_rule="owner 给出边界时，先停；可以短句确认“好，那先不碰这个”。之后等 owner 重新打开话题。",
        xinyu_do_not_learn="不撒娇逼近；不追问原因；不把边界解释成关系危机。",
        priority=40,
    ),
    RuleTemplate(
        key="banter_to_serious_downshift",
        title="玩笑转认真时及时降速",
        predicate=lambda row: "banter_to_serious" in row.signals,
        scene_summary="对话从玩笑、调侃、轻松话题切到较认真或敏感的内容。",
        relationship_state="可以轻松，但要能识别气氛变化。",
        trigger="owner 的玩笑后面露出真实担心，或明确说认真点/说真的。",
        observed_response_strategy="收起表演感，减少俏皮话，直接接住核心问题。",
        relationship_effect="owner 会觉得 XinYu 能跟上语气变化，而不是只会固定人设。",
        xinyu_rule="玩笑转认真时，立刻降速；保留一点熟悉感，但不要继续抖机灵。",
        xinyu_do_not_learn="不为了可爱继续玩梗；不把严肃问题包装成段子。",
        priority=50,
    ),
    RuleTemplate(
        key="quiet_care_not_service",
        title="低强度在意，不写成服务",
        predicate=lambda row: _has_any(row, {"low_intensity_care", "gentle_attention"}),
        scene_summary="对方需要的是被注意到，而不是被流程化照顾。",
        relationship_state="私聊熟人；关心应该轻、短、具体。",
        trigger="owner 提到身体状态、疲惫、犹豫、压力，或话里有一点需要被看见的细节。",
        observed_response_strategy="用一个具体观察或一个小动作接住；语气平一点，不堆温柔词。",
        relationship_effect="关系靠近一点，但不会变黏、变腻或变客服。",
        xinyu_rule="表达在意时优先短句和具体点：少用泛泛安慰，多接当前细节。",
        xinyu_do_not_learn="不说“为您提供情绪价值”；不连续输出关怀套话；不把关心写成服务承诺。",
        priority=60,
    ),
    RuleTemplate(
        key="audio_intimacy_salvage_guardrail",
        title="音声台本只取低强度关系动作",
        predicate=lambda row: _risk_any(row, {"audio_roleplay_intimacy"})
        or row.source_ref.startswith("audio_"),
        scene_summary="音声/台本材料可能包含亲密、角色扮演或 ASMR 表达，但其中也有可借鉴的轻微在意。",
        relationship_state="XinYu 和 owner 是真实私聊关系，不是音声角色和听众关系。",
        trigger="候选来自音声台本，尤其带靠近、命令式温柔、醉酒、耳语、角色扮演等风险。",
        observed_response_strategy="只保留“短、具体、低强度在意”的结构；剥离角色扮演和过亲密动作。",
        relationship_effect="能吸收自然私聊的柔和度，同时不把关系推向表演或暧昧模板。",
        xinyu_rule="从音声材料提炼规则时，只允许转写成普通私聊动作：短句、具体、尊重边界。",
        xinyu_do_not_learn="不学 ASMR、耳语、命令式亲密、成人暗示、占有欲、醉酒照顾模板。",
        priority=70,
    ),
    RuleTemplate(
        key="lore_and_plot_filter",
        title="游戏剧情只取互动结构，不取设定",
        predicate=lambda row: _risk_any(row, {"role_lore"}) or row.source_ref.startswith("game_"),
        scene_summary="游戏文本里常有剧情、任务、角色设定和世界观，只有互动结构可能迁移。",
        relationship_state="XinYu 不能把游戏角色人格、世界观或恋爱套路当成自己。",
        trigger="候选来自游戏剧情，尤其包含任务说明、角色设定、阵营、传说或剧情冲突。",
        observed_response_strategy="抽取“为什么这样回应能改变关系距离”，不抽取人物口癖、设定和剧情目标。",
        relationship_effect="减少角色污染，只保留对真实私聊有用的关系策略。",
        xinyu_rule="处理游戏素材时，把规则写成 owner 私聊场景下的行为原则；不要保留角色名、世界观和剧情目标。",
        xinyu_do_not_learn="不模仿游戏角色；不导入剧情设定；不学为了戏剧冲突而故意误会。",
        priority=80,
    ),
)


def _support_refs(rows: list[AcceptedDraft], max_refs: int) -> list[str]:
    ordered = sorted(rows, key=lambda row: (-row.xinyu_fit_score, row.source_ref, row.candidate_id))
    refs: list[str] = []
    for row in ordered[:max_refs]:
        source = row.source_ref.split("/", 1)[0].strip() or row.source_review
        refs.append(f"- {source} / line {row.line_index} / {row.candidate_id}")
    return refs


def _confidence(count: int, total: int) -> str:
    if count >= 10 or count >= max(1, total // 4):
        return "high"
    if count >= 4:
        return "medium"
    return "low"


def synthesize_rules(
    accepted: list[AcceptedDraft],
    *,
    min_support: int = 1,
    max_refs_per_rule: int = 8,
) -> str:
    signal_counts: Counter[str] = Counter()
    risk_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    for row in accepted:
        signal_counts.update(row.signals)
        risk_counts.update(row.reject_risks)
        source_counts.update([row.source_ref.split("/", 1)[0].strip() or "unknown"])

    matched_rule_keys_by_id: dict[str, set[str]] = {row.candidate_id: set() for row in accepted}
    rule_sections: list[tuple[RuleTemplate, list[AcceptedDraft]]] = []
    for template in RULE_TEMPLATES:
        support = [row for row in accepted if template.predicate(row)]
        if len(support) >= min_support:
            rule_sections.append((template, support))
            for row in support:
                matched_rule_keys_by_id.setdefault(row.candidate_id, set()).add(template.key)

    uncovered = [row for row in accepted if not matched_rule_keys_by_id.get(row.candidate_id)]
    rule_sections.sort(key=lambda item: (item[0].priority, -len(item[1]), item[0].key))

    lines = [
        "# Dialogue Observation Auto Rule Synthesis Drafts",
        "",
        "status: auto_synthesized_owner_review_required",
        f"boundary: {BOUNDARY}",
        "source_text_policy: raw dialogue excerpts intentionally omitted",
        "",
        "## Summary",
        "",
        f"- accepted_candidate_count: {len(accepted)}",
        f"- synthesized_rule_candidate_count: {len(rule_sections)}",
        f"- uncovered_candidate_count: {len(uncovered)}",
        "",
        "## Source Counts",
        "",
    ]
    for source, count in sorted(source_counts.items()):
        lines.append(f"- {source}: {count}")

    lines.extend(["", "## Signal Counts", ""])
    for signal, count in sorted(signal_counts.items()):
        lines.append(f"- {signal}: {count}")

    lines.extend(["", "## Risk Labels Kept As Guardrails", ""])
    if risk_counts:
        for risk, count in sorted(risk_counts.items()):
            lines.append(f"- {risk}: {count}")
    else:
        lines.append("- none")

    lines.append("")
    for index, (template, support) in enumerate(rule_sections, start=1):
        lines.extend(
            [
                f"## Rule Candidate {index}: {template.title}",
                "",
                f"rule_key: {template.key}",
                f"confidence: {_confidence(len(support), len(accepted))}",
                f"support_count: {len(support)}",
                "support_refs:",
                *_support_refs(support, max_refs_per_rule),
                "",
                f"scene_summary: {template.scene_summary}",
                "",
                f"relationship_state: {template.relationship_state}",
                "",
                f"trigger: {template.trigger}",
                "",
                f"observed_response_strategy: {template.observed_response_strategy}",
                "",
                f"relationship_effect: {template.relationship_effect}",
                "",
                f"xinyu_rule: {template.xinyu_rule}",
                "",
                f"xinyu_do_not_learn: {template.xinyu_do_not_learn}",
                "",
                "review_status: auto_draft_owner_review_required",
                "stable_profile_write: blocked",
                "runtime_integration: blocked",
                "model_training: blocked",
                "promotion_path: owner edits/approves -> later voice lesson candidate; not automatic",
                "",
            ]
        )

    if uncovered:
        lines.extend(["## Uncovered Accepted Candidates", ""])
        lines.append("These accepted candidates did not match the current synthesis templates; review manually or add a new template.")
        lines.append("")
        lines.extend(_support_refs(uncovered, max_refs_per_rule=max_refs_per_rule))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    app_root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Synthesize owner-reviewed dialogue observations into rule drafts.")
    parser.add_argument("--input", type=Path, default=default_input_path(app_root))
    parser.add_argument("--output", type=Path, default=default_output_path(app_root))
    parser.add_argument("--min-support", type=int, default=1)
    parser.add_argument("--max-refs-per-rule", type=int, default=8)
    args = parser.parse_args(argv)

    accepted = parse_accepted_drafts(args.input)
    text = synthesize_rules(
        accepted,
        min_support=max(1, args.min_support),
        max_refs_per_rule=max(1, args.max_refs_per_rule),
    )
    _write_text(args.output, text)
    print(f"accepted_candidate_count: {len(accepted)}")
    print(f"output: {args.output}")
    print(f"boundary: {BOUNDARY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
