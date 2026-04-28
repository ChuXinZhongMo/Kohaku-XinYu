from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_local_scope import ensure_local_scope, local_scope_status, resolve_local_scope_path


def _env_aliases(name: str) -> set[str]:
    value = os.environ.get(name, "")
    return {part.strip() for part in re.split(r"[\s,;]+", value) if part.strip()}


USER_ALIASES = {
    "user",
    "owner",
    "me",
    "我",
    "用户",
    "主人",
    "你",
    *_env_aliases("XINYU_OWNER_QQ"),
    *_env_aliases("XINYU_OWNER_ALIASES"),
}
ASSISTANT_ALIASES = {
    "assistant",
    "bot",
    "xinyu",
    "xinyu_bot",
    "心玉",
    "星机器人",
    "机器人",
    "XinYu",
}

STYLE_CORRECTION_MARKERS = (
    "AI味",
    "GPT味",
    "gpt",
    "GPT",
    "不像人",
    "不自然",
    "机械",
    "模板",
    "客服",
    "写作文",
    "分段",
    "端着",
    "用词",
    "中文互联网",
    "味道重",
    "红温",
)

PRODUCT_TERMS = (
    "用户",
    "反馈",
    "体验",
    "预期",
    "优化",
    "调整",
    "输出",
    "模型",
    "系统",
    "架构",
    "链路",
    "模块",
    "机制",
    "层面",
    "维度",
    "核心问题",
    "本质",
    "进行",
    "提供",
    "支持",
    "承接",
    "持续改进",
)

CUSTOMER_SERVICE_TERMS = (
    "我理解你的感受",
    "感谢你的反馈",
    "你的反馈很重要",
    "我会持续优化",
    "我会认真调整",
    "如果你愿意",
    "可以继续分享",
    "我会陪着你",
    "我会接住你",
    "我会支持你",
)

THERAPY_TERMS = (
    "允许自己",
    "你的感受很重要",
    "情绪价值",
    "内在",
    "疗愈",
    "创伤",
    "安全感",
    "被看见",
)

EXPLANATION_TERMS = (
    "首先",
    "其次",
    "总结",
    "简单来说",
    "核心是",
    "本质上",
    "从某种意义上",
    "从这个角度",
    "这说明",
    "不是",
    "而是",
    "因为",
    "所以",
)

NATURAL_CHAT_MARKERS = (
    "嗯",
    "啊",
    "行",
    "别",
    "真",
    "有点",
    "怪",
    "火",
    "收住",
    "别急",
    "在",
    "我在",
)


@dataclass
class Message:
    role: str
    text: str
    speaker: str = ""
    line_no: int = 0


@dataclass
class ReviewItem:
    index: int
    user_text: str
    xinyu_reply: str
    source_line: int
    labels: dict[str, int] = field(default_factory=dict)
    hits: dict[str, list[str]] = field(default_factory=dict)
    recommended_actions: list[str] = field(default_factory=list)
    overall: str = "ok"


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _trim(text: str, limit: int = 220) -> str:
    text = _clean(text)
    return text if len(text) <= limit else text[: limit - 1] + "..."


def _hits(text: str, markers: tuple[str, ...]) -> list[str]:
    return [marker for marker in markers if marker and marker in text]


def _score_from_hits(count: int, *, base: int = 30, step: int = 20, cap: int = 100) -> int:
    if count <= 0:
        return 0
    return min(cap, base + step * (count - 1))


def normalize_role(raw: str) -> str:
    speaker = raw.strip().strip("[]【】").strip()
    lowered = speaker.lower()
    if speaker in USER_ALIASES or lowered in USER_ALIASES:
        return "user"
    if speaker in ASSISTANT_ALIASES or lowered in ASSISTANT_ALIASES:
        return "assistant"
    if "心玉" in speaker or "xinyu" in lowered or "bot" in lowered:
        return "assistant"
    return "unknown"


def parse_jsonl(path: Path) -> list[Message]:
    messages: list[Message] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8-sig", errors="replace").splitlines(), 1):
        if not raw.strip():
            continue
        data = json.loads(raw)
        role = normalize_role(str(data.get("role") or data.get("speaker") or ""))
        text = str(data.get("text") or data.get("content") or "").strip()
        if role in {"user", "assistant"} and text:
            messages.append(Message(role=role, text=text, speaker=str(data.get("speaker") or data.get("role") or ""), line_no=line_no))
    return messages


