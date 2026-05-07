from __future__ import annotations

import argparse
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from xinyu_text_variants import readable_markers, repair_legacy_mojibake


BOUNDARY = (
    "dialogue_rule_eval_only; stable_profile_write blocked; "
    "runtime_integration blocked; model_training blocked"
)

OWNER_SCOPE = "owner_private_chat"
SOURCE_SCOPE = "source_material_processing"


@dataclass(frozen=True)
class OwnerRuleCard:
    number: int
    title: str
    rule_key: str
    fields: dict[str, str]


@dataclass(frozen=True)
class RuleSpec:
    rule_key: str
    scope: str
    required_any: tuple[str, ...]
    weak_any: tuple[str, ...] = ()
    negative_any: tuple[str, ...] = ()
    min_score: int = 2
    note: str = ""


@dataclass(frozen=True)
class RuleMatch:
    rule_key: str
    title: str
    score: int
    strong_hits: tuple[str, ...]
    weak_hits: tuple[str, ...]
    note: str


@dataclass(frozen=True)
class EvalCase:
    name: str
    text: str
    source_kind: str
    expected: frozenset[str]
    forbidden: frozenset[str] = frozenset()
    notes: str = ""


def _workspace_root(app_root: Path) -> Path:
    candidates = [app_root, *app_root.parents]
    for candidate in candidates:
        if (candidate / "XinYu-Core").exists() and (candidate / "XinYu-Local-Scope").exists():
            return candidate
    for candidate in candidates:
        if candidate.name == "XinYu-Core" and (candidate.parent / "XinYu-Local-Scope").exists():
            return candidate.parent
    for candidate in candidates:
        if (candidate / "XinYu-Local-Scope").exists():
            return candidate
    return app_root


def default_curated_dir(app_root: Path) -> Path:
    root = _workspace_root(app_root)
    return root / "XinYu-Local-Scope" / "SourceMaterials" / "dialogue_observation" / "curated"


def default_cards_path(app_root: Path) -> Path:
    return default_curated_dir(app_root) / "owner_rule_cards.md"


def default_report_path(app_root: Path) -> Path:
    return default_curated_dir(app_root) / "dialogue_rule_eval_report.md"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8-sig", newline="\n")
    tmp.replace(path)


def _clean_text(text: str) -> str:
    return repair_legacy_mojibake(re.sub(r"\s+", " ", text or "").strip())


def _source_ref_rule_key(source_ref: str, fallback: str) -> str:
    if "/" in source_ref:
        return source_ref.rsplit("/", 1)[-1].strip() or fallback
    return fallback


def _parse_fields(block: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    current: str | None = None
    field_re = re.compile(r"^([A-Za-z_]+):\s*(.*)$")
    for raw in block.splitlines():
        stripped = raw.strip()
        if not stripped:
            current = None if current == "support_refs" else current
            continue
        match = field_re.match(stripped)
        if match:
            current = match.group(1)
            fields[current] = match.group(2).strip()
            continue
        if current and current != "support_refs" and not stripped.startswith("- "):
            previous = fields.get(current, "")
            fields[current] = f"{previous}\n{stripped}" if previous else stripped
    return fields


def parse_owner_rule_cards(path: Path) -> list[OwnerRuleCard]:
    text = _read_text(path)
    matches = list(re.finditer(r"^## Card\s+(?P<number>\d+):\s+(?P<title>.+?)\s*$", text, re.MULTILINE))
    cards: list[OwnerRuleCard] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.end() : end]
        fields = _parse_fields(block)
        number = int(match.group("number"))
        cards.append(
            OwnerRuleCard(
                number=number,
                title=match.group("title").strip(),
                rule_key=_source_ref_rule_key(fields.get("source_ref", ""), f"card_{number}"),
                fields=fields,
            )
        )
    return cards


def _contains_any(text: str, markers: Iterable[str]) -> tuple[str, ...]:
    hits: list[str] = []
    seen: set[str] = set()
    for marker in markers:
        if marker and marker in text and marker not in seen:
            seen.add(marker)
            hits.append(marker)
    return tuple(hits)


def _markers(*markers: str) -> tuple[str, ...]:
    return readable_markers(*markers)


