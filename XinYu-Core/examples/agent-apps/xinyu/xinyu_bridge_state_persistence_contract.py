from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping


STATE_PERSISTENCE_OWNER = "StateService"
STATE_PERSISTENCE_FALLBACK_ADAPTER = (
    "local_persistence_adapters_only_no_public_runtime_facade"
)
STATE_PERSISTENCE_ROLLBACK = (
    "disable new callers and keep existing in-process JSON/text state writers unchanged"
)
STATE_PERSISTENCE_READINESS_PROBE = (
    "local harness verifies contract shape, default local adapter availability, and tmp-path read/write probes only"
)


@dataclass(frozen=True, slots=True)
class StatePersistenceAdapterContract:
    adapter_id: str
    owner: str
    contract: str


@dataclass(frozen=True, slots=True)
class StatePersistenceContract:
    service_id: str
    local_only: bool
    process_split_candidate: bool
    process_split_ready: bool
    state_owner: str
    owner_layer: str
    local_adapters: tuple[StatePersistenceAdapterContract, ...]
    protected_gates: tuple[str, ...]
    runtime_queues_and_traces: tuple[str, ...]
    public_api_routes: tuple[str, ...]
    public_runtime_facade_methods: tuple[str, ...]
    fallback_adapter: str
    rollback: str
    readiness_probe: str
    harness: str


@dataclass(frozen=True, slots=True)
class StatePersistenceReadiness:
    service_id: str
    mode: str
    started: bool
    ready: bool
    local_only: bool
    process_split_candidate: bool
    process_split_ready: bool
    state_owner: str
    fallback_adapter: str
    rollback: str
    missing_local_adapters: tuple[str, ...]
    public_runtime_facade_methods: tuple[str, ...]
    notes: tuple[str, ...] = ()


STATE_PERSISTENCE_LOCAL_ADAPTERS = (
    StatePersistenceAdapterContract(
        adapter_id="atomic_write_json",
        owner=STATE_PERSISTENCE_OWNER,
        contract="write JSON through the local atomic replace path",
    ),
    StatePersistenceAdapterContract(
        adapter_id="atomic_write_text",
        owner=STATE_PERSISTENCE_OWNER,
        contract="write text through the local atomic replace path",
    ),
    StatePersistenceAdapterContract(
        adapter_id="append_jsonl",
        owner=STATE_PERSISTENCE_OWNER,
        contract="append local trace/event rows without exposing a runtime facade",
    ),
    StatePersistenceAdapterContract(
        adapter_id="read_json",
        owner=STATE_PERSISTENCE_OWNER,
        contract="read local JSON with caller-owned defaults",
    ),
    StatePersistenceAdapterContract(
        adapter_id="read_text_safe",
        owner=STATE_PERSISTENCE_OWNER,
        contract="read local text state with caller-owned defaults and replacement decoding",
    ),
)

STATE_PERSISTENCE_CONTRACT = StatePersistenceContract(
    service_id="state_persistence",
    local_only=True,
    process_split_candidate=False,
    process_split_ready=False,
    state_owner=STATE_PERSISTENCE_OWNER,
    owner_layer="persistence",
    local_adapters=STATE_PERSISTENCE_LOCAL_ADAPTERS,
    protected_gates=(
        "protected_memory_writes_remain_behind_existing_review_gates",
        "reviewed_memory_promotion_is_not_owned_by_public_routes",
        "owner_private_state_stays_local_until_explicit_service_contract",
    ),
    runtime_queues_and_traces=(
        "runtime_startup_traces",
        "turn_route_traces",
        "runtime_queue_state",
    ),
    public_api_routes=(),
    public_runtime_facade_methods=(),
    fallback_adapter=STATE_PERSISTENCE_FALLBACK_ADAPTER,
    rollback=STATE_PERSISTENCE_ROLLBACK,
    readiness_probe=STATE_PERSISTENCE_READINESS_PROBE,
    harness="StatePersistenceLocalHarness",
)


def state_persistence_contract() -> StatePersistenceContract:
    return STATE_PERSISTENCE_CONTRACT


def state_persistence_local_adapter_ids() -> tuple[str, ...]:
    return tuple(adapter.adapter_id for adapter in STATE_PERSISTENCE_LOCAL_ADAPTERS)


def state_persistence_fallback_adapter(
    local_adapters: Mapping[str, Callable[..., Any]],
) -> dict[str, Callable[..., Any]]:
    """Expose only named local persistence adapters; no runtime HTTP facade is mapped."""
    return {
        adapter_id: local_adapters[adapter_id]
        for adapter_id in state_persistence_local_adapter_ids()
        if adapter_id in local_adapters
    }


def state_persistence_default_local_adapters() -> dict[str, Callable[..., Any]]:
    """Bind the contract harness to the existing in-process persistence facade."""
    from state_service import append_jsonl
    from state_service import atomic_write_json
    from state_service import atomic_write_text
    from state_service import read_json
    from state_service import read_text_safe

    return {
        "atomic_write_json": atomic_write_json,
        "atomic_write_text": atomic_write_text,
        "append_jsonl": append_jsonl,
        "read_json": read_json,
        "read_text_safe": read_text_safe,
    }


class StatePersistenceLocalHarness:
    def __init__(self, local_adapters: Mapping[str, Callable[..., Any]] | None = None) -> None:
        self._started = False
        self._local_adapters = (
            state_persistence_default_local_adapters()
            if local_adapters is None
            else dict(local_adapters)
        )

    def start(self) -> StatePersistenceReadiness:
        self._started = True
        return self.readiness()

    def stop(self) -> StatePersistenceReadiness:
        self._started = False
        return self.readiness()

    def readiness(self) -> StatePersistenceReadiness:
        missing = tuple(
            adapter_id
            for adapter_id in state_persistence_local_adapter_ids()
            if not callable(self._local_adapters.get(adapter_id))
        )
        return StatePersistenceReadiness(
            service_id=STATE_PERSISTENCE_CONTRACT.service_id,
            mode="local_consolidation_only",
            started=self._started,
            ready=self._started and not missing,
            local_only=STATE_PERSISTENCE_CONTRACT.local_only,
            process_split_candidate=STATE_PERSISTENCE_CONTRACT.process_split_candidate,
            process_split_ready=STATE_PERSISTENCE_CONTRACT.process_split_ready,
            state_owner=STATE_PERSISTENCE_CONTRACT.state_owner,
            fallback_adapter=STATE_PERSISTENCE_CONTRACT.fallback_adapter,
            rollback=STATE_PERSISTENCE_CONTRACT.rollback,
            missing_local_adapters=missing,
            public_runtime_facade_methods=STATE_PERSISTENCE_CONTRACT.public_runtime_facade_methods,
            notes=(
                "local_persistence_adapters_only",
                "default_state_service_adapters_bound",
                "no_public_runtime_facade",
                "harness_contract_only_no_process_split_candidate",
            ),
        )

    def fallback_adapter(self) -> dict[str, Callable[..., Any]]:
        return state_persistence_fallback_adapter(self._local_adapters)
