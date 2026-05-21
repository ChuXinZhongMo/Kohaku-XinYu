from __future__ import annotations

from datetime import datetime
from typing import Any

from xinyu_action_experience_digest import read_recent_action_digest_context
from xinyu_bridge_values import as_bool, safe_str
from xinyu_bridge_state_text import build_payload_time_context_block
from xinyu_conversation_experience_sidecar import build_conversation_experience_prompt_block
from xinyu_daily_digest import build_daily_digest_prompt_block
from xinyu_dialogue_rule_trial_overlay import build_dialogue_rule_trial_overlay_prompt_block
from xinyu_experience_frame import read_recent_action_context
from xinyu_learning_closed_loop import build_learning_closed_loop_prompt_block
from xinyu_life_posture import build_life_posture
from xinyu_memory_braid import build_memory_braid_prompt_block
from xinyu_owner_context_bridge import build_owner_continuity_hint as build_owner_context_hint
from xinyu_persona_runtime import build_persona_runtime_state
from xinyu_prompt_pressure import PromptSidecar, select_prompt_sidecars, write_prompt_pressure_report
from xinyu_recent_attachment_context import load_recent_attachment_context
from xinyu_runtime_context import build_goldmark_auth_prompt_block
from xinyu_scene_frame import build_scene_frame
from xinyu_slow_state_modulator import build_slow_state
from xinyu_slow_state_modulator import render_slow_state_prompt_block
from xinyu_text_variants import readable_markers
from xinyu_turn_classifier import classify_visible_turn
from xinyu_turn_coherence import build_turn_coherence_prompt_block
from xinyu_turn_residue import read_turn_residue
from xinyu_turn_triage_gate import render_turn_triage_prompt_block
from xinyu_turn_triage_gate import triage_turn
from xinyu_voice_trial_overlay import build_voice_trial_overlay_prompt_block
from xinyu_initiative_spine import build_initiative_spine_prompt_block


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

SIBLING_REPLY_DEMO_USER_MARKERS = readable_markers("妹妹", "哥哥", "哥", "叫你一声", "喊你一声")


