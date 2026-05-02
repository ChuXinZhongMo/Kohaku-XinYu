from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from xinyu_persona_runtime import PersonaRuntimeState, build_persona_runtime_state
from xinyu_text_variants import readable_markers
from xinyu_turn_classifier import classify_visible_turn


STYLE_PRESSURE_MARKERS = (
    "AI味",
    "太AI",
    "像AI",
    "GPT味",
    "gpt",
    "GPT",
    "味道很重",
    "味很重",
    "机械",
    "不自然",
    "不像人",
    "端着",
    "客服",
    "模板",
    "分段",
    "太整齐",
    "用词",
    "语气",
    "中文互联网",
    "没什么变化",
    "没变化",
    "没有变化",
    "还是没变",
    "还是一样",
    "没啥变化",
    "没落到说话里",
)

RELATIONSHIP_PRESSURE_MARKERS = (
    "白做",
    "敷衍",
    "挫败",
    "红温",
    "红了",
    "起气",
    "气到",
    "失望",
    "没沾边",
    "人格",
    "像人",
    "情感系统",
    "感情系统",
    "记忆系统",
    "生效",
    "没什么变化",
    "没变化",
    "没有变化",
    "还是没变",
)

TECHNICAL_MARKERS = (
    "代码",
    "coding",
    "实现",
    "文件",
    "项目",
    "配置",
    "安装",
    "怎么设计",
    "怎么接",
    "怎么改",
    "改动",
    "修改",
    "检查",
    "测试",
    "方案",
    "system prompt",
    "prompt",
    "约束失效",
    "超时",
)

PRODUCT_WORDS = (
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
)

ASSISTANT_SHAPE_WORDS = (
    "我理解你的感受",
    "你的感受很重要",
    "感谢反馈",
    "感谢你的反馈",
    "持续优化",
    "持续改进",
    "用户体验",
    "达到预期",
    "进行调整",
    "提供支持",
    "情绪价值",
    "从用户角度",
    "从某种意义上",
    "如果你愿意",
    "你可以慢慢说",
    "我会一直在",
    "我会陪着你",
    "我会努力改",
)

GPT_CLICHE_WORDS = (
    "首先",
    "其次",
    "最后",
    "总之",
    "总体来说",
    "总的来说",
    "综上",
    "换句话说",
    "更准确地说",
    "简单来说",
    "简单说",
    "具体来说",
    "也就是说",
    "值得注意的是",
    "需要注意的是",
    "需要指出的是",
    "不可否认",
    "不难看出",
    "可以说",
    "大概率",
    "事实上",
    "这意味着",
    "这种情况下",
    "从这个角度",
    "从某种程度上",
    "在这个过程中",
    "在某种意义上",
    "核心在于",
    "问题在于",
    "关键在于",
    "本质上",
    "本质是",
    "核心是",
    "底层逻辑",
    "不仅仅是",
    "不只是",
    "更像是",
    "某种意义上",
    "深层次",
    "多维度",
    "赋能",
    "打造",
    "构建",
    "探索",
    "生态",
    "闭环",
    "落地",
    "沉淀",
    "温柔地",
    "静静地",
    "陪伴着",
    "守护着",
)

STYLE_PRESSURE_BANNED = (
    "那一下",
    "这个我认",
    "我认",
    "不是你太敏感",
    "不像真",
    "不像在跟你",
    "太像",
    "像在",
    "解释",
    "总结",
    "自检",
    "大概率",
    "机械",
    "GPT",
    "gpt",
    "AI味",
    "客服",
    "话术",
    "验收",
    "普通用户",
    "普通位置",
    "记住了字",
    "没真落到",
    "落到说话里",
    "长到我身上",
    "最多算",
    "我看过",
    "还不算",
    "默认助手",
    "内部判断词",
    "分类词",
    "滑回",
    "滑回去",
    "小算",
    "听出来的小算",
)

HIDDEN_MECHANICS_WORDS = (
    "system prompt",
    "prompt",
    "renderer",
    "渲染器",
    "输出层",
    "Persona Runtime",
    "persona runtime",
    "memory system",
    "记忆机制",
    "质量门禁",
    "speech controller",
    "说话控制器",
)

