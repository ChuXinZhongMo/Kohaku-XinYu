"""
LLM provider factory.

Creates the correct LLM provider based on:
  1. LLM profile (from config, CLI override, or default)
  2. Inline controller config (backward compat)
"""

import os
from dataclasses import MISSING, fields
from typing import Any

from xinyu_runtime.core.config import AgentConfig
from xinyu_runtime.llm.base import LLMProvider
from xinyu_runtime.llm.codex_provider import CodexOAuthProvider
from xinyu_runtime.llm.failover import wrap_llm_with_visible_failover
from xinyu_runtime.llm.openai import OpenAIProvider
from xinyu_runtime.llm.profiles import LLMProfile, get_api_key, resolve_controller_llm
from xinyu_runtime.utils.logging import get_logger

logger = get_logger(__name__)

# Env-configurable model-level fallback: when the primary LLM (e.g. grok via a flaky
# aggregator) returns a recoverable error (429/timeout/quota), try this secondary
# provider before hitting TinyKernel. Set XINYU_FALLBACK_* in xinyu.local.env.
_FALLBACK_BASE_URL_ENV = "XINYU_FALLBACK_BASE_URL"
_FALLBACK_API_KEY_ENV = "XINYU_FALLBACK_API_KEY"
_FALLBACK_MODEL_ENV = "XINYU_FALLBACK_MODEL"


def _build_fallback_provider() -> OpenAIProvider | None:
    """Build an optional secondary LLM from env. Returns None if not configured."""
    base_url = os.environ.get(_FALLBACK_BASE_URL_ENV, "").strip()
    api_key = os.environ.get(_FALLBACK_API_KEY_ENV, "").strip()
    model = os.environ.get(_FALLBACK_MODEL_ENV, "").strip()
    if not (base_url and api_key and model):
        return None
    try:
        return OpenAIProvider(api_key=api_key, base_url=base_url, model=model, temperature=0.7)
    except Exception:
        return None

_AGENT_CONFIG_FIELDS = {field.name: field for field in fields(AgentConfig)}


def _agent_config_default(field_name: str) -> Any:
    field = _AGENT_CONFIG_FIELDS[field_name]
    if field.default is not MISSING:
        return field.default
    if field.default_factory is not MISSING:
        return field.default_factory()
    return MISSING


def _is_meaningful_config_value(field_name: str, value: Any) -> bool:
    """Return True when a config value should override preset/default resolution."""
    if value is None:
        return False

    default = _agent_config_default(field_name)
    if isinstance(value, str):
        return value != "" and value != default
    if isinstance(value, dict):
        return bool(value)
    return value != default


def create_llm_provider(
    config: AgentConfig,
    llm_override: str | None = None,
) -> LLMProvider:
    """Create an LLM provider from agent config.

    Tries LLM profiles first (centralized config), falls back to
    inline controller settings (backward compat).

    Args:
        config: Agent configuration
        llm_override: Override profile name (from --llm CLI flag)
    """
    # Try profile resolution
    controller_data = _extract_controller_data(config)
    profile = resolve_controller_llm(controller_data, llm_override)

    if profile:
        return _create_from_profile(profile)

    # Backward compat: inline config
    return _create_from_inline(config)


def _extract_controller_data(config: AgentConfig) -> dict[str, Any]:
    """Extract only meaningful controller overrides for profile resolution."""
    data: dict[str, Any] = {}

    for field_name in (
        "model",
        "provider",
        "variation_selections",
        "variation",
        "auth_mode",
        "temperature",
        "max_tokens",
        "reasoning_effort",
        "service_tier",
        "extra_body",
    ):
        value = getattr(config, field_name)
        if _is_meaningful_config_value(field_name, value):
            data[field_name] = dict(value) if isinstance(value, dict) else value

    llm_ref = getattr(config, "llm_profile", None)
    if llm_ref:
        data["llm"] = llm_ref
    return data


