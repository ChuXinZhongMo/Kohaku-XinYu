from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from xinyu_bridge_health_provider_registry import (
    HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_RUNTIME_ATTR,
    health_diagnostics_provider_registry_readiness,
)
from xinyu_bridge_health_service_providers import service_health_provider_ids
from xinyu_bridge_health_snapshot import health_snapshot
from xinyu_bridge_health_diagnostics_service import HealthDiagnosticsServiceHealthProvider


class _SelfChoiceStore:
    def health_snapshot(self) -> dict[str, object]:
        return {"available": True}


class _ExternalProviderRegistry:
    mode = "external_provider_registry_smoke"

    def providers(self, runtime: object) -> tuple[HealthDiagnosticsServiceHealthProvider, ...]:
        del runtime

        def provider(service_id: str):
            return lambda received_runtime: {
                "ok": True,
                "ready": True,
                "status": "ok",
                "mode": self.mode,
                "notes": [f"{service_id}:external-registry"],
            }

        return tuple(
            HealthDiagnosticsServiceHealthProvider(service_id, provider(service_id))
            for service_id in service_health_provider_ids()
        )


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
        setattr(runtime, HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_RUNTIME_ATTR, _ExternalProviderRegistry())

        external_ready = health_diagnostics_provider_registry_readiness(runtime)
        external_snapshot = health_snapshot(
            runtime,
            bridge_version="registry-smoke",
            source_digest="bridge-digest",
            runtime_source_digest="runtime-digest",
        )
        external_health = external_snapshot["service_health"]

        _check(failures, external_ready.mode == "external_provider_registry_smoke", "external registry not selected")
        _check(failures, external_ready.ready is True, "external registry not ready")
        _check(failures, external_health["service_health_status"] == "ok", "external registry health not ok")
        _check(
            failures,
            all(
                "external-registry" in ",".join(external_health["services"][service_id]["notes"])
                for service_id in service_health_provider_ids()
            ),
            "external registry notes missing",
        )

        delattr(runtime, HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_RUNTIME_ATTR)
        fallback_ready = health_diagnostics_provider_registry_readiness(runtime)
        fallback_snapshot = health_snapshot(
            runtime,
            bridge_version="registry-smoke",
            source_digest="bridge-digest",
            runtime_source_digest="runtime-digest",
        )
        fallback_health = fallback_snapshot["service_health"]

        _check(failures, fallback_ready.mode == "in_process_provider_registry", "fallback registry not selected")
        _check(failures, fallback_health["service_count"] == len(service_health_provider_ids()), "fallback count changed")
        _check(failures, not (root / "runtime").exists(), "registry smoke created runtime state")
        _check(failures, not (root / "memory").exists(), "registry smoke created memory state")

    if failures:
        print("health diagnostics provider registry smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("health diagnostics provider registry smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
