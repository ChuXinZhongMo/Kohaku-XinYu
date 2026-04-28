from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from xinyu_text_variants import readable_markers


STYLE_PRESSURE_MARKERS = readable_markers(
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
    "太顺",
    "落下来",
    "没落到",
    "没什么变化",
    "没变化",
    "没有变化",
    "还是没变",
    "还是一样",
    "没啥变化",
    "每一句都回",
    "一句都在回",
    "一句一句回",
    "一字一句回",
)

NO_CHANGE_MARKERS = readable_markers(
    "没什么变化",
    "没变化",
    "没有变化",
    "还是没变",
    "还是一样",
    "没啥变化",
    "没感觉变化",
    "变化不大",
    "没落到说话里",
    "没有落到说话里",
)

RELATIONSHIP_PRESSURE_MARKERS = readable_markers(
    "白做",
    "敷衍",
    "红温",
    "气到",
    "失望",
    "人格",
    "感情系统",
    "情感系统",
    "记忆系统",
    "像人",
    "生效",
    "在乎",
    "受伤",
    "道歉",
    "关系",
    "反馈",
)

TECHNICAL_MARKERS = readable_markers(
    "代码",
    "项目",
    "文件",
    "配置",
    "实现",
    "调试",
    "测试",
    "脚本",
    "模块",
    "接口",
    "部署",
    "安装",
    "worktree",
    "rebase",
    "merge",
    "commit",
    "git",
    "plan",
    "prompt",
    "system prompt",
    "runtime",
    "bridge",
    "smoke",
)

REST_SILENCE_MARKERS = readable_markers(
    "困",
    "累",
    "睡",
    "休息",
    "别追问",
    "别问",
    "不要说太多",
    "先别说",
    "安静",
    "不想聊",
    "别每一句都回",
    "别一句一句回",
    "别一字一句回",
    "别都回",
    "少回点",
)

DAILY_LIFE_MARKERS = readable_markers(
    "泡面",
    "吃饭",
    "睡觉",
    "天气",
    "热",
    "空调",
    "地铁",
    "游戏",
    "维他柠",
    "鸭屎香",
    "柠檬茶",
    "回南天",
    "广州",
    "梅花园",
    "茶几",
    "试卷",
    "物理题",
    "键盘",
)

STYLE_PRESSURE_MARKERS = STYLE_PRESSURE_MARKERS + readable_markers(
    "默认助手",
    "现成腔",
    "助手腔",
    "回默认助手",
    "变回默认助手",
)

TECHNICAL_MARKERS = TECHNICAL_MARKERS + readable_markers(
    "稳定层",
    "浮动层",
    "权重递减",
    "出口检查",
    "人格稳定性",
    "上一轮情绪",
    "上一轮语气",
)

STYLE_PRESSURE_MARKERS = STYLE_PRESSURE_MARKERS + readable_markers(
    "默认助手",
    "现成腔",
    "助手腔",
    "客服腔",
    "每轮都回默认",
    "又变回默认助手",
    "AI味",
    "GPT味",
    "不像人",
    "不自然",
    "机械",
    "模板",
    "分段",
    "端着",
    "说话没变化",
)

NO_CHANGE_MARKERS = NO_CHANGE_MARKERS + readable_markers(
    "没什么变化",
    "没变化",
    "没有变化",
    "还是没变",
    "还是一样",
    "没啥变化",
    "没有落到说话里",
)

RELATIONSHIP_PRESSURE_MARKERS = RELATIONSHIP_PRESSURE_MARKERS + readable_markers(
    "白做",
    "敷衍",
    "人格",
    "感情系统",
    "情感系统",
    "记忆系统",
    "像人",
    "生效",
    "在乎",
    "受伤",
    "道歉",
    "关系",
)

TECHNICAL_MARKERS = TECHNICAL_MARKERS + readable_markers(
    "稳定层",
    "浮动层",
    "权重递减",
    "出口检查",
    "人格稳定性",
    "上一轮情绪",
    "上一轮语气",
    "记忆影响",
    "记忆残留",
    "影响残留",
    "残留",
    "哪层",
    "什么层",
    "生成机制",
    "主动生成",
    "系统提示词",
    "月槽",
    "记忆节点",
    "记忆蓝图",
    "约束失效",
    "超时",
    "测试",
)

REST_SILENCE_MARKERS = REST_SILENCE_MARKERS + readable_markers(
    "困",
    "累",
    "睡",
    "休息",
    "别追问",
    "别问",
    "不要说太多",
    "先别说",
    "安静",
    "不想聊",
)

DAILY_LIFE_MARKERS = DAILY_LIFE_MARKERS + readable_markers(
    "泡面",
    "吃饭",
    "睡觉",
    "天气",
    "热",
    "空调",
    "地铁",
    "游戏",
    "广州",
    "回南天",
    "学习",
    "作业",
    "试卷",
    "物理题",
    "键盘",
)


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


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


def _metadata(payload: dict[str, Any] | None) -> dict[str, Any]:
    raw = payload.get("metadata") if isinstance(payload, dict) else {}
    return raw if isinstance(raw, dict) else {}


