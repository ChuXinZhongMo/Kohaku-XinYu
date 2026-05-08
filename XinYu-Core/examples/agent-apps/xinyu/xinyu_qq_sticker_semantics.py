from __future__ import annotations

from typing import Any


RECEIVED_STICKER_MOOD_MARKERS: dict[str, tuple[str, ...]] = {
    "laugh": ("哈哈", "笑死", "乐", "绷不住", "lol", "laugh"),
    "happy": ("开心", "高兴", "好耶", "可爱", "喜欢", "happy", "joy"),
    "confused": ("疑惑", "问号", "懵", "啊？", "啊?", "what", "confused"),
    "deadpan": ("无语", "沉默", "面无表情", "冷漠", "stare", "blank"),
    "awkward": ("尴尬", "流汗", "汗", "embarrassed", "sweat"),
    "sad": ("难过", "委屈", "低落", "哭", "sad", "cry"),
    "comfort": ("抱抱", "安慰", "摸摸", "hug", "comfort"),
    "annoyed": ("烦", "嫌弃", "不爽", "哼", "angry", "annoyed"),
    "surprised": ("震惊", "惊了", "意外", "真的假的", "wow", "shock"),
    "thinking": ("思考", "想想", "疑问", "thinking"),
}
RECEIVED_STICKER_MOOD_MEANING: dict[str, str] = {
    "laugh": "大笑、觉得好笑、跟着一起乐",
    "happy": "开心、轻松、正向回应",
    "confused": "疑惑、没看懂、觉得哪里不对",
    "deadpan": "无语、沉默、冷静看着",
    "awkward": "尴尬、流汗、卡住",
    "sad": "难过、委屈、低落",
    "comfort": "安慰、抱抱、陪一下",
    "annoyed": "嫌弃、不爽、被烦到",
    "surprised": "震惊、惊讶、没想到",
    "thinking": "思考、暂停判断",
}


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def infer_received_sticker_semantics(summary: str) -> dict[str, str]:
    text = safe_str(summary).strip()
    lowered = text.lower()
    for mood, markers in RECEIVED_STICKER_MOOD_MARKERS.items():
        if any(marker.lower() in lowered or marker in text for marker in markers):
            return {
                "mood": mood,
                "meaning": RECEIVED_STICKER_MOOD_MEANING.get(mood, ""),
                "confidence": "medium",
            }
    return {"mood": "unclear", "meaning": "QQ 只给了表情摘要，具体语气不确定", "confidence": "low"}