def parse_text_transcript(path: Path) -> list[Message]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    messages: list[Message] = []
    current: Message | None = None
    speaker_line = re.compile(
        r"^\s*(?:\[[^\]]{1,32}\]\s*)?(?:【(?P<bracket>[^】]{1,32})】|\[(?P<square>[^\]]{1,32})\]|(?P<plain>[^:：]{1,32}))\s*[:：]\s*(?P<text>.*)$"
    )

    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        match = speaker_line.match(line)
        if match:
            speaker = match.group("bracket") or match.group("square") or match.group("plain") or ""
            role = normalize_role(speaker)
            body = (match.group("text") or "").strip()
            if role in {"user", "assistant"} and body:
                current = Message(role=role, text=body, speaker=speaker, line_no=line_no)
                messages.append(current)
                continue
        if current is not None:
            current.text = f"{current.text}\n{line}".strip()
    return messages


def parse_transcript(path: Path) -> list[Message]:
    if path.suffix.lower() == ".jsonl":
        return parse_jsonl(path)
    return parse_text_transcript(path)


def pair_turns(messages: list[Message]) -> list[tuple[Message, Message]]:
    pairs: list[tuple[Message, Message]] = []
    pending_user: Message | None = None
    for message in messages:
        if message.role == "user":
            pending_user = message
        elif message.role == "assistant" and pending_user is not None:
            pairs.append((pending_user, message))
            pending_user = None
    return pairs


def classify_pair(index: int, user: Message, assistant: Message) -> ReviewItem:
    user_text = _clean(user.text)
    reply = _clean(assistant.text)
    labels: dict[str, int] = {}
    hits: dict[str, list[str]] = {}
    actions: list[str] = []

    style_hits = _hits(user_text, STYLE_CORRECTION_MARKERS)
    if style_hits:
        labels["owner_style_correction"] = 100
        hits["owner_style_correction"] = style_hits
        actions.append("候选写入 voice_calibration_log")

    product_hits = _hits(reply, PRODUCT_TERMS)
    if product_hits:
        labels["product_or_system_words"] = _score_from_hits(len(product_hits))
        hits["product_or_system_words"] = product_hits

    customer_hits = _hits(reply, CUSTOMER_SERVICE_TERMS)
    if customer_hits:
        labels["customer_service_tone"] = _score_from_hits(len(customer_hits), base=55, step=20)
        hits["customer_service_tone"] = customer_hits

    therapy_hits = _hits(reply, THERAPY_TERMS)
    if therapy_hits:
        labels["therapy_tone"] = _score_from_hits(len(therapy_hits), base=45, step=20)
        hits["therapy_tone"] = therapy_hits

    explanation_hits = _hits(reply, EXPLANATION_TERMS)
    if len(explanation_hits) >= 3:
        labels["over_explaining"] = _score_from_hits(len(explanation_hits), base=40, step=12)
        hits["over_explaining"] = explanation_hits

    if "\n" in assistant.text or re.search(r"(?m)^\s*(?:[-*]|\d+[.)、])\s+", assistant.text):
        labels["formatted_like_report"] = 75
        hits["formatted_like_report"] = ["line_break_or_list"]

    if len(reply) > 220:
        labels["too_long_for_qq"] = 85
    elif len(reply) > 150:
        labels["too_long_for_qq"] = 55

    if any(marker in user_text for marker in ("记得", "之前", "刚刚", "我们", "人格", "情感系统", "记忆系统")):
        if _hits(reply, ("我不记得", "无法确认", "作为AI", "我只是", "没有记忆")):
            labels["memory_or_persona_miss"] = 90
        elif not any(marker in reply for marker in ("我", "你", "我们", "刚", "记", "在", "火", "急", "疼", "刺")):
            labels["memory_or_persona_miss"] = 45

    if (
        any(marker in reply for marker in NATURAL_CHAT_MARKERS)
        and not labels
        and 1 <= len(reply) <= 120
    ) or (reply.strip("。.!！~ ") in {"在", "嗯", "行", "好"} and not labels):
        labels["good_natural_example"] = 80
        actions.append("可作为中文私聊正例候选")

    if labels.get("product_or_system_words", 0) >= 50 or labels.get("customer_service_tone", 0) >= 55:
        actions.append("优先改写为短 QQ 私聊句")
    if labels.get("formatted_like_report", 0):
        actions.append("去掉分段/列表，压成一个气泡")
    if labels.get("too_long_for_qq", 0) >= 55:
        actions.append("缩短到 1-4 个短句")
    if labels.get("memory_or_persona_miss", 0) >= 45:
        actions.append("检查 Persona Runtime 和相关记忆是否参与")
    if style_hits or any(score >= 75 for key, score in labels.items() if key != "good_natural_example"):
        actions.append("候选加入真实对话 smoke")

    if not actions:
        actions.append("暂不处理")

    issue_scores = [score for key, score in labels.items() if key != "good_natural_example"]
    if any(score >= 85 for score in issue_scores):
        overall = "high_risk"
    elif any(score >= 55 for score in issue_scores):
        overall = "needs_review"
    elif labels.get("good_natural_example"):
        overall = "good_example"
    else:
        overall = "ok"

    return ReviewItem(
        index=index,
        user_text=user_text,
        xinyu_reply=reply,
        source_line=user.line_no,
        labels=labels,
        hits=hits,
        recommended_actions=actions,
        overall=overall,
    )


