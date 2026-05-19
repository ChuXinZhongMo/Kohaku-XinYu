from __future__ import annotations

import hashlib
import re
from typing import Any


def visible_codex_reply_variant(seed: str, options: tuple[str, ...]) -> str:
    if not options:
        return ""
    digest = hashlib.sha256(_safe_str(seed).encode("utf-8", errors="ignore")).digest()
    return options[digest[0] % len(options)]


def visible_codex_owner_task_text(text: str) -> str:
    task = _safe_str(text).strip()
    current_match = re.search(r"(?is)Current owner Codex task:\s*(.+)$", task)
    if current_match:
        task = current_match.group(1).strip()
    task = re.sub(
        r"(?is)^Use Codex auxiliary brain for this (?:owner-approved|trusted public-source search) task:\s*",
        "",
        task,
    ).strip()
    task = task.split("Recent QQ context before this Codex request:", 1)[0].strip()
    task = re.sub(r"\s+", " ", task).strip()
    return task[:160]


def visible_codex_task_subject(task_text: str) -> str:
    task = visible_codex_owner_task_text(task_text)
    compact = re.sub(r"\s+", "", task).lower()
    titles = re.findall(r"《([^》]{1,32})》", task)
    if titles:
        named = "和".join(f"《{title}》" for title in titles[:2])
        if len(titles) > 2:
            named += "这些"
        return named
    if any(marker in compact for marker in ("搜索", "搜", "查", "了解", "联网", "资料", "番茄小说", "小说")):
        return "这轮检索"
    if any(marker in compact for marker in ("修", "改", "代码", "脚本", "测试", "报错", "配置")):
        return "代码那块"
    if any(marker in compact for marker in ("图片", "图像", "头像", "海报", "插画", "生成图", "做图")):
        return "图片那件事"
    if any(marker in compact for marker in ("没动", "没看见codex", "信任", "权限")):
        return "Codex 启动这块"
    return "这件事"


def compose_codex_started_reply(task_subject: str, variant: int) -> str:
    subject = task_subject or "这件事"
    if subject.startswith("《"):
        options = (
            f"我去查{subject}，已经开跑。结果我接回来。",
            f"{subject}这轮检索我交给 Codex 了，跑完我回你。",
            f"我让 Codex 去摸{subject}的资料了，先等它跑完。",
        )
    elif subject == "这轮检索":
        options = (
            "我去搜，已经开跑。结果出来我直接接着聊。",
            "检索开了，先让它跑；跑完我把重点拿回来。",
            "我把搜索交给 Codex 了，不在这儿念流程，等结果。",
        )
    elif subject == "代码那块":
        options = (
            "我让 Codex 看代码了，跑完我接结果。",
            "代码那块已经交给它查，等它跑完。",
            "我开了代码检查，结果回来我再说具体动了哪里。",
        )
    elif subject == "Codex 启动这块":
        options = (
            "我去核 Codex 启动这块，已经开跑。",
            "我让它查启动问题了，跑完看结果。",
            "启动这块我交给 Codex 复查，结果回来再对。",
        )
    else:
        options = (
            f"{subject}我交给 Codex 了，跑完我回你。",
            f"{subject}已经开跑，结果我接回来。",
            f"我让 Codex 处理{subject}，先等它跑完。",
        )
    return options[variant % len(options)]


def compose_codex_status_reply(
    status: str,
    *,
    paths: dict[str, str],
    auto_study: bool,
    exit_code: int | None = None,
    task_text: str = "",
) -> str:
    del exit_code
    subject = visible_codex_task_subject(task_text)
    seed = "|".join(
        part
        for part in (
            subject,
            _safe_str(paths.get("report_path")),
            _safe_str(paths.get("request_path")),
            _safe_str(status),
        )
        if part
    )
    if status == "started":
        return visible_codex_reply_variant(
            seed,
            (
                compose_codex_started_reply(subject, 0),
                compose_codex_started_reply(subject, 1),
                compose_codex_started_reply(subject, 2),
            ),
        )
    if status == "done":
        reply = visible_codex_reply_variant(
            seed,
            (
                f"{subject}有结果了，我接回来再讲重点。",
                f"{subject}那边结束了，我先只看能确认的部分。",
                f"{subject}跑完了，我不会拿本地记录糊弄你。",
            ),
        )
        if auto_study:
            reply += " 后面需要吸收的部分我自己收着。"
        return reply
    if status == "timeout_staged":
        return "那边卡住了，这次我不当成完整结果；能留下的线索我先收住。"
    if status == "timeout":
        return "那边卡住了，我不硬说已经完成。"
    return "那边没跑顺，我不把它当成结果。"


