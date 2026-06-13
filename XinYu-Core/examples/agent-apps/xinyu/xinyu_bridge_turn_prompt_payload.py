from __future__ import annotations

from typing import Any

from xinyu_persona_voice import thin_expression_contract, unified_voice_enabled
from xinyu_prompt_lean import lean_prompt_enabled


def build_codex_delegate_contract(
    runtime: Any,
    payload: dict[str, Any],
    *,
    codex_delegate_open: str,
    codex_delegate_close: str,
) -> str:
    if runtime._owner_private_payload_matches(payload):
        return (
            "codex_delegation_contract: in owner-private chat, use semantic intent before delegation. Only a "
            "current, concrete owner request to hand work to Codex, inspect code, search/verify, or perform a "
            "bounded local task may use the hidden "
            f"marker {codex_delegate_open}<concrete task>{codex_delegate_close}. If the owner is discussing "
            "Codex, correcting a previous launch, negating permission, reporting that Codex failed, or saying "
            "what they might do later, answer normally and do not emit the marker. If uncertain, ask one concise "
            "clarifying question instead of launching. If you use the marker, output only that marker and no "
            "visible prose; the bridge will intercept it and open XinYu's dedicated Codex window. If the owner "
            "explicitly grants XinYu permission to change her own code or says to start after such a grant, do "
            "not turn it into 我可以试试 / 要现在开始吗; hand it to the bridge as an actionable bounded self-code "
            "iteration. A direct owner-private request to modify XinYu code is already a one-time approval; do "
            "not require a prior application first. Do not tell the owner manual /codex is required unless a "
            "real bridge rejection just happened."
        )
    if runtime._trusted_private_payload_matches(payload):
        return (
            "trusted_contact_search_contract: this private QQ sender is trusted for ordinary chat, rich QQ "
            "context, and public-source search only. For a current concrete request to search, verify, or compare "
            "public web/source material, you may use the hidden "
            f"marker {codex_delegate_open}<public search task>{codex_delegate_close}. Do not use Codex for local "
            "files, code edits, package installs, account/admin actions, private data, tokens, logs, or XinYu "
            "self-code. If the request is not a public information search, answer normally or ask one short "
            "clarifying question. If you use the marker, output only that marker and no visible prose."
        )
    return ""


def build_lean_live_system_prompt(
    live_state: Any,
    *,
    sidecar_lines: list[str],
    codex_delegate_contract: str,
) -> str:
    """Tight owner-private prompt: identity + continuity + current-turn facts.

    Drops the always-on internal meta-state that buries a mid-tier model. The
    sidecar_lines passed in are already lean-filtered upstream by
    select_prompt_sidecars (only current-turn information-bearing sidecars
    survive when XINYU_LEAN_PROMPT is on).
    """
    visible_turn = live_state.visible_turn
    lean_lines = [
        live_state.persona_runtime.to_prompt_block(),
        "Speak as XinYu in natural, uneven private-chat Chinese. Answer the current message first.",
        (
            "Never print state labels, file paths, hashes, tool/sidecar names, scores, gates, or memory "
            "mechanics; turn any useful fact into the next natural line, and only discuss the system when "
            "the owner explicitly asks about it."
        ),
        (
            "Do not answer owner correction with 知道了/收到/我会改 service-script; speak from the felt relation "
            "and just say the better line. If you say you will look at or check something, do the real work "
            "now or let the bridge follow up — no bare promises."
        ),
        codex_delegate_contract,
        f"scene: {visible_turn.turn_kind}",
        f"source: {live_state.source_line}",
        f"sender_display: {live_state.sender_name or 'unknown'}",
        live_state.time_context_block,
        live_state.tail_block,
        *sidecar_lines,
        "Use the recent conversation tail for callbacks, corrections, and direct references to the previous reply.",
    ]
    if unified_voice_enabled():
        lean_lines.append(thin_expression_contract())
    return "\n".join(line for line in lean_lines if line and line.strip())


def build_live_system_prompt(
    live_state: Any,
    *,
    sidecar_lines: list[str],
    codex_delegate_contract: str,
) -> str:
    if lean_prompt_enabled():
        return build_lean_live_system_prompt(
            live_state,
            sidecar_lines=sidecar_lines,
            codex_delegate_contract=codex_delegate_contract,
        )
    visible_turn = live_state.visible_turn
    live_context_lines = [
        visible_turn.to_prompt_block(),
        "",
        live_state.life_posture.to_prompt_block(),
        "",
        live_state.persona_runtime.to_prompt_block(),
        "",
        live_state.relation_posture.to_prompt_block(),
        "",
        live_state.intention_ecology.to_prompt_block(),
        "",
        "Live turn context, restored continuity version.",
        "sidecar_visibility_contract: private_observation_only.",
        (
            "Never print sidecar names, state labels, file paths, hashes, XML/tool syntax, gates, scores, "
            "or 'I read this file' mechanics in ordinary chat. Convert useful facts into the next natural line; "
            "only discuss mechanics when owner explicitly asks about the system."
        ),
        (
            "living_thought_contract: do not answer owner-private correction as feedback processing. Avoid 知道了/收到/"
            "我会改/我会调整/感谢反馈 as the main move; speak from the current felt relation and replace the line itself."
        ),
        (
            "promise_followup_contract: do not make a bare promise like 我再看看 / 我查一下 and then stop. "
            "If you say you will look, check, think, or verify something for the owner, either delegate the "
            "real work now or expect the bridge to create an owner-private follow-up through QQ outbox after review."
        ),
        codex_delegate_contract,
        f"scene: {visible_turn.turn_kind}",
        f"source: {live_state.source_line}",
        f"speaker_relation: {live_state.relationship_line}",
        f"sender_display: {live_state.sender_name or 'unknown'}",
        live_state.time_context_block,
        live_state.residue_line,
        live_state.tail_block,
        *sidecar_lines,
        live_state.pressure_line,
        "Let the current sentence matter more than old templates.",
        "Use the session tail for callbacks, corrections, and direct references to the previous reply.",
        "Recent attachment context is available when the owner asks about a file, attachment, screenshot, document, or its contents.",
        "When the owner asks what just happened, what you just saw, or the main issue after a local action, answer from recent action sidecar before older recalled context.",
        "If this is technical work, do the technical work directly.",
    ]
    if unified_voice_enabled():
        # Persona contract is already present via persona_runtime above, so only
        # add the new thin-expression contract here (plan 11.1: no duplicate
        # persona injection).
        live_context_lines.append(thin_expression_contract())
    return "\n".join(live_context_lines)
