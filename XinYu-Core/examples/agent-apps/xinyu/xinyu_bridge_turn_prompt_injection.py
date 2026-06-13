from __future__ import annotations

from typing import Any

from xinyu_bridge_turn_prompt_payload import build_codex_delegate_contract, build_live_system_prompt
from xinyu_bridge_turn_prompt_reports import append_prompt_and_reports
from xinyu_bridge_turn_sidecar_context import collect_context_sidecars
from xinyu_bridge_turn_sidecar_owner import collect_owner_policy_sidecars
from xinyu_bridge_turn_sidecar_state import collect_state_sidecars, sidecar_adder
from xinyu_group_social_sidecar import assemble_group_social_view
from xinyu_prompt_pressure import PromptSidecar


def inject_live_turn_context_from_facade(
    deps: Any,
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

    tail = dialogue_tail or []
    live_state = deps.build_live_turn_state(
        runtime,
        payload=payload,
        visible_turn=visible_turn,
        dialogue_tail=tail,
        text=text,
        recalled_context=recalled_context,
        runtime_presence_context=runtime_presence_context,
        continuity_context=continuity_context,
    )
    sidecar_candidates: list[Any] = []
    add_sidecar = sidecar_adder(deps, sidecar_candidates)

    blocks = collect_state_sidecars(
        deps,
        add_sidecar,
        runtime,
        payload=payload,
        text=text,
        turn_id=turn_id,
        dialogue_tail=tail,
        live_state=live_state,
        recalled_context=recalled_context,
        runtime_presence_context=runtime_presence_context,
        continuity_context=continuity_context,
        persona_context=persona_context,
        curiosity_context=curiosity_context,
        emotion_council_context=emotion_council_context,
    )
    collect_owner_policy_sidecars(deps, add_sidecar, live_state.is_owner, live_state.visible_turn, text)
    collect_context_sidecars(
        deps,
        add_sidecar,
        runtime,
        payload=payload,
        text=text,
        turn_id=turn_id,
        dialogue_tail=tail,
        live_state=live_state,
        blocks=blocks,
        persona_context=persona_context,
        curiosity_context=curiosity_context,
        recalled_context=recalled_context,
        runtime_presence_context=runtime_presence_context,
        continuity_context=continuity_context,
        uncertainty_pause_context=uncertainty_pause_context,
        life_reply_context=life_reply_context,
        emotion_council_context=emotion_council_context,
    )
    sidecar_candidates.extend(deps.collect_transport_sidecars(live_state.metadata))

    # Read-side wiring: inject compact group social context (gated; returns no
    # lines when XINYU_GROUP_SOCIAL_ENABLED is off or this is not a group turn).
    group_social_view = assemble_group_social_view(runtime.xinyu_dir, payload=payload, text=text)
    if group_social_view.get("lines"):
        sidecar_candidates.append(
            PromptSidecar.from_parts("group_social_context", group_social_view["lines"], admission="current_turn")
        )

    codex_delegate_contract = build_codex_delegate_contract(
        runtime,
        payload,
        codex_delegate_open=codex_delegate_open,
        codex_delegate_close=codex_delegate_close,
    )
    pressure_selection = deps.select_prompt_sidecars(
        sidecar_candidates,
        payload=payload,
        user_text=text,
        visible_turn=live_state.visible_turn,
    )
    live_system_prompt = build_live_system_prompt(
        live_state,
        sidecar_lines=pressure_selection.flat_lines(),
        codex_delegate_contract=codex_delegate_contract,
    )
    append_prompt_and_reports(
        deps,
        runtime,
        agent,
        pending,
        payload=payload,
        text=text,
        turn_id=turn_id,
        live_state=live_state,
        live_system_prompt=live_system_prompt,
        pressure_selection=pressure_selection,
        short_term_continuity_block=blocks.short_term_continuity,
    )