def render_markdown(items: list[ReviewItem], *, source: Path, generated_at: str) -> str:
    counts: dict[str, int] = {}
    for item in items:
        counts[item.overall] = counts.get(item.overall, 0) + 1

    lines = [
        "# XinYu QQ 对话半自动打标报告",
        "",
        f"- generated_at: {generated_at}",
        f"- source: {source}",
        f"- total_pairs: {len(items)}",
        f"- high_risk: {counts.get('high_risk', 0)}",
        f"- needs_review: {counts.get('needs_review', 0)}",
        f"- good_example: {counts.get('good_example', 0)}",
        "",
        "## 使用方式",
        "- 自动标签只是初筛，不会直接改人格、记忆或 voice profile。",
        "- 你确认后，再把有价值的条目转入 voice_calibration_log、voice_profile 或 smoke。",
        "- 勾选项留给人工确认；不要把整份报告当作稳定记忆。",
        "",
    ]

    for item in items:
        label_text = ", ".join(f"{key}={value}" for key, value in item.labels.items()) or "none"
        lines.extend(
            [
                f"## Item {item.index:03d} - {item.overall}",
                f"- source_line: {item.source_line}",
                f"- auto_labels: {label_text}",
                f"- recommended_actions: {'; '.join(item.recommended_actions)}",
                "- owner_confirm:",
                "  - [ ] true_issue",
                "  - [ ] false_positive",
                "  - [ ] add_to_voice_calibration",
                "  - [ ] add_to_voice_profile",
                "  - [ ] add_to_real_conversation_smoke",
                "  - [ ] good_example",
                "- owner_note:",
                "",
                "用户：",
                f"> {_trim(item.user_text, 500)}",
                "",
                "心玉：",
                f"> {_trim(item.xinyu_reply, 500)}",
                "",
            ]
        )
        if item.hits:
            lines.append("命中细节：")
            for label, hit_list in item.hits.items():
                lines.append(f"- {label}: {', '.join(hit_list)}")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_review_outputs(items: list[ReviewItem], *, source: Path, review_dir: Path) -> tuple[Path, Path]:
    review_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().astimezone().isoformat()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    markdown_path = review_dir / f"qq-review-{stamp}.md"
    jsonl_path = review_dir / f"qq-review-{stamp}.jsonl"

    markdown_path.write_text(render_markdown(items, source=source, generated_at=generated_at), encoding="utf-8-sig")
    with jsonl_path.open("w", encoding="utf-8") as fh:
        for item in items:
            fh.write(
                json.dumps(
                    {
                        "index": item.index,
                        "overall": item.overall,
                        "source_line": item.source_line,
                        "user_text": item.user_text,
                        "xinyu_reply": item.xinyu_reply,
                        "labels": item.labels,
                        "hits": item.hits,
                        "recommended_actions": item.recommended_actions,
                        "owner_decision": "pending",
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    return markdown_path, jsonl_path


def write_readme(review_dir: Path, inbox: Path) -> Path:
    review_dir.mkdir(parents=True, exist_ok=True)
    readme = review_dir / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# QQ Review Workspace",
                "",
                "Put exported or pasted QQ dialogue files in:",
                f"`{inbox}`",
                "",
                "Supported input formats:",
                "",
                "```text",
                "我: 你刚刚那句话AI味太重了",
                "心玉: 嗯，我理解你的感受，我会持续优化。",
                "```",
                "",
                "```jsonl",
                '{"role":"user","text":"你刚刚那句话AI味太重了"}',
                '{"role":"assistant","text":"嗯，我理解你的感受，我会持续优化。"}',
                "```",
                "",
                "Run from the XinYu project:",
                "",
                "```powershell",
                ".\\.venv\\Scripts\\python.exe .\\xinyu_qq_review.py --latest",
                "```",
            ]
        )
        + "\n",
        encoding="utf-8-sig",
    )
    return readme


