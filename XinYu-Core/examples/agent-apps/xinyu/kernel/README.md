# Cognitive Kernel

This package is the independent foundation layer for XinYu's cognitive architecture.

## Current Scope (K-001)

- **Self**: The persistent owning subject.
  - Unique `self_id`
  - Ownership claiming: `claim_ownership(obj_id, obj_type)`
  - Verification: `verify_ownership(obj_id) -> bool`
  - Introspection: `get_owned_objects()`
  - Full serialization: `to_dict()` / `from_dict()`

## Design Principles

- Self represents **persistent ownership**, not personality or emotion.
- Ownership is the core mechanism by which experiences, beliefs, and memories become "mine".
- This module must remain decoupled from runtime concerns (QQ gateway, bridge, prompts, emotion state, etc.).
- Future modules (Belief Engine, Prediction, Memory Ownership, etc.) will be built *on top of* or *owned by* a `Self`.

## Directory Layout

```
kernel/
├── __init__.py
├── base.py              # Optional base abstractions for kernel modules
├── exceptions.py
├── self/
│   ├── __init__.py
│   ├── model.py         # Pydantic data model (SelfModel, OwnedObject)
│   ├── ownership.py     # Self class with ownership API
│   └── persistence.py   # JSON file + string helpers (memory-first)
└── README.md
```

## Usage Example

```python
from kernel.self import Self
from kernel.self.persistence import save_self_to_json, load_self_from_json

# Create or restore
self = Self(self_id="my_persistent_self_001")

self.claim_ownership("mem-42", "episodic_memory")
self.claim_ownership("belief-about-coffee", "belief")

print(self.verify_ownership("mem-42"))          # True
print(self.get_owned_objects())

# Persist (optional)
save_self_to_json(self, "data/my_self.json")

# Later
restored = load_self_from_json("data/my_self.json")
assert restored.self_id == "my_persistent_self_001"
```

## Roadmap (Main Line)

**K-007 (done)**: World Model with generative predictions
- Implemented with belief/goal-driven rule learning and multi-step simulation
- Added details: 
  - sync_with_self_state + reorganize (from actual Beliefs/Goals + multiple errors)
  - Structured simulate output (with confidence_delta, affected)
  - learn/simulate methods
- Deeper hook: WM update **after** real Experience in turn pipeline
- Owner review gate + pending facts (review_only held until explicit apply_reviewed)
- Bridge context augmentation (now includes generative world_context)
- 18 kernel tests passing
- Demo demonstrates review pending + apply + structured sim

**K-008 (当前主线, advanced)**: Self Reorganization Loop
- `ReorganizationLoop` consumes Prediction Error + Belief + WM + Experience signals
- Cross-layer apply: Attention, Goals, memory candidates, belief reinforce, Self Model proposals
- Owner review gate + `apply_reviewed_reorg` for pending proposals
- `reorg_events.jsonl` trace + turn pipeline hook (post-experience)
- 20 kernel tests passing

**K-009 (当前主线, advanced)**: Closed cognitive cycle
- `run_full_cognitive_cycle`: Experience → Self Model → Prediction Error → Belief → WM → Reorg
- Slow vs fast reorg with escalation; persistent runtime Self (v2 JSON)
- `cognitive_cycle_events.jsonl` + unified turn pipeline hook
- 26 kernel tests passing

**K-010 (advanced)**: Deep Bridge Integration + Owner Governance
- Pre-turn kernel context inject + post-turn cognitive cycle in bridge finish sidecars
- Unified review inbox (WM / Reorg / Belief) + batch owner apply
- `query_kernel_state` / `run_kernel_turn_update` safe read-write paths
- Status exposes `kernel_pending_review_count`, `kernel_writes_blocked`
- 32 tests passing

Higher goals:
- Self-generated long-term narrative from reorganization history
- Persistent identity continuity
- Owner as explicit co-evolver of the Self

See `kernel/COGNITIVE_ARCHITECTURE.md` for the complete extended roadmap and principles.

Current status: 32 tests passing. Kernel participates in every live turn via bridge hooks.

## Constraints

- No pre-defined personality
- No emotion logic
- No runtime coupling at this layer
- Persistence is currently file-based only (no DB)
```

## Status

K-001 complete: minimal viable Self with ownership primitives.
```

## Testing

Tests are located at `tests/kernel/test_self.py`.
Run with the project's test environment.
