from __future__ import annotations

from typing import Any, Callable



FacadeGlobals = Callable[[], dict[str, Any]]


def bind_record_uncertainty_pause(facade_globals: FacadeGlobals) -> Callable[..., dict[str, Any]]:
    def _record_uncertainty_pause(
        runtime: Any,
        *,
        payload: dict[str, Any],
        text: str,
        draft_reply: str,
        reply: str,
        final_guard_flags: list[str],
        session_key: str,
        visible_turn: Any,
    ) -> dict[str, Any]:
        facade = facade_globals()
        return facade["_runtime_record_uncertainty_pause"](
            runtime,
            payload=payload,
            text=text,
            draft_reply=draft_reply,
            reply=reply,
            final_guard_flags=final_guard_flags,
            session_key=session_key,
            visible_turn=visible_turn,
            is_waiting_reply_func=facade["is_waiting_reply"],
            record_uncertainty_pause_func=facade["record_uncertainty_pause"],
            safe_str_func=facade["_safe_str"],
        )

    return _record_uncertainty_pause


def bind_observe_post_reply_self_observation(facade_globals: FacadeGlobals) -> Callable[..., dict[str, Any]]:
    def _observe_post_reply_self_observation(
        runtime: Any,
        *,
        payload: dict[str, Any],
        text: str,
        reply: str,
        visible_turn: Any,
        final_guard_flags: list[str],
        expression_learning: dict[str, Any],
        recalled_context: Any,
    ) -> dict[str, Any]:
        facade = facade_globals()
        return facade["_runtime_observe_post_reply_self_observation"](
            runtime,
            payload=payload,
            text=text,
            reply=reply,
            visible_turn=visible_turn,
            final_guard_flags=final_guard_flags,
            expression_learning=expression_learning,
            recalled_context=recalled_context,
            observe_post_reply_self_observation_func=facade["observe_post_reply_self_observation"],
            dedupe_func=facade["_dedupe"],
            safe_str_func=facade["_safe_str"],
        )

    return _observe_post_reply_self_observation


def bind_record_learning_closed_loop(facade_globals: FacadeGlobals) -> Callable[..., dict[str, Any]]:
    def _record_learning_closed_loop(
        runtime: Any,
        *,
        payload: dict[str, Any],
        text: str,
        reply: str,
        session_key: str,
        visible_turn: Any,
        final_guard_flags: list[str],
        expression_learning: dict[str, Any],
        post_reply_observation: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        facade = facade_globals()
        return facade["_runtime_record_learning_closed_loop"](
            runtime,
            payload=payload,
            text=text,
            reply=reply,
            session_key=session_key,
            visible_turn=visible_turn,
            final_guard_flags=final_guard_flags,
            expression_learning=expression_learning,
            post_reply_observation=post_reply_observation,
            record_learning_closed_loop_turn_func=facade["record_learning_closed_loop_turn"],
            dedupe_func=facade["_dedupe"],
            safe_str_func=facade["_safe_str"],
        )

    return _record_learning_closed_loop


def bind_record_curiosity_prediction(facade_globals: FacadeGlobals) -> Callable[..., dict[str, Any]]:
    def _record_curiosity_prediction(
        runtime: Any,
        *,
        payload: dict[str, Any],
        text: str,
        reply: str,
        session_key: str,
    ) -> dict[str, Any]:
        facade = facade_globals()
        return facade["_runtime_record_curiosity_prediction"](
            runtime,
            payload=payload,
            text=text,
            reply=reply,
            session_key=session_key,
            record_reply_prediction_func=facade["record_reply_prediction"],
        )

    return _record_curiosity_prediction


def bind_record_private_thought_link(facade_globals: FacadeGlobals) -> Callable[..., dict[str, Any]]:
    def _record_private_thought_link(
        runtime: Any,
        *,
        payload: dict[str, Any],
        text: str,
        reply: str,
        session_key: str,
    ) -> dict[str, Any]:
        facade = facade_globals()
        return facade["_runtime_record_private_thought_link"](
            runtime,
            payload=payload,
            text=text,
            reply=reply,
            session_key=session_key,
            record_private_thought_reply_link_func=facade["record_private_thought_reply_link"],
        )

    return _record_private_thought_link
