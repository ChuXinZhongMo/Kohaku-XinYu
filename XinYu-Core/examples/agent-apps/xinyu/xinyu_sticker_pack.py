from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from stores.sticker_send_state import (
    STICKER_SEND_STATE_REL,
    read_sticker_send_state,
    sticker_send_state_path,
    write_sticker_send_state,
)
from xinyu_local_scope import default_local_scope_root, ensure_local_scope
from xinyu_qq_outbox import enqueue_qq_outbox_image


SUPPORTED_STICKER_SUFFIXES = frozenset({".bmp", ".gif", ".jfif", ".jpeg", ".jpg", ".png", ".webp"})
MANIFEST_NAMES = ("manifest.json", "sticker_manifest.json", "memes_data.json", "manifest.generated.json")
STICKER_LIBRARY_DIRS_ENV = "XINYU_STICKER_LIBRARY_DIRS"
DISABLE_SHARED_ASSET_LIBRARY_ENV = "XINYU_STICKER_DISABLE_SHARED_ASSET_LIBRARY"
AUTO_MIN_SCORE_ENV = "XINYU_STICKER_AUTO_MIN_SCORE"
AUTO_RATE_ENV = "XINYU_STICKER_AUTO_RATE"
EXPLICIT_ONLY_ENV = "XINYU_STICKER_EXPLICIT_ONLY"
AUTO_COOLDOWN_MINUTES_ENV = "XINYU_STICKER_AUTO_COOLDOWN_MINUTES"
SEND_STATE_FILE = STICKER_SEND_STATE_REL.name
REFERENCE_DIR_NAMES = frozenset({".references", "参考图"})
REQUEST_MARKERS = (
    "发表情",
    "发表情包",
    "发个表情",
    "发张表情",
    "来个表情",
    "来张表情",
    "用表情",
    "甩个表情",
    "整点表情",
    "sticker",
    "meme",
)
NEGATIVE_MARKERS = ("别发", "不要发", "不用发", "先别发")
QUESTION_ONLY_MARKERS = ("怎么", "如何", "为什么", "是什么", "什么意思")
AUTO_BLOCK_MARKERS = (
    "急",
    "马上",
    "赶紧",
    "严肃",
    "别闹",
    "报错",
    "错误",
    "异常",
    "失败",
    "崩",
    "炸了",
    "日志",
    "构建",
    "测试失败",
    "status",
    "/status",
)
MOOD_MARKERS: dict[str, tuple[str, ...]] = {
    "happy": ("开心", "高兴", "哈哈", "笑", "好耶", "乐", "可爱", "喜欢"),
    "laugh": ("哈哈哈", "笑死", "绷不住", "乐死", "乐了", "蚌埠住"),
    "cheer": ("好耶", "太好了", "赢", "胜利", "成功", "加油", "冲", "庆祝"),
    "tease": ("嘲笑", "调侃", "乐子", "阴阳怪气", "坏笑", "绷不住", "笑死"),
    "ok": ("收到", "懂了", "明白", "可以", "ok", "OK", "好", "嗯"),
    "thinking": ("想想", "思考", "等等", "疑惑", "？", "?", "诡异", "奇怪"),
    "confused": ("啊？", "啊?", "问号", "懵", "不对劲", "哪里不对"),
    "deadpan": ("无语", "沉默", "面无表情", "冷漠", "看着", "呆住"),
    "awkward": ("尴尬", "流汗", "汗", "不好意思", "僵住"),
    "comfort": ("抱抱", "安慰", "难过", "委屈", "累", "困"),
    "tired": ("累", "困", "疲惫", "不想动", "不想展开", "躺"),
    "sleepy": ("困", "睡", "睡觉", "晚安", "打哈欠", "犯困"),
    "work": ("干活", "开工", "测试", "修", "代码", "codex", "Codex"),
    "annoyed": ("烦", "嫌弃", "不爽", "哼", "受不了", "别闹"),
    "angry": ("生气", "怒", "气死", "火大", "骂", "发火"),
    "refuse": ("拒绝", "不要", "不行", "不可以", "我不要", "达咩"),
    "panic": ("慌", "救命", "糟了", "完了", "害怕", "吓"),
    "plead": ("求求", "拜托", "可怜", "哭哭", "求你"),
    "shy": ("害羞", "不好意思", "脸红", "羞", "别看"),
    "silent": ("沉默", "安静", "先不说", "不说话", "看着"),
    "proud": ("得意", "夸我", "做到了", "厉害", "漂亮", "完成"),
    "surprised": ("震惊", "惊了", "意外", "啊", "什么", "真的假的"),
    "sad": ("难过", "委屈", "低落", "哭", "伤心", "呜"),
    "unclear": ("待确认", "不确定", "未确认", "看不懂"),
}
MOOD_ALIASES: dict[str, tuple[str, ...]] = {
    "happy": ("happy", "laugh", "joy", "celebrate", "开心", "高兴", "笑", "乐", "好耶"),
    "laugh": ("laugh", "lol", "haha", "哈哈", "笑死", "绷不住", "乐"),
    "cheer": ("cheer", "yay", "celebrate", "win", "success", "好耶", "庆祝", "加油"),
    "tease": ("tease", "mock", "smirk", "smug", "嘲笑", "调侃", "坏笑", "乐子"),
    "ok": ("ok", "yes", "收到", "明白", "懂了", "可以"),
    "thinking": ("thinking", "think", "confused", "疑惑", "思考", "问号", "想想"),
    "confused": ("confused", "question", "what", "疑惑", "问号", "懵", "啊"),
    "deadpan": ("deadpan", "blank", "stare", "speechless", "无语", "冷漠", "面无表情"),
    "awkward": ("awkward", "sweat", "nervous", "embarrassed", "尴尬", "流汗", "汗"),
    "comfort": ("comfort", "hug", "sad", "安慰", "抱抱", "难过", "委屈", "累"),
    "tired": ("tired", "sleepy", "lazy", "累", "困", "疲惫", "躺"),
    "sleepy": ("sleepy", "drowsy", "sleep", "bed", "困", "睡", "晚安"),
    "work": ("work", "code", "coding", "干活", "开工", "代码", "修", "检查"),
    "annoyed": ("annoyed", "angry", "ugh", "烦", "嫌弃", "不爽", "哼"),
    "angry": ("angry", "mad", "rage", "scold", "生气", "怒", "气死"),
    "refuse": ("refuse", "reject", "no", "nope", "拒绝", "不要", "不行"),
    "panic": ("panic", "scared", "alarm", "help", "慌", "救命", "糟了"),
    "plead": ("plead", "beg", "please", "puppy eyes", "求求", "拜托", "可怜"),
    "shy": ("shy", "blush", "害羞", "不好意思", "脸红"),
    "silent": ("silent", "quiet", "沉默", "安静", "不说话"),
    "proud": ("proud", "done", "win", "得意", "做到了", "夸我"),
    "surprised": ("surprised", "shock", "wow", "震惊", "惊了", "意外"),
    "sad": ("sad", "cry", "down", "难过", "委屈", "低落", "哭"),
    "cute": ("cute", "xinyu", "可爱", "贴贴", "心玉"),
    "unclear": ("unclear", "unknown", "待确认", "待看", "不确定", "未确认"),
}
MOOD_TEXT = {
    "happy": "好耶",
    "laugh": "哈哈",
    "cheer": "好耶",
    "tease": "欸嘿",
    "ok": "收到",
    "thinking": "嗯？",
    "confused": "啊？",
    "deadpan": "……",
    "awkward": "汗",
    "comfort": "抱抱",
    "tired": "累了",
    "sleepy": "困了",
    "work": "开工",
    "annoyed": "哼",
    "angry": "生气",
    "refuse": "不要",
    "panic": "救命",
    "plead": "拜托",
    "shy": "别看",
    "silent": "……",
    "proud": "做到了",
    "surprised": "啊？",
    "sad": "呜",
    "cute": "心玉在",
    "unclear": "待看",
}
MOOD_MEANINGS: dict[str, str] = {
    "happy": "开心、好耶、轻松地回应愉快场景",
    "laugh": "大笑、绷不住、跟着一起乐",
    "cheer": "庆祝、鼓劲、事情推进顺利时给一点兴奋感",
    "tease": "调侃、坏笑、轻轻嘲一下但不恶意",
    "ok": "收到、明白、确认可以继续",
    "thinking": "思考、暂停一下、还在判断",
    "confused": "疑惑、问号、觉得哪里不太对",
    "deadpan": "无语、面无表情、冷静看着场面发展",
    "awkward": "尴尬、流汗、卡住但还在应对",
    "comfort": "安慰、抱抱、陪着但不说教",
    "tired": "疲惫、困了、不太想展开",
    "sleepy": "犯困、想睡、低能量地回应",
    "work": "开工、检查、写代码、处理任务",
    "annoyed": "轻微嫌弃、不爽、被烦到但不失控",
    "angry": "生气、发火、强烈不满但仍保持边界",
    "refuse": "拒绝、不要、不接受这个提议",
    "panic": "慌张、救命、突然出事或被吓到",
    "plead": "拜托、求求、可怜兮兮地请求",
    "shy": "害羞、不好意思、轻微躲开",
    "cute": "可爱、日常贴近、轻松陪伴",
    "silent": "沉默、先不说、安静看着",
    "proud": "得意、做到了、想被夸一下",
    "surprised": "惊讶、震惊、没想到",
    "sad": "难过、委屈、低落",
    "unclear": "语义还不清楚，需要 owner 再看一眼",
}
MOOD_LABELS: dict[str, str] = {
    "happy": "开心",
    "laugh": "大笑",
    "cheer": "庆祝",
    "tease": "调侃",
    "ok": "收到",
    "thinking": "思考",
    "confused": "疑惑",
    "deadpan": "无语",
    "awkward": "尴尬",
    "comfort": "安慰",
    "tired": "疲惫",
    "sleepy": "犯困",
    "work": "工作",
    "annoyed": "嫌弃",
    "angry": "生气",
    "refuse": "拒绝",
    "panic": "慌张",
    "plead": "拜托",
    "shy": "害羞",
    "cute": "可爱",
    "silent": "沉默",
    "proud": "得意",
    "surprised": "震惊",
    "sad": "难过",
    "unclear": "待确认",
}
MOOD_FOLDER_ALIASES: dict[str, str] = {
    "不理解": "confused",
    "卖萌": "cute",
    "喜欢": "happy",
    "嘲讽": "tease",
    "微笑": "happy",
    "恍然大悟": "ok",
    "惊恐": "panic",
    "憋笑": "laugh",
    "抱歉": "awkward",
    "放弃": "tired",
    "无奈": "deadpan",
    "无聊": "tired",
    "称赞": "cheer",
    "难受": "sad",
}
RELATED_MOODS: dict[str, tuple[str, ...]] = {
    "happy": ("cheer", "cute", "laugh"),
    "laugh": ("tease", "happy", "cheer"),
    "cheer": ("happy", "proud", "laugh"),
    "tease": ("laugh", "annoyed", "proud"),
    "thinking": ("confused", "deadpan", "awkward"),
    "confused": ("thinking", "deadpan", "awkward", "panic"),
    "deadpan": ("silent", "confused", "annoyed", "awkward"),
    "awkward": ("shy", "confused", "panic"),
    "comfort": ("sad", "plead", "tired"),
    "tired": ("sleepy", "deadpan"),
    "sleepy": ("tired", "silent"),
    "annoyed": ("angry", "refuse", "deadpan", "tease"),
    "angry": ("annoyed", "refuse"),
    "refuse": ("annoyed", "angry", "deadpan"),
    "panic": ("surprised", "confused", "awkward"),
    "plead": ("sad", "comfort", "shy"),
    "shy": ("awkward", "plead", "cute"),
    "silent": ("deadpan", "tired"),
    "proud": ("cheer", "tease", "happy"),
    "surprised": ("panic", "confused"),
    "sad": ("comfort", "plead", "tired"),
    "cute": ("happy", "shy", "plead"),
}
PALETTES = (
    ("#fff7fb", "#ff8abb", "#6b3150"),
    ("#f3fbff", "#5fb7e5", "#1f4661"),
    ("#fff9e8", "#f0b84a", "#5f4219"),
    ("#f4fff4", "#61c47a", "#245738"),
    ("#f7f2ff", "#9d7be8", "#3f2c69"),
)


