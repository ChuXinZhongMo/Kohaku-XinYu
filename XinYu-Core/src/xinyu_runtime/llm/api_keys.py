"""
API key storage and retrieval.

Keys are stored in ~/.xinyu/api_keys.yaml.
Format: { openrouter: "sk-or-...", openai: "sk-...", anthropic: "sk-ant-...", gemini: "AI..." }
"""

import os

import yaml

from xinyu_runtime.utils.logging import get_logger
from xinyu_runtime.utils.paths import xinyu_path

logger = get_logger(__name__)

XINYU_CONFIG_DIR = xinyu_path()
KEYS_PATH = XINYU_CONFIG_DIR / "api_keys.yaml"

# Maps provider short names to env var names (for fallback)
PROVIDER_KEY_MAP: dict[str, str] = {
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "mimo": "MIMO_API_KEY",
}


def save_api_key(provider: str, key: str) -> None:
    """Save an API key for a provider."""
    KEYS_PATH.parent.mkdir(parents=True, exist_ok=True)
    keys = _load_api_keys()
    keys[provider] = key
    with open(KEYS_PATH, "w", encoding="utf-8") as f:
        yaml.dump(keys, f, default_flow_style=False)
    logger.info("API key saved", provider=provider)


def get_api_key(provider_or_env: str) -> str:
    """Get an API key by provider name or env var name.

    Resolution:
      1. Stored key in ~/.xinyu/api_keys.yaml
      2. Environment variable
      3. Empty string (not found)
    """
    # Normalize: env var name -> provider name
    provider = provider_or_env
    for prov, env in PROVIDER_KEY_MAP.items():
        if provider_or_env == env:
            provider = prov
            break

    # 1. Stored key
    keys = _load_api_keys()
    if keys.get(provider):
        return keys[provider]

    # 2. Env var (by provider name or direct env var name)
    env_var = PROVIDER_KEY_MAP.get(provider, provider_or_env)
    key = os.environ.get(env_var, "")
    if key:
        return key

    # 3. Try the raw string as env var
    if provider_or_env != env_var:
        key = os.environ.get(provider_or_env, "")

    return key


def list_api_keys() -> dict[str, str]:
    """List stored API keys (masked)."""
    keys = _load_api_keys()
    masked = {}
    for provider, key in keys.items():
        if key and len(key) > 8:
            masked[provider] = f"{key[:4]}...{key[-4:]}"
        elif key:
            masked[provider] = "****"
    return masked


def _load_api_keys() -> dict[str, str]:
    """Load API keys from file."""
    keys: dict[str, str] = {}
    for path in [KEYS_PATH]:
        if not path.exists():
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                keys.update(data)
        except Exception as e:
            logger.debug("Failed to load API keys file", path=str(path), error=str(e))
    return keys