def _create_from_profile(profile: LLMProfile) -> LLMProvider:
    """Create LLM provider from a resolved profile."""
    logger.info(
        "Using LLM profile",
        profile=profile.name,
        model=profile.model,
        provider=profile.provider,
        backend_type=profile.backend_type,
    )

    if profile.backend_type == "codex":
        provider = CodexOAuthProvider(
            model=profile.model,
            reasoning_effort=profile.reasoning_effort or "medium",
            service_tier=profile.service_tier or None,
        )
        provider._profile_max_context = profile.max_context
        _apply_backend_native_identity(provider, profile)
        return wrap_llm_with_visible_failover(provider, fallback_provider=_build_fallback_provider())

    api_key = get_api_key(profile.provider) if profile.provider else ""
    if not api_key and profile.api_key_env:
        api_key = get_api_key(profile.api_key_env)
    if not api_key:
        raise ValueError(
            f"API key not found for profile '{profile.name}'. "
            f"Use 'kt login {profile.provider or 'openai'}' or set "
            f"{profile.api_key_env or 'OPENAI_API_KEY'} environment variable."
        )

    provider = OpenAIProvider(
        api_key=api_key,
        base_url=profile.base_url or None,
        model=profile.model,
        temperature=profile.temperature,
        max_tokens=profile.max_output or None,
        extra_body=profile.extra_body or None,
    )
    provider._profile_max_context = profile.max_context
    _apply_backend_native_identity(provider, profile)
    return wrap_llm_with_visible_failover(provider, fallback_provider=_build_fallback_provider())


def _apply_backend_native_identity(provider: LLMProvider, profile: LLMProfile) -> None:
    """Stamp the backend's provider_name and provider_native_tools onto the
    instance.

    The tool-injection logic in :mod:`bootstrap.agent_init` reads these
    via ``getattr(llm, "provider_name")`` / ``provider_native_tools``.
    Class-level defaults on the provider subclass serve as fallbacks:
    a custom provider that leaves ``provider_name`` empty and declares
    no native tools inherits the class defaults (empty sets).
    """
    backend_name = getattr(profile, "backend_provider_name", "")
    if backend_name:
        provider.provider_name = backend_name
    backend_tools = getattr(profile, "backend_native_tools", None)
    if backend_tools is not None:
        # Always respect the backend's list (including the empty list —
        # an explicit empty list means "opt out of every native tool").
        provider.provider_native_tools = frozenset(backend_tools)


def create_llm_from_profile_name(name: str) -> LLMProvider:
    """Create an LLM provider from a profile/preset name.

    Used for live model switching. Resolves the name to a profile,
    then creates the appropriate provider.

    Raises:
        ValueError: If profile not found or API key missing.
    """
    profile = resolve_controller_llm({}, llm_override=name)
    if not profile:
        raise ValueError(f"Model profile not found: {name}")
    return wrap_llm_with_visible_failover(_create_from_profile(profile), fallback_provider=_build_fallback_provider())


def _create_from_inline(config: AgentConfig) -> LLMProvider:
    """Create LLM provider from inline controller config (backward compat)."""
    if not config.model:
        raise ValueError(
            "No LLM model configured and no default model set. "
            "Use 'kt login <provider>' to authenticate, then "
            "'kt model default <name>' to set a default, "
            "or add 'llm: <profile>' to your creature config."
        )

    if config.auth_mode == "codex-oauth":
        provider = CodexOAuthProvider(
            model=config.model,
            reasoning_effort=config.reasoning_effort,
            service_tier=config.service_tier,
        )
        logger.info(
            "Using Codex OAuth provider (ChatGPT subscription)",
            model=config.model,
        )
        return wrap_llm_with_visible_failover(provider, fallback_provider=_build_fallback_provider())

    # Standard API key auth (OpenAI, OpenRouter, etc.)
    api_key = config.get_api_key()
    if not api_key:
        raise ValueError(
            f"API key not found. Set {config.api_key_env} environment variable."
        )

    return wrap_llm_with_visible_failover(OpenAIProvider(
        api_key=api_key,
        base_url=config.base_url,
        model=config.model,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        extra_body=config.extra_body or None,
    ), fallback_provider=_build_fallback_provider())