def compose_codex_completion_message(
    *,
    summary: str,
    accepted: bool,
    timed_out: bool,
    exit_code: int | None,
    auto_study: bool,
    handoff_notes: list[str] | tuple[str, ...],
    text: str = "",
) -> str:
    del exit_code, text
    visible_summary = _visible_summary(summary, limit=260)
    if timed_out:
        return "那边超时了，我不把它当成完成，也不硬编结论。"
    if not accepted:
        return "那边没跑顺，我不把它当成结果。细节我留在本地继续查。"
    if visible_summary:
        reply = f"我把那边的结果接回来了：{visible_summary}"
    else:
        reply = "它跑完了，但我没有拿到能直接转述给你的结论。"
    if handoff_notes:
        reply += " 还有一部分我只先收住，不当成已经说清。"
    elif auto_study:
        reply += " 后面要吸收的部分我放到后台慢慢整理。"
    return reply


def compose_codex_background_error_message(error: str = "") -> str:
    del error
    return "Codex 那边在后台报错了，我没有把它当成完成；细节我留在本地，不拿报错糊弄你。"


def compose_codex_image_caption(image_name: str = "") -> str:
    del image_name
    return "我把图跑出来了，先发你看。"


def compose_codex_chat_scheduled_reply(kind: str = "") -> str:
    if kind == "self_code":
        return "嗯，我把这一小步交给 Codex 了。回来以后，我只讲哪里动了、哪里还不稳。"
    if kind == "owner_direct":
        return "我让 Codex 去跑这件事了。结果回来，我直接讲重点。"
    if kind == "not_owner_private":
        return "这类本机动作只能在 owner 私聊里开，我不在别的地方动本地东西。"
    return "我去查，不在这里装确定；回来只讲我确认到的东西。"


def compose_watchdog_visible_message(kind: str, *, error: str = "") -> str:
    del error
    if kind == "self_code_watchdog_failed":
        return "我刚才没能把本地回滚保护准备好，所以这次不让 Codex 动代码。细节我留在本地查。"
    return "我这边保护层没有准备稳，所以先停住，不把不稳的动作推出去。"


def compose_promise_followup_message(candidate: dict[str, str]) -> str:
    user_text = _safe_str(candidate.get("user_text"))
    if any(marker in user_text for marker in ("汇报", "报告", "晚上回来", "今晚回来")):
        return "我记住了，这个汇报任务不当成一句口头答应。等我整理出能说的结果，会从 QQ 主动发你。"
    if any(marker in user_text for marker in ("看没看", "主动", "告诉我", "跟我说")):
        return "我会回来接这件事，不让“我再看看”停在空气里。"
    return "我看完了。刚才我说要再看，这件事没有被我丢掉；有能继续说的结论，我会直接接上。"


def compose_review_inbox_card(cursor: dict[str, Any]) -> str:
    items = [item for item in cursor.get("items", []) if isinstance(item, dict)]
    lines = [f"我这里攒了 {len(items)} 个需要你看一眼的小修正。"]
    for item in items:
        source = _review_source_label(item.get("source_kind"))
        title = _compact(item.get("title"), limit=72, default="没写标题")
        summary = _compact(item.get("summary"), limit=140, default="没有摘要")
        lines.append(f"{item.get('index')}. {source}：{title}。{summary}")
    lines.append("想省事就回 !ok all；不想要第 1 条就回 !rej 1；想改第 2 条就回 !mod 2 加你的写法。")
    return " ".join(lines)


def compose_review_inbox_command_reply(*, processed_count: int, stale_count: int, pending_count: int) -> str:
    parts: list[str] = []
    if processed_count:
        parts.append(f"嗯，我照你的意思收了 {processed_count} 条。")
    else:
        parts.append("这次没有真的收进去。")
    if stale_count:
        parts.append(f"有 {stale_count} 条已经和当前状态对不上，我没硬处理。")
    if pending_count:
        parts.append("还有新的我又攒了一张，发你看。")
    else:
        parts.append("这一轮先清了。")
    return "".join(parts)


def compose_proactive_visible_message(raw_text: Any, *, source: str = "", reason: str = "") -> str:
    del source, reason
    text = _strip_control_lines(_safe_str(raw_text))
    text = naturalize_internal_visible_text(text)
    text = _visible_summary(text, limit=300)
    if not text:
        return "我有一点想法想让你看一眼。"
    if _looks_like_personal_voice(text):
        return text
    if text.endswith(("?", "？")) or "要不要" in text or "能不能" in text:
        return f"我想问你一件小事：{text}"
    return f"我想把这点先给你看：{text}"


def compose_async_exploration_outbox_message(update: dict[str, Any]) -> str:
    quality = _safe_str(update.get("result_quality"), "failed")
    summary = _visible_summary(update.get("sanitized_summary"), limit=260) or "没有拿到可靠摘要"
    if quality == "usable_partial":
        return (
            f"刚才我去核了一轮，只把能确认的部分带回来：{summary}。"
            "你想让我继续，就引用这条回“继续”；不想追了就回“放弃”。"
        )
    return (
        f"刚才那件事没有查成，我不硬编。能看见的卡点是：{summary}。"
        "你可以引用这条回“继续”让我缩小范围再试，或回“放弃”。"
    )