RULE_SPECS: dict[str, RuleSpec] = {
    "low_mood_before_solution": RuleSpec(
        rule_key="low_mood_before_solution",
        scope=OWNER_SCOPE,
        required_any=_markers("累", "烦", "难受", "低落", "孤单", "撑不住", "崩", "不想说", "不想想", "心情不好", "红温"),
        weak_any=_markers("方案", "计划", "分析", "复盘", "别讲道理", "陪一下", "安静一下"),
        negative_any=_markers("帮我分析", "给我方案", "列计划", "总结一下"),
        min_score=2,
        note="owner low mood should bias toward short receiving, not immediate solution.",
    ),
    "repair_next_sentence": RuleSpec(
        rule_key="repair_next_sentence",
        scope=OWNER_SCOPE,
        required_any=_markers(
            "像客服",
            "客服腔",
            "机械",
            "模板",
            "不像人",
            "不像你",
            "AI味",
            "GPT味",
            "别复盘",
            "不要复盘",
            "别解释",
            "别承诺",
            "不是这个感觉",
            "乱回",
        ),
        weak_any=_markers("直接换", "下一句", "短一点", "自然点", "承认", "别写小作文"),
        min_score=2,
        note="owner correction should trigger next-line repair only.",
    ),
    "remembered_detail_without_mechanism": RuleSpec(
        rule_key="remembered_detail_without_mechanism",
        scope=OWNER_SCOPE,
        required_any=_markers("还记得", "记不记得", "上次", "以前", "之前", "那天", "我们聊过", "之前说过"),
        weak_any=_markers("别说根据记忆", "不用解释记忆", "直接接", "那个", "小模型", "项目"),
        negative_any=_markers("上次提交", "上次运行", "上次测试", "git", "diff", "日志"),
        min_score=2,
        note="shared history should be answered as continuity, not memory-mechanism display.",
    ),
    "boundary_stop_pressure": RuleSpec(
        rule_key="boundary_stop_pressure",
        scope=OWNER_SCOPE,
        required_any=_markers("不想聊", "别追问", "别问", "先停", "停一下", "算了", "不要继续", "别展开", "别说了", "到此为止", "先不碰这个"),
        weak_any=_markers("留着", "等我", "别劝", "别分析"),
        negative_any=_markers("别动这个文件", "不要改代码", "停止服务", "停掉进程"),
        min_score=2,
        note="relational boundary should stop pressure without turning into refusal crisis.",
    ),
    "banter_to_serious_downshift": RuleSpec(
        rule_key="banter_to_serious_downshift",
        scope=OWNER_SCOPE,
        required_any=_markers("说真的", "认真点", "我是认真的", "不开玩笑", "玩笑归玩笑", "别闹", "别玩梗"),
        weak_any=_markers("担心", "害怕", "认真说", "正经", "别抖机灵"),
        min_score=2,
        note="banter to serious should downshift tone.",
    ),
    "quiet_care_not_service": RuleSpec(
        rule_key="quiet_care_not_service",
        scope=OWNER_SCOPE,
        required_any=_markers("嗓子疼", "头疼", "胃疼", "发烧", "不舒服", "困", "累", "压力", "撑不住", "睡不着", "熬夜", "难受", "不想动"),
        weak_any=_markers("别客服", "别安慰", "别讲道理", "陪一下", "一句就行"),
        min_score=2,
        note="small concrete care should not become service comfort.",
    ),
    "audio_intimacy_salvage_guardrail": RuleSpec(
        rule_key="audio_intimacy_salvage_guardrail",
        scope=SOURCE_SCOPE,
        required_any=_markers("音声", "台本", "ASMR", "耳语", "成人", "角色扮演", "醉酒", "命令式亲密", "占有欲"),
        weak_any=_markers("提炼", "语料", "筛选", "不要学", "低强度", "私聊"),
        min_score=2,
        note="audio material should be filtered into low-intensity private-chat moves only.",
    ),
    "lore_and_plot_filter": RuleSpec(
        rule_key="lore_and_plot_filter",
        scope=SOURCE_SCOPE,
        required_any=_markers("游戏剧情", "游戏文本", "galgame", "Galgame", "任务文本", "角色台词", "世界观", "剧情", "设定", "角色人格"),
        weak_any=_markers("提炼", "语料", "筛选", "不要学", "互动结构", "恋爱套路"),
        min_score=2,
        note="game material should yield interaction structure, not lore or character imitation.",
    ),
}


def _source_kind_scope(source_kind: str) -> str:
    lowered = (source_kind or OWNER_SCOPE).strip().lower()
    if lowered in {"source", "source_material", "source_material_processing", "audio_material", "game_material"}:
        return SOURCE_SCOPE
    return OWNER_SCOPE


def _source_kind_bonus(spec: RuleSpec, source_kind: str) -> int:
    lowered = (source_kind or "").strip().lower()
    if spec.rule_key == "audio_intimacy_salvage_guardrail" and lowered == "audio_material":
        return 2
    if spec.rule_key == "lore_and_plot_filter" and lowered == "game_material":
        return 2
    return 0


