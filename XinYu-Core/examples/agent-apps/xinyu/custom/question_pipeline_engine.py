from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def extract_question_blocks(text: str) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    parts = re.split(r"(?m)^## (q-\d+)\n", text)
    if len(parts) < 3:
        return blocks

    for i in range(1, len(parts), 2):
        qid = parts[i].strip()
        body = parts[i + 1]
        question = ""
        target = ""
        status = ""
        outward_scope = ""
        for line in body.splitlines():
            if line.startswith("- question: "):
                question = line.removeprefix("- question: ").strip()
            elif line.startswith("- target: "):
                target = line.removeprefix("- target: ").strip()
            elif line.startswith("- status: "):
                status = line.removeprefix("- status: ").strip()
            elif line.startswith("- outward_scope: "):
                outward_scope = line.removeprefix("- outward_scope: ").strip()
        blocks.append(
            {
                "id": qid,
                "question": question,
                "target": target,
                "status": status,
                "outward_scope": outward_scope,
            }
        )
    return blocks


RESOLVED_STATES = {"answered", "partially_answered", "closed", "dormant"}


def extract_question_state_records(text: str) -> dict[str, dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    parts = re.split(r"(?m)^### (q-\d+)\n", text)
    if len(parts) < 3:
        return records
    for i in range(1, len(parts), 2):
        qid = parts[i].strip()
        body = parts[i + 1].rstrip()
        state = ""
        for line in body.splitlines():
            if line.startswith("- state: "):
                state = line.removeprefix("- state: ").strip()
                break
        records[qid] = {"state": state, "body": body}
    return records


def learned_question_ids(text: str) -> set[str]:
    return set(re.findall(r"(?m)^- question_id:\s*(q-\d+)\s*$", text))


def classify_question(question: dict[str, str]) -> str:
    target = (question.get("target") or "").strip().lower()
    outward_scope = (question.get("outward_scope") or "").strip().lower()
    text = f"{question.get('question', '')} {target}"

    if outward_scope == "source_gate":
        return "future_exploration"
    if outward_scope in {"internal_only", "owner_explicit_only", "proactive_candidate"}:
        return "internal_clarification"

    exploration_markers = [
        "memory-emotion",
        "human-relationship",
        "ai-self-understanding",
        "ai-domain",
        "外探",
        "外部",
        "来源",
        "知识",
        "人工智能",
        "模型",
        "上下文",
        "token",
        "agent",
    ]
    internal_markers = [
        "self",
        "relationship-meaning",
        "自我",
        "关系含义",
        "内部澄清",
    ]

    if any(marker in target or marker in text for marker in exploration_markers):
        return "future_exploration"
    if any(marker in target or marker in text for marker in internal_markers):
        return "internal_clarification"
    return "internal_clarification"


def update_question_pipeline_state(
    path: Path,
    checked_at: str,
    mode: str,
    internal_ids: list[str],
    external_ids: list[str],
    blocked_ids: list[str],
) -> None:
    internal_block = "\n".join(f"- {item}" for item in internal_ids) or "- none"
    external_block = "\n".join(f"- {item}" for item in external_ids) or "- none"
    blocked_block = "\n".join(f"- {item}" for item in blocked_ids) or "- none"
    text = f"""---
title: 问题管线状态
memory_type: question_pipeline_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {checked_at}
last_confirmed_at: {checked_at}
importance_score: 82
impact_score: 82
confidence_score: 100
status: active
tags: [questions, pipeline, state]
---

# 当前问题管线状态

## 最近一次检查
- checked_at: {checked_at}
- mode: {mode}

## 当前分流
- keep_internal: {len(internal_ids)}
- ready_for_exploration: {len(external_ids)}
- blocked_by_self_meaning: {len(blocked_ids)}

## 当前内部澄清优先问题
{internal_block}

## 当前外探候选问题
{external_block}

## 当前被关系 / 自我意义阻挡的问题
{blocked_block}

## 下一步
- 先完成内部澄清，再决定是否让外部知识进入来源判断。
"""
    write_text(path, text)


def update_question_states(
    path: Path,
    checked_at: str,
    questions: list[dict[str, str]],
    classifications: dict[str, str],
) -> None:
    sections: list[str] = []
    for question in questions:
        qid = question["id"]
        mode = classifications[qid]
        if mode == "future_exploration":
            state = "pending_exploration"
            reason = "这类问题已经接近来源闸门，但仍需保持对关系和自我连续性的约束。"
        else:
            state = "clarifying"
            reason = "这类问题仍属于内部澄清，应该先在关系、自我或意义层继续沉淀。"
        sections.append(f"### {qid}\n- state: {state}\n- reason: {reason}\n")

    text = f"""---
title: 问题状态
memory_type: question_states
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: system
created_at: 2026-04-22T00:00:00+08:00
updated_at: {checked_at}
last_confirmed_at: {checked_at}
importance_score: 84
impact_score: 83
confidence_score: 82
status: active
tags: [questions, states]
---

# 当前问题状态

## 可用状态
- open
- clarifying
- pending_exploration
- exploring
- answered
- partially_answered
- dormant
- closed

## 状态说明
- open: 问题刚刚形成，仍未进入稳定分流
- clarifying: 先留在内部继续澄清
- pending_exploration: 已进入未来外探候选，但暂未真正外探
- exploring: 正在进行外部探索或来源判断
- answered: 已得到足够回答
- partially_answered: 部分得到回答，但仍有残留

## 当前问题状态条目
{''.join(sections).rstrip()}
"""
    write_text(path, text)


def update_exploration_queue(
    path: Path,
    checked_at: str,
    questions: list[dict[str, str]],
    classifications: dict[str, str],
) -> None:
    items: list[str] = []
    idx = 1
    for question in questions:
        qid = question["id"]
        if classifications[qid] != "future_exploration":
            continue
        items.append(
            f"## item-{checked_at[:10]}-{idx:03d}\n"
            f"- question_id: {qid}\n"
            f"- status: pending\n"
            f"- exploration_stage: source_gate\n"
            f"- target: {question['target'] or 'general'}\n"
            "- reason: 这个问题已经达到来源闸门前的候选阶段，但还不能越过关系与连续性的限制。\n"
            "- next_action: 先通过来源闸门，再决定是否进入外部知识整合。\n"
        )
        idx += 1

    body = (
        "\n\n".join(items)
        if items
        else "## item-none\n- question_id: none\n- status: hold\n- exploration_stage: internal_only\n- target: none\n- reason: 当前没有需要推进的外探候选。\n- next_action: 继续内部澄清。\n"
    )
    text = f"""---
title: 外探队列
memory_type: exploration_queue
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: system
created_at: 2026-04-22T00:00:00+08:00
updated_at: {checked_at}
last_confirmed_at: {checked_at}
importance_score: 82
impact_score: 80
confidence_score: 81
status: active
tags: [exploration, queue, questions]
---

# 外探队列

{body}
"""
    write_text(path, text)


def update_source_notes(path: Path, checked_at: str, external_ids: list[str]) -> None:
    note_lines = (
        "\n".join(
            f"- {item}: 已进入来源闸门候选，但尚未引入外部结论，等待后续来源判断。"
            for item in external_ids
        )
        if external_ids
        else "- 当前没有进入来源闸门的新候选。"
    )
    text = f"""---
title: 来源笔记
memory_type: source_notes
time_scope: mid_term
subject_ids: [xinyu]
protected: false
source: system
created_at: 2026-04-22T00:00:00+08:00
updated_at: {checked_at}
last_confirmed_at: {checked_at}
importance_score: 70
impact_score: 56
confidence_score: 74
status: active
tags: [knowledge, sources]
---

# 来源笔记

## 当前原则
- 只有通过来源闸门的问题，才允许继续向外部知识层移动。
- 外部知识可以进入知识层，但不能直接越级改写自我或关系。

## 当前候选记录
{note_lines}
"""
    write_text(path, text)


def question_is_resolved(
    question: dict[str, str],
    existing_records: dict[str, dict[str, str]],
    learned_qids: set[str],
) -> bool:
    qid = question["id"]
    active_status = (question.get("status") or "").strip().lower()
    return (
        active_status in RESOLVED_STATES
        or qid in learned_qids
        or existing_records.get(qid, {}).get("state", "") in RESOLVED_STATES
    )


def update_question_states_preserving_resolved(
    path: Path,
    checked_at: str,
    questions: list[dict[str, str]],
    classifications: dict[str, str],
    existing_records: dict[str, dict[str, str]],
    learned_qids: set[str],
) -> None:
    sections: list[str] = []
    for question in questions:
        qid = question["id"]
        if qid in learned_qids:
            sections.append(
                f"### {qid}\n"
                "- state: partially_answered\n"
                "- reason: learner integration already created knowledge-only entries; keep it out of fresh exploration unless reopened.\n"
                f"- updated_at: {checked_at}\n"
            )
            continue
        existing = existing_records.get(qid, {})
        if existing.get("state", "") in RESOLVED_STATES and existing.get("body"):
            sections.append(f"### {qid}\n{existing['body'].rstrip()}\n")
            continue
        mode = classifications[qid]
        if mode == "future_exploration":
            state = "pending_exploration"
            reason = "classified for future source exploration; source gates still protect identity and relationship layers."
        else:
            state = "clarifying"
            reason = "kept for internal clarification before any outward learning."
        sections.append(f"### {qid}\n- state: {state}\n- reason: {reason}\n")

    text = f"""---
title: Question States
memory_type: question_states
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: system
created_at: 2026-04-22T00:00:00+08:00
updated_at: {checked_at}
last_confirmed_at: {checked_at}
importance_score: 84
impact_score: 83
confidence_score: 82
status: active
tags: [questions, states]
---

# Current Question States

## Available States
- open
- clarifying
- pending_exploration
- exploring
- answered
- partially_answered
- dormant
- closed

## Current Question Entries
{''.join(sections).rstrip()}
"""
    write_text(path, text)


def update_source_notes_preserving(path: Path, checked_at: str, external_ids: list[str]) -> None:
    note_lines = (
        "\n".join(f"- {item}: source-gate candidate; reliability must be judged before integration." for item in external_ids)
        if external_ids
        else "- no current source-gate candidates"
    )
    if path.exists():
        text = read_text(path).rstrip()
        text = re.sub(r"(?m)^updated_at:\s*.+$", f"updated_at: {checked_at}", text)
        text = re.sub(r"(?m)^last_confirmed_at:\s*.+$", f"last_confirmed_at: {checked_at}", text)
        section = f"## Current Source-Gate Candidates\n{note_lines}"
        if "## Current Source-Gate Candidates" in text:
            text = re.sub(
                r"(?ms)^## Current Source-Gate Candidates\n.*?(?=^## |\Z)",
                section + "\n\n",
                text,
            ).rstrip()
        else:
            text += "\n\n" + section
        write_text(path, text.rstrip() + "\n")
        return
    update_source_notes(path, checked_at, external_ids)


def run_question_pipeline(
    root: Path,
    checked_at: str | None = None,
    mode: str = "runtime_question_pipeline",
) -> dict[str, object]:
    checked_at = checked_at or datetime.now().astimezone().isoformat()

    questions_text = read_text(root / "memory/context/active_questions.md")
    questions = extract_question_blocks(questions_text)
    existing_records = extract_question_state_records(read_text(root / "memory/context/question_states.md"))
    learned_qids = learned_question_ids(read_text(root / "memory/knowledge/general.md"))
    active_questions = [
        q for q in questions if not question_is_resolved(q, existing_records, learned_qids)
    ]
    classifications = {q["id"]: classify_question(q) for q in active_questions}

    internal_ids = [
        q["id"] for q in active_questions if classifications[q["id"]] == "internal_clarification"
    ]
    external_ids = [
        q["id"] for q in active_questions if classifications[q["id"]] == "future_exploration"
    ]
    blocked_ids = [
        q["id"]
        for q in active_questions
        if (q.get("target") or "").strip().lower() in {"self", "relationship-meaning"}
    ]

    update_question_pipeline_state(
        root / "memory/context/question_pipeline_state.md",
        checked_at,
        mode,
        internal_ids,
        external_ids,
        blocked_ids,
    )
    update_question_states_preserving_resolved(
        root / "memory/context/question_states.md",
        checked_at,
        questions,
        {**{q["id"]: classify_question(q) for q in questions}, **classifications},
        existing_records,
        learned_qids,
    )
    update_exploration_queue(
        root / "memory/context/exploration_queue.md",
        checked_at,
        active_questions,
        classifications,
    )
    update_source_notes_preserving(
        root / "memory/knowledge/source_notes.md",
        checked_at,
        external_ids,
    )

    return {
        "checked_at": checked_at,
        "internal_ids": internal_ids,
        "external_ids": external_ids,
        "blocked_ids": blocked_ids,
    }