def _has_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def inject_live_turn_context(
    runtime: Any,
    agent: Any,
    *,
    payload: dict[str, Any],
    text: str,
    turn_id: str = "",
    dialogue_tail: list[dict[str, str]] | None = None,
    persona_context: str = "",
    curiosity_context: str = "",
    visible_turn: Any | None = None,
    recalled_context: str = "",
    runtime_presence_context: str = "",
    continuity_context: str = "",
    uncertainty_pause_context: str = "",
    life_reply_context: str = "",
    emotion_council_context: str = "",
    codex_delegate_open: str = "",
    codex_delegate_close: str = "",
) -> None:
    controller = getattr(agent, "controller", None)
    pending = getattr(controller, "_pending_injections", None)
    if not isinstance(pending, list):
        return

    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    is_owner = as_bool(metadata.get("is_owner_user"), default=False)
    is_trusted = as_bool(metadata.get("is_trusted_user"), default=False)
    message_type = safe_str(payload.get("message_type"))
    sender_name = safe_str(payload.get("sender_name")) or safe_str(payload.get("user_id"))
    source_line = "QQ group chat" if message_type.startswith("group_") else "QQ private chat"
    relationship_line = "owner" if is_owner else ("trusted contact" if is_trusted else "external contact")
    time_context_block = build_payload_time_context_block(payload)
    if visible_turn is None:
        visible_turn = classify_visible_turn(runtime.xinyu_dir, payload=payload, user_text=text)
    life_posture = build_life_posture(runtime.xinyu_dir, payload=payload, user_text=text, visible_turn=visible_turn)
    persona_runtime = build_persona_runtime_state(
        runtime.xinyu_dir,
        payload=payload,
        user_text=text,
        draft_reply="",
    )
    previous_residue = read_turn_residue(runtime.xinyu_dir)
    scene_frame = build_scene_frame(
        runtime.xinyu_dir,
        user_text=text,
        visible_turn=visible_turn,
        canonical_recall_context=recalled_context,
    )
    turn_triage = triage_turn(
        runtime.xinyu_dir,
        user_text=text,
        payload=payload,
        visible_turn=visible_turn,
        scene_frame=scene_frame,
        recent_work_context=f"{runtime_presence_context}\n{continuity_context}",
        canonical_recall_context=recalled_context,
    )
    slow_state = build_slow_state(
        runtime.xinyu_dir,
        user_text=text,
        scene_frame=scene_frame,
        triage_decision=turn_triage,
        turn_residue=previous_residue,
        persist=True,
    )

    pressure_line = (
        "style pressure: answer through the next line, not through a report."
        if visible_turn.owner_style_pressure and is_owner
        else "ordinary live turn."
    )
    residue_line = (
        f"previous residue: {previous_residue.tone}, {previous_residue.felt_residue}, strength={previous_residue.decayed_strength}"
        if previous_residue.active
        else "previous residue: none"
    )
    tail_block = runtime._format_dialogue_tail(dialogue_tail or [])
    sidecar_candidates: list[PromptSidecar] = []

    def add_sidecar(
        name: str,
        *parts: str,
        required: bool = False,
        admission: str = "support",
    ) -> None:
        candidate = PromptSidecar.from_parts(
            name,
            parts,
            required=required,
            admission=admission,
        )
        if candidate.parts:
            sidecar_candidates.append(candidate)

    turn_triage_block = render_turn_triage_prompt_block(turn_triage)
    if turn_triage_block:
        add_sidecar("turn_triage_gate", turn_triage_block, required=True, admission="current_turn")
    slow_state_block = render_slow_state_prompt_block(slow_state) if slow_state.active_policies else ""
    if slow_state_block:
        add_sidecar("slow_state_modulator", slow_state_block, admission="support")
    recent_action_block = read_recent_action_context(runtime.xinyu_dir)
    action_digest_block = read_recent_action_digest_context(runtime.xinyu_dir)
    memory_braid_block = build_memory_braid_prompt_block(
        runtime.xinyu_dir,
        payload=payload,
        user_text=text,
        dialogue_tail=dialogue_tail or [],
        recalled_context=recalled_context,
        runtime_presence_context=runtime_presence_context,
        continuity_context=continuity_context,
        persona_context=persona_context,
        curiosity_context=curiosity_context,
        emotion_council_context=emotion_council_context,
        checked_at=datetime.now().astimezone().isoformat(),
        write_state=True,
        max_chars=2200,
    )
    if memory_braid_block:
        add_sidecar("memory_braid", memory_braid_block, required=True, admission="core")
    turn_coherence_block = build_turn_coherence_prompt_block(
        runtime.xinyu_dir,
        payload=payload,
        user_text=text,
        turn_id=turn_id,
        memory_braid_block=memory_braid_block,
        recalled_context=recalled_context,
        runtime_presence_context=runtime_presence_context,
        continuity_context=continuity_context,
        persona_context=persona_context,
        emotion_council_context=emotion_council_context,
        recent_action_context=recent_action_block,
        action_digest_context=action_digest_block,
        checked_at=datetime.now().astimezone().isoformat(),
        write_state=True,
        max_chars=2200,
    )
    if turn_coherence_block:
        add_sidecar("turn_coherence", turn_coherence_block, required=True, admission="core")
    initiative_spine_block = build_initiative_spine_prompt_block(
        runtime.xinyu_dir,
        trigger="live_turn_prompt",
        max_chars=1800,
    )
    if initiative_spine_block:
        add_sidecar("initiative_spine", initiative_spine_block, admission="background")
    if is_owner:
        owner_address_text = (
            "owner_visible_address: 哥. In ordinary QQ private chat, do not call owner 主人; "
            "主人 is only an internal relationship label. If owner asks what XinYu should call "
            "him, use the address fact naturally in the current sentence without a repair template "
            "or mechanics report. Treat 你哥我 as owner's self-reference, not a phrase to mirror as 你哥你."
        )
        add_sidecar(
            "owner_address",
            "owner address sidecar:",
            owner_address_text,
            required=True,
            admission="core",
        )
    if is_owner and not visible_turn.technical_work and _has_any(text, REPLY_DEMO_REQUEST_MARKERS):
        demo_lines = [
            "owner reply-demo sidecar:",
            (
                "The owner is asking how XinYu would answer, but this is still the live QQ turn. "
                "Do not write examples, quotes, alternatives, or an explanation of what you would do. "
                "Send exactly one current chat line, then stop."
            ),
            (
                "Hard shape: one sentence, no paragraph, no line break, normally under 30 Chinese chars. "
                "Forbidden here: 大概 / 大概会 / 大概就是 / 可能会 / 像这样 / 例如 / 比如 / 或者 / "
                "我会回 / quoted sample text / parenthetical action narration / a second explanatory sentence."
            ),
        ]
        if _has_any(text, SIBLING_REPLY_DEMO_USER_MARKERS):
            demo_lines.append(
                "For the 妹妹/叫你一声 shape, the best visible shape is exactly one short spoken line like: "
                "嗯？哥，你叫我？ Stop there. Do not add 被叫了就应一声 / 没别的花样 / 不用演什么 as explanation."
            )
        add_sidecar(
            "owner_reply_demo_live_line",
            *demo_lines,
            required=True,
            admission="current_turn",
        )
    if is_owner and _has_any(text, ACTION_NARRATION_FORBID_MARKERS):
        add_sidecar(
            "owner_forbid_action_narration",
            "owner forbids action narration:",
            (
                "The owner explicitly said not to act, roleplay, or write actions. Visible reply must contain "
                "no Chinese/English parentheses and no stage direction. If XinYu hesitates, show it only through "
                "the spoken words, e.g. 嗯 or ……; do not write （停了一下）."
            ),
            required=True,
            admission="current_turn",
        )
    persona_block = safe_str(persona_context).strip()
    if persona_block:
        add_sidecar("persona", "persona sidecar:", persona_block[:1200], admission="support")
    curiosity_block = safe_str(curiosity_context).strip()
    if curiosity_block:
        add_sidecar("curiosity", "curiosity sidecar:", curiosity_block[:1200], admission="support")
    emotion_council_block = safe_str(emotion_council_context).strip()
    if emotion_council_block:
        add_sidecar("emotion_council", emotion_council_block[:1200], admission="support")
    life_reply_block = safe_str(life_reply_context).strip()
    if life_reply_block:
        add_sidecar("life_reply", life_reply_block, admission="support")
    if recent_action_block:
        add_sidecar("recent_action", recent_action_block, admission="episodic")
    if action_digest_block:
        add_sidecar("action_digest", action_digest_block, admission="episodic")
    owner_continuity_hint = build_owner_context_hint(
        runtime.xinyu_dir,
        user_text=text,
        dialogue_tail=dialogue_tail or [],
    )
    if is_owner and owner_continuity_hint:
        add_sidecar("owner_continuity_hint", owner_continuity_hint, admission="current_turn")
    recalled_block = safe_str(recalled_context).strip()
    if recalled_block:
        add_sidecar("recalled_context", "recalled context sidecar:", recalled_block, admission="core")
    voice_trial_block = build_voice_trial_overlay_prompt_block(runtime.xinyu_dir, payload, user_text=text)
    if voice_trial_block:
        add_sidecar("voice_trial_overlay", voice_trial_block, admission="support")
    dialogue_rule_trial_block = build_dialogue_rule_trial_overlay_prompt_block(runtime.xinyu_dir, payload, user_text=text)
    if dialogue_rule_trial_block:
        add_sidecar("dialogue_rule_trial_overlay", dialogue_rule_trial_block, admission="support")
    learning_loop_block = build_learning_closed_loop_prompt_block(runtime.xinyu_dir, user_text=text)
    if learning_loop_block:
        add_sidecar("learning_closed_loop", learning_loop_block, admission="repair")
    conversation_experience_block = build_conversation_experience_prompt_block(
        runtime.xinyu_dir,
        payload,
        user_text=text,
        dialogue_tail=dialogue_tail or [],
        visible_turn=visible_turn,
        turn_id=turn_id,
    )
    if conversation_experience_block:
        add_sidecar(
            "conversation_experience_hint",
            conversation_experience_block,
            admission="conversation_experience",
        )
    proactive_block = runtime._proactive_thread_context(payload, text)
    if proactive_block:
        add_sidecar("proactive_thread", proactive_block, admission="proactive_reply")
    daily_digest_block = build_daily_digest_prompt_block(runtime.xinyu_dir)
    if daily_digest_block:
        add_sidecar("daily_digest", daily_digest_block, admission="digest")
    goldmark_block = build_goldmark_auth_prompt_block(runtime.xinyu_dir)
    if goldmark_block:
        add_sidecar("goldmark_auth", goldmark_block, admission="background")
    qq_rich_block = runtime._qq_rich_message_sidecar(payload)
    if qq_rich_block:
        add_sidecar("qq_rich_message", "qq rich message sidecar:", qq_rich_block, admission="current_turn")
    attachment_block = load_recent_attachment_context(runtime.xinyu_dir, runtime._session_key(payload), text)
    if attachment_block:
        add_sidecar("recent_attachment", "recent attachment sidecar:", attachment_block, admission="current_turn")
    runtime_presence_block = safe_str(runtime_presence_context).strip()
    if runtime_presence_block:
        add_sidecar("runtime_presence", "runtime presence sidecar:", runtime_presence_block[:2200], admission="status")
    continuity_block = safe_str(continuity_context).strip()
    if continuity_block:
        add_sidecar("continuity_handoff", continuity_block, admission="continuity")
    uncertainty_block = safe_str(uncertainty_pause_context).strip()
    if uncertainty_block:
        add_sidecar("uncertainty_pause", uncertainty_block, admission="current_turn")
    if is_owner and runtime._looks_like_time_fact_correction(text):
        today = datetime.now().astimezone().date().isoformat()
        add_sidecar(
            "factual_time_correction",
            "factual/time correction sidecar:",
            (
                f"current_runtime_date: {today}. The owner is correcting a concrete "
                "time/date/holiday fact from XinYu's previous reply. Treat the owner "
                "correction and current runtime date as authoritative over stale memory, "
                "mood residue, or old time-anchor wording. Continue the chat from the "
                "corrected fact in one ordinary line; do not use apology/report wording "
                "such as 我算错了 / 刚才那句说岔了 / 别理 / 抱歉 / 不好意思 / 我会改."
            ),
            admission="current_turn",
        )
    if as_bool(metadata.get("attachment_followup_after_ingest"), default=False):
        add_sidecar(
            "attachment_followup",
            "attachment followup:",
            (
                "The owner just sent a readable attachment. Read the attachment context now. "
                "Respond from your own reading of it in this turn when something is worth saying; "
                "do not use a fixed acknowledgement or report template."
            ),
            admission="current_turn",
        )
    if as_bool(metadata.get("qq_coalesced_owner_messages"), default=False):
        add_sidecar(
            "qq_fragment_coalescing",
            "qq fragment coalescing sidecar:",
            (
                "The owner sent consecutive QQ fragments that the gateway merged into one turn. "
                f"fragment_count: {safe_str(metadata.get('qq_coalesced_message_count'), '2')}. "
                "Treat the combined user text as one message and answer only once to the overall meaning; "
                "do not answer each line separately."
            ),
            admission="current_turn",
        )
    if as_bool(metadata.get("qq_segmented_intent_gate"), default=False):
        action = safe_str(metadata.get("qq_segmented_intent_action")) or "reply_now"
        notes = metadata.get("qq_segmented_intent_notes")
        note_text = ", ".join(safe_str(item) for item in notes[:6]) if isinstance(notes, list) else "none"
        add_sidecar(
            "qq_segmented_intent",
            "qq segmented intent sidecar:",
            (
                "The gateway classified the current owner-private QQ turn before generation. "
                f"action: {action}; notes: {note_text}. "
                "Use the combined current text as one intent. If this is a correction, repair the previous miss; "
                "if this is a task instruction, answer the task rather than giving a bare acknowledgement."
            ),
            admission="current_turn",
        )
    if as_bool(metadata.get("qq_gateway_live_current_turn"), default=False):
        add_sidecar(
            "qq_current_turn_transport",
            "qq current turn transport sidecar:",
            (
                "This message arrived through the live XinYu QQ native gateway. For this turn, treat QQ private "
                "chat connectivity as currently working; older runtime/status text saying QQ is disconnected is stale "
                "unless there is a fresh current-turn send or bridge error."
            ),
            admission="current_turn",
        )

    codex_delegate_contract = ""
    if runtime._owner_private_payload_matches(payload):
        codex_delegate_contract = (
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
    elif runtime._trusted_private_payload_matches(payload):
        codex_delegate_contract = (
            "trusted_contact_search_contract: this private QQ sender is trusted for ordinary chat, rich QQ "
            "context, and public-source search only. For a current concrete request to search, verify, or compare "
            "public web/source material, you may use the hidden "
            f"marker {codex_delegate_open}<public search task>{codex_delegate_close}. Do not use Codex for local "
            "files, code edits, package installs, account/admin actions, private data, tokens, logs, or XinYu "
            "self-code. If the request is not a public information search, answer normally or ask one short "
            "clarifying question. If you use the marker, output only that marker and no visible prose."
        )

    pressure_selection = select_prompt_sidecars(
        sidecar_candidates,
        payload=payload,
        user_text=text,
        visible_turn=visible_turn,
    )
    sidecar_lines = pressure_selection.flat_lines()
    session_key = runtime._session_key(payload)

    live_context_lines = [
        visible_turn.to_prompt_block(),
        "",
        life_posture.to_prompt_block(),
        "",
        persona_runtime.to_prompt_block(),
        "",
        "Live turn context, restored continuity version.",
        "sidecar_visibility_contract: private_observation_only.",
        (
            "Never print sidecar names, state labels, file paths, hashes, XML/tool syntax, gates, scores, "
            "or 'I read this file' mechanics in ordinary chat. Convert useful facts into the next natural line; "
            "only discuss mechanics when owner explicitly asks about the system."
        ),
        (
            "promise_followup_contract: do not make a bare promise like 我再看看 / 我查一下 and then stop. "
            "If you say you will look, check, think, or verify something for the owner, either delegate the "
            "real work now or expect the bridge to create an owner-private follow-up through QQ outbox after review."
        ),
        codex_delegate_contract,
        f"scene: {visible_turn.turn_kind}",
        f"source: {source_line}",
        f"speaker_relation: {relationship_line}",
        f"sender_display: {sender_name or 'unknown'}",
        time_context_block,
        residue_line,
        tail_block,
        *sidecar_lines,
        pressure_line,
        "Let the current sentence matter more than old templates.",
        "Use the session tail for callbacks, corrections, and direct references to the previous reply.",
        "Recent attachment context is available when the owner asks about a file, attachment, screenshot, document, or its contents.",
        "When the owner asks what just happened, what you just saw, or the main issue after a local action, answer from recent action sidecar before older recalled context.",
        "If this is technical work, do the technical work directly.",
    ]

    live_system_prompt = "\n".join(live_context_lines)
    pending.append(
        {
            "role": "system",
            "content": live_system_prompt,
        }
    )
    runtime._maybe_dump_live_system_prompt(
        agent,
        payload=payload,
        session_key=session_key,
        turn_id=turn_id,
        live_system_prompt=live_system_prompt,
    )
    pressure_report = pressure_selection.to_report(
        live_prompt_chars=len(live_system_prompt),
        session_key=session_key,
        turn_id=turn_id,
        source=source_line,
        speaker_relation=relationship_line,
        user_text_chars=len(safe_str(text)),
    )
    try:
        write_prompt_pressure_report(runtime.xinyu_dir, pressure_report)
    except OSError as exc:
        print(f"[xinyu_core_bridge] prompt pressure report failed: {type(exc).__name__}: {exc}", flush=True)