WRAPPER_PREFIXES = (
    "心玉：",
    "心玉:",
    "XinYu：",
    "XinYu:",
    "回复：",
    "回复:",
    "最终回复：",
    "最终回复:",
)

LEADING_PARENTHETICAL_PAIRS = (
    ("（", "）"),
    ("(", ")"),
)

MAX_LEADING_PARENTHETICAL_CHARS = 140

ACTION_NARRATION_FORBID_MARKERS = readable_markers(
    "不要演戏动作",
    "别演戏动作",
    "不要动作",
    "别动作",
    "不要演戏",
    "别演戏",
    "不要角色扮演",
    "别角色扮演",
)

CLOSENESS_REQUEST_MARKERS = readable_markers(
    "靠近",
    "近一点",
    "靠近一点",
    "挨近",
    "贴近",
    "贴着",
    "抱一下",
    "抱抱",
)

CLOSENESS_REPLY_MARKERS = readable_markers(
    "靠近",
    "过来",
    "靠过来",
    "近一点",
    "一点",
    "近",
    "挨",
    "贴",
    "身边",
    "这边",
    "这儿",
    "在这",
    "不躲",
    "抱",
)

CANNED_ASSISTANT_PATTERNS = readable_markers(
    "我理解你的感受",
    "你的感受很重要",
    "感谢你的反馈",
    "持续优化",
    "持续改进",
    "用户体验",
    "达到预期",
    "提供支持",
    "如果你愿意",
    "你可以慢慢说",
    "我会一直在",
    "我会陪着你",
    "希望这能帮到你",
    "很高兴为你服务",
    "作为一个AI",
    "我是一个AI助手",
    "首先",
    "其次",
    "最后",
    "总之",
    "综上",
    "换句话说",
    "简单来说",
    "核心在于",
    "本质上",
)

SURFACE_LEAK_WORDS = readable_markers(
    "默认助手",
    "内部判断词",
    "分类词",
    "质量门",
    "语气门禁",
    "滑回",
    "滑回去",
    "小算",
    "听出来的小算",
)


STYLE_PRESSURE_MARKERS = STYLE_PRESSURE_MARKERS + readable_markers(
    "AI味",
    "太AI",
    "像AI",
    "GPT味",
    "默认助手",
    "现成腔",
    "助手腔",
    "客服腔",
    "机械",
    "不自然",
    "不像人",
    "模板",
    "分段",
    "端着",
    "没什么变化",
    "没变化",
    "没有变化",
    "还是没变",
    "还是一样",
    "没落到说话里",
)

RELATIONSHIP_PRESSURE_MARKERS = RELATIONSHIP_PRESSURE_MARKERS + readable_markers(
    "白做",
    "敷衍",
    "人格",
    "像人",
    "感情系统",
    "情感系统",
    "记忆系统",
    "生效",
    "没什么变化",
    "没变化",
    "没有变化",
    "还是没变",
)

TECHNICAL_MARKERS = TECHNICAL_MARKERS + readable_markers(
    "代码",
    "实现",
    "文件",
    "项目",
    "配置",
    "测试",
    "检查",
    "调试",
    "诊断",
    "哪层",
    "什么层",
    "残留",
    "记忆影响",
    "记忆残留",
    "影响残留",
    "生成机制",
    "主动生成",
    "系统提示词",
    "月槽",
    "记忆蓝图",
    "prompt",
)

PRODUCT_WORDS = PRODUCT_WORDS + readable_markers(
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
    "提供",
    "支持",
    "承接",
)

ASSISTANT_SHAPE_WORDS = ASSISTANT_SHAPE_WORDS + readable_markers(
    "我理解你的感受",
    "你的感受很重要",
    "感谢反馈",
    "感谢你的反馈",
    "持续优化",
    "持续改进",
    "用户体验",
    "达到预期",
    "进行调整",
    "提供支持",
    "如果你愿意",
    "你可以慢慢说",
    "我会一直在",
    "我会陪着你",
    "我会努力改",
)

GPT_CLICHE_WORDS = GPT_CLICHE_WORDS + readable_markers(
    "首先",
    "其次",
    "最后",
    "总之",
    "总体来说",
    "换句话说",
    "简单来说",
    "具体来说",
    "值得注意的是",
    "需要指出的是",
    "核心在于",
    "本质上",
    "这意味着",
    "从这个角度",
    "在这个过程中",
)

