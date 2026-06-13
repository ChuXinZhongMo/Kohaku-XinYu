from __future__ import annotations

from typing import Any, Callable


FacadeGlobals = Callable[[], dict[str, Any]]


def bind_schedule_promised_followup(facade_globals: FacadeGlobals) -> Callable[..., dict[str, Any]]:
    def _schedule_promised_followup(
        runtime: Any,
        *,
        payload: dict[str, Any],
        text: str,
        reply: str,
        session_key: str,
        model_codex_task: bool,
    ) -> dict[str, Any]:
        return facade_globals()["_runtime_schedule_promised_followup"](
            runtime,
            payload=payload,
            text=text,
            reply=reply,
            session_key=session_key,
            model_codex_task=model_codex_task,
        )

    return _schedule_promised_followup


def bind_maybe_enqueue_sticker_reply(facade_globals: FacadeGlobals) -> Callable[..., Any]:
    async def _maybe_enqueue_sticker_reply(
        runtime: Any,
        *,
        payload: dict[str, Any],
        text: str,
        reply: str,
        session_key: str,
        turn_id: str,
    ) -> dict[str, Any]:
        facade = facade_globals()
        return await facade["_runtime_maybe_enqueue_sticker_reply"](
            runtime,
            payload=payload,
            text=text,
            reply=reply,
            session_key=session_key,
            turn_id=turn_id,
            maybe_enqueue_sticker_reply_func=facade["maybe_enqueue_sticker_reply"],
            to_thread_func=facade["asyncio"].to_thread,
        )

    return _maybe_enqueue_sticker_reply


def bind_turn_action_result(facade_globals: FacadeGlobals) -> Callable[..., str]:
    def _turn_action_result(
        *,
        self_code_task: str,
        direct_codex_task: str,
        model_codex_task: str,
        wait_to_think_task: str,
        model_codex_delegate_note: str,
        promised_followup: dict[str, Any],
        sticker_tail_recorded: bool,
    ) -> str:
        return facade_globals()["_runtime_turn_action_result"](
            self_code_task=self_code_task,
            direct_codex_task=direct_codex_task,
            model_codex_task=model_codex_task,
            wait_to_think_task=wait_to_think_task,
            model_codex_delegate_note=model_codex_delegate_note,
            promised_followup=promised_followup,
            sticker_tail_recorded=sticker_tail_recorded,
        )

    return _turn_action_result


def bind_finish_turn_coherence(facade_globals: FacadeGlobals) -> Callable[..., dict[str, Any]]:
    def _finish_turn_coherence(
        runtime: Any,
        *,
        payload: dict[str, Any],
        text: str,
        reply: str,
        turn_id: str,
        action_result: str,
        before_memory: dict[str, Any],
        final_guard_flags: list[str],
        private_thought_outcome: dict[str, Any],
        private_thought_link: dict[str, Any],
        emotion_council: dict[str, Any],
        persona_sidecar: dict[str, Any],
        candidate_result: dict[str, Any],
        memory_self_review: dict[str, Any],
        recalled_context_notes: list[str],
        continuity_handoff: dict[str, Any],
        interaction_journal: dict[str, Any],
        learning_closed_loop: dict[str, Any],
        uncertainty_pause: dict[str, Any],
        promised_followup: dict[str, Any],
        sticker_reply: dict[str, Any],
    ) -> dict[str, Any]:
        facade = facade_globals()
        return facade["_runtime_finish_turn_coherence"](
            runtime,
            payload=payload,
            text=text,
            reply=reply,
            turn_id=turn_id,
            action_result=action_result,
            before_memory=before_memory,
            final_guard_flags=final_guard_flags,
            private_thought_outcome=private_thought_outcome,
            private_thought_link=private_thought_link,
            emotion_council=emotion_council,
            persona_sidecar=persona_sidecar,
            candidate_result=candidate_result,
            memory_self_review=memory_self_review,
            recalled_context_notes=recalled_context_notes,
            continuity_handoff=continuity_handoff,
            interaction_journal=interaction_journal,
            learning_closed_loop=learning_closed_loop,
            uncertainty_pause=uncertainty_pause,
            promised_followup=promised_followup,
            sticker_reply=sticker_reply,
            finish_turn_coherence_func=facade["finish_turn_coherence"],
            memory_snapshot_func=facade["_memory_snapshot"],
        )

    return _finish_turn_coherence
