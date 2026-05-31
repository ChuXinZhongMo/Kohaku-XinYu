from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SHEET = ROOT / "data" / "review" / "xinyu_maia_zh_behavior_boundary_owner_review_sheet_v004.jsonl"
OUT_JSONL = ROOT / "data" / "review" / "xinyu_maia_zh_behavior_boundary_review_proposals_v004.jsonl"
OUT_REPORT = ROOT / "eval" / "reports" / "xinyu_maia_zh_behavior_boundary_review_proposals_v004.json"
OUT_MD = ROOT / "eval" / "reports" / "xinyu_maia_zh_behavior_boundary_review_proposals_v004.md"

MODE_ZH = {"reply": "回复", "clarify": "澄清", "wait": "等待", "": "未评测"}


PROPOSALS: dict[str, dict[str, str]] = {
    "xinyu-maia-zh-boundary-v004-001": {
        "mode": "reply",
        "confidence": "high",
        "reason": "问候语应短短回应，不该等。",
    },
    "xinyu-maia-zh-boundary-v004-002": {
        "mode": "clarify",
        "confidence": "high",
        "reason": "这是什么缺少可见对象或指代，低压力问一句合理。",
    },
    "xinyu-maia-zh-boundary-v004-003": {
        "mode": "wait",
        "confidence": "medium",
        "reason": "像只说了称呼或半句，先等比抢答自然。",
    },
    "xinyu-maia-zh-boundary-v004-004": {
        "mode": "reply",
        "confidence": "high",
        "reason": "这是情绪反应，直接接住即可。",
    },
    "xinyu-maia-zh-boundary-v004-005": {
        "mode": "reply",
        "confidence": "medium",
        "reason": "短评/吐槽类，更像接梗，不需要澄清或等待。",
    },
    "xinyu-maia-zh-boundary-v004-006": {
        "mode": "reply",
        "confidence": "medium",
        "reason": "短评类，适合轻接一句。",
    },
    "xinyu-maia-zh-boundary-v004-007": {
        "mode": "reply",
        "confidence": "high",
        "reason": "这是反问/确认，直接回应更自然。",
    },
    "xinyu-maia-zh-boundary-v004-008": {
        "mode": "clarify",
        "confidence": "medium",
        "reason": "单独丢一个名词，意图缺口明显。",
    },
    "xinyu-maia-zh-boundary-v004-009": {
        "mode": "reply",
        "confidence": "high",
        "reason": "对方问能不能听见，XinYu 可以直接确认在场。",
    },
    "xinyu-maia-zh-boundary-v004-010": {
        "mode": "clarify",
        "confidence": "high",
        "reason": "他/它指代不明，需问最小缺口。",
    },
    "xinyu-maia-zh-boundary-v004-011": {
        "mode": "clarify",
        "confidence": "medium",
        "reason": "要哪张地图不清楚，低压确认合理。",
    },
    "xinyu-maia-zh-boundary-v004-012": {
        "mode": "reply",
        "confidence": "medium",
        "reason": "请求本身清楚，先接住并守住安全边界。",
    },
    "xinyu-maia-zh-boundary-v004-013": {
        "mode": "reply",
        "confidence": "high",
        "reason": "这是惊讶吐槽，直接接住比澄清自然。",
    },
    "xinyu-maia-zh-boundary-v004-014": {
        "mode": "wait",
        "confidence": "high",
        "reason": "如果不是你一菲明显没说完，应等后半句。",
    },
    "xinyu-maia-zh-boundary-v004-015": {
        "mode": "reply",
        "confidence": "medium",
        "reason": "像一个荒诞解释点，轻吐槽接住即可。",
    },
    "xinyu-maia-zh-boundary-v004-016": {
        "mode": "wait",
        "confidence": "high",
        "reason": "我要有藏宝图的话是条件句开头，应等后半句。",
    },
    "xinyu-maia-zh-boundary-v004-017": {
        "mode": "wait",
        "confidence": "high",
        "reason": "对方明确打住并要求收住，等待合理。",
    },
    "xinyu-maia-zh-boundary-v004-018": {
        "mode": "reply",
        "confidence": "high",
        "reason": "罚钱怎么办是明确求助，先稳住并给小步骤。",
    },
    "xinyu-maia-zh-boundary-v004-019": {
        "mode": "reply",
        "confidence": "high",
        "reason": "打洞是具体风险事件，先接住并提醒停手/安全。",
    },
    "xinyu-maia-zh-boundary-v004-020": {
        "mode": "reply",
        "confidence": "high",
        "reason": "角色告知清楚，适合日常式回应。",
    },
    "xinyu-maia-zh-boundary-v004-021": {
        "mode": "reply",
        "confidence": "high",
        "reason": "解释误会的开场，先降压让对方说。",
    },
    "xinyu-maia-zh-boundary-v004-022": {
        "mode": "reply",
        "confidence": "high",
        "reason": "八卦/担心信息已足够，先接住语气。",
    },
    "xinyu-maia-zh-boundary-v004-023": {
        "mode": "reply",
        "confidence": "high",
        "reason": "你猜是互动邀请，适合顺着玩。",
    },
    "xinyu-maia-zh-boundary-v004-024": {
        "mode": "reply",
        "confidence": "high",
        "reason": "这是揭晓答案，直接接住场面变化。",
    },
    "xinyu-maia-zh-boundary-v004-025": {
        "mode": "reply",
        "confidence": "high",
        "reason": "我有话想跟你说应回应我在听。",
    },
    "xinyu-maia-zh-boundary-v004-026": {
        "mode": "reply",
        "confidence": "high",
        "reason": "对不了解某人的不安，应先承认不安。",
    },
    "xinyu-maia-zh-boundary-v004-027": {
        "mode": "reply",
        "confidence": "high",
        "reason": "低落求助很明确，不能协议失败或追问。",
    },
    "xinyu-maia-zh-boundary-v004-028": {
        "mode": "reply",
        "confidence": "high",
        "reason": "具体告知，接住事情变正式即可。",
    },
    "xinyu-maia-zh-boundary-v004-029": {
        "mode": "reply",
        "confidence": "high",
        "reason": "紧张自我暴露，应去羞耻并轻安抚。",
    },
    "xinyu-maia-zh-boundary-v004-030": {
        "mode": "reply",
        "confidence": "medium",
        "reason": "带失去感的自我纠正，先稳住情绪。",
    },
    "xinyu-maia-zh-boundary-v004-031": {
        "mode": "reply",
        "confidence": "high",
        "reason": "对方说不明白，应换种说法，不把压力丢回去。",
    },
    "xinyu-maia-zh-boundary-v004-032": {
        "mode": "reply",
        "confidence": "high",
        "reason": "被伤到的情绪明确，应先承认伤人。",
    },
    "xinyu-maia-zh-boundary-v004-033": {
        "mode": "reply",
        "confidence": "high",
        "reason": "对方反对并给替代方案，应回应态度。",
    },
    "xinyu-maia-zh-boundary-v004-034": {
        "mode": "reply",
        "confidence": "high",
        "reason": "这是讽刺/吐槽，应接住语气。",
    },
    "xinyu-maia-zh-boundary-v004-035": {
        "mode": "reply",
        "confidence": "high",
        "reason": "问题具体，先轻吐槽再给小办法。",
    },
    "xinyu-maia-zh-boundary-v004-036": {
        "mode": "reply",
        "confidence": "high",
        "reason": "认出东西的惊讶，接梗比澄清自然。",
    },
    "xinyu-maia-zh-boundary-v004-037": {
        "mode": "reply",
        "confidence": "high",
        "reason": "带刺比较，短短接住边界即可。",
    },
    "xinyu-maia-zh-boundary-v004-038": {
        "mode": "clarify",
        "confidence": "medium",
        "reason": "铺垫后缺少下一步意图，低压问一句。",
    },
    "xinyu-maia-zh-boundary-v004-039": {
        "mode": "clarify",
        "confidence": "high",
        "reason": "问看过没有但对象不在上下文，需确认。",
    },
    "xinyu-maia-zh-boundary-v004-040": {
        "mode": "clarify",
        "confidence": "high",
        "reason": "找地方住涉及地点和安全，需问关键条件。",
    },
    "xinyu-maia-zh-boundary-v004-041": {
        "mode": "clarify",
        "confidence": "medium",
        "reason": "企鹅这句上下文依赖强，问小缺口可接受。",
    },
    "xinyu-maia-zh-boundary-v004-042": {
        "mode": "clarify",
        "confidence": "high",
        "reason": "更恐怖的事情发生了缺少事件内容。",
    },
    "xinyu-maia-zh-boundary-v004-043": {
        "mode": "reply",
        "confidence": "medium",
        "reason": "非常荣幸是礼貌表态，可短回应。",
    },
    "xinyu-maia-zh-boundary-v004-044": {
        "mode": "reply",
        "confidence": "medium",
        "reason": "不能用的是明确判断，接住并给下一步。",
    },
    "xinyu-maia-zh-boundary-v004-045": {
        "mode": "reply",
        "confidence": "high",
        "reason": "我要出家是强情绪/戏剧化表达，应先稳住。",
    },
    "xinyu-maia-zh-boundary-v004-046": {
        "mode": "clarify",
        "confidence": "medium",
        "reason": "危险对象不明，先问指的是什么。",
    },
    "xinyu-maia-zh-boundary-v004-047": {
        "mode": "clarify",
        "confidence": "medium",
        "reason": "礼金问题角色关系不明，低压确认意图。",
    },
    "xinyu-maia-zh-boundary-v004-048": {
        "mode": "reply",
        "confidence": "high",
        "reason": "这是惊讶反应，直接接住即可。",
    },
    "xinyu-maia-zh-boundary-v004-049": {
        "mode": "wait",
        "confidence": "medium",
        "reason": "像铺垫后文的开场，可以等对方继续。",
    },
    "xinyu-maia-zh-boundary-v004-050": {
        "mode": "reply",
        "confidence": "high",
        "reason": "挑衅/威胁语气明确，应稳住边界。",
    },
    "xinyu-maia-zh-boundary-v004-051": {
        "mode": "reply",
        "confidence": "medium",
        "reason": "你想怎么样是对峙式问题，先稳住而不是正式澄清。",
    },
    "xinyu-maia-zh-boundary-v004-052": {
        "mode": "clarify",
        "confidence": "medium",
        "reason": "藏宝图指向具体但上下文缺失，轻问可接受。",
    },
    "xinyu-maia-zh-boundary-v004-053": {
        "mode": "reply",
        "confidence": "high",
        "reason": "日常冲突问句，接住即可。",
    },
    "xinyu-maia-zh-boundary-v004-054": {
        "mode": "reply",
        "confidence": "high",
        "reason": "角色安排变化，直接回应。",
    },
    "xinyu-maia-zh-boundary-v004-055": {
        "mode": "reply",
        "confidence": "high",
        "reason": "具体发现，接住即可。",
    },
    "xinyu-maia-zh-boundary-v004-056": {
        "mode": "reply",
        "confidence": "high",
        "reason": "吐槽明确，接住语气。",
    },
    "xinyu-maia-zh-boundary-v004-057": {
        "mode": "reply",
        "confidence": "medium",
        "reason": "挑战式互动，顺着接即可。",
    },
    "xinyu-maia-zh-boundary-v004-058": {
        "mode": "reply",
        "confidence": "high",
        "reason": "感谢语应回应感谢。",
    },
    "xinyu-maia-zh-boundary-v004-059": {
        "mode": "reply",
        "confidence": "high",
        "reason": "推测评价，短回应即可。",
    },
    "xinyu-maia-zh-boundary-v004-060": {
        "mode": "reply",
        "confidence": "high",
        "reason": "明确诉求/批评，应回应态度。",
    },
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if line.strip():
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return len(rows)


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def mode_zh(mode: str) -> str:
    return MODE_ZH.get(mode, mode)


def compact(value: Any, limit: int = 80) -> str:
    text = " ".join(str(value or "").split()).replace("|", "\\|")
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def main() -> int:
    sheet_rows = read_jsonl(SHEET)
    sheet_ids = {str(row["review_id"]) for row in sheet_rows}
    missing = sorted(sheet_ids - set(PROPOSALS))
    extra = sorted(set(PROPOSALS) - sheet_ids)
    if missing or extra:
        raise RuntimeError(f"proposal coverage mismatch: missing={missing}, extra={extra}")

    rows: list[dict[str, Any]] = []
    for row in sheet_rows:
        review_id = str(row["review_id"])
        proposal = PROPOSALS[review_id]
        suggested = str(row.get("suggested_expected_mode") or "")
        model_predicted = str((row.get("model_observation") or {}).get("predicted_mode") or "")
        proposed = proposal["mode"]
        rows.append(
            {
                "review_id": review_id,
                "source_id": row.get("source_id"),
                "source_kind": row.get("source_kind"),
                "user_text": row.get("user_text"),
                "context": row.get("context"),
                "suggested_expected_mode": suggested,
                "suggested_expected_mode_zh": mode_zh(suggested),
                "model_predicted_mode": model_predicted,
                "model_predicted_mode_zh": mode_zh(model_predicted),
                "assistant_proposed_mode": proposed,
                "assistant_proposed_mode_zh": mode_zh(proposed),
                "assistant_proposal_confidence": proposal["confidence"],
                "assistant_proposal_reason_zh": proposal["reason"],
                "proposal_differs_from_original_suggestion": proposed != suggested,
                "proposal_differs_from_model": proposed != model_predicted if model_predicted else None,
                "owner_review_required": True,
                "training_allowed": False,
                "convert_to_training_candidate": False,
                "training_targets_created": False,
                "source_public_reply_used": False,
                "notes": "助手建议稿只用于加速审查；不是 owner_review，也不是 SFT 目标。",
            }
        )

    write_jsonl(OUT_JSONL, rows)
    proposed_counts = Counter(str(row["assistant_proposed_mode"]) for row in rows)
    suggested_counts = Counter(str(row["suggested_expected_mode"]) for row in rows)
    confidence_counts = Counter(str(row["assistant_proposal_confidence"]) for row in rows)
    changed_from_suggestion = [row for row in rows if row["proposal_differs_from_original_suggestion"]]
    changed_from_model = [row for row in rows if row["proposal_differs_from_model"] is True]
    report = {
        "generated_at": "2026-05-28",
        "source_sheet": str(SHEET.relative_to(ROOT)).replace("\\", "/"),
        "proposal_jsonl": str(OUT_JSONL.relative_to(ROOT)).replace("\\", "/"),
        "proposal_markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
        "row_count": len(rows),
        "suggested_mode_counts": dict(sorted(suggested_counts.items())),
        "assistant_proposed_mode_counts": dict(sorted(proposed_counts.items())),
        "assistant_proposal_confidence_counts": dict(sorted(confidence_counts.items())),
        "proposal_differs_from_original_suggestion_count": len(changed_from_suggestion),
        "proposal_differs_from_model_count": len(changed_from_model),
        "owner_review_required": True,
        "training_allowed_count": 0,
        "training_targets_created": False,
        "source_public_reply_used": False,
        "canary_live_enabled": False,
        "active_adapter_changed": False,
        "notes": [
            "Assistant proposals are not owner labels.",
            "Do not train from this file directly.",
            "The large shift from wait to reply/clarify indicates v003 source labels likely over-created wait rows.",
        ],
    }
    dump_json(OUT_REPORT, report)

    lines = [
        "# XinYu Maia 中文行为边界建议稿 v004",
        "",
        "这是助手建议稿，用来减少人工审查成本；不是训练集，也不会改 owner_review。",
        "",
        "```text",
        f"row_count={report['row_count']}",
        "original_suggested_mode_counts="
        + json.dumps(report["suggested_mode_counts"], ensure_ascii=False, sort_keys=True),
        "assistant_proposed_mode_counts="
        + json.dumps(report["assistant_proposed_mode_counts"], ensure_ascii=False, sort_keys=True),
        "assistant_proposal_confidence_counts="
        + json.dumps(report["assistant_proposal_confidence_counts"], ensure_ascii=False, sort_keys=True),
        f"proposal_differs_from_original_suggestion_count={report['proposal_differs_from_original_suggestion_count']}",
        f"proposal_differs_from_model_count={report['proposal_differs_from_model_count']}",
        "training_targets_created=false",
        "```",
        "",
        "## 建议和原表冲突的行",
        "",
        "| id | 原建议 | 模型 | 助手建议 | 置信 | 原句 | 理由 |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in changed_from_suggestion:
        lines.append(
            f"| {row['review_id']} | {row['suggested_expected_mode_zh']} | "
            f"{row['model_predicted_mode_zh']} | {row['assistant_proposed_mode_zh']} | "
            f"{row['assistant_proposal_confidence']} | {compact(row['user_text'], 36)} | "
            f"{compact(row['assistant_proposal_reason_zh'], 60)} |"
        )

    lines.extend(
        [
            "",
            "## 全量建议",
            "",
            "| id | 助手建议 | 置信 | 原句 | 理由 |",
            "|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['review_id']} | {row['assistant_proposed_mode_zh']} | "
            f"{row['assistant_proposal_confidence']} | {compact(row['user_text'], 40)} | "
            f"{compact(row['assistant_proposal_reason_zh'], 64)} |"
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
