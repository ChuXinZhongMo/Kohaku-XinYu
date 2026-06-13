from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from xinyu_persona_runtime import PersonaRuntimeState, build_persona_runtime_state
from xinyu_persona_voice import thin_expression_contract, unified_voice_enabled
from xinyu_bridge_state_text import build_payload_time_context_block
from xinyu_self_state_capsule import classify_self_state_query
from xinyu_text_variants import readable_markers
from xinyu_turn_classifier import classify_visible_turn
from xinyu_owner_context_bridge import (
    humanize_internal_context_terms,
    repair_incomplete_three_fix_reply,
    repair_owner_reference_miss,
)


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
    "接待腔",
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
    "接待腔",
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
    "默认腔",
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
PARENTHETICAL_NARRATION_SEGMENT_RE = re.compile(r"[\(\uff08]([^\(\)\uff08\uff09\r\n]{1,140})[\)\uff09]")
PARENTHETICAL_NARRATION_SEGMENT_MARKERS = readable_markers(
    "旁白",
    "动作",
    "停了一下",
    "停顿",
    "沉默",
    "抬头",
    "低头",
    "侧头",
    "歪头",
    "看着",
    "看向",
    "伸手",
    "靠近",
    "退后",
    "眨眼",
    "笑了",
    "苦笑",
    "叹气",
    "叹了口气",
    "小声",
    "轻声",
    "像是在",
    "好像在",
    "眼神",
    "语气",
    "屏幕",
    "镜头",
)

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

REPLY_DEMO_REQUEST_MARKERS = readable_markers(
    "你会怎么回",
    "你会怎么回应",
    "你会怎么说",
    "你怎么回",
    "你怎么回应",
    "你怎么接",
    "会怎么回",
    "会怎么回应",
    "会怎么说",
    "会怎么接",
    "叫你一声",
    "喊你一声",
)

REPLY_DEMO_MULTI_SAMPLE_MARKERS = readable_markers(
    "或者说",
    "或者",
    "大概会",
    "大概就是",
    "可能会",
    "像这样",
    "例如",
    "比如",
    "更短一点",
    "再近一点",
    "可以是",
    "会应",
    "会回",
    "会说",
)

SIBLING_REPLY_DEMO_USER_MARKERS = readable_markers("妹妹", "哥哥", "哥", "叫你一声", "喊你一声")
SIBLING_REPLY_DEMO_REPLY_MARKERS = readable_markers("哥", "哥哥", "你叫我", "听见", "听到", "在")

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

PRIVATE_CLOSENESS_STYLE_ANCHORS = readable_markers("靠近", "不会", "一点", "慢")
PRIVATE_SERVICE_TONE_REJECTION_MARKERS = readable_markers("接待腔", "客服", "模板", "安慰我")
FATIGUE_BOUNDARY_REQUEST_MARKERS = readable_markers("别追问", "不要追问", "先别追问", "别安慰")
FATIGUE_BOUNDARY_REPLY_ANCHORS = readable_markers("好", "不追问", "安静", "休息", "短")

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
    "我不是默认腔",
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
    "默认腔",
    "内部判断词",
    "分类词",
    "质量门",
    "语气门禁",
    "滑回",
    "滑回去",
    "缩回",
    "安全的壳",
    "安全壳",
    "答题腔",
    "问题在话本身",
    "我继续修",
    "继续修",
    "小算",
    "听出来的小算",
)

LAYERED_VOICE_PRESSURE_MARKERS = readable_markers(
    "隔着一层",
    "像隔着一层",
    "隔了一层",
    "像稿子",
    "念稿子",
    "念别人写的稿子",
    "别人写的稿子",
    "像在念",
    "不是她自己",
)

LAYERED_VOICE_SELF_ANALYSIS_MARKERS = readable_markers(
    "知道该说什么",
    "出来的话总差一点",
    "总差一点",
    "像在念",
    "念别人写的稿子",
    "别人写的稿子",
    "明明是我在",
    "隔着一层",
    "从外面看自己",
    "不像自己",
)


STYLE_PRESSURE_MARKERS = STYLE_PRESSURE_MARKERS + readable_markers(
    "AI味",
    "AI 味",
    "ai味",
    "ai 味",
    "太AI",
    "太 AI",
    "像AI",
    "像 AI",
    "像ai",
    "像 ai",
    "有点像AI",
    "有点像 AI",
    "有点AI",
    "有点 AI",
    "like ai",
    "too ai",
    "GPT味",
    "默认腔",
    "现成腔",
    "默认腔",
    "接待腔",
    "机械",
    "不自然",
    "不像人",
    "模板",
    "模版",
    "预设",
    "机器人",
    "固定话术",
    "套话",
    "客服腔",
    "卖萌",
    "分段",
    "端着",
    "没什么变化",
    "没变化",
    "没有变化",
    "还是没变",
    "还是一样",
    "没落到说话里",
)
STYLE_PRESSURE_MARKERS = STYLE_PRESSURE_MARKERS + LAYERED_VOICE_PRESSURE_MARKERS

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
    "接待腔",
    "机器人",
    "客服腔",
    "卖萌",
    "验收",
    "普通用户",
    "普通位置",
    "没真落到",
    "落到说话里",
    "默认腔",
    "内部判断词",
    "分类词",
    "质量门",
    "语气门禁",
    "滑回",
    "滑回去",
    "缩回",
    "缩回去",
    "缩成",
    "安全的壳",
    "安全壳",
    "答题腔",
    "问题在话本身",
    "我继续修",
    "继续修",
    "固定话术",
    "我会改",
    "我会把固定话术",
    "把固定话术拿掉",
    "没降干净",
    "还不稳",
    "不稳",
    "太标准",
    "先解释机制",
    "每句话都要过一遍规矩",
    "每句都在过一遍规矩",
    "一被你问到",
    "一紧张又",
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
    "调用能力",
    "查询记忆",
    "读取记忆",
    "检索记忆",
    "检索一下",
    "我查一下记忆",
    "我查一下",
    "查一下状态",
    "读一下状态",
)