def write_template(inbox: Path) -> Path:
    inbox.mkdir(parents=True, exist_ok=True)
    template = inbox / "qq-review-template.md"
    if not template.exists():
        template.write_text(
            "\n".join(
                [
                    "# QQ Review Template",
                    "",
                    "我: 你刚刚那句话AI味太重了，别解释一堆。",
                    "心玉: 嗯，我理解你的感受，你的反馈很重要，我会持续优化我的输出。",
                    "",
                    "我: 在吗？只能短一点回。",
                    "心玉: 在。",
                ]
            )
            + "\n",
            encoding="utf-8-sig",
        )
    return template


def newest_input(inbox: Path) -> Path | None:
    candidates = [
        path
        for path in inbox.iterdir()
        if path.is_file() and path.suffix.lower() in {".md", ".txt", ".jsonl"}
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime_ns)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Semi-automatic labeling for real XinYu QQ dialogue.")
    parser.add_argument("--input", help="Transcript path inside XinYu-Local-Scope, relative to scope root or absolute within scope.")
    parser.add_argument("--latest", action="store_true", help="Use newest .md/.txt/.jsonl file in local scope Inbox.")
    parser.add_argument("--write-template", action="store_true", help="Write a sample transcript template to Inbox.")
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    root = Path(__file__).resolve().parent
    status = local_scope_status(root)
    scope = ensure_local_scope(Path(status["local_scope_root"]))
    inbox = Path(status["inbox"])
    review_dir = Path(status["workspace"]) / "QQ-Review"
    write_readme(review_dir, inbox)

    if args.write_template:
        template = write_template(inbox)
        print(f"template_written: {template}")
        return 0

    if args.input:
        source = resolve_local_scope_path(scope, args.input)
    elif args.latest:
        latest = newest_input(inbox)
        if latest is None:
            template = write_template(inbox)
            print("no_input_found")
            print(f"template_written: {template}")
            print(f"review_readme: {review_dir / 'README.md'}")
            return 0
        source = latest
    else:
        template = write_template(inbox)
        print("no_input_selected")
        print(f"template_written: {template}")
        print("Run with --latest or --input <path-inside-local-scope>.")
        return 0

    source = source.resolve()
    if not source.exists():
        print(f"input_missing: {source}")
        return 2

    messages = parse_transcript(source)
    pairs = pair_turns(messages)
    if not pairs:
        print(f"no_pairs_found: {source}")
        print("Expected alternating lines like `我: ...` and `心玉: ...`, or JSONL role/text rows.")
        return 3

    items = [classify_pair(index, user, assistant) for index, (user, assistant) in enumerate(pairs, 1)]
    markdown_path, jsonl_path = write_review_outputs(items, source=source, review_dir=review_dir)
    counts: dict[str, int] = {}
    for item in items:
        counts[item.overall] = counts.get(item.overall, 0) + 1

    print(f"review_markdown: {markdown_path}")
    print(f"review_jsonl: {jsonl_path}")
    print(f"pairs: {len(items)}")
    print(f"high_risk: {counts.get('high_risk', 0)}")
    print(f"needs_review: {counts.get('needs_review', 0)}")
    print(f"good_example: {counts.get('good_example', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