@dataclass(frozen=True)
class VisibleTurnContext:
    turn_kind: str
    speaker_is_owner: bool
    owner_style_pressure: bool
    owner_no_change_pressure: bool
    daily_life: bool
    technical_work: bool
    relationship_pressure: bool
    rest_silence: bool
    pressure_level: str
    max_visible_chars: int
    draft_bias: str
    memory_write_bias: str
    proactive_constraint: str

    def to_prompt_block(self) -> str:
        return "\n".join(
            [
                "## Visible Turn Context",
                "This is pre-draft routing metadata, not hidden reasoning. Do not print it.",
                f"- turn_kind: {self.turn_kind}",
                f"- speaker_is_owner: {str(self.speaker_is_owner).lower()}",
                f"- owner_style_pressure: {str(self.owner_style_pressure).lower()}",
                f"- owner_no_change_pressure: {str(self.owner_no_change_pressure).lower()}",
                f"- daily_life: {str(self.daily_life).lower()}",
                f"- technical_work: {str(self.technical_work).lower()}",
                f"- relationship_pressure: {str(self.relationship_pressure).lower()}",
                f"- rest_silence: {str(self.rest_silence).lower()}",
                f"- pressure_level: {self.pressure_level}",
                f"- max_visible_chars: {self.max_visible_chars}",
                f"- draft_bias: {self.draft_bias}",
                f"- memory_write_bias: {self.memory_write_bias}",
                f"- proactive_constraint: {self.proactive_constraint}",
            ]
        )


def classify_visible_turn(
    root: Path | None = None,
    *,
    payload: dict[str, Any] | None,
    user_text: str,
) -> VisibleTurnContext:
    del root
    text = user_text or ""
    metadata = _metadata(payload)
    is_owner = _as_bool(metadata.get("is_owner_user"), default=False)

    technical = _contains_any(text, TECHNICAL_MARKERS)
    no_change = _contains_any(text, NO_CHANGE_MARKERS) and not technical
    style = (_contains_any(text, STYLE_PRESSURE_MARKERS) or no_change) and not technical
    relationship = _contains_any(text, RELATIONSHIP_PRESSURE_MARKERS) and not technical
    rest = _contains_any(text, REST_SILENCE_MARKERS) and not technical
    daily = _contains_any(text, DAILY_LIFE_MARKERS) and not technical and not style and not relationship

    if technical:
        return VisibleTurnContext(
            turn_kind="technical_work",
            speaker_is_owner=is_owner,
            owner_style_pressure=False,
            owner_no_change_pressure=False,
            daily_life=False,
            technical_work=True,
            relationship_pressure=False,
            rest_silence=False,
            pressure_level="task",
            max_visible_chars=420,
            draft_bias="answer the engineering task directly; do not force pressure-mode QQ wording",
            memory_write_bias="write only if the turn changes project/runtime state",
            proactive_constraint="unchanged",
        )

    if is_owner and no_change:
        return VisibleTurnContext(
            turn_kind="owner_no_change_pressure",
            speaker_is_owner=True,
            owner_style_pressure=True,
            owner_no_change_pressure=True,
            daily_life=False,
            technical_work=False,
            relationship_pressure=True,
            rest_silence=False,
            pressure_level="high",
            max_visible_chars=80,
            draft_bias="do not explain why change failed; send the changed short line itself, with 知道了 when natural",
            memory_write_bias="style-pressure residue only; do not rewrite stable personality from one correction",
            proactive_constraint="block proactive until pressure cools",
        )

    if is_owner and style:
        return VisibleTurnContext(
            turn_kind="owner_style_pressure",
            speaker_is_owner=True,
            owner_style_pressure=True,
            owner_no_change_pressure=False,
            daily_life=False,
            technical_work=False,
            relationship_pressure=relationship,
            rest_silence=False,
            pressure_level="medium",
            max_visible_chars=90,
            draft_bias="short affected QQ line; if owner says 重来/换一句, send the replacement line itself instead of only acknowledging",
            memory_write_bias="voice calibration candidate only",
            proactive_constraint="hold proactive for this turn",
        )

    if rest:
        return VisibleTurnContext(
            turn_kind="rest_silence",
            speaker_is_owner=is_owner,
            owner_style_pressure=False,
            owner_no_change_pressure=False,
            daily_life=False,
            technical_work=False,
            relationship_pressure=False,
            rest_silence=True,
            pressure_level="low",
            max_visible_chars=60,
            draft_bias="respect rest; one quiet line or silence marker if appropriate",
            memory_write_bias="normally no durable write",
            proactive_constraint="block proactive during rest/silence boundary",
        )

    if is_owner and relationship:
        return VisibleTurnContext(
            turn_kind="owner_relationship_pressure",
            speaker_is_owner=True,
            owner_style_pressure=False,
            owner_no_change_pressure=False,
            daily_life=False,
            technical_work=False,
            relationship_pressure=True,
            rest_silence=False,
            pressure_level="high",
            max_visible_chars=150,
            draft_bias="answer the relationship/persona pressure without product/support language",
            memory_write_bias="relationship/emotion review only if residue is meaningful",
            proactive_constraint="block proactive until the pressure turn settles",
        )

    if daily:
        return VisibleTurnContext(
            turn_kind="daily_life",
            speaker_is_owner=is_owner,
            owner_style_pressure=False,
            owner_no_change_pressure=False,
            daily_life=True,
            technical_work=False,
            relationship_pressure=False,
            rest_silence=False,
            pressure_level="low",
            max_visible_chars=90,
            draft_bias="ordinary private-chat reply; do not inflate daily life into analysis",
            memory_write_bias="no durable write unless owner marks it meaningful",
            proactive_constraint="unchanged",
        )

    return VisibleTurnContext(
        turn_kind="ordinary_owner_chat" if is_owner else "external_chat",
        speaker_is_owner=is_owner,
        owner_style_pressure=False,
        owner_no_change_pressure=False,
        daily_life=False,
        technical_work=False,
        relationship_pressure=False,
        rest_silence=False,
        pressure_level="normal",
        max_visible_chars=160 if is_owner else 120,
        draft_bias="natural compact reply",
        memory_write_bias="selective memory only",
        proactive_constraint="unchanged",
    )
