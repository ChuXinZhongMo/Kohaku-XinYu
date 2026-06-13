from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from xinyu_bridge_health_provider_registry import (
    HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_RUNTIME_ATTR,
    HttpHealthDiagnosticsProviderRegistry,
)
from xinyu_bridge_health_provider_registry_service import (
    HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_SERVICE_MODE,
    HealthDiagnosticsProviderRegistryService,
    health_provider_registry_service_transport,
)
from xinyu_bridge_health_service_providers import service_health_provider_ids
from xinyu_bridge_health_snapshot import health_snapshot


class _SelfChoiceStore:
    def health_snapshot(self) -> dict[str, object]:
        return {"available": True}


def _runtime(root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        xinyu_dir=root,
        memory_root=root / "memory",
        _sessions={},
        turn_timeout_seconds=1,
        pre_model_routes_timeout_seconds=1,
        outward_renderer=False,
        renderer_mode="off",
        render_timeout_seconds=1,
        session_idle_ttl_seconds=60,
        max_sessions=2,
        dialogue_prompt_tail_entries=0,
        dialogue_session_tail_entries=0,
        dialogue_persisted_tail_entries=0,
        proactive_min_interval_seconds=60,
        autonomous_maintenance_enabled=False,
        _autonomous_task=None,
        _autonomous_in_progress=False,
        autonomous_maintenance_session_key="",
        autonomous_maintenance_initial_delay_seconds=0,
        autonomous_maintenance_interval_seconds=0,
        _autonomous_run_count=0,
        _autonomous_failure_count=0,
        _autonomous_last_started_at="",
        _autonomous_last_success_at="",
        _autonomous_last_error="",
        _autonomous_last_memory_changed=False,
        _autonomous_next_run_at="",
        _metabolism_task=None,
        _metabolism_in_progress=False,
        metabolism_runner_interval_seconds=0,
        _metabolism_run_count=0,
        _metabolism_last_started_at="",
        _metabolism_last_success_at="",
        _metabolism_last_error="",
        _v1_health=lambda: {"enabled": False},
        self_choice_store=_SelfChoiceStore(),
        _closed=False,
    )


def _check(failures: list[str], condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        runtime = _runtime(root)
        service = HealthDiagnosticsProviderRegistryService()
        registry = HttpHealthDiagnosticsProviderRegistry(
            endpoint="http://127.0.0.1:8791/",
            enabled=True,
            transport=health_provider_registry_service_transport(service),
        )
        setattr(runtime, HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_RUNTIME_ATTR, registry)

        snapshot = health_snapshot(
            runtime,
            bridge_version="registry-service-smoke",
            source_digest="bridge-digest",
            runtime_source_digest="runtime-digest",
        )
        service_health = snapshot["service_health"]

        _check(failures, service_health["service_health_status"] == "ok", "service health not ok")
        _check(failures, service_health["service_count"] == len(service_health_provider_ids()), "provider count changed")
        _check(
            failures,
            all(
                item["payload"].get("source") == HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_SERVICE_MODE
                for item in service_health["services"].values()
            ),
            "provider service source missing",
        )
        _check(failures, not (root / "runtime").exists(), "provider service created runtime state")
        _check(failures, not (root / "memory").exists(), "provider service created memory state")

    if failures:
        print("health diagnostics provider registry service smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("health diagnostics provider registry service smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