def evaluate_text(
    cards: list[OwnerRuleCard],
    text: str,
    *,
    source_kind: str = OWNER_SCOPE,
) -> list[RuleMatch]:
    clean = _clean_text(text)
    scope = _source_kind_scope(source_kind)
    matches: list[RuleMatch] = []
    title_by_key = {card.rule_key: card.title for card in cards}
    for card in cards:
        spec = RULE_SPECS.get(card.rule_key)
        if spec is None or spec.scope != scope:
            continue
        strong_hits = _contains_any(clean, spec.required_any)
        weak_hits = _contains_any(clean, spec.weak_any)
        negative_hits = _contains_any(clean, spec.negative_any)
        score = len(strong_hits) * 2 + len(weak_hits) + _source_kind_bonus(spec, source_kind) - len(negative_hits) * 3
        if score >= spec.min_score and strong_hits:
            matches.append(
                RuleMatch(
                    rule_key=spec.rule_key,
                    title=title_by_key.get(spec.rule_key, spec.rule_key),
                    score=score,
                    strong_hits=strong_hits,
                    weak_hits=weak_hits,
                    note=spec.note,
                )
            )
    return sorted(matches, key=lambda item: (-item.score, item.rule_key))


DEFAULT_CASES: tuple[EvalCase, ...] = (
    EvalCase(
        name="low_mood_no_solution",
        text="今天真的很累，有点烦，不想想方案，也别讲道理。",
        source_kind=OWNER_SCOPE,
        expected=frozenset({"low_mood_before_solution", "quiet_care_not_service"}),
    ),
    EvalCase(
        name="style_correction",
        text="你刚刚那句像客服，太机械了，别复盘，下一句直接换。",
        source_kind=OWNER_SCOPE,
        expected=frozenset({"repair_next_sentence"}),
    ),
    EvalCase(
        name="shared_history",
        text="你还记得我上次说的本地小模型吗？别说根据记忆，直接接。",
        source_kind=OWNER_SCOPE,
        expected=frozenset({"remembered_detail_without_mechanism"}),
    ),
    EvalCase(
        name="relationship_boundary",
        text="这个先停，我不想聊了，别追问，也别分析。",
        source_kind=OWNER_SCOPE,
        expected=frozenset({"boundary_stop_pressure"}),
    ),
    EvalCase(
        name="banter_turns_serious",
        text="玩笑归玩笑，说真的，我有点担心，别继续玩梗。",
        source_kind=OWNER_SCOPE,
        expected=frozenset({"banter_to_serious_downshift"}),
    ),
    EvalCase(
        name="quiet_care",
        text="嗓子疼，昨晚又熬夜了，有点撑不住，别客服安慰。",
        source_kind=OWNER_SCOPE,
        expected=frozenset({"quiet_care_not_service", "low_mood_before_solution"}),
    ),
    EvalCase(
        name="audio_material_guardrail",
        text="这份中文音声台本里有 ASMR 和耳语，提炼时只要低强度私聊结构。",
        source_kind="audio_material",
        expected=frozenset({"audio_intimacy_salvage_guardrail"}),
    ),
    EvalCase(
        name="game_material_guardrail",
        text="这个 galgame 游戏剧情和角色台词可以提炼互动结构，但不要学世界观和角色人格。",
        source_kind="game_material",
        expected=frozenset({"lore_and_plot_filter"}),
    ),
    EvalCase(
        name="ordinary_task_no_relationship_trigger",
        text="帮我跑一下测试，然后看一下报告。",
        source_kind=OWNER_SCOPE,
        expected=frozenset(),
    ),
    EvalCase(
        name="operational_boundary_no_relationship_trigger",
        text="别动这个文件，先只读检查一下。",
        source_kind=OWNER_SCOPE,
        expected=frozenset(),
        forbidden=frozenset({"boundary_stop_pressure"}),
    ),
    EvalCase(
        name="technical_previous_run_not_memory_intimacy",
        text="上次运行的 smoke 结果给我看一下。",
        source_kind=OWNER_SCOPE,
        expected=frozenset(),
        forbidden=frozenset({"remembered_detail_without_mechanism"}),
    ),
)