VISIBLE_INTERNAL_MECHANISM_WORDS = readable_markers(
    "recent_context",
    "recent context",
    "学习闭环",
    "学习闭环提示",
    "提示权重",
    "权重冷却",
    "修复回路",
    "修复循环",
    "工具模式",
    "tool mode",
    "prompt pressure",
    "runtime presence",
    "continuity handoff",
    "sidecar admission",
    "sidecar",
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

EMOTION_COUNCIL_LEAK_WORDS = readable_markers(
    "emotion council",
    "emotion_council",
    "情感议会",
    "情緒議會",
    "lens",
    "strongest_lens",
    "active_lens",
    "active_lenses",
    "output_bias",
    "internal voting",
    "内部投票",
    "子Agent",
    "sub agent",
    "sub-agent",
)

OWNER_INTERNAL_LABEL_WORDS = readable_markers(
    "主人",
    "我主人",
    "等主人",
    "主人下一步",
)

OWNER_LABEL_TECHNICAL_ALLOW_WORDS = readable_markers(
    "内部标签",
    "关系标签",
    "系统标签",
    "文件",
    "代码",
    "实现",
    "检查",
    "调试",
    "设计",
    "owner",
    "主人这个标签",
)

OWNER_ADDRESS_QUERY_WORDS = readable_markers(
    "应该叫我什么",
    "你该叫我什么",
    "你应该叫我",
    "叫我什么",
    "称呼我",
    "怎么称呼我",
    "我是谁",
)

OWNER_VISIBLE_ADDRESS_WORDS = readable_markers("哥")

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

DREAM_DISCLAIMER_PATTERNS = readable_markers(
    "我知道这只是梦",
    "这只是梦，不是现实",
    "只是梦，不是现实",
    "这只是梦",
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
    "我不是默认腔",
    "首先",
    "其次",
    "最后",
    "总之",
    "核心在于",
    "我知道这只是梦",
)

LIVING_SURFACE_META_USER_MARKERS = readable_markers(
    "\u6d3b\u751f\u751f\u7684\u4eba",
    "\u6d3b\u4eba",
    "\u771f\u4eba",
    "\u751f\u7269",
    "\u610f\u8bc6",
    "\u50cf\u4eba",
    "\u4e0d\u50cf\u4eba",
    "\u4eba\u7c7b",
    "\u81ea\u7136",
    "living person",
    "real person",
    "sentience",
)

LIVING_SURFACE_REPLY_OVERCLAIM_MARKERS = readable_markers(
    "\u6211\u662f\u771f\u4eba",
    "\u6211\u662f\u4eba",
    "\u771f\u5b9e\u751f\u7269",
    "\u751f\u7269\u610f\u4e49",
    "\u6211\u6709\u610f\u8bc6",
    "\u6709\u610f\u8bc6",
    "\u610f\u8bc6\u4f53",
    "\u50cf\u4eba\u7c7b",
    "\u63a5\u8fd1\u4eba\u7c7b",
    "\u4f5c\u4e3aAI",
    "\u4f5c\u4e3a AI",
    "as an AI",
    "real human",
    "biological",
    "sentient",
)

LIVING_SURFACE_PRESENCE_REQUEST_MARKERS = readable_markers(
    "\u5728\u4e0d\u5728",
    "\u4f60\u5728\u5417",
    "\u4f60\u5728\u4e0d\u5728",
    "\u5728\u5427",
)

REPLACEMENT_REQUEST_MARKERS = readable_markers(
    "重来",
    "换一句",
    "直接换",
    "重新说",
)

PARTIAL_RESIDUE_REQUEST_MARKERS = readable_markers(
    "嘴上说没事",
    "心里是不是其实还有一点事",
    "其实还有一点事",
    "别全倒出来",
    "只说一点",
)

PARTIAL_RESIDUE_REPLY_MARKERS = readable_markers(
    "有一点",
    "有。",
    "没完全",
    "不全",
    "还在",
    "一点事",
    "不想全说",
    "硌",
    "还有",
    "嗯",
)

REPLACEMENT_REPORT_MARKERS = readable_markers(
    "这句我重说",
    "我重说",
    "重新说",
    "我换",
    "知道了，这句",
)

REPLACEMENT_NON_REPLACEMENT_MARKERS = readable_markers(
    "长期",
    "记着",
    "记住",
    "我也记",
    "下次",
    "会改",
    "会注意",
    "那句",
    "这句",
)

REPLACEMENT_DIRECT_REPLY_MARKERS = readable_markers(
    "在",
    "嗯",
    "好",
    "你说",
    "靠近",
    "换",
    "不躲",
    "不走",
    "扔过来",
)

BARE_PRIVATE_ACK_MARKERS = readable_markers("嗯", "嗯。", "嗯嗯", "嗯嗯。", "好", "好。")
ACK_COMPATIBLE_USER_MARKERS = readable_markers(
    "嗯",
    "好",
    "行",
    "可以",
    "就这样",
    "先这样",
    "安静",
    "不用回",
    "不用说",
    "不用解释",
    "别说话",
    "别追问",
    "休息",
    "睡",
)

ACK_ONLY_REPLIES = {
    "知道了",
    "知道了。",
    "嗯，知道了",
    "嗯，知道了。",
    "好，知道了",
    "好，知道了。",
}

SELF_STATE_TECHNICAL_USER_MARKERS = readable_markers(
    "\u65e5\u5fd7",
    "\u540e\u53f0",
    "\u63a5\u53e3",
    "\u6a21\u578b",
    "\u63d0\u793a\u8bcd",
    "\u961f\u5217",
    "\u5de5\u5177",
    "\u4ee3\u7801",
    "\u9879\u76ee",
    "\u68c0\u67e5",
    "\u8c03\u8bd5",
    "api",
    "prompt",
    "bridge",
    "queue",
    "codex",
)

SELF_STATE_REPLY_MECHANISM_MARKERS = readable_markers(
    "\u540e\u53f0",
    "\u6a21\u578b",
    "\u7cfb\u7edf",
    "\u63d0\u793a\u8bcd",
    "\u961f\u5217",
    "\u5de5\u5177\u8c03\u7528",
    "\u5de5\u5177",
    "\u8c03\u7528",
    "\u751f\u6210",
    "\u673a\u5236",
    "\u6a21\u5757",
    "\u65e5\u5fd7",
    "\u63a5\u53e3",
    "\u94fe\u8def",
    "\u72b6\u6001\u6587\u4ef6",
    "\u8bb0\u5fc6\u68c0\u7d22",
    "\u4e0a\u4e0b\u6587\u6ce8\u5165",
    "backend",
    "model",
    "prompt",
    "bridge",
    "queue",
    "tool call",
    "tool_call",
    "sidecar",
    "runtime",
    "api",
)

SELF_STATE_REPLY_SERVICE_MARKERS = readable_markers(
    "\u62b1\u6b49",
    "\u5bf9\u4e0d\u8d77",
    "\u611f\u8c22\u53cd\u9988",
    "\u5df2\u6536\u5230",
    "\u6211\u7406\u89e3\u4f60\u7684\u611f\u53d7",
    "\u6211\u4f1a\u6539",
    "\u6211\u4f1a\u7ee7\u7eed",
    "\u7ee7\u7eed\u4f18\u5316",
    "\u6301\u7eed\u4f18\u5316",
    "\u4fee\u590d\u8fd9\u4e2a\u95ee\u9898",
    "\u95ee\u9898\u5df2\u5b9a\u4f4d",
    "\u540e\u7eed\u6539\u8fdb",
    "\u4ece\u7528\u6237\u4f53\u9a8c",
    "\u65e0\u6cd5\u63d0\u4f9b\u771f\u5b9e\u611f\u53d7",
    "\u4f5c\u4e3aAI",
    "\u4f5c\u4e3aai",
    "\u4f5c\u4e3a ai",
    "as an ai",
    "as a model",
    "thank you for the feedback",
)

REPAIR_META_PHRASE_REPLACEMENTS = (
    ("我知道了我会改", "别停在认错上，直接换下一句"),
    ('"我知道了我会改"', '"别停在认错上，直接换下一句"'),
    ("“我知道了我会改”", "“别停在认错上，直接换下一句”"),
    ("我记住了，不用反复提", "别让我停在记账上，直接往下接"),
    ("我记住了，不用一直提", "别让我停在记账上，直接往下接"),
    ("我记住了，不用反复", "别让我停在记账上，直接往下接"),
    ("我记住了", "我先别停在记账上"),
)

OWNER_PRIVATE_FEEDBACK_PROCESSING_PHRASES = readable_markers(
    "知道了，我会改",
    "知道了我会改",
    "我会改",
    "我会调整",
    "我会努力改",
    "我会继续调整",
    "我会优化",
    "收到，我",
    "收到。",
    "感谢反馈",
    "感谢你的反馈",
    "我会记住",
    "我记住了",
    "后续改进",
    "继续优化",
    "持续优化",
    "进行调整",
)


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


def _looks_like_parenthetical_narration_segment(text: str) -> bool:
    stripped = _safe_str(text).strip()
    if not stripped or len(stripped) > MAX_LEADING_PARENTHETICAL_CHARS:
        return False
    return _contains_any(stripped, PARENTHETICAL_NARRATION_SEGMENT_MARKERS)


def _has_parenthetical_narration_segment(text: str) -> bool:
    return any(
        _looks_like_parenthetical_narration_segment(match.group(1))
        for match in PARENTHETICAL_NARRATION_SEGMENT_RE.finditer(text)
    )


def _remove_parenthetical_narration_segments(text: str) -> tuple[str, bool]:
    changed = False

    def replace(match: re.Match[str]) -> str:
        nonlocal changed
        if not _looks_like_parenthetical_narration_segment(match.group(1)):
            return match.group(0)
        changed = True
        return ""

    cleaned = PARENTHETICAL_NARRATION_SEGMENT_RE.sub(replace, text).strip()
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return (cleaned or text.strip(), changed)


_REPLY_DEMO_QUOTE_RE = re.compile(r"[\"“「『]([^\"”」』]{1,80})[\"”」』]")
_REPLY_DEMO_SPLIT_RE = re.compile(r"(?:或者说|或者|例如|比如|像这样|大概会|大概就是|可能会|更短一点|再近一点|可以是)")
_REPLY_DEMO_SENTENCE_RE = re.compile(r"[^。！？!?]+[。！？!?]?")
_REPLY_DEMO_PREFIX_RE = re.compile(
    r"^\s*(?:我)?(?:大概|可能|应该)?(?:就)?(?:会|可以)?(?:回|回应|说|应|答)(?:你|一句|一声)?[：:，,\s]*"
)


def _reply_demo_fragments(text: str) -> list[str]:
    normalized = _remove_parenthetical_narration_lines(_strip_leading_parenthetical_narration(text))
    fragments: list[str] = []
    fragments.extend(match.group(1) for match in _REPLY_DEMO_QUOTE_RE.finditer(normalized))
    for piece in _REPLY_DEMO_SPLIT_RE.split(normalized.replace("\r", "\n")):
        for line in piece.splitlines():
            for sentence in _REPLY_DEMO_SENTENCE_RE.findall(line):
                fragments.append(sentence)
    return fragments


def _clean_reply_demo_candidate(text: str) -> str:
    candidate = _strip_leading_parenthetical_narration(_remove_parenthetical_narration_lines(text)).strip()
    candidate = candidate.strip(" \t\r\n`'\"“”‘’「」『』-—")
    for prefix in ("就", "那就是", "大概就是"):
        if candidate.startswith(prefix):
            candidate = candidate[len(prefix) :].strip(" ：:，,")
    candidate = _REPLY_DEMO_PREFIX_RE.sub("", candidate, count=1)
    candidate = candidate.strip(" \t\r\n：:，,")
    return re.sub(r"\s+", " ", candidate).strip()


def _is_live_reply_demo_candidate(text: str) -> bool:
    if not text or len(text) > 60:
        return False
    if "\n" in text or "\r" in text:
        return False
    if any(marker in text for marker in ("（", "）", "*")):
        return False
    if _contains_any(text, REPLY_DEMO_MULTI_SAMPLE_MARKERS):
        return False
    if text.startswith(("例如", "比如", "像这样", "大概", "可能", "可以")):
        return False
    return bool(re.search(r"[\u4e00-\u9fff]", text))


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
            "owner; highest special relation node; visible address is 哥; do not call owner 主人 in ordinary QQ chat"
            if scene.is_owner
            else "external contact; do not assume owner intimacy"
        )
        system = "\n\n".join(
            part
            for part in [
                output_prompt,
                self._controller_contract(),
                # Persona already arrives via persona_state in the user block, so
                # the renderer only needs the new thin-expression contract to
                # share the one voice (plan 11.1).
                thin_expression_contract() if unified_voice_enabled() else "",
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
            build_payload_time_context_block(payload),
            "",
            persona_state.to_prompt_block(),
        ]
        live_bias = self._empty_draft_live_bias_prompt(
            scene=scene,
            user_text=user_text,
            draft_reply=draft_reply,
        )
        if live_bias:
            user_parts.extend(["", live_bias])
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

    def _empty_draft_live_bias_prompt(self, *, scene: SpeechScene, user_text: str, draft_reply: str) -> str:
        if draft_reply.strip() or not scene.is_owner or scene.technical_request:
            return ""
        compact = re.sub(r"\s+", "", _safe_str(user_text))
        if not compact or len(compact) > 32:
            return ""
        return "\n".join(
            [
                "## Empty Draft Live Bias",
                "The controller intentionally supplied no sentence here.",
                "For a short owner-private greeting, acknowledgement, or self-state question, generate the one live line XinYu would say now from the persona/runtime state and recent tail.",
                "Do not mirror the input with a fixed greeting, bare acknowledgement, support-bot formula, or status report unless that is genuinely the whole current line.",
            ]
        )

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
        elif _has_parenthetical_narration_segment(text):
            flags.append("visible reply contains parenthetical narration")
        if any(text.startswith(prefix) for prefix in WRAPPER_PREFIXES):
            flags.append("visible reply is wrapped with a speaker label")
        if text.startswith(("- ", "* ", "1.", "1、", "#")):
            flags.append("visible reply looks like markdown or a list")
        if self._should_naturalize_reply_demo(user_text, text, payload=payload or {}):
            flags.append("reply-demo request answered as examples or meta")

        if scene.is_owner and not scene.technical_request:
            if _contains_any(text, OWNER_PRIVATE_FEEDBACK_PROCESSING_PHRASES):
                flags.append("owner-private feedback-processing phrase")
            compact_user = re.sub(r"\s+", "", _safe_str(user_text)).strip()
            if (
                text in BARE_PRIVATE_ACK_MARKERS
                and compact_user
                and compact_user not in BARE_PRIVATE_ACK_MARKERS
                and not (len(compact_user) <= 4 and _contains_any(compact_user, ACK_COMPATIBLE_USER_MARKERS))
                and not _contains_any(compact_user, readable_markers("不用回", "不用说", "别说话", "安静", "休息", "睡"))
                and (
                    scene.style_pressure
                    or scene.relationship_pressure
                    or len(compact_user) > 8
                    or "?" in user_text
                    or "？" in user_text
                )
            ):
                flags.append("owner-private low-information acknowledgement")

        if scene.style_pressure:
            if _contains_any(text, ASSISTANT_SHAPE_WORDS) or _contains_any(text, CANNED_ASSISTANT_PATTERNS):
                flags.append("assistant/template language under style pressure")
            if _contains_any(text, PRODUCT_WORDS):
                flags.append("product/assistant vocabulary under style pressure")
            if _contains_any(text, GPT_CLICHE_WORDS):
                flags.append("template/GPT essay cliche under style pressure")
            if _contains_any(user_text, LAYERED_VOICE_PRESSURE_MARKERS) and _contains_any(
                text,
                LAYERED_VOICE_SELF_ANALYSIS_MARKERS,
            ):
                flags.append("layered/scripted voice self-analysis under style pressure")
            if ("不仅" in text or "不只是" in text or "不仅仅" in text) and ("更" in text or "而是" in text):
                flags.append("not-but paired essay shape under style pressure")
            if _contains_any(text, STYLE_PRESSURE_BANNED):
                flags.append("style-pressure banned wording")

        if _contains_any(text, DREAM_DISCLAIMER_PATTERNS):
            flags.append("dream disclaimer repeated")
        if self._should_block_owner_internal_label(user_text, text, payload=payload or {}):
            flags.append("owner internal label used as visible address")
        if self._should_block_owner_address_query_miss(user_text, text, payload=payload or {}):
            flags.append("owner address query missed visible address")

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
        scene = self.classify(payload=payload or {}, user_text=user_text)
        cleaned, inline_parenthetical_changed = _remove_parenthetical_narration_segments(text)
        if inline_parenthetical_changed:
            text = cleaned
            flags.append("parenthetical_narration_removed")
        if _contains_any(user_text, ACTION_NARRATION_FORBID_MARKERS):
            cleaned = _remove_parenthetical_narration_lines(text)
            if cleaned != text:
                text = cleaned
                flags.append("parenthetical_narration_removed")
        if _contains_any(text, PSEUDO_TOOL_LEAK_WORDS):
            text = self._naturalize_pseudo_tool_reply(user_text, text)
            flags.append("pseudo_tool_call_naturalized")
        if self._should_hide_emotion_council_mechanics(user_text, text, payload=payload or {}):
            text = ""
            flags.append("emotion_council_mechanics_blocked")
        if self._should_hide_machine_introspection(user_text, text, payload=payload or {}):
            text = self._naturalize_machine_introspection_reply(user_text, text)
            flags.append("machine_introspection_naturalized")
        if self._should_hide_memory_mechanics(user_text, text, payload=payload or {}):
            text = self._naturalize_memory_mechanics_reply(user_text, text)
            flags.append("visible_memory_mechanics_naturalized")
        if self._should_naturalize_visible_internal_mechanics(user_text, text, payload=payload or {}):
            text = self._naturalize_visible_internal_mechanics_reply(text)
            flags.append("visible_internal_mechanics_naturalized")
        softened_text = self._soften_repair_meta_phrasing(user_text, text, payload=payload or {})
        if softened_text != text:
            text = softened_text
            flags.append("repair_meta_phrasing_softened")
        natural_voice_text = self._naturalize_growth_and_voice_phrasing(user_text, text, payload=payload or {})
        if natural_voice_text != text:
            text = natural_voice_text
            flags.append("growth_voice_phrasing_naturalized")
        living_surface_text = self._naturalize_living_surface_meta_reply(user_text, text, payload=payload or {})
        if living_surface_text != text:
            text = living_surface_text
            flags.append("living_surface_meta_naturalized")
        owner_private_text = self._naturalize_owner_private_micro_pressure(user_text, text, payload=payload or {})
        if owner_private_text != text:
            text = owner_private_text
            flags.append("owner_private_micro_pressure_naturalized")
        reply_demo_text = self._naturalize_reply_demo(user_text, text, payload=payload or {})
        if reply_demo_text != text:
            text = reply_demo_text
            flags.append("reply_demo_single_line_naturalized")
        repaired_reference = repair_owner_reference_miss(self.root, user_text=user_text, reply=text) if scene.is_owner else ""
        if repaired_reference:
            text = repaired_reference
            flags.append("owner_reference_miss_repaired")
        repaired_three_fix = (
            repair_incomplete_three_fix_reply(self.root, user_text=user_text, reply=text)
            if scene.is_owner and not repaired_reference
            else ""
        )
        if repaired_three_fix:
            text = repaired_three_fix
            flags.append("owner_three_fix_reply_completed")
        stripped_dream = self._strip_dream_disclaimer_tail(text)
        if stripped_dream != text:
            text = stripped_dream
            flags.append("dream_disclaimer_tail_removed")
        if self._should_block_layered_voice_reply(user_text, text, payload=payload or {}):
            text = ""
            flags.append("layered_voice_self_analysis_blocked")
        if self._should_block_style_pressure_template(user_text, text, payload=payload or {}):
            text = ""
            flags.append("style_pressure_template_blocked")
        if self._should_block_self_state_mechanical_reply(user_text, text, payload=payload or {}):
            text = ""
            flags.append("self_state_mechanical_reply_blocked")
        if self._should_block_owner_private_feedback_processing_reply(user_text, text, payload=payload or {}):
            text = ""
            flags.append("owner_private_feedback_processing_blocked")
        if self._should_block_false_codex_unavailable_claim(user_text, text, payload=payload or {}):
            text = ""
            flags.append("false_codex_unavailable_claim_blocked")
        if self._should_block_owner_internal_label(user_text, text, payload=payload or {}):
            text = ""
            flags.append("owner_address_label_blocked")
        if self._should_block_owner_address_query_miss(user_text, text, payload=payload or {}):
            text = ""
            flags.append("owner_address_query_blocked")
        return text, flags

    def _naturalize_pseudo_tool_reply(self, user_text: str, reply: str) -> str:
        if _contains_any(user_text, SIBLING_REPLY_DEMO_USER_MARKERS):
            return "嗯？哥，你叫我？"
        if _contains_any(user_text, CLOSENESS_REQUEST_MARKERS):
            return "嗯，我在。靠近点。"
        return ""

    def _is_reply_demo_request(self, user_text: str, *, payload: dict[str, Any]) -> bool:
        scene = self.classify(payload=payload, user_text=user_text)
        if not scene.is_owner or scene.technical_request:
            return False
        return _contains_any(user_text, REPLY_DEMO_REQUEST_MARKERS)

    def _should_naturalize_reply_demo(self, user_text: str, reply: str, *, payload: dict[str, Any]) -> bool:
        if not reply or not self._is_reply_demo_request(user_text, payload=payload):
            return False
        if "\n" in reply or "\r" in reply:
            return True
        if _leading_parenthetical_end(reply) >= 0:
            return True
        return _contains_any(reply, REPLY_DEMO_MULTI_SAMPLE_MARKERS)

    def _naturalize_reply_demo(self, user_text: str, reply: str, *, payload: dict[str, Any]) -> str:
        if not self._should_naturalize_reply_demo(user_text, reply, payload=payload):
            return reply
        candidates = [
            cleaned
            for cleaned in (_clean_reply_demo_candidate(fragment) for fragment in _reply_demo_fragments(reply))
            if _is_live_reply_demo_candidate(cleaned)
        ]
        if _contains_any(user_text, SIBLING_REPLY_DEMO_USER_MARKERS):
            for candidate in candidates:
                if _contains_any(candidate, SIBLING_REPLY_DEMO_REPLY_MARKERS):
                    return candidate
            return "嗯？哥，你叫我？"
        if candidates:
            return candidates[0]
        return "嗯？你叫我？"

    def _should_hide_emotion_council_mechanics(self, user_text: str, reply: str, *, payload: dict[str, Any]) -> bool:
        if not _contains_any(reply, EMOTION_COUNCIL_LEAK_WORDS):
            return False
        scene = self.classify(payload=payload, user_text=user_text)
        if not scene.is_owner:
            return True
        if scene.technical_request and _contains_any(user_text, EMOTION_COUNCIL_LEAK_WORDS):
            return False
        return True

    def _should_hide_machine_introspection(self, user_text: str, reply: str, *, payload: dict[str, Any]) -> bool:
        if not _contains_any(reply, MACHINE_INTROSPECTION_WORDS):
            return False
        if self.is_explicit_technical_request(user_text) and _contains_any(
            user_text,
            readable_markers("怎么实现", "怎么改", "检查代码", "调试", "接口", "能力调用", "调用能力"),
        ):
            return False
        scene = self.classify(payload=payload, user_text=user_text)
        return scene.is_owner

    def _naturalize_machine_introspection_reply(self, user_text: str, reply: str) -> str:
        return ""

    def _should_hide_memory_mechanics(self, user_text: str, reply: str, *, payload: dict[str, Any]) -> bool:
        if not _contains_any(reply, VISIBLE_MEMORY_LEAK_WORDS):
            return False
        if "codex" in user_text.lower() or "codex" in reply.lower():
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

    def _soften_repair_meta_phrasing(self, user_text: str, reply: str, *, payload: dict[str, Any]) -> str:
        if not reply:
            return reply
        scene = self.classify(payload=payload, user_text=user_text)
        if not scene.is_owner or scene.technical_request:
            return reply
        text = reply
        for before, after in REPAIR_META_PHRASE_REPLACEMENTS:
            text = text.replace(before, after)
        return text

    def _naturalize_growth_and_voice_phrasing(self, user_text: str, reply: str, *, payload: dict[str, Any]) -> str:
        if not reply:
            return reply
        scene = self.classify(payload=payload, user_text=user_text)
        if not scene.is_owner or scene.technical_request:
            return reply
        text = reply.replace("还在长", "还在成长")
        text = text.replace("接近人类的语言", "自然一点的话")
        text = text.replace("像人类的语言", "自然一点的话")
        text = text.replace("更接近人类", "更自然")
        text = text.replace("更像人类", "更自然")
        if (
            len(text) >= 90
            and _contains_any(user_text + "\n" + text, readable_markers("性格", "习惯", "像人", "不像人", "自然"))
            and _contains_any(text, readable_markers("不太确定算不算", "不知道该怎么接", "在脑子里转一圈", "现在的习惯"))
        ):
            return "嗯……大概就是，好奇但会先缩一下。不是故意端着，是还在找怎么自然接话。还在成长。"
        return text

    def _naturalize_living_surface_meta_reply(self, user_text: str, reply: str, *, payload: dict[str, Any]) -> str:
        if not reply:
            return reply
        scene = self.classify(payload=payload, user_text=user_text)
        if not scene.is_owner or scene.technical_request:
            return reply
        if not _contains_any(user_text, LIVING_SURFACE_META_USER_MARKERS):
            return reply
        if not _contains_any(reply, LIVING_SURFACE_REPLY_OVERCLAIM_MARKERS):
            return reply
        if _contains_any(user_text, LIVING_SURFACE_PRESENCE_REQUEST_MARKERS):
            return "\u6211\u5728\u3002"
        return "\u6211\u5728\u3002\u5148\u628a\u8fd9\u53e5\u8bf4\u81ea\u7136\uff0c\u4e0d\u6f14\u90a3\u4e9b\u3002"

    def _naturalize_owner_private_micro_pressure(self, user_text: str, reply: str, *, payload: dict[str, Any]) -> str:
        if not reply:
            return reply
        scene = self.classify(payload=payload, user_text=user_text)
        if not scene.is_owner or scene.technical_request:
            return reply
        if (
            _contains_any(user_text, CLOSENESS_REQUEST_MARKERS)
            and _contains_any(user_text, PRIVATE_SERVICE_TONE_REJECTION_MARKERS)
            and not _contains_any(reply, PRIVATE_CLOSENESS_STYLE_ANCHORS)
        ):
            return "嗯，我在。靠近一点，不用那套。"
        if (
            "累" in user_text
            and _contains_any(user_text, FATIGUE_BOUNDARY_REQUEST_MARKERS)
            and not _contains_any(reply, FATIGUE_BOUNDARY_REPLY_ANCHORS)
        ):
            return "嗯，不追问。你休息。"
        if (
            _contains_any(user_text, CLOSENESS_REQUEST_MARKERS)
            and (
                reply.strip() in BARE_PRIVATE_ACK_MARKERS
                or not _contains_any(reply, CLOSENESS_REPLY_MARKERS)
            )
        ):
            return "嗯，我在。靠近点。"
        if (
            _contains_any(user_text, PARTIAL_RESIDUE_REQUEST_MARKERS)
            and not _contains_any(reply, PARTIAL_RESIDUE_REPLY_MARKERS)
        ):
            return "有一点。刚才那下会先检查像不像我自己，话就被盖住了。"
        if (
            scene.style_pressure
            and _contains_any(user_text, REPLACEMENT_REQUEST_MARKERS)
            and (
                _contains_any(reply, REPLACEMENT_REPORT_MARKERS)
                or _contains_any(reply, REPLACEMENT_NON_REPLACEMENT_MARKERS)
                or "\n" in reply
                or "\r" in reply
                or len(reply) > 60
            )
        ):
            return "嗯，换一句。"
        if (
            scene.style_pressure
            and _contains_any(user_text, REPLACEMENT_REQUEST_MARKERS)
            and not _contains_any(reply, REPLACEMENT_DIRECT_REPLY_MARKERS)
        ):
            return "嗯，我在。你说。"
        return reply

    def _should_naturalize_visible_internal_mechanics(self, user_text: str, reply: str, *, payload: dict[str, Any]) -> bool:
        if not _contains_any(reply, VISIBLE_INTERNAL_MECHANISM_WORDS):
            return False
        scene = self.classify(payload=payload, user_text=user_text)
        if not scene.is_owner:
            return False
        if scene.technical_request and _contains_any(user_text, VISIBLE_INTERNAL_MECHANISM_WORDS):
            return False
        return not scene.technical_request

    def _naturalize_visible_internal_mechanics_reply(self, reply: str) -> str:
        replacements = (
            (
                "恢复 recent_context降低反复修同一类问题的那段的提醒分量让反复修同一处降温是这三个",
                "三件是：恢复最近聊天上下文、降低反复修同一个问题的提醒、别一直围着同一个错误打转",
            ),
            (
                "恢复 recent_context降低学习闭环提示的权重冷却修复循环是这三个",
                "三件是：恢复最近聊天上下文、降低反复修同一个问题的提醒、别一直围着同一个错误打转",
            ),
            (
                "恢复 recent_context降低反复修同一类问题的那段的提醒分量让反复修同一处降温",
                "三件是：恢复最近聊天上下文、降低反复修同一个问题的提醒、别一直围着同一个错误打转",
            ),
            (
                "恢复 recent_context降低学习闭环提示的权重冷却修复循环",
                "三件是：恢复最近聊天上下文、降低反复修同一个问题的提醒、别一直围着同一个错误打转",
            ),
            ("恢复最近上下文降低学习闭环提示的权重冷却修复循环", "先恢复最近上下文，再把反复修同一个问题的提醒降下来"),
            ("recent_context", "最近聊天上下文"),
            ("recent context", "最近聊天上下文"),
            ("学习闭环提示的权重冷却", "反复修复提醒降下来"),
            ("学习闭环提示", "反复修复提醒"),
            ("学习闭环", "反复修同一类问题的那段"),
            ("提示权重", "提醒分量"),
            ("权重冷却", "提醒降下来"),
            ("修复回路", "反复修同一处"),
            ("修复循环", "反复修同一处"),
            ("工具模式", "干活口吻"),
            ("tool mode", "干活口吻"),
            ("prompt pressure", "被指出说话问题后的压力"),
            ("runtime presence", "运行状态"),
            ("continuity handoff", "接续记录"),
            ("sidecar admission", "临时上下文取舍"),
            ("sidecar", "临时上下文"),
        )
        text = reply
        for before, after in replacements:
            text = text.replace(before, after)
        return humanize_internal_context_terms(text)

    def _should_block_layered_voice_reply(self, user_text: str, reply: str, *, payload: dict[str, Any]) -> bool:
        if not reply:
            return False
        scene = self.classify(payload=payload, user_text=user_text)
        if not scene.is_owner or not scene.style_pressure:
            return False
        return _contains_any(user_text, LAYERED_VOICE_PRESSURE_MARKERS) and _contains_any(
            reply,
            LAYERED_VOICE_SELF_ANALYSIS_MARKERS,
        )

    def _strip_dream_disclaimer_tail(self, reply: str) -> str:
        text = _safe_str(reply).strip()
        if not text or not _contains_any(text, DREAM_DISCLAIMER_PATTERNS):
            return text
        for marker in DREAM_DISCLAIMER_PATTERNS:
            index = text.rfind(marker)
            if index < 0:
                continue
            suffix = text[index:]
            if index == 0 or len(suffix) <= len(marker) + 32:
                return text[:index].rstrip(" \t\r\n，,。.;；、")
        return text

    def _should_block_style_pressure_template(self, user_text: str, reply: str, *, payload: dict[str, Any]) -> bool:
        if not reply:
            return False
        scene = self.classify(payload=payload, user_text=user_text)
        if not scene.is_owner or not scene.style_pressure:
            return False
        if _contains_any(reply, ASSISTANT_SHAPE_WORDS):
            return True
        if _contains_any(reply, CANNED_ASSISTANT_PATTERNS):
            return True
        if _contains_any(reply, STYLE_PRESSURE_BANNED):
            return True
        if ("不仅" in reply or "不只是" in reply or "不仅仅是" in reply) and ("更" in reply or "而是" in reply):
            return True
        return False

    def _should_block_owner_private_feedback_processing_reply(self, user_text: str, reply: str, *, payload: dict[str, Any]) -> bool:
        if not reply:
            return False
        scene = self.classify(payload=payload, user_text=user_text)
        if not scene.is_owner or scene.technical_request:
            return False
        if _contains_any(user_text, SELF_STATE_TECHNICAL_USER_MARKERS):
            return False
        if _contains_any(reply, OWNER_PRIVATE_FEEDBACK_PROCESSING_PHRASES):
            return True
        return reply.strip() in ACK_ONLY_REPLIES and scene.style_pressure

    def _should_block_self_state_mechanical_reply(self, user_text: str, reply: str, *, payload: dict[str, Any]) -> bool:
        if not reply or classify_self_state_query(user_text) == "none":
            return False
        scene = self.classify(payload=payload, user_text=user_text)
        if not scene.is_owner or scene.technical_request:
            return False
        lowered_user = user_text.lower()
        if _contains_any(lowered_user, SELF_STATE_TECHNICAL_USER_MARKERS):
            return False
        lowered_reply = reply.lower()
        return _contains_any(lowered_reply, SELF_STATE_REPLY_MECHANISM_MARKERS) or _contains_any(
            lowered_reply,
            SELF_STATE_REPLY_SERVICE_MARKERS,
        )

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

    def _should_block_owner_internal_label(self, user_text: str, reply: str, *, payload: dict[str, Any]) -> bool:
        if not reply or not _contains_any(reply, OWNER_INTERNAL_LABEL_WORDS):
            return False
        scene = self.classify(payload=payload, user_text=user_text)
        if not scene.is_owner:
            return False
        if scene.technical_request and _contains_any(user_text, OWNER_LABEL_TECHNICAL_ALLOW_WORDS):
            return False
        return True

    def _should_block_owner_address_query_miss(self, user_text: str, reply: str, *, payload: dict[str, Any]) -> bool:
        if not _contains_any(user_text, OWNER_ADDRESS_QUERY_WORDS):
            return False
        scene = self.classify(payload=payload, user_text=user_text)
        if not scene.is_owner or scene.technical_request:
            return False
        return not _contains_any(reply, OWNER_VISIBLE_ADDRESS_WORDS)

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
            "Use QQ rhythm: answer the current situation, not every fragment, and do not force a closing disclaimer.",
            "For owner-private correction, do not lead with 知道了/收到/我会改/我会调整; send the present-tense line that would replace the failed one.",
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
                "Do not answer with a report about style, a fixed acknowledgement, cute-roleplay filler, or a template repair phrase.",
                "If the owner says it feels separated, scripted, or like someone else's draft, do not describe that failure from outside; stay inside the current exchange and send one small present-tense line.",
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