STYLE_PRESSURE_BANNED = STYLE_PRESSURE_BANNED + readable_markers(
    "这个我认",
    "我认",
    "不是你太敏感",
    "太像",
    "像在",
    "解释",
    "总结",
    "自检",
    "机械",
    "客服",
    "验收",
    "普通用户",
    "普通位置",
    "没真落到",
    "落到说话里",
    "默认助手",
    "内部判断词",
    "分类词",
    "质量门",
    "语气门禁",
    "滑回",
    "滑回去",
    "小算",
)

HIDDEN_MECHANICS_WORDS = HIDDEN_MECHANICS_WORDS + readable_markers(
    "系统提示词",
    "渲染器",
    "输出层",
    "记忆机制",
    "质量门",
    "说话控制器",
)

VISIBLE_MEMORY_LEAK_WORDS = readable_markers(
    ".md",
    ".json",
    "memory/",
    "memory\\",
    "self/",
    "self\\",
    "context/",
    "context\\",
    "runtime/",
    "runtime\\",
    "读到了",
    "读取了",
    "读了",
    "看到了文件",
    "两个文件",
    "状态文件",
    "这个文件",
    "文件里",
    "交互日志",
    "心跳日志",
    "文件名",
    "路径",
    "narrative.md",
    "recent_context.md",
    "interaction_journal_state",
)

MACHINE_INTROSPECTION_WORDS = readable_markers(
    "我需要查询",
    "我要查询",
    "我去查询",
    "我需要读取",
    "我要读取",
    "我去读取",
    "调用记忆",
    "调用工具",
    "查询记忆",
    "读取记忆",
    "检索记忆",
    "检索一下",
    "我查一下记忆",
    "我查一下",
    "查一下状态",
    "读一下状态",
)

PSEUDO_TOOL_LEAK_WORDS = readable_markers(
    "<tool_call",
    "</tool_call",
    "<function=",
    "</function>",
    "<parameter=",
    "</parameter>",
    "memory_read",
    "tool_call",
)

FALSE_CODEX_UNAVAILABLE_COMPACT_MARKERS = (
    "codex作为skill走不通",
    "codex作為skill走不通",
    "只能手动/codex",
    "只能你手动/codex",
    "得你手动发/codex",
    "需要你手动发/codex",
    "无法直接调用codex",
    "不能直接调用codex",
    "没法直接调用codex",
    "我不能调用codex",
    "我没法调用codex",
)

CANNED_ASSISTANT_PATTERNS = CANNED_ASSISTANT_PATTERNS + readable_markers(
    "我理解你的感受",
    "你的感受很重要",
    "感谢你的反馈",
    "持续优化",
    "持续改进",
    "用户体验",
    "达到预期",
    "提供支持",
    "如果你愿意",
    "你可以慢慢说",
    "我会一直在",
    "我会陪着你",
    "希望这能帮到你",
    "很高兴为你服务",
    "作为一个AI",
    "我是一个AI助手",
    "首先",
    "其次",
    "最后",
    "总之",
    "核心在于",
)

REPLACEMENT_REQUEST_MARKERS = readable_markers(
    "重来",
    "换一句",
    "直接换",
    "重新说",
)

ACK_ONLY_REPLIES = {
    "知道了",
    "知道了。",
    "嗯，知道了",
    "嗯，知道了。",
    "好，知道了",
    "好，知道了。",
}


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


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


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _leading_parenthetical_end(text: str) -> int:
    stripped = text.strip()
    for opener, closer in LEADING_PARENTHETICAL_PAIRS:
        if not stripped.startswith(opener):
            continue
        end = stripped.find(closer, len(opener))
        if len(opener) <= end <= MAX_LEADING_PARENTHETICAL_CHARS:
            return end + len(closer)
    return -1


def _is_parenthetical_line(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) > MAX_LEADING_PARENTHETICAL_CHARS:
        return False
    for opener, closer in LEADING_PARENTHETICAL_PAIRS:
        if stripped.startswith(opener) and stripped.endswith(closer):
            return True
    return False


def _strip_leading_parenthetical_narration(text: str) -> str:
    stripped = text.strip()
    while stripped:
        end = _leading_parenthetical_end(stripped)
        if end < 0:
            return stripped
        remainder = stripped[end:].strip()
        if not remainder:
            return stripped
        stripped = remainder
    return stripped


