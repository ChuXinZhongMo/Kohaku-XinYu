from __future__ import annotations

from typing import Any, Callable


FacadeGlobals = Callable[[], dict[str, Any]]


def bind_record_owner_voice_sidecars(facade_globals: FacadeGlobals) -> Callable[..., tuple[dict[str, Any], bool]]:
    def _record_owner_voice_sidecars(
        runtime: Any,
        *,
        payload: dict[str, Any],
        text: str,
        reply: str,
    ) -> tuple[dict[str, Any], bool]:
        facade = facade_globals()
        return facade["_runtime_record_owner_voice_sidecars"](
            runtime,
            payload=payload,
            text=text,
            reply=reply,
            as_bool_func=facade["_as_bool"],
            record_voice_trial_overlay_func=facade["record_voice_trial_overlay"],
            record_voice_correction_func=facade["record_voice_correction"],
        )

    return _record_owner_voice_sidecars