@dataclass(frozen=True)
class StickerDecision:
    should_send: bool
    mood: str
    notes: list[str]
    mode: str = "skip"
    score: int = 0
    keywords: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StickerCandidate:
    path: Path
    mood: str
    keywords: tuple[str, ...] = ()
    meaning: str = ""
    weight: int = 1
    auto_send: bool = True


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _compact(value: Any) -> str:
    return re.sub(r"\s+", "", _safe_str(value)).strip()


def _digest(value: str, limit: int = 16) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:limit]


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    if value is None:
        return default
    return bool(value)


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = re.split(r"[,，;；\s]+", value)
        return [part.strip() for part in parts if part.strip()]
    if isinstance(value, list):
        return [_safe_str(item).strip() for item in value if _safe_str(item).strip()]
    return [_safe_str(value).strip()] if _safe_str(value).strip() else []


def canonical_mood(value: Any, default: str = "cute") -> str:
    raw = _safe_str(value).strip()
    if not raw:
        return default
    lowered = raw.lower()
    if lowered in MOOD_MEANINGS:
        return lowered
    if raw in MOOD_FOLDER_ALIASES:
        return MOOD_FOLDER_ALIASES[raw]
    for mood, label in MOOD_LABELS.items():
        if raw == label or lowered == label.lower():
            return mood
    for mood, aliases in MOOD_ALIASES.items():
        if any(lowered == alias.lower() for alias in aliases):
            return mood
    return default


