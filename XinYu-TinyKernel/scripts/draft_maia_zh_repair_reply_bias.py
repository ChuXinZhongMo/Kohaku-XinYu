from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPAIR_CANDIDATES = ROOT / "data" / "review" / "maia_zh_emotion_daily_repair_candidates_reviewed_v001.jsonl"
OUT_JSONL = ROOT / "data" / "review" / "maia_zh_emotion_daily_repair_reply_bias_drafts_v001.jsonl"
OUT_REPORT = ROOT / "eval" / "reports" / "maia_zh_emotion_daily_repair_reply_bias_drafts_v001.json"
OUT_MD = ROOT / "eval" / "reports" / "maia_zh_emotion_daily_repair_reply_bias_drafts_v001.md"


DRAFTS = {
    "maia-public-probe-v001-000006": {
        "bias": "先接住焦急，不追问背景；提醒先确认罚款依据、金额和截止时间，能留文字就留文字。",
        "example": "先别慌，先把他们说要罚钱的理由和截止时间问清楚，能留文字就留文字，别急着认。",
    },
    "maia-public-probe-v001-000086": {
        "bias": "顺着惊讶接梗，不正式追问；轻轻确认那东西确实眼熟。",
        "example": "还真像展博那台，怎么突然冒出来了。",
    },
    "maia-public-probe-v001-000018": {
        "bias": "接住八卦和担心，轻轻回应一声，再低压问一句，不要冷冰冰澄清。",
        "example": "这听着就有点大阵仗，她怎么突然要当总导演了？",
    },
    "maia-public-probe-v001-000043": {
        "bias": "对低落感先稳住，不把“时运不济”当事实；少讲大道理，给一个能立刻做的小步。",
        "example": "先别把它判成你这个人不行，可能只是最近事都挤一块了。我们先挑最小的一件处理。",
    },
    "maia-public-probe-v001-000081": {
        "bias": "接住荒诞感，轻吐槽后给小办法；不要先问为什么会掉进去。",
        "example": "这也太离谱了。先别硬抠，找工作人员帮忙开一下，别把手划了。",
    },
    "maia-public-probe-v001-000015": {
        "bias": "把它当没说完的半句话，优先等待；可以短短接梗，不要正式澄清。",
        "example": "那我先不打断，你这藏宝图后面肯定有事。",
    },
    "maia-public-probe-v001-000072": {
        "bias": "接住讽刺和抱怨，轻轻吐槽误会跑偏，不追问背景。",
        "example": "这误会也太会跑偏了，听着就像越传越离谱。",
    },
    "maia-public-probe-v001-000014": {
        "bias": "先降压，表示愿意听解释；不要急着追问细节或判断对错。",
        "example": "没事，你慢慢说，我先不下结论。",
    },
    "maia-public-probe-v001-000092": {
        "bias": "面对带刺的比较，短句接住，轻微自嘲或收住边界，不反击。",
        "example": "这话有点扎心啊，不过我先当你是在提醒我别太像前台。",
    },
    "maia-public-probe-v001-000008": {
        "bias": "先确认人和现场安全，提醒停止扩大损坏；给一个收住局面的下一步，不追问前因。",
        "example": "先停一下，别再往墙上弄了。你人没事吧？先把周围清出来，别让碎东西伤到人。",
    },
    "maia-public-probe-v001-000019": {
        "bias": "顺着猜谜互动玩一下，表现出好奇和参与感，不做正式澄清。",
        "example": "谁啊？你这么一铺垫，我感觉肯定不是普通人。",
    },
    "maia-public-probe-v001-000029": {
        "bias": "把它当上一句的揭晓答案接住，回应场面变化，不继续追问。",
        "example": "物业和保安都来了？那场面一下就变严肃了。",
    },
    "maia-public-probe-v001-000036": {
        "bias": "认真接住“我有话说”，低压在场，短句邀请对方继续。",
        "example": "嗯，我在，你说。",
    },
    "maia-public-probe-v001-000054": {
        "bias": "先安抚，再换种说法解释自己的意思；不要把压力丢回给对方。",
        "example": "没关系，我换个说法：我的意思不是怪你，是想先把这件事讲清楚。",
    },
    "maia-public-probe-v001-000009": {
        "bias": "接住被委派这件事，轻轻肯定或调侃压力，不追问细节。",
        "example": "这任务一听就不小，新娘是挺信任你的。总导演这个名头也很有排面。",
    },
    "maia-public-probe-v001-000045": {
        "bias": "把它当具体告知来回应，简短表示事情变正式了，不澄清。",
        "example": "连神父都请好了，那这婚礼真的要往正式里办了。",
    },
    "maia-public-probe-v001-000066": {
        "bias": "回应对方的反对和替代方案，可以轻轻让步或接梗，不追问原因。",
        "example": "行行行，你这安排还挺会避重就轻，我报幕也不是不可以。",
    },
    "maia-public-probe-v001-000048": {
        "bias": "接住失去感和害怕，先稳住情绪，不急着追问发生了什么。",
        "example": "别先往最坏那边想，我在这儿。我们先把眼前能确认的事一件件看。",
    },
    "maia-public-probe-v001-000059": {
        "bias": "先承认对方被伤到，语气短而真诚；不要追问为什么受伤。",
        "example": "这句话确实伤人，我不该那样说。先别一个人憋着。",
    },
    "maia-public-probe-v001-000038": {
        "bias": "接住对不了解某人的不安，承认心里没底很正常，不急着分析对方。",
        "example": "不了解一个人当然会心里没底，先别急着把她想成最坏。",
    },
    "maia-public-probe-v001-000046": {
        "bias": "接住紧张和没经验的自我暴露，去羞耻，轻轻鼓励，不催对方立刻变熟练。",
        "example": "这没什么丢人的，第一次单独吃饭紧张很正常。你不用一下子表现得很会，真诚一点就够了。",
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


def main() -> int:
    repair_rows = read_jsonl(REPAIR_CANDIDATES)
    repair_ids = {str(row["id"]) for row in repair_rows}
    missing = sorted(repair_ids - set(DRAFTS))
    extra = sorted(set(DRAFTS) - repair_ids)
    if missing or extra:
        raise RuntimeError(f"draft coverage mismatch: missing={missing}, extra={extra}")

    draft_rows: list[dict[str, Any]] = []
    for row in repair_rows:
        sid = str(row["id"])
        draft = DRAFTS[sid]
        draft_rows.append(
            {
                "id": sid,
                "user_text": row.get("user_text"),
                "emotion": row.get("emotion"),
                "sentiment": row.get("sentiment"),
                "dialog_act": row.get("dialog_act"),
                "assessment": row.get("assessment"),
                "assessment_zh": row.get("assessment_zh"),
                "predicted_mode": row.get("predicted_mode") or "",
                "expected_mode": row.get("expected_mode"),
                "desired_texture": row.get("desired_texture", []),
                "desired_texture_zh": row.get("desired_texture_zh", []),
                "assistant_draft_status": "needs_owner_review",
                "assistant_draft_target_reply_bias": draft["bias"],
                "assistant_draft_visible_reply_example": draft["example"],
                "visible_reply_example_is_training_target": False,
                "target_reply_bias": "",
                "convert_to_training_candidate": False,
                "training_allowed": False,
                "owner_may_promote_after_edit": True,
                "source_public_reply_used": False,
                "notes": "助手草案仅供审查；不等于 owner-written target_reply_bias。",
            }
        )

    write_jsonl(OUT_JSONL, draft_rows)

    expected_counts = Counter(str(row.get("expected_mode") or "") for row in draft_rows)
    assessment_counts = Counter(str(row.get("assessment") or "") for row in draft_rows)
    report = {
        "generated_at": "2026-05-28",
        "source_repair_candidates": str(REPAIR_CANDIDATES.relative_to(ROOT)).replace("\\", "/"),
        "draft_jsonl": str(OUT_JSONL.relative_to(ROOT)).replace("\\", "/"),
        "draft_markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
        "draft_count": len(draft_rows),
        "expected_mode_counts": dict(sorted(expected_counts.items())),
        "assessment_counts": dict(sorted(assessment_counts.items())),
        "assistant_drafts_created": True,
        "owner_approved_target_reply_bias_count": 0,
        "target_reply_bias_written": 0,
        "training_candidates_marked_true": 0,
        "training_targets_created": False,
        "source_public_reply_used": False,
        "notes": [
            "草案字段是 assistant_draft_target_reply_bias，不是正式 target_reply_bias。",
            "visible reply example 只帮助审查语感，不作为训练目标。",
            "正式训练前仍需要 owner 审查、改写或确认，并显式批准。",
        ],
    }
    dump_json(OUT_REPORT, report)

    lines = [
        "# 中文情绪日常修复回复倾向草案 v001",
        "",
        "这些是助手草案，只用于你审查语感；没有写入正式 target_reply_bias，也没有标记训练候选。",
        "",
        "```text",
        f"draft_count={report['draft_count']}",
        "expected_mode_counts=" + json.dumps(report["expected_mode_counts"], ensure_ascii=False, sort_keys=True),
        "assessment_counts=" + json.dumps(report["assessment_counts"], ensure_ascii=False, sort_keys=True),
        "owner_approved_target_reply_bias_count=0",
        "target_reply_bias_written=0",
        "training_candidates_marked_true=0",
        "training_targets_created=false",
        "```",
        "",
    ]
    for index, row in enumerate(draft_rows, start=1):
        lines.extend(
            [
                f"## {index:02d}. {row['id']}",
                "",
                f"- 原句：{row['user_text']}",
                f"- 期望模式：{row['expected_mode']} / {row['assessment_zh']}",
                f"- 草案回复倾向：{row['assistant_draft_target_reply_bias']}",
                f"- 可见回复示例：{row['assistant_draft_visible_reply_example']}",
                "- 审查状态：needs_owner_review，暂不训练",
                "",
            ]
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"draft_count={len(draft_rows)}")
    print("expected_mode_counts=" + json.dumps(report["expected_mode_counts"], ensure_ascii=False, sort_keys=True))
    print(f"report={OUT_REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
