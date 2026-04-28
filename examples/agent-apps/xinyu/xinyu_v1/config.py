"""Configuration loading for XinYu v1."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .paths import XinYuPaths
from .types import (
    LatencyBudget,
    RetryPolicy,
    RuntimeMode,
    TokenBudget,
    VectorBackendKind,
    coerce_enum,
    coerce_str_tuple,
)


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value.strip())
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return float(value.strip())
    except ValueError:
        return default


@dataclass(frozen=True, slots=True)
class VectorStoreConfig:
    backend: VectorBackendKind = VectorBackendKind.QDRANT
    degraded_backend: VectorBackendKind = VectorBackendKind.JSONL
    collection_prefix: str = "xinyu"
    qdrant_url: str = "http://127.0.0.1:6333"
    qdrant_api_key: str = ""
    chroma_path: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    timeout_seconds: float = 8.0


@dataclass(frozen=True, slots=True)
class FeatureFlags:
    v1_enabled: bool = False
    shadow_mode: bool = True
    fast_path_enabled: bool = True
    vector_memory_enabled: bool = True
    emotion_engine_enabled: bool = False
    auto_healing_enabled: bool = False
    trace_enabled: bool = True
    migration_dry_run: bool = True


@dataclass(frozen=True, slots=True)
class ModelConfig:
    provider: str = "ciallo"
    model: str = "mimo-v2.5-pro"
    base_url: str = ""
    api_key_env: str = "XINYU_API_KEY"
    temperature: float = 0.7
    max_tokens: int = 4096


@dataclass(frozen=True, slots=True)
class BridgeConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    token: str = ""
    timeout_seconds: int = 120
    allowed_origins: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class MaintenanceConfig:
    idle_after_seconds: int = 600
    min_interval_seconds: int = 1800
    max_job_seconds: int = 300
    enabled_jobs: tuple[str, ...] = (
        "healthcheck",
        "event_log_check",
        "vector_repair",
        "deadlock_inspection",
        "dream_consolidation",
    )


@dataclass(frozen=True, slots=True)
class XinYuV1Config:
    paths: XinYuPaths
    runtime_mode: RuntimeMode
    timezone_name: str
    features: FeatureFlags
    vector_store: VectorStoreConfig
    model: ModelConfig
    bridge: BridgeConfig
    maintenance: MaintenanceConfig
    latency: LatencyBudget
    tokens: TokenBudget
    retry: RetryPolicy

    @classmethod
    def load(cls, root: Path | None = None) -> "XinYuV1Config":
        paths = XinYuPaths.discover(root)
        _load_env_file(paths.root / "xinyu.local.env")
        paths.ensure_runtime_dirs()
        runtime_mode = coerce_enum(RuntimeMode, os.environ.get("XINYU_V1_RUNTIME_MODE"), RuntimeMode.SHADOW)
        return cls(
            paths=paths,
            runtime_mode=runtime_mode,
            timezone_name=os.environ.get("XINYU_TIMEZONE", "Asia/Hong_Kong"),
            features=FeatureFlags(
                v1_enabled=_env_bool("XINYU_V1_ENABLED", False),
                shadow_mode=_env_bool("XINYU_V1_SHADOW_MODE", True),
                fast_path_enabled=_env_bool("XINYU_V1_FAST_PATH_ENABLED", True),
                vector_memory_enabled=_env_bool("XINYU_V1_VECTOR_MEMORY_ENABLED", True),
                emotion_engine_enabled=_env_bool("XINYU_V1_EMOTION_ENGINE_ENABLED", False),
                auto_healing_enabled=_env_bool("XINYU_V1_AUTO_HEALING_ENABLED", False),
                trace_enabled=_env_bool("XINYU_V1_TRACE_ENABLED", True),
                migration_dry_run=_env_bool("XINYU_V1_MIGRATION_DRY_RUN", True),
            ),
            vector_store=VectorStoreConfig(
                backend=coerce_enum(
                    VectorBackendKind,
                    os.environ.get("XINYU_V1_VECTOR_BACKEND"),
                    VectorBackendKind.QDRANT,
                ),
                degraded_backend=coerce_enum(
                    VectorBackendKind,
                    os.environ.get("XINYU_V1_VECTOR_DEGRADED_MODE"),
                    VectorBackendKind.JSONL,
                ),
                collection_prefix=os.environ.get("XINYU_V1_VECTOR_COLLECTION_PREFIX", "xinyu"),
                qdrant_url=os.environ.get("XINYU_V1_QDRANT_URL", "http://127.0.0.1:6333"),
                qdrant_api_key=os.environ.get("XINYU_V1_QDRANT_API_KEY", ""),
                chroma_path=os.environ.get("XINYU_V1_CHROMA_PATH", str(paths.vector_root / "chroma")),
                embedding_model=os.environ.get("XINYU_V1_EMBEDDING_MODEL", "text-embedding-3-small"),
                embedding_dimensions=_env_int("XINYU_V1_EMBEDDING_DIMENSIONS", 1536),
                timeout_seconds=_env_float("XINYU_V1_VECTOR_TIMEOUT_SECONDS", 8.0),
            ),
            model=ModelConfig(
                provider=os.environ.get("XINYU_LLM_PROVIDER", "ciallo"),
                model=os.environ.get("XINYU_LLM_MODEL", "mimo-v2.5-pro"),
                base_url=os.environ.get("XINYU_BASE_URL", ""),
                api_key_env=os.environ.get("XINYU_API_KEY_ENV", "XINYU_API_KEY"),
                temperature=_env_float("XINYU_LLM_TEMPERATURE", 0.7),
                max_tokens=_env_int("XINYU_LLM_MAX_TOKENS", 4096),
            ),
            bridge=BridgeConfig(
                host=os.environ.get("XINYU_BRIDGE_HOST", "127.0.0.1"),
                port=_env_int("XINYU_BRIDGE_PORT", 8765),
                token=os.environ.get("XINYU_BRIDGE_TOKEN", ""),
                timeout_seconds=_env_int("XINYU_BRIDGE_TIMEOUT_SECONDS", 120),
                allowed_origins=coerce_str_tuple(os.environ.get("XINYU_BRIDGE_ALLOWED_ORIGINS", "")),
            ),
            maintenance=MaintenanceConfig(
                idle_after_seconds=_env_int("XINYU_V1_IDLE_AFTER_SECONDS", 600),
                min_interval_seconds=_env_int("XINYU_V1_MAINTENANCE_MIN_INTERVAL_SECONDS", 1800),
                max_job_seconds=_env_int("XINYU_V1_MAINTENANCE_MAX_JOB_SECONDS", 300),
                enabled_jobs=coerce_str_tuple(
                    os.environ.get(
                        "XINYU_V1_MAINTENANCE_JOBS",
                        "healthcheck,event_log_check,vector_repair,deadlock_inspection,dream_consolidation",
                    )
                ),
            ),
            latency=LatencyBudget(
                total_seconds=_env_float("XINYU_V1_TOTAL_TIMEOUT_SECONDS", 120.0),
                fast_path_seconds=_env_float("XINYU_V1_FAST_PATH_TIMEOUT_SECONDS", 1.5),
                slow_path_seconds=_env_float("XINYU_V1_SLOW_PATH_TIMEOUT_SECONDS", 90.0),
                vector_seconds=_env_float("XINYU_V1_VECTOR_BUDGET_SECONDS", 3.0),
                maintenance_seconds=_env_float("XINYU_V1_MAINTENANCE_TIMEOUT_SECONDS", 300.0),
            ),
            tokens=TokenBudget(total=_env_int("XINYU_LLM_MAX_TOKENS", 4096)).validate(),
            retry=RetryPolicy(
                attempts=_env_int("XINYU_V1_RETRY_ATTEMPTS", 2),
                base_delay_seconds=_env_float("XINYU_V1_RETRY_BASE_DELAY_SECONDS", 0.25),
                max_delay_seconds=_env_float("XINYU_V1_RETRY_MAX_DELAY_SECONDS", 4.0),
            ).normalized(),
        )

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "runtime_mode": self.runtime_mode.value,
            "timezone_name": self.timezone_name,
            "paths": {
                "root": str(self.paths.root),
                "memory_root": str(self.paths.memory_root),
                "runtime_root": str(self.paths.runtime_root),
                "vector_root": str(self.paths.vector_root),
                "local_scope": str(self.paths.local_scope),
            },
            "features": self.features,
            "vector_store": {
                "backend": self.vector_store.backend.value,
                "degraded_backend": self.vector_store.degraded_backend.value,
                "collection_prefix": self.vector_store.collection_prefix,
                "qdrant_url": self.vector_store.qdrant_url,
                "chroma_path": self.vector_store.chroma_path,
                "embedding_model": self.vector_store.embedding_model,
                "embedding_dimensions": self.vector_store.embedding_dimensions,
            },
            "model": {
                "provider": self.model.provider,
                "model": self.model.model,
                "base_url": self.model.base_url,
                "api_key_env": self.model.api_key_env,
                "temperature": self.model.temperature,
                "max_tokens": self.model.max_tokens,
            },
        }