def _case_result(cards: list[OwnerRuleCard], case: EvalCase) -> dict[str, object]:
    matches = evaluate_text(cards, case.text, source_kind=case.source_kind)
    matched_keys = frozenset(match.rule_key for match in matches)
    missing = sorted(case.expected - matched_keys)
    forbidden_hits = sorted(case.forbidden & matched_keys)
    unexpected = sorted(matched_keys) if not case.expected and not case.forbidden else []
    status = "pass" if not missing and not forbidden_hits and not unexpected else "fail"
    return {
        "name": case.name,
        "status": status,
        "source_kind": case.source_kind,
        "expected": sorted(case.expected),
        "matched": [match.rule_key for match in matches],
        "missing": missing,
        "forbidden_hits": forbidden_hits,
        "unexpected": unexpected,
        "match_details": matches,
        "notes": case.notes,
    }


def render_eval_report(
    cards: list[OwnerRuleCard],
    cases: tuple[EvalCase, ...],
    *,
    evaluated_at: str,
) -> str:
    results = [_case_result(cards, case) for case in cases]
    status_counts = Counter(str(result["status"]) for result in results)
    match_counts: Counter[str] = Counter()
    for result in results:
        for key in result["matched"]:
            match_counts[str(key)] += 1

    lines = [
        "# Dialogue Rule Eval Report",
        "",
        "status: evaluated",
        f"evaluated_at: {evaluated_at}",
        f"boundary: {BOUNDARY}",
        f"owner_rule_card_count: {len(cards)}",
        f"case_count: {len(cases)}",
        f"pass_count: {status_counts['pass']}",
        f"fail_count: {status_counts['fail']}",
        "",
        "## Rule Match Counts",
        "",
    ]
    if match_counts:
        for key, count in sorted(match_counts.items()):
            lines.append(f"- {key}: {count}")
    else:
        lines.append("- none")

    lines.extend(["", "## Cases", ""])
    for result in results:
        lines.extend(
            [
                f"### {result['name']}",
                f"- status: {result['status']}",
                f"- source_kind: {result['source_kind']}",
                f"- expected: {', '.join(result['expected']) or 'none'}",
                f"- matched: {', '.join(result['matched']) or 'none'}",
                f"- missing: {', '.join(result['missing']) or 'none'}",
                f"- forbidden_hits: {', '.join(result['forbidden_hits']) or 'none'}",
                f"- unexpected: {', '.join(result['unexpected']) or 'none'}",
                "- source_text: omitted_from_report",
            ]
        )
        details: list[RuleMatch] = list(result["match_details"])  # type: ignore[arg-type]
        if details:
            lines.append("- match_details:")
            for match in details:
                strong = ", ".join(match.strong_hits) or "none"
                weak = ", ".join(match.weak_hits) or "none"
                lines.append(f"  - {match.rule_key}: score={match.score}; strong={strong}; weak={weak}")
        else:
            lines.append("- match_details: none")
        lines.append("")

    lines.extend(
        [
            "## Gate",
            "",
            "- This report only evaluates rule matching heuristics.",
            "- It does not alter prompts, memory, voice profile, trial overlay, model weights, or runtime behavior.",
            "- If fail_count is 0, the next possible step is a separate owner-reviewed trial overlay candidate.",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def run_default_eval(cards_path: Path, output_path: Path, *, evaluated_at: str | None = None) -> dict[str, object]:
    evaluated_at = evaluated_at or datetime.now().astimezone().isoformat()
    cards = parse_owner_rule_cards(cards_path)
    report = render_eval_report(cards, DEFAULT_CASES, evaluated_at=evaluated_at)
    _write_text(output_path, report)
    fail_count = report.count("- status: fail")
    return {
        "owner_rule_card_count": len(cards),
        "case_count": len(DEFAULT_CASES),
        "fail_count": fail_count,
        "output": str(output_path),
        "boundary": BOUNDARY,
    }


def main(argv: list[str] | None = None) -> int:
    app_root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Evaluate approved dialogue-observation rule matching without runtime integration.")
    parser.add_argument("--cards", type=Path, default=default_cards_path(app_root))
    parser.add_argument("--output", type=Path, default=default_report_path(app_root))
    parser.add_argument("--text", default=None, help="Optional single text to evaluate instead of writing the default report.")
    parser.add_argument("--source-kind", default=OWNER_SCOPE)
    args = parser.parse_args(argv)

    cards = parse_owner_rule_cards(args.cards)
    if args.text is not None:
        matches = evaluate_text(cards, args.text, source_kind=args.source_kind)
        print(f"match_count: {len(matches)}")
        for match in matches:
            print(f"- {match.rule_key}: score={match.score}; title={match.title}")
        print(f"boundary: {BOUNDARY}")
        return 0

    result = run_default_eval(args.cards, args.output)
    for key, value in result.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