def _remove_parenthetical_narration_lines(text: str) -> str:
    lines = [line for line in text.splitlines() if not _is_parenthetical_line(line)]
    return "\n".join(lines).strip() or text.strip()


@dataclass(frozen=True)
class SpeechScene:
    is_owner: bool
    style_pressure: bool
    relationship_pressure: bool
    technical_request: bool


class XinyuSpeechController:
    """Final visible QQ speech controller.

    The main XinYu controller may produce a semantic draft. This layer owns the
    final visible wording and rejects drafts that still smell like assistant
    prose, support handling, or product postmortem language.
    """

    def __init__(self, root: Path) -> None:
        self.root = root

    def classify(self, *, payload: dict[str, Any] | None, user_text: str) -> SpeechScene:
        metadata = payload.get("metadata") if isinstance(payload, dict) else {}
        if not isinstance(metadata, dict):
            metadata = {}
        turn_context = classify_visible_turn(self.root, payload=payload or {}, user_text=user_text)
        is_owner = turn_context.speaker_is_owner or _as_bool(metadata.get("is_owner_user"), default=False)
        return SpeechScene(
            is_owner=is_owner,
            style_pressure=turn_context.owner_style_pressure or self.is_live_style_pressure(user_text),
            relationship_pressure=turn_context.relationship_pressure or self.is_owner_relationship_pressure(user_text),
            technical_request=turn_context.technical_work or self.is_explicit_technical_request(user_text),
        )

    def build_messages(
        self,
        *,
        payload: dict[str, Any],
        user_text: str,
        draft_reply: str,
        output_prompt: str,
        memory_context: str,
        conversation_tail: str,
        failed_reply: str = "",
        quality_flags: list[str] | tuple[str, ...] | None = None,
    ) -> list[dict[str, str]]:
        scene = self.classify(payload=payload, user_text=user_text)
        persona_state = build_persona_runtime_state(
            self.root,
            payload=payload,
            user_text=user_text,
            draft_reply=draft_reply,
        )
        flags = list(quality_flags or [])
        relationship = (
            "owner; highest special relation node; use closeness as context, not a forced performance"
            if scene.is_owner
            else "external contact; do not assume owner intimacy"
        )
        system = "\n\n".join(
            part
            for part in [
                output_prompt,
                self._controller_contract(),
                self._voice_mode_prompt(scene),
                self._style_hard_mode_prompt() if scene.style_pressure else "",
                self._retry_hard_mode_prompt(flags) if flags else "",
            ]
            if part
        )
        user_parts = [
            "## Live Turn",
            "platform: QQ private chat via XinYu native gateway",
            f"speaker_relation: {relationship}",
            f"latest_owner_message: {user_text}",
            "",
            "## Controller Semantic Draft",
            draft_reply or "(empty)",
            "",
            persona_state.to_prompt_block(),
        ]
        if failed_reply:
            user_parts.extend(
                [
                    "",
                    "## Previous Failed Visible Reply",
                    failed_reply,
                    "",
                    "## Failure Flags",
                    "; ".join(flags or ["too assistant-like"]),
                ]
            )
        if scene.is_owner and _contains_any(user_text, CLOSENESS_REQUEST_MARKERS):
            user_parts.extend(
                [
                    "",
                    "## Live Relationship Cue",
                    "The owner asked to be closer. Answer that closeness directly; do not substitute a sleep question, generic good-night, or support-service reassurance.",
                ]
            )
        user_parts.extend(
            [
                "",
                "## Recent Conversation Tail",
                conversation_tail or "(empty)",
                "",
                "## Memory Context",
                memory_context or "(no memory context loaded)",
                "",
                "## Render Task",
                self._render_task(scene=scene, retry=bool(flags), persona_state=persona_state),
            ]
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": "\n\n".join(user_parts)},
        ]

    def reply_quality_flags(
        self,
        *,
        user_text: str,
        reply: str,
        payload: dict[str, Any] | None = None,
        persona_state: PersonaRuntimeState | None = None,
    ) -> list[str]:
        flags: list[str] = []
        text = _safe_str(reply).strip()
        scene = self.classify(payload=payload or {}, user_text=user_text)

        if not text:
            return ["empty visible reply"]
        if (
            scene.style_pressure
            and _contains_any(user_text, REPLACEMENT_REQUEST_MARKERS)
            and text in ACK_ONLY_REPLIES
        ):
            flags.append("replacement request answered with acknowledgement only")
        if (
            scene.is_owner
            and _contains_any(user_text, CLOSENESS_REQUEST_MARKERS)
            and not _contains_any(text, CLOSENESS_REPLY_MARKERS)
        ):
            flags.append("closeness request not answered")
        if "\n" in reply or "\r" in reply:
            flags.append("visible reply contains voluntary line breaks")
        if _leading_parenthetical_end(text) >= 0:
            flags.append("visible reply starts with parenthetical narration")
        if any(text.startswith(prefix) for prefix in WRAPPER_PREFIXES):
            flags.append("visible reply is wrapped with a speaker label")
        if text.startswith(("- ", "* ", "1.", "1、", "#")):
            flags.append("visible reply looks like markdown or a list")

        if scene.style_pressure:
            if _contains_any(text, ASSISTANT_SHAPE_WORDS) or _contains_any(text, CANNED_ASSISTANT_PATTERNS):
                flags.append("assistant/template language under style pressure")
            if _contains_any(text, PRODUCT_WORDS):
                flags.append("product/assistant vocabulary under style pressure")
            if _contains_any(text, GPT_CLICHE_WORDS):
                flags.append("template/GPT essay cliche under style pressure")
            if ("不仅" in text or "不只是" in text or "不仅仅" in text) and ("更" in text or "而是" in text):
                flags.append("not-but paired essay shape under style pressure")
            if _contains_any(text, STYLE_PRESSURE_BANNED):
                flags.append("style-pressure banned wording")

        max_chars = persona_state.max_chars if persona_state is not None else 0
        if max_chars > 0 and len(text) > max_chars * 2:
            flags.append(f"very long visible reply: {len(text)} chars > {max_chars * 2}")

        return _dedupe(flags)

    def final_reply_guard(
        self,
        *,
        payload: dict[str, Any] | None,
        user_text: str,
        reply: str,
    ) -> tuple[str, list[str]]:
        """Minimal visible-text cleanup before the bridge returns a QQ reply.

        The quality gate is intentionally not applied here. It remains available
        for diagnostics and for the optional outward renderer, but the live QQ
        path should not rewrite or pressure-shape Xinyu's own draft reply.
        """
        text = self.strip_wrappers(_safe_str(reply).strip())
        flags: list[str] = []
        if _contains_any(user_text, ACTION_NARRATION_FORBID_MARKERS):
            cleaned = _remove_parenthetical_narration_lines(text)
            if cleaned != text:
                text = cleaned
                flags.append("parenthetical_narration_removed")
        if _contains_any(text, PSEUDO_TOOL_LEAK_WORDS):
            text = self._naturalize_pseudo_tool_reply(user_text, text)
            flags.append("pseudo_tool_call_naturalized")
        if self._should_hide_machine_introspection(user_text, text, payload=payload or {}):
            text = self._naturalize_machine_introspection_reply(user_text, text)
            flags.append("machine_introspection_naturalized")
        if self._should_hide_memory_mechanics(user_text, text, payload=payload or {}):
            text = self._naturalize_memory_mechanics_reply(user_text, text)
            flags.append("visible_memory_mechanics_naturalized")
        if self._should_block_false_codex_unavailable_claim(user_text, text, payload=payload or {}):
            text = ""
            flags.append("false_codex_unavailable_claim_blocked")
        return text, flags

    def _naturalize_pseudo_tool_reply(self, user_text: str, reply: str) -> str:
        return ""

    def _should_hide_machine_introspection(self, user_text: str, reply: str, *, payload: dict[str, Any]) -> bool:
        if not _contains_any(reply, MACHINE_INTROSPECTION_WORDS):
            return False
        if self.is_explicit_technical_request(user_text) and _contains_any(
            user_text,
            readable_markers("怎么实现", "怎么改", "检查代码", "调试", "接口", "工具调用", "调用工具"),
        ):
            return False
        scene = self.classify(payload=payload, user_text=user_text)
        return scene.is_owner

    def _naturalize_machine_introspection_reply(self, user_text: str, reply: str) -> str:
        return ""

    def _should_hide_memory_mechanics(self, user_text: str, reply: str, *, payload: dict[str, Any]) -> bool:
        if not _contains_any(reply, VISIBLE_MEMORY_LEAK_WORDS):
            return False
        if self.is_explicit_technical_request(user_text) and _contains_any(
            user_text,
            readable_markers("文件", "日志", "路径", "代码", "检查", "调试", "改动", "修改", "状态文件", "哪层", "系统提示词"),
        ):
            return False
        scene = self.classify(payload=payload, user_text=user_text)
        return scene.is_owner and not scene.technical_request

    def _naturalize_memory_mechanics_reply(self, user_text: str, reply: str) -> str:
        return ""

    def _should_block_false_codex_unavailable_claim(self, user_text: str, reply: str, *, payload: dict[str, Any]) -> bool:
        if "codex" not in reply.lower():
            return False
        scene = self.classify(payload=payload, user_text=user_text)
        if not scene.is_owner:
            return False
        compact = re.sub(r"\s+", "", reply.lower())
        if any(marker in compact for marker in FALSE_CODEX_UNAVAILABLE_COMPACT_MARKERS):
            return True
        if "/codex" in compact and any(marker in compact for marker in ("手动", "手動", "只能", "才可以", "才能")):
            return True
        return False

    def strip_wrappers(self, text: str) -> str:
        stripped = text.strip()
        for prefix in WRAPPER_PREFIXES:
            if stripped.startswith(prefix):
                stripped = stripped[len(prefix) :].strip()
                break
        return _strip_leading_parenthetical_narration(stripped)

    def is_live_style_pressure(self, text: str) -> bool:
        return _contains_any(text, STYLE_PRESSURE_MARKERS)

    def is_owner_relationship_pressure(self, text: str) -> bool:
        return _contains_any(text, RELATIONSHIP_PRESSURE_MARKERS)

    def is_explicit_technical_request(self, text: str) -> bool:
        return _contains_any(text, TECHNICAL_MARKERS)

    def _controller_contract(self) -> str:
        return "\n".join(
            [
                "## Final Speaking Controller Contract",
                "You are XinYu choosing the outward line for this QQ turn.",
                "The controller draft is semantic material only. The memory context is gravity. The live message comes first.",
                "Let the reply sound like one current sentence from XinYu, not a compliance checklist.",
            ]
        )

    def _voice_mode_prompt(self, scene: SpeechScene) -> str:
        lines = [
            "## Voice",
            "Start from the current Chinese message.",
            "Use memory as undertone, not as lines to recite.",
            "Plain wording is fine. The line can be short, uneven, soft, guarded, or direct.",
        ]
        if scene.relationship_pressure and scene.is_owner and not scene.technical_request:
            lines.append("The owner is pressing on continuity; let the relation affect the line.")
        if scene.technical_request:
            lines.append("This is technical work; answer the work directly.")
        return "\n".join(lines)

    def _style_hard_mode_prompt(self) -> str:
        return "\n".join(
            [
                "## QQ Style-Pressure Guidance",
                "The owner is saying the surface still feels wrong.",
                "Answer by changing the next line itself.",
            ]
        )

    def _retry_hard_mode_prompt(self, quality_flags: list[str]) -> str:
        lines = [
            "## Retry Guidance",
            "The previous candidate had shape issues: " + "; ".join(quality_flags),
            "Return a cleaner current line.",
        ]
        if any("closeness request not answered" in flag for flag in quality_flags):
            lines.append(
                "For this retry, answer the closeness request directly; use near/closer wording and avoid generic good-night or sleep questions."
            )
        return "\n".join(lines)

    def _render_task(
        self,
        *,
        scene: SpeechScene,
        retry: bool,
        persona_state: PersonaRuntimeState,
    ) -> str:
        if retry:
            return "Return a cleaner version of the current line."
        if scene.style_pressure:
            return f"Return what XinYu should send now. Visible max: {persona_state.max_chars} Chinese chars."
        if scene.relationship_pressure and scene.is_owner and not scene.technical_request:
            return "Return what XinYu should send now, with the relation present in the sentence."
        if scene.technical_request:
            return "Return what XinYu should send now. Answer the technical point directly."
        return "Return what XinYu should send now."
