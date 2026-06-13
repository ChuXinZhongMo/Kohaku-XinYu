from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from state_service import atomic_write_json, atomic_write_text, read_json


PROACTIVE_DELIVERY_STATE_STORE_OWNER = "ProactiveDeliveryStateStore"
PROACTIVE_DELIVERY_STATE_STORE_MODE = "local_state_service_adapter"
PROACTIVE_DELIVERY_STATE_STORE_ROLLBACK = "keep existing in-process markdown_json_state_files"
PROACTIVE_DELIVERY_STATE_STORE_ADAPTER_IDS = (
    "paths",
    "read_text",
    "write_text",
    "read_outbox_queue",
    "write_outbox_queue",
)


@dataclass(frozen=True, slots=True)
class ProactiveDeliveryStatePaths:
    root: Path
    proactive_request_state: Path
    proactive_dispatch_state: Path
    proactive_presence_state: Path
    qq_outbox_queue: Path
    qq_outbox_dispatch_state: Path
    qq_outbox_lock: Path


@dataclass(frozen=True, slots=True)
class ProactiveDeliveryStateStoreContract:
    service_id: str
    owner: str
    mode: str
    state_files: tuple[str, ...]
    queue_files: tuple[str, ...]
    local_adapters: tuple[str, ...]
    fallback_adapter: str
    rollback: str
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProactiveDeliveryStateStoreReadiness:
    service_id: str
    mode: str
    started: bool
    ready: bool
    owner: str
    fallback_adapter: str
    rollback: str
    missing_local_adapters: tuple[str, ...]
    notes: tuple[str, ...] = ()


PROACTIVE_DELIVERY_STATE_STORE_CONTRACT = ProactiveDeliveryStateStoreContract(
    service_id="proactive_delivery",
    owner=PROACTIVE_DELIVERY_STATE_STORE_OWNER,
    mode=PROACTIVE_DELIVERY_STATE_STORE_MODE,
    state_files=(
        "memory/context/proactive_request_state.md",
        "memory/context/proactive_qq_dispatch_state.md",
        "memory/context/proactive_presence_state.md",
        "memory/context/qq_outbox_dispatch_state.md",
    ),
    queue_files=(
        "memory/context/qq_outbox_queue.json",
        "memory/context/.qq_outbox_queue.lock",
    ),
    local_adapters=PROACTIVE_DELIVERY_STATE_STORE_ADAPTER_IDS,
    fallback_adapter="current_in_process_proactive_delivery_state_files",
    rollback=PROACTIVE_DELIVERY_STATE_STORE_ROLLBACK,
    notes=(
        "local_adapter_contract_only",
        "request_dispatch_and_outbox_paths_have_single_owner",
        "external_state_service_not_started",
    ),
)


def proactive_delivery_state_paths(root: Path) -> ProactiveDeliveryStatePaths:
    context = Path(root) / "memory/context"
    return ProactiveDeliveryStatePaths(
        root=Path(root),
        proactive_request_state=context / "proactive_request_state.md",
        proactive_dispatch_state=context / "proactive_qq_dispatch_state.md",
        proactive_presence_state=context / "proactive_presence_state.md",
        qq_outbox_queue=context / "qq_outbox_queue.json",
        qq_outbox_dispatch_state=context / "qq_outbox_dispatch_state.md",
        qq_outbox_lock=context / ".qq_outbox_queue.lock",
    )


def proactive_delivery_state_store_contract() -> ProactiveDeliveryStateStoreContract:
    return PROACTIVE_DELIVERY_STATE_STORE_CONTRACT


def proactive_delivery_state_store_adapter_ids() -> tuple[str, ...]:
    return PROACTIVE_DELIVERY_STATE_STORE_ADAPTER_IDS


class LocalProactiveDeliveryStateStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def paths(self) -> ProactiveDeliveryStatePaths:
        return proactive_delivery_state_paths(self.root)

    def read_text(self, path: Path) -> str:
        try:
            return Path(path).read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            return ""

    def write_text(self, path: Path, text: str) -> None:
        atomic_write_text(Path(path), str(text).rstrip() + "\n", final_newline=False)

    def read_outbox_queue(self, default: Any = None) -> Any:
        return read_json(self.paths().qq_outbox_queue, default)

    def write_outbox_queue(self, data: Mapping[str, Any]) -> None:
        atomic_write_json(self.paths().qq_outbox_queue, dict(data), sort_keys=False)

    def fallback_adapter(self) -> dict[str, Callable[..., Any]]:
        return {
            "paths": self.paths,
            "read_text": self.read_text,
            "write_text": self.write_text,
            "read_outbox_queue": self.read_outbox_queue,
            "write_outbox_queue": self.write_outbox_queue,
        }


class ProactiveDeliveryStateStoreHarness:
    def __init__(self, root: Path, local_adapters: Mapping[str, Callable[..., Any]] | None = None) -> None:
        self._started = False
        self._store = LocalProactiveDeliveryStateStore(root)
        self._local_adapters = dict(local_adapters or self._store.fallback_adapter())

    def start(self) -> ProactiveDeliveryStateStoreReadiness:
        self._started = True
        return self.readiness()

    def stop(self) -> ProactiveDeliveryStateStoreReadiness:
        self._started = False
        return self.readiness()

    def readiness(self) -> ProactiveDeliveryStateStoreReadiness:
        missing = tuple(
            adapter_id
            for adapter_id in PROACTIVE_DELIVERY_STATE_STORE_ADAPTER_IDS
            if not callable(self._local_adapters.get(adapter_id))
        )
        return ProactiveDeliveryStateStoreReadiness(
            service_id=PROACTIVE_DELIVERY_STATE_STORE_CONTRACT.service_id,
            mode=PROACTIVE_DELIVERY_STATE_STORE_MODE,
            started=self._started,
            ready=self._started and not missing,
            owner=PROACTIVE_DELIVERY_STATE_STORE_OWNER,
            fallback_adapter=PROACTIVE_DELIVERY_STATE_STORE_CONTRACT.fallback_adapter,
            rollback=PROACTIVE_DELIVERY_STATE_STORE_ROLLBACK,
            missing_local_adapters=missing,
            notes=(
                "local_state_service_adapter",
                "no_external_state_service_started",
                "fallback_to_current_in_process_state_files",
            ),
        )

    def fallback_adapter(self) -> dict[str, Callable[..., Any]]:
        return {
            adapter_id: self._local_adapters[adapter_id]
            for adapter_id in PROACTIVE_DELIVERY_STATE_STORE_ADAPTER_IDS
            if callable(self._local_adapters.get(adapter_id))
        }