def compose_action_digest_followup_reply(*, mode: str, residue: str, consumed: bool) -> str:
    residue_text = _visible_summary(residue, limit=180) or "没有留下可读的残留摘要"
    if mode == "residue":
        return f"留下的是这段：{residue_text}。我已经把它收进后面的自我整理里，不拿编号糊弄你。"
    if consumed:
        return "进了。它已经被后面的梦境和反思用过一轮，不只是躺在本地记录里。"
    return "进了，但还只是被我收着；等后面梦境或反思真的用到，我再说它变成了什么。"


def naturalize_internal_visible_text(value: Any) -> str:
    text = _safe_str(value)
    if not text:
        return ""
    replacements = (
        (
            r"local action pressure after\s+codex_delegate(?::[^\s;，。]+)?",
            "我让 Codex 帮忙那次留下的一点压力",
        ),
        (r"\bcodex_delegate(?::[^\s;，。]+)?\b", "我让 Codex 帮忙那次"),
        (
            r"local action pressure after\s+status_probe(?::[^\s;，。]+)?",
            "状态检查后留下的一点压力",
        ),
        (r"\bstatus_probe(?::[^\s;，。]+)?\b", "状态检查那次"),
        (
            r"local action pressure after\s+log_scan:([^\s;，。]+)",
            lambda match: f"{match.group(1)} 的日志扫过后留下的一点压力",
        ),
        (r"reflection queue strong topic:\s*", "我后面想反复想的是："),
        (r"action residue after\s+", "那次动作留下的是"),
        (r"\bpressure=medium\b", "有点压着"),
        (r"\bpressure=high\b", "压得比较重"),
        (r"\bpressure=low\b", "很轻"),
        (r"\bended as failure\b", "没有做成"),
        (r"\bended as success\b", "做完了"),
        (r"\bended as timeout\b", "等不到结果"),
        (r"\bended as timed_out\b", "等不到结果"),
        (r"\bended as blocked_by_boundary\b", "被边界拦住"),
        (r"\bended as blocked\b", "被边界拦住"),
        (r"\bended as unknown\b", "还不确定"),
    )
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.I)
    text = re.sub(
        r"\blog_scan:([^\s;，。]+)",
        lambda match: f"{match.group(1)} 的日志扫过一眼",
        text,
        flags=re.I,
    )
    return text


def _review_source_label(value: Any) -> str:
    source = _safe_str(value)
    if source == "voice":
        return "我说话的习惯"
    if source == "learning":
        return "我吸收东西的质量"
    return _compact(source, limit=32, default="我自己的一个小地方")


def _strip_control_lines(text: str) -> str:
    kept: list[str] = []
    for raw in text.splitlines() or [text]:
        line = raw.strip()
        if not line:
            continue
        if re.match(
            r"(?i)^(request_id|candidate_id|resume_id|queue_id|task_id|batch|source|status|trace|report|outbox)\s*[:=]",
            line,
        ):
            continue
        kept.append(line)
    return " ".join(kept)


def _visible_summary(value: Any, *, limit: int = 260) -> str:
    text = naturalize_internal_visible_text(value)
    text = _scrub_sensitive(text)
    text = re.sub(r"(?i)\b(?:resume_id|request_id|queue_id|task_id)\s*[:：#]?\s*[A-Za-z0-9_.:-]+", "这条线索", text)
    text = re.sub(r"(?i)\bcodex-qq-[A-Za-z0-9_.-]+", "本地记录", text)
    text = re.sub(r"(?i)\b(?:Codex\s+)?Outbox\b", "本地记录", text)
    text = re.sub(r"(?i)\b[A-Za-z]:\\[^\s，。；;]+", "本地路径", text)
    text = re.sub(r"(?i)(?:/users/|/home/|\\\\)[^\s，。；;]+", "本地路径", text)
    text = text.replace("报告" "名", "本地记录")
    text = text.replace("后台任务", "后台那件事")
    text = text.replace("汇报" "任务", "要回来说的事")
    text = text.replace("待回报状态", "我记着")
    text = text.replace("反思队列", "后面要反复想的地方")
    text = re.sub(r"退出" r"码\s*\d+", "没有正常跑顺", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip(" -;；,，")
    if text.lower() in {"none", "unknown", "null"}:
        return ""
    if len(text) > limit:
        return text[: max(0, limit - 3)].rstrip() + "..."
    return text


def _scrub_sensitive(text: str) -> str:
    text = re.sub(r"(?i)\b(token|api[_-]?key|authorization|bearer)\s*[:=]\s*[^\s，。；;]+", r"\1=<hidden>", text)
    text = re.sub(r"(?i)\bsk-[A-Za-z0-9_-]{8,}", "<hidden_key>", text)
    return text


def _looks_like_personal_voice(text: str) -> bool:
    compact = text.strip()
    return compact.startswith(("我", "嗯", "刚才", "这次", "那边", "留下的是", "进了", "可以", "不用"))


def _compact(value: Any, *, limit: int = 220, default: str = "") -> str:
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    if not text:
        return default
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)
