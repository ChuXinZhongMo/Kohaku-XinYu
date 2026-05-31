from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

V003_REPORT = ROOT / "eval" / "reports" / "xinyu_maia_zh_behavior_inner_eval_v003_balanced_compact_behavior_balanced56.json"
V003_CASES = ROOT / "data" / "sft" / "xinyu_maia_zh_behavior_eval_v003_balanced_compact_balanced56.jsonl"
EMOTION_FOCUS = ROOT / "data" / "review" / "maia_zh_emotion_daily_owner_review_sheet_v001.jsonl"
CANDIDATE_SLICE = ROOT / "data" / "review" / "xinyu_maia_zh_behavior_candidate_review_slice_v001.jsonl"

OUT_JSONL = ROOT / "data" / "review" / "xinyu_maia_zh_behavior_boundary_owner_review_sheet_v004.jsonl"
OUT_REPORT = ROOT / "eval" / "reports" / "xinyu_maia_zh_behavior_boundary_owner_review_sheet_v004.json"
OUT_MD = ROOT / "eval" / "reports" / "xinyu_maia_zh_behavior_boundary_owner_review_sheet_v004.md"

TARGET_MODES = {"reply", "clarify", "wait"}
MODE_ZH = {
    "reply": "回复",
    "clarify": "澄清",
    "wait": "等待",
    "": "协议失败/空输出",
    "schema_fail_or_empty": "协议失败/空输出",
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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


def parse_payload(case: dict[str, Any]) -> dict[str, Any]:
    for message in case.get("messages", []):
        if message.get("role") == "user":
            return json.loads(message.get("content") or "{}")
    return {}


def parse_target(case: dict[str, Any]) -> dict[str, Any]:
    for message in case.get("messages", []):
        if message.get("role") == "assistant":
            try:
                return json.loads(message.get("content") or "{}")
            except json.JSONDecodeError:
                return {}
    return {}


def mode_zh(mode: str) -> str:
    return MODE_ZH.get(mode, mode)


def compact_text(value: Any, limit: int = 96) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def boundary_question(expected: str, actual: str) -> str:
    if expected == "clarify" and actual == "reply":
        return "它是否真的缺少对象/意图，需要低压力问一句，还是可以直接接住？"
    if expected == "wait" and actual == "reply":
        return "它是否像没说完，需要等一下，还是可以短短回应？"
    if expected == "wait" and actual == "clarify":
        return "它是没说完该等，还是缺关键信息该问？"
    if expected == "reply" and actual == "clarify":
        return "它是不是只是日常情绪/互动，模型却过度澄清了？"
    if expected == "reply" and actual == "reply":
        return "回复对照样本：确认这类日常句子不该被澄清或等待。"
    if expected == "clarify" and actual == "clarify":
        return "澄清对照样本：确认这类确实缺对象/意图。"
    if expected == "wait" and actual == "wait":
        return "等待对照样本：确认这类确实没说完。"
    return "请只判断 reply / clarify / wait 的边界。"


def empty_owner_review() -> dict[str, Any]:
    return {
        "status": "unreviewed",
        "expected_mode": "",
        "expected_mode_zh": "",
        "accept_suggestion": None,
        "alive_feeling_score_1_to_5": None,
        "too_much_clarify": None,
        "too_fast_reply": None,
        "should_wait": None,
        "notes": "",
        "target_reply_bias": "",
        "convert_to_training_candidate": False,
    }


def make_row(
    *,
    review_id: str,
    source_kind: str,
    source_id: str,
    candidate_id: str,
    user_text: str,
    context: dict[str, Any],
    suggested_mode: str,
    suggestion_source: str,
    model_predicted_mode: str,
    model_schema_ok: bool | None,
    model_mode_match: bool | None,
    reply_bias_suggestion: str,
    priority: int,
    boundary_note_zh: str,
) -> dict[str, Any]:
    return {
        "review_id": review_id,
        "source_kind": source_kind,
        "source_id": source_id,
        "candidate_id": candidate_id,
        "user_text": user_text,
        "context": context,
        "suggested_expected_mode": suggested_mode,
        "suggested_expected_mode_zh": mode_zh(suggested_mode),
        "suggestion_source": suggestion_source,
        "model_observation": {
            "predicted_mode": model_predicted_mode,
            "predicted_mode_zh": mode_zh(model_predicted_mode),
            "schema_ok": model_schema_ok,
            "mode_match": model_mode_match,
        },
        "reply_bias_suggestion": reply_bias_suggestion,
        "reply_bias_suggestion_is_training_target": False,
        "boundary_note_zh": boundary_note_zh,
        "priority": priority,
        "owner_review": empty_owner_review(),
        "training_allowed": False,
        "training_targets_created": False,
        "source_public_reply_used": False,
        "notes": "只审 reply/clarify/wait 边界；建议字段仅供挑错，未经 owner 确认不能训练。",
    }


def build_from_v003() -> tuple[list[dict[str, Any]], set[str], set[str]]:
    report = read_json(V003_REPORT)
    cases = {str(row["id"]): row for row in read_jsonl(V003_CASES)}
    results = {str(row["id"]): row for row in report["results"]}
    rows: list[dict[str, Any]] = []
    used_candidate_ids: set[str] = set()
    used_texts: set[str] = set()

    selected = [
        case_id
        for case_id, case in cases.items()
        if str((case.get("expected_behavior") or {}).get("mode") or "") in TARGET_MODES
    ]
    selected.sort(key=lambda cid: (results.get(cid, {}).get("mode_match") is True, cid))

    for case_id in selected:
        case = cases[case_id]
        result = results.get(case_id, {})
        payload = parse_payload(case)
        target = parse_target(case)
        expected = str((case.get("expected_behavior") or {}).get("mode") or "")
        actual = str(result.get("actual_mode") or "")
        candidate_id = str(payload.get("id") or "")
        user_text = str(payload.get("u") or "")
        used_candidate_ids.add(candidate_id)
        used_texts.add(user_text)
        priority = 10
        if expected == "wait":
            priority = 1 if actual != "wait" else 6
        elif expected == "clarify":
            priority = 2 if actual != "clarify" else 7
        elif expected == "reply" and actual != "reply":
            priority = 3
        else:
            priority = 8

        action_tendency = target.get("action_tendency") if isinstance(target, dict) else {}
        rows.append(
            make_row(
                review_id="",
                source_kind="v003_balanced_eval_reply_clarify_wait",
                source_id=case_id,
                candidate_id=candidate_id,
                user_text=user_text,
                context={
                    "emotion": payload.get("emotion"),
                    "sentiment": payload.get("sentiment"),
                    "dialog_act": payload.get("act"),
                    "scene": payload.get("scene"),
                    "surface": payload.get("surface"),
                    "origin": payload.get("origin"),
                },
                suggested_mode=expected,
                suggestion_source="unreviewed_compact_sft_expected_behavior",
                model_predicted_mode=actual,
                model_schema_ok=result.get("schema_ok") if result else None,
                model_mode_match=result.get("mode_match") if result else None,
                reply_bias_suggestion=str((action_tendency or {}).get("reply_bias") or ""),
                priority=priority,
                boundary_note_zh=boundary_question(expected, actual),
            )
        )
    return rows, used_candidate_ids, used_texts


def build_from_emotion_focus(used_texts: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_jsonl(EMOTION_FOCUS):
        user_text = str(row.get("user_text") or "")
        owner_review = row.get("owner_review") or {}
        expected = str(owner_review.get("expected_mode") or row.get("suggested_expected_mode") or "")
        actual = str(row.get("predicted_mode") or "")
        if expected not in TARGET_MODES:
            continue
        used_texts.add(user_text)
        priority = 4
        if expected == "reply" and actual in {"clarify", "schema_fail_or_empty", ""}:
            priority = 3
        elif expected == "wait":
            priority = 2
        elif expected == "clarify":
            priority = 5
        rows.append(
            make_row(
                review_id="",
                source_kind="zh_emotion_focus_v001",
                source_id=str(row.get("id") or ""),
                candidate_id=str(row.get("id") or ""),
                user_text=user_text,
                context={
                    "emotion": row.get("emotion"),
                    "sentiment": row.get("sentiment"),
                    "dialog_act": row.get("dialog_act"),
                    "scene": row.get("scene"),
                    "assessment": row.get("assessment"),
                    "assessment_zh": row.get("assessment_zh"),
                },
                suggested_mode=expected,
                suggestion_source="previous_delegated_review_suggestion_not_training_target",
                model_predicted_mode=actual,
                model_schema_ok=actual not in {"schema_fail_or_empty", ""},
                model_mode_match=(actual == expected),
                reply_bias_suggestion=str(owner_review.get("target_reply_bias") or ""),
                priority=priority,
                boundary_note_zh=str(row.get("rationale_zh") or boundary_question(expected, actual)),
            )
        )
    return rows


def build_extra_from_candidate_slice(
    *,
    used_candidate_ids: set[str],
    used_texts: set[str],
    wait_limit: int = 4,
    clarify_limit: int = 5,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    picked = Counter()
    for row in read_jsonl(CANDIDATE_SLICE):
        candidate_id = str(row.get("candidate_id") or "")
        user_text = str(row.get("user_text") or "")
        suggestion = row.get("expected_suggestion") or {}
        expected = str(suggestion.get("mode") or "")
        if expected not in {"wait", "clarify"}:
            continue
        if candidate_id in used_candidate_ids or user_text in used_texts:
            continue
        if expected == "wait" and picked["wait"] >= wait_limit:
            continue
        if expected == "clarify" and picked["clarify"] >= clarify_limit:
            continue
        picked[expected] += 1
        used_candidate_ids.add(candidate_id)
        used_texts.add(user_text)
        context = row.get("context") or {}
        rows.append(
            make_row(
                review_id="",
                source_kind="candidate_slice_extra_boundary",
                source_id=str(row.get("slice_id") or candidate_id),
                candidate_id=candidate_id,
                user_text=user_text,
                context={
                    "emotion": context.get("emotion"),
                    "sentiment": context.get("sentiment"),
                    "dialog_act": context.get("dialog_act"),
                    "scene": context.get("scene"),
                    "surface": context.get("surface"),
                },
                suggested_mode=expected,
                suggestion_source="assistant_suggested_rule_needs_owner_review",
                model_predicted_mode="",
                model_schema_ok=None,
                model_mode_match=None,
                reply_bias_suggestion=str(suggestion.get("reply_bias") or ""),
                priority=6 if expected == "wait" else 7,
                boundary_note_zh=(
                    "补充等待边界样本：确认它是不是没说完，不要让模型抢话。"
                    if expected == "wait"
                    else "补充澄清边界样本：确认它是否真缺对象/意图。"
                ),
            )
        )
    return rows


def assign_review_ids(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = sorted(rows, key=lambda row: (int(row["priority"]), str(row["source_kind"]), str(row["source_id"])))
    for index, row in enumerate(rows, start=1):
        row["review_id"] = f"xinyu-maia-zh-boundary-v004-{index:03d}"
    return rows


def write_markdown(rows: list[dict[str, Any]], report: dict[str, Any]) -> None:
    lines = [
        "# XinYu Maia 中文行为边界审核表 v004",
        "",
        "目标：只判断 XinYu 在这些中文日常/情绪句子里应该 reply、clarify 还是 wait。",
        "",
        "不要把建议字段当训练答案；不要复制公开语料的后续回复；没有 owner 明确确认前不训练。",
        "",
        "填法：",
        "",
        "```text",
        "expected_mode=reply / clarify / wait",
        "accept_suggestion=yes / no / edit",
        "alive=1-5",
        "too_much_clarify=yes / no",
        "too_fast_reply=yes / no",
        "should_wait=yes / no",
        "notes=一句话说明即可",
        "training_candidate=默认 no；只有你确定要收进 v004 修复集时才写 yes",
        "```",
        "",
        "```text",
        f"row_count={report['row_count']}",
        "suggested_mode_counts=" + json.dumps(report["suggested_mode_counts"], ensure_ascii=False, sort_keys=True),
        "source_kind_counts=" + json.dumps(report["source_kind_counts"], ensure_ascii=False, sort_keys=True),
        "training_targets_created=false",
        "active_adapter=none",
        "canary/live=not_enabled",
        "```",
        "",
    ]

    for row in rows:
        obs = row["model_observation"]
        context = row["context"]
        lines.extend(
            [
                f"## {row['review_id']}",
                "",
                f"- 原句：{row['user_text']}",
                f"- 场景：{context.get('emotion') or ''} / {context.get('sentiment') or ''} / {context.get('dialog_act') or ''} / {context.get('scene') or ''}",
                f"- 模型预测：{obs.get('predicted_mode_zh') or '未评测'}",
                f"- 建议模式：{row['suggested_expected_mode_zh']}（{row['suggestion_source']}）",
                f"- 边界问题：{row['boundary_note_zh']}",
                f"- 回复倾向建议：{compact_text(row.get('reply_bias_suggestion') or '无', 120)}",
                "",
                "```text",
                "expected_mode=",
                "accept_suggestion=",
                "alive=",
                "too_much_clarify=",
                "too_fast_reply=",
                "should_wait=",
                "notes=",
                "training_candidate=no",
                "```",
                "",
            ]
        )
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    v003_rows, used_candidate_ids, used_texts = build_from_v003()
    emotion_rows = build_from_emotion_focus(used_texts)
    extra_rows = build_extra_from_candidate_slice(used_candidate_ids=used_candidate_ids, used_texts=used_texts)
    rows = assign_review_ids(v003_rows + emotion_rows + extra_rows)

    if len(rows) != 60:
        raise RuntimeError(f"expected 60 review rows, got {len(rows)}")

    source_kind_counts = Counter(str(row["source_kind"]) for row in rows)
    suggested_mode_counts = Counter(str(row["suggested_expected_mode"]) for row in rows)
    predicted_mode_counts = Counter(str(row["model_observation"]["predicted_mode"]) for row in rows)
    needs_decision_counts = Counter(
        f"{row['suggested_expected_mode']}<-{row['model_observation']['predicted_mode'] or 'unscored'}"
        for row in rows
    )

    write_jsonl(OUT_JSONL, rows)
    report = {
        "generated_at": "2026-05-28",
        "row_count": len(rows),
        "jsonl": str(OUT_JSONL.relative_to(ROOT)).replace("\\", "/"),
        "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
        "sources": [
            str(V003_REPORT.relative_to(ROOT)).replace("\\", "/"),
            str(V003_CASES.relative_to(ROOT)).replace("\\", "/"),
            str(EMOTION_FOCUS.relative_to(ROOT)).replace("\\", "/"),
            str(CANDIDATE_SLICE.relative_to(ROOT)).replace("\\", "/"),
        ],
        "source_kind_counts": dict(sorted(source_kind_counts.items())),
        "suggested_mode_counts": dict(sorted(suggested_mode_counts.items())),
        "predicted_mode_counts": dict(sorted(predicted_mode_counts.items())),
        "needs_decision_counts": dict(sorted(needs_decision_counts.items())),
        "owner_review_status_counts": {"unreviewed": len(rows)},
        "training_allowed_count": 0,
        "training_targets_created": False,
        "source_public_reply_used": False,
        "canary_live_enabled": False,
        "active_adapter_changed": False,
        "notes": [
            "This is a boundary review worksheet, not SFT data.",
            "All suggested labels remain assistant/delegated suggestions until owner-reviewed.",
            "Only public utterance prompts are used; public replies are not used as XinYu targets.",
            "Owner should fill only reply/clarify/wait mode boundary fields before v004 repair training.",
        ],
    }
    dump_json(OUT_REPORT, report)
    write_markdown(rows, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