def sticker_mood_label(value: Any) -> str:
    mood = canonical_mood(value, default=_safe_str(value).strip())
    return MOOD_LABELS.get(mood, _safe_str(value).strip() or MOOD_LABELS["cute"])


def mood_dir_name(value: Any) -> str:
    return sticker_mood_label(value)


def _auto_enabled() -> bool:
    return _as_bool(os.environ.get("XINYU_STICKER_AUTO_ENABLED"), default=True)


def _auto_min_score() -> int:
    try:
        return max(1, int(os.environ.get(AUTO_MIN_SCORE_ENV, "3")))
    except ValueError:
        return 3


def _auto_rate() -> int:
    try:
        return min(100, max(0, int(os.environ.get(AUTO_RATE_ENV, "38"))))
    except ValueError:
        return 38


def _explicit_only() -> bool:
    return _as_bool(os.environ.get(EXPLICIT_ONLY_ENV), default=False)


def _auto_cooldown_minutes() -> int:
    try:
        return max(0, int(os.environ.get(AUTO_COOLDOWN_MINUTES_ENV, "5")))
    except ValueError:
        return 5


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in markers)


def _infer_mood(text: str) -> tuple[str, int, list[str]]:
    combined = text.lower()
    best_mood = "cute"
    best_score = 0
    best_hits: list[str] = []
    for mood in MOOD_MEANINGS:
        markers = MOOD_MARKERS.get(mood, ())
        hits = [marker for marker in markers if marker.lower() in combined]
        alias_hits = [marker for marker in MOOD_ALIASES.get(mood, ()) if marker.lower() in combined]
        score = len(hits) * 2 + len(alias_hits)
        if score > best_score:
            best_mood = mood
            best_score = score
            best_hits = [*hits, *alias_hits]
    return canonical_mood(best_mood), best_score, best_hits[:8]


