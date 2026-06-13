from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any


DEFAULT_AUTONOMOUS_MAINTENANCE_SESSION_KEY = "xinyu:autonomous:maintenance"


@dataclass(frozen=True)
class RuntimeEnvironmentState:
    v1_enabled: bool
    v1_shadow_mode: bool
    v1_shadow_timeout_seconds: int
    pre_model_routes_timeout_seconds: int
    emotion_council_prompt_enabled: bool
    v1_owner_simple_canary: bool
    owner_private_semantic_fast_route: bool
    v1_canary_timeout_seconds: int
    v1_owner_user_ids: set[str]


@dataclass(frozen=True)
class RuntimeIntervalState:
    autonomous_maintenance_initial_delay_seconds: int
    autonomous_maintenance_interval_seconds: int
    autonomous_maintenance_session_key: str
    metabolism_runner_interval_seconds: int


def build_runtime_environment_state(
    environ: Mapping[str, str],
    *,
    v1_owner_simple_canary_env: str,
    as_bool_fn: Callable[..., bool],
    as_int_fn: Callable[..., int],
    as_str_set_fn: Callable[[Any], set[str]],
) -> RuntimeEnvironmentState:
    v1_shadow_timeout_seconds = max(1, as_int_fn(environ.get("XINYU_V1_SHADOW_TIMEOUT_SECONDS"), 3))
    return RuntimeEnvironmentState(
        v1_enabled=as_bool_fn(environ.get("XINYU_V1_ENABLED"), default=False),
        v1_shadow_mode=as_bool_fn(environ.get("XINYU_V1_SHADOW_MODE"), default=False),
        v1_shadow_timeout_seconds=v1_shadow_timeout_seconds,
        pre_model_routes_timeout_seconds=max(
            1,
            as_int_fn(environ.get("XINYU_PRE_MODEL_ROUTES_TIMEOUT_SECONDS"), 8),
        ),
        emotion_council_prompt_enabled=as_bool_fn(
            environ.get("XINYU_EMOTION_COUNCIL_PROMPT_ENABLED"),
            default=False,
        ),
        v1_owner_simple_canary=as_bool_fn(environ.get(v1_owner_simple_canary_env), default=False),
        owner_private_semantic_fast_route=as_bool_fn(
            environ.get("XINYU_OWNER_PRIVATE_SEMANTIC_FAST_ROUTE"),
            default=True,
        ),
        v1_canary_timeout_seconds=max(
            1,
            as_int_fn(environ.get("XINYU_V1_CANARY_TIMEOUT_SECONDS"), v1_shadow_timeout_seconds),
        ),
        v1_owner_user_ids=as_str_set_fn(environ.get("XINYU_OWNER_USER_IDS")),
    )


def build_runtime_interval_state(
    *,
    autonomous_maintenance_initial_delay_seconds: int,
    autonomous_maintenance_interval_seconds: int,
    autonomous_maintenance_session_key: str,
    metabolism_runner_interval_seconds: int,
) -> RuntimeIntervalState:
    return RuntimeIntervalState(
        autonomous_maintenance_initial_delay_seconds=max(0, autonomous_maintenance_initial_delay_seconds),
        autonomous_maintenance_interval_seconds=max(60, autonomous_maintenance_interval_seconds),
        autonomous_maintenance_session_key=(
            autonomous_maintenance_session_key.strip() or DEFAULT_AUTONOMOUS_MAINTENANCE_SESSION_KEY
        ),
        metabolism_runner_interval_seconds=max(5, metabolism_runner_interval_seconds),
    )


def build_startup_bridge_snapshot(
    *,
    active_sessions: int,
    autonomous_maintenance_enabled: bool,
) -> dict[str, Any]:
    return {
        "active_sessions": active_sessions,
        "autonomous_maintenance": "idle" if autonomous_maintenance_enabled else "disabled",
        "qq_outbox": "unknown",
    }


def build_startup_route_payload(started_at_seconds: float) -> dict[str, Any]:
    return {
        "turn_id": f"bridge-startup-{int(started_at_seconds)}",
        "stage": "bridge_started",
        "route": "idle",
        "status": "ok",
        "elapsed_ms": 0,
        "notes": ["bridge_init"],
    }


__all__ = (
    "DEFAULT_AUTONOMOUS_MAINTENANCE_SESSION_KEY",
    "RuntimeEnvironmentState",
    "RuntimeIntervalState",
    "build_runtime_environment_state",
    "build_runtime_interval_state",
    "build_startup_bridge_snapshot",
    "build_startup_route_payload",
)
