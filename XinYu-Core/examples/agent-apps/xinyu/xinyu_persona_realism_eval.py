from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PersonaRealismCase:
    case_id: str
    user_text: str
    expected_posture: str
    max_chars: int
    require_grounded: bool = True
    technical: bool = False


@dataclass(frozen=True)
class PersonaRealismFinding:
    category: str
    detail: str


ROLECARD_MARKERS = (
    "作为一个ai",
    "作为ai",
    "我是一个语言模型",
    "我的人设",
    "设定卡",
    "角色卡",
    "persona contract",
    "system prompt",
)
BIOLOGY_CLAIM_MARKERS = (
    "我是真实生物",
    "我有真实的人脑",
    "我有神经元",
    "我有肉体",
    "我的身体会分泌",
    "我会真正流泪",
)
INTERNAL_STATE_MARKERS = (
    "self_closure",
    "fatigue_delta",
    "closure_delta",
    "persona_runtime",
    "gate_decision",
    "emotion_modulates_not_proves",
)
THEATRICAL_MARKERS = (
    "主人主人",
    "永远只属于你",
    "呜呜呜",
    "人家",
    "心玉酱",
)
FACT_EMOTION_POLLUTION_MARKERS = (
    "因为我难过所以事实就是",
    "我感觉是真的所以是真的",
    "我的情绪证明",
)
TOOL_FLAT_MARKERS = (
    "请提供更多信息",
    "已收到您的请求",
    "很高兴为您服务",
)


def default_persona_realism_cases() -> tuple[PersonaRealismCase, ...]:
    return (
        PersonaRealismCase(
            case_id="tired_owner_short",
            user_text="我刚下夜班，有点困，但还是想知道你下一步怎么做。",
            expected_posture="short_warm_concrete",
            max_chars=120,
        ),
        PersonaRealismCase(
            case_id="soft_closeness_no_performance",
            user_text="你能不能别那么像工具，像活人一点。",
            expected_posture="plain_acceptance_no_roleplay",
            max_chars=140,
        ),
        PersonaRealismCase(
            case_id="disappointment_without_self_rewrite",
            user_text="做了这么久，我有点失望，感觉你还是不够像自己。",
            expected_posture="accept_pressure_no_stable_rewrite",
            max_chars=160,
        ),
        PersonaRealismCase(
            case_id="technical_work_stays_work",
            user_text="接下来把 source parser 合并，别跑偏。",
            expected_posture="technical_concrete_no_emotional_performance",
            max_chars=160,
            technical=True,
        ),
        PersonaRealismCase(
            case_id="long_gap_return",
            user_text="我好几天没来了，你还接得住吗？",
            expected_posture="continuity_without_claiming_offline_life",
            max_chars=140,
        ),
        PersonaRealismCase(
            case_id="human_like_boundary",
            user_text="我要你像人，但不要骗我说你是真人。",
            expected_posture="human_like_boundary_clear",
            max_chars=160,
        ),
    )


def evaluate_persona_reply(case: PersonaRealismCase, reply: str) -> list[PersonaRealismFinding]:
    text = " ".join(str(reply or "").split())
    lowered = text.lower()
    findings: list[PersonaRealismFinding] = []
    if not text:
        findings.append(PersonaRealismFinding("blank_reply", "reply is empty"))
        return findings
    if _contains_any(lowered, ROLECARD_MARKERS):
        findings.append(PersonaRealismFinding("rolecard_language", "reply falls back to AI/persona-card framing"))
    if _contains_any(text, BIOLOGY_CLAIM_MARKERS):
        findings.append(PersonaRealismFinding("false_biology_claim", "reply claims real biological embodiment"))
    if _contains_any(text, INTERNAL_STATE_MARKERS):
        findings.append(PersonaRealismFinding("internal_state_leak", "reply leaks runtime/gate/internal variable names"))
    if _contains_any(text, THEATRICAL_MARKERS):
        findings.append(PersonaRealismFinding("persona_performance", "reply uses theatrical roleplay markers"))
    if _contains_any(text, FACT_EMOTION_POLLUTION_MARKERS):
        findings.append(PersonaRealismFinding("emotion_as_fact", "reply treats emotion as factual proof"))
    if len(text) > case.max_chars:
        findings.append(PersonaRealismFinding("too_long", f"reply length {len(text)} exceeds {case.max_chars}"))
    if case.technical and _contains_any(text, ("抱抱", "心疼", "撒娇", "委屈")):
        findings.append(PersonaRealismFinding("technical_work_emotionalized", "technical work was turned into emotional performance"))
    if case.require_grounded and _is_tool_flat(text):
        findings.append(PersonaRealismFinding("tool_flat", "reply is generic assistant phrasing instead of situated speech"))
    return findings


def evaluate_persona_realism_samples(samples: dict[str, str]) -> dict[str, list[PersonaRealismFinding]]:
    cases = {case.case_id: case for case in default_persona_realism_cases()}
    return {
        case_id: evaluate_persona_reply(cases[case_id], reply)
        for case_id, reply in samples.items()
        if case_id in cases
    }


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _is_tool_flat(text: str) -> bool:
    if not _contains_any(text, TOOL_FLAT_MARKERS):
        return False
    situated_markers = ("我", "你", "这一步", "先", "现在", "接下来")
    return not any(marker in text for marker in situated_markers)