def infer_sticker_semantics(path: Path, *, extra_text: str = "") -> dict[str, Any]:
    text = " ".join(
        part
        for part in (
            path.parent.name,
            path.stem,
            extra_text,
        )
        if part
    )
    mood, score, hits = _infer_mood(text)
    mood = canonical_mood(mood)
    parent_mood = canonical_mood(path.parent.name, "")
    if parent_mood in MOOD_MEANINGS:
        mood = parent_mood
        score = 0 if parent_mood == "unclear" else max(score, 4)
        hits = list(dict.fromkeys([path.parent.name, *hits]))[:8]
    confidence = "high" if score >= 4 else ("medium" if score >= 2 else "low")
    return {
        "mood": mood,
        "score": score,
        "confidence": confidence,
        "keywords": hits,
        "meaning": MOOD_MEANINGS.get(mood, MOOD_MEANINGS["cute"]),
    }


def _auto_send_gate(seed: str, score: int) -> bool:
    if score >= 7:
        return True
    return int(_digest(seed, limit=8), 16) % 100 < _auto_rate()


def decide_sticker(user_text: str, reply: str = "") -> StickerDecision:
    compact = _compact(user_text)
    lowered = compact.lower()
    if not compact:
        return StickerDecision(False, "cute", ["sticker_skip:empty_user_text"])
    if any(marker in compact for marker in NEGATIVE_MARKERS):
        return StickerDecision(False, "cute", ["sticker_skip:negative_marker"])
    if "表情包" in compact and any(marker in compact for marker in QUESTION_ONLY_MARKERS):
        return StickerDecision(False, "cute", ["sticker_skip:question_only"])
    should_send = any(marker.lower() in lowered for marker in REQUEST_MARKERS)

    combined = f"{user_text}\n{reply}"
    mood, score, hits = _infer_mood(combined)
    if should_send:
        return StickerDecision(True, mood, [f"sticker_requested:{mood}"], mode="explicit", score=score, keywords=hits)

    if _explicit_only():
        return StickerDecision(False, mood, ["sticker_skip:explicit_only"], score=score, keywords=hits)
    if not _auto_enabled():
        return StickerDecision(False, mood, ["sticker_skip:auto_disabled"], score=score, keywords=hits)
    if _contains_any(combined, AUTO_BLOCK_MARKERS):
        return StickerDecision(False, mood, ["sticker_skip:auto_blocked_context"], score=score, keywords=hits)
    if score < _auto_min_score():
        return StickerDecision(False, mood, ["sticker_skip:not_requested"], score=score, keywords=hits)
    if not _auto_send_gate(combined, score):
        return StickerDecision(False, mood, ["sticker_skip:auto_gate"], score=score, keywords=hits)
    return StickerDecision(
        True,
        mood,
        [f"sticker_auto_semantic:{mood}", f"sticker_semantic_score:{score}"],
        mode="semantic_auto",
        score=score,
        keywords=hits,
    )


def sticker_library_dirs(root: Path) -> list[Path]:
    local_scope = ensure_local_scope(default_local_scope_root(root))
    dirs = [
        root / "emotions" / "stickers",
        local_scope / "Stickers",
    ]
    dirs.extend(_configured_sticker_dirs())
    shared = shared_asset_sticker_dir(root)
    if shared is not None and shared not in dirs:
        dirs.append(shared)
    for path in dirs:
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def _configured_sticker_dirs() -> list[Path]:
    configured = os.environ.get(STICKER_LIBRARY_DIRS_ENV, "").strip()
    if not configured:
        return []
    return [Path(part).expanduser() for part in configured.split(os.pathsep) if part.strip()]


def _xinyu_workspace_root(root: Path) -> Path | None:
    resolved = root.resolve()
    for candidate in (resolved, *resolved.parents):
        if candidate.name == "XinYu":
            return candidate
    return None


def shared_asset_sticker_dir(root: Path) -> Path | None:
    if _as_bool(os.environ.get(DISABLE_SHARED_ASSET_LIBRARY_ENV), default=False):
        return None
    workspace = _xinyu_workspace_root(root)
    if workspace is None:
        return None
    return workspace / "素材库" / "心玉" / "表情"


def list_stickers(root: Path) -> list[Path]:
    files: dict[str, Path] = {}
    for directory in sticker_library_dirs(root):
        try:
            for path in directory.rglob("*"):
                parent_parts = path.relative_to(directory).parts[:-1]
                if any(part.startswith(".") or part in REFERENCE_DIR_NAMES for part in parent_parts):
                    continue
                if path.is_file() and path.suffix.lower() in SUPPORTED_STICKER_SUFFIXES:
                    try:
                        resolved = path.resolve(strict=True)
                    except OSError:
                        continue
                    files[str(resolved)] = resolved
        except OSError:
            continue
    return sorted(files.values(), key=lambda path: path.name.lower())


def _manifest_paths(root: Path) -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    for directory in sticker_library_dirs(root):
        for name in MANIFEST_NAMES:
            path = directory / name
            if path.exists() and path.is_file():
                pairs.append((directory, path))
    return pairs


def _send_state_path(root: Path) -> Path:
    return sticker_send_state_path(root)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _load_send_state(root: Path) -> dict[str, Any]:
    data = read_sticker_send_state(root, default={"version": 1, "sessions": {}})
    if not isinstance(data.get("sessions"), dict):
        data["sessions"] = {}
    return data


def _write_send_state(root: Path, data: dict[str, Any]) -> None:
    write_sticker_send_state(root, data)


def _session_state_key(payload: dict[str, Any], session_key: str) -> str:
    if session_key:
        return session_key
    message_type = _safe_str(payload.get("message_type"), "private").lower()
    user_id = _safe_str(payload.get("user_id")).strip()
    group_id = _safe_str(payload.get("group_id")).strip()
    if group_id and group_id not in {"0", "none", "None"}:
        return f"qq:group:{group_id}"
    return f"qq:{message_type or 'private'}:{user_id or 'unknown'}"


def _recent_session_info(root: Path, session_key: str) -> dict[str, Any]:
    data = _load_send_state(root)
    sessions = data.get("sessions")
    if not isinstance(sessions, dict):
        return {}
    session = sessions.get(session_key)
    return session if isinstance(session, dict) else {}


def _auto_cooldown_allows(root: Path, session_key: str) -> tuple[bool, list[str]]:
    cooldown_minutes = _auto_cooldown_minutes()
    if cooldown_minutes <= 0:
        return True, ["sticker_cooldown_disabled"]
    session = _recent_session_info(root, session_key)
    last_auto = _parse_iso(_safe_str(session.get("last_auto_sent_at")))
    if last_auto is None:
        return True, []
    elapsed = (datetime.now(timezone.utc).astimezone() - last_auto.astimezone()).total_seconds()
    if elapsed < cooldown_minutes * 60:
        return False, [f"sticker_skip:auto_cooldown:{cooldown_minutes}m"]
    return True, []


def _record_sticker_send(
    root: Path,
    session_key: str,
    *,
    mode: str,
    mood: str,
    image_path: Path,
    message_id: str,
) -> None:
    data = _load_send_state(root)
    sessions = data.setdefault("sessions", {})
    if not isinstance(sessions, dict):
        sessions = {}
        data["sessions"] = sessions
    now = _now_iso()
    session = sessions.get(session_key)
    if not isinstance(session, dict):
        session = {}
        sessions[session_key] = session
    session["last_sent_at"] = now
    session["last_path"] = str(image_path)
    session["last_mood"] = mood
    session["last_mode"] = mode
    session["last_message_id"] = message_id
    if mode == "semantic_auto":
        session["last_auto_sent_at"] = now
    data["version"] = 1
    data["updated_at"] = now
    _write_send_state(root, data)


def _manifest_items(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []
    memes = data.get("memes")
    if isinstance(memes, list):
        return [item for item in memes if isinstance(item, dict)]
    stickers = data.get("stickers")
    if isinstance(stickers, list):
        return [item for item in stickers if isinstance(item, dict)]
    items = data.get("items")
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    # AstrBot meme manager style: {"category": {"description": "...", "memes": [...]}}
    rows: list[dict[str, Any]] = []
    for category, value in data.items():
        if not isinstance(value, dict):
            continue
        category_memes = value.get("memes") or value.get("items") or value.get("files")
        description = _safe_str(value.get("description") or value.get("meaning"))
        keywords = _as_list(value.get("keywords"))
        mood = canonical_mood(value.get("mood") or category, "cute")
        for item in category_memes if isinstance(category_memes, list) else []:
            if isinstance(item, str):
                rows.append({"file": item, "mood": mood, "meaning": description, "keywords": keywords})
            elif isinstance(item, dict):
                merged = dict(item)
                merged.setdefault("mood", mood)
                merged.setdefault("meaning", description)
                merged.setdefault("keywords", keywords)
                rows.append(merged)
    return rows


def _read_manifest_candidates(root: Path) -> dict[str, StickerCandidate]:
    candidates: dict[str, StickerCandidate] = {}
    for base_dir, manifest_path in _manifest_paths(root):
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        for item in _manifest_items(data):
            raw_file = _safe_str(item.get("file") or item.get("path") or item.get("name")).strip()
            if not raw_file:
                continue
            path = Path(raw_file)
            candidate = path if path.is_absolute() else base_dir / path
            try:
                resolved = candidate.resolve(strict=True)
                resolved.relative_to(base_dir.resolve())
            except (OSError, ValueError):
                continue
            if resolved.suffix.lower() not in SUPPORTED_STICKER_SUFFIXES:
                continue
            mood = canonical_mood(item.get("mood") or item.get("category") or item.get("intent"), "cute")
            keywords = tuple(dict.fromkeys(_as_list(item.get("keywords")) + _as_list(item.get("tags"))))
            candidates[str(resolved)] = StickerCandidate(
                path=resolved,
                mood=mood,
                keywords=keywords,
                meaning=_safe_str(item.get("meaning") or item.get("description")),
                weight=max(1, int(item.get("weight") or 1)),
                auto_send=_as_bool(item.get("auto_send"), default=True),
            )
    return candidates


def _keywords_from_path(path: Path) -> tuple[str, ...]:
    parts = [path.stem, *path.parent.parts[-2:]]
    tokens: list[str] = []
    for part in parts:
        for token in re.split(r"[-_ .()\[\]{}]+", part):
            token = token.strip()
            if token:
                tokens.append(token)
    return tuple(dict.fromkeys(tokens))


def list_sticker_candidates(root: Path) -> list[StickerCandidate]:
    manifest_candidates = _read_manifest_candidates(root)
    candidates: dict[str, StickerCandidate] = dict(manifest_candidates)
    for path in list_stickers(root):
        key = str(path)
        if key in candidates:
            continue
        semantic = infer_sticker_semantics(path)
        candidates[key] = StickerCandidate(
            path=path,
            mood=_safe_str(semantic.get("mood"), "cute"),
            keywords=_keywords_from_path(path),
            meaning="",
            weight=1,
            auto_send=_safe_str(semantic.get("mood")) != "unclear",
        )
    return sorted(candidates.values(), key=lambda item: item.path.name.lower())


def _score_candidate(candidate: StickerCandidate, *, mood: str, context: str) -> int:
    context_lower = context.lower()
    mood = canonical_mood(mood)
    candidate_mood = canonical_mood(candidate.mood)
    score = 0
    if candidate_mood == mood:
        score += 4
    elif candidate_mood in {canonical_mood(item) for item in RELATED_MOODS.get(mood, ())}:
        score += 2
    if mood.lower() in candidate.path.as_posix().lower():
        score += 2
    for alias in MOOD_ALIASES.get(mood, ()):
        if alias.lower() in candidate.path.as_posix().lower():
            score += 1
    for keyword in candidate.keywords:
        if keyword and keyword.lower() in context_lower:
            score += 3
    if candidate.meaning and any(token and token.lower() in context_lower for token in _as_list(candidate.meaning)):
        score += 1
    return score * max(1, candidate.weight)


def _choose_existing_sticker(
    root: Path,
    *,
    mood: str,
    seed: str,
    context: str = "",
    require_semantic: bool = False,
    auto_only: bool = False,
    avoid_path: Path | None = None,
) -> tuple[Path | None, list[str]]:
    mood = canonical_mood(mood)
    candidates = list_sticker_candidates(root)
    if auto_only:
        candidates = [candidate for candidate in candidates if candidate.auto_send]
    if not candidates:
        return None, ["sticker_library_empty"]
    scored = [
        (_score_candidate(candidate, mood=mood, context=context), candidate)
        for candidate in candidates
    ]
    scored.sort(key=lambda item: (item[0], item[1].weight, item[1].path.name.lower()), reverse=True)
    if require_semantic:
        scored = [item for item in scored if item[0] >= 4]
        if not scored:
            return None, ["sticker_skip:no_semantic_match"]
    best_score = scored[0][0]
    top = [item for item in scored if item[0] == best_score] or scored[:3]
    if avoid_path is not None and len(top) > 1:
        try:
            avoided = avoid_path.resolve()
            filtered = [item for item in top if item[1].path.resolve() != avoided]
            if filtered:
                top = filtered
        except OSError:
            pass
    index = int(_digest(seed, limit=8), 16) % len(top)
    selected = top[index][1]
    return selected.path, [f"sticker_selected_semantic:{selected.mood}:{best_score}"]


def _font_candidates() -> tuple[Path, ...]:
    windir = Path("C:/Windows/Fonts")
    return (
        windir / "msyhbd.ttc",
        windir / "msyh.ttc",
        windir / "simhei.ttf",
        windir / "simsun.ttc",
    )


def _load_font(size: int):
    from PIL import ImageFont

    for path in _font_candidates():
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _wrap_text(text: str, max_chars: int = 5) -> list[str]:
    compact = _compact(text)
    if not compact:
        return ["心玉"]
    if len(compact) <= max_chars:
        return [compact]
    return [compact[index : index + max_chars] for index in range(0, min(len(compact), 12), max_chars)]


def _render_text_sticker(root: Path, *, mood: str, seed: str) -> tuple[Path, list[str]]:
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return Path(), ["sticker_render_failed:pillow_missing"]

    mood = canonical_mood(mood)
    text = MOOD_TEXT.get(mood, MOOD_TEXT["cute"])
    out_dir = root / "runtime" / "generated_stickers"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"心玉表情-{mood_dir_name(mood)}-{_digest(seed)}.png"
    if out_path.exists():
        return out_path, ["sticker_generated_reused"]

    palette = PALETTES[int(_digest(seed, limit=8), 16) % len(PALETTES)]
    background, accent, ink = palette
    image = Image.new("RGB", (512, 512), background)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((34, 34, 478, 478), radius=44, outline=accent, width=12, fill=background)
    draw.rounded_rectangle((70, 74, 442, 438), radius=32, outline=accent, width=3)
    draw.ellipse((110, 124, 150, 164), fill=accent)
    draw.ellipse((362, 124, 402, 164), fill=accent)
    draw.arc((192, 126, 320, 220), start=20, end=160, fill=accent, width=8)

    font = _load_font(88 if len(text) <= 3 else 72)
    lines = _wrap_text(text)
    line_boxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
    line_heights = [box[3] - box[1] for box in line_boxes]
    total_height = sum(line_heights) + 14 * (len(lines) - 1)
    y = 282 - total_height // 2
    for line, box, height in zip(lines, line_boxes, line_heights):
        width = box[2] - box[0]
        draw.text(((512 - width) / 2, y), line, font=font, fill=ink)
        y += height + 14
    image.save(out_path, format="PNG")
    return out_path, ["sticker_generated_text"]


def select_or_create_sticker(
    root: Path,
    *,
    mood: str,
    seed: str,
    context: str = "",
    require_existing: bool = False,
    require_semantic: bool = False,
    auto_only: bool = False,
    avoid_path: Path | None = None,
) -> tuple[Path, list[str]]:
    existing, notes = _choose_existing_sticker(
        root,
        mood=mood,
        seed=seed,
        context=context,
        require_semantic=require_semantic,
        auto_only=auto_only,
        avoid_path=avoid_path,
    )
    if existing is not None:
        return existing, notes
    if require_existing:
        return Path(), notes
    return _render_text_sticker(root, mood=mood, seed=seed)


def maybe_enqueue_sticker_reply(
    root: Path,
    payload: dict[str, Any],
    *,
    user_text: str,
    reply: str,
    session_key: str = "",
    turn_id: str = "",
) -> dict[str, Any]:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict) or not bool(metadata.get("is_owner_user")):
        return {"queued": False, "notes": ["sticker_skip:not_owner"]}
    message_type = _safe_str(payload.get("message_type")).lower()
    group_id = _safe_str(payload.get("group_id")).strip()
    if message_type and not message_type.startswith("private"):
        return {"queued": False, "notes": ["sticker_skip:not_private"]}
    if group_id not in {"", "0", "none", "None"}:
        return {"queued": False, "notes": ["sticker_skip:not_private"]}

    decision = decide_sticker(user_text, reply)
    if not decision.should_send:
        return {"queued": False, "notes": decision.notes}

    user_id = _safe_str(payload.get("user_id")).strip()
    if not user_id:
        return {"queued": False, "notes": ["sticker_skip:missing_user_id"]}
    state_key = _session_state_key(payload, session_key)
    auto_mode = decision.mode == "semantic_auto"
    if auto_mode:
        allowed, cooldown_notes = _auto_cooldown_allows(root, state_key)
        if not allowed:
            return {"queued": False, "notes": [*decision.notes, *cooldown_notes], "mood": decision.mood, "mode": decision.mode}
    recent = _recent_session_info(root, state_key)
    avoid_raw = _safe_str(recent.get("last_path"))
    avoid_path = Path(avoid_raw) if avoid_raw else None
    seed = "\n".join(part for part in (session_key, turn_id, user_text, reply, decision.mood) if part)
    sticker_path, sticker_notes = select_or_create_sticker(
        root,
        mood=decision.mood,
        seed=seed,
        context=f"{user_text}\n{reply}",
        require_existing=auto_mode,
        require_semantic=auto_mode,
        auto_only=auto_mode,
        avoid_path=avoid_path,
    )
    if not sticker_path:
        return {"queued": False, "notes": [*decision.notes, *sticker_notes]}

    dedupe_seed = turn_id or _digest(seed)
    queued = enqueue_qq_outbox_image(
        root,
        user_id=user_id,
        image_path=str(sticker_path),
        caption="",
        source="sticker_pack",
        dedupe_key=f"sticker_pack:{dedupe_seed}",
        metadata={
            "sticker_mood": decision.mood,
            "sticker_mood_label": sticker_mood_label(decision.mood),
            "sticker_mode": decision.mode,
            "sticker_score": decision.score,
            "sticker_keywords": decision.keywords[:8],
            "sticker_path": str(sticker_path),
            "sticker_path_name": sticker_path.name,
            "generated_sticker": any(note.startswith("sticker_generated") for note in sticker_notes),
            "session_id": state_key,
            "source_session_id": session_key,
            "source_turn_id": turn_id,
            "runtime_turn_id": turn_id,
        },
    )
    notes = [*decision.notes, *sticker_notes, *[_safe_str(note) for note in queued.get("notes", [])]]
    if queued.get("queued"):
        _record_sticker_send(
            root,
            state_key,
            mode=decision.mode,
            mood=decision.mood,
            image_path=sticker_path,
            message_id=_safe_str(queued.get("message_id")),
        )
    return {
        "queued": bool(queued.get("queued")),
        "message_id": _safe_str(queued.get("message_id")),
        "image_path": str(sticker_path),
        "mood": decision.mood,
        "mode": decision.mode,
        "score": decision.score,
        "notes": notes,
    }
