# XinYu P69 Cross-Domain Runtime Integration Closeout - 2026-05-19

## Scope

Plan: `project-plans/XINYU-CROSS-DOMAIN-SYNAESTHESIA-PLAN-2026-05-19.md`

Batch: runtime integration and closeout after A-F.

Goal: move the cross-domain providers from standalone tested modules into the
runtime spine as advisory gates, while keeping the current owner turn and
canonical recall owner authoritative.

## Runtime Integration Completed

- `xinyu_runtime_context.py`
  - Adds `[runtime/turn_triage_gate]` after Scene Frame.
  - Adds `[runtime/slow_state_modulator]` when slow state has active policy.
  - Uses recent project context and canonical recall context only as advisory
    inputs.
- `xinyu_bridge_turn_sidecars.py`
  - Injects `turn_triage_gate` into live prompt sidecars.
  - Injects `slow_state_modulator` when active.
  - Persists slow state through the store boundary.
- `xinyu_core_bridge.py`
  - Runs `classify_response_error(...)` after final reply shaping.
  - Feeds response error outcome into `build_slow_state(...)`.
  - Adds compact runtime notes without changing the visible reply.
- `xinyu_memory_candidate_extractor.py`
  - Runs `evaluate_memory_immune_gate(...)` before candidate storage.
  - Blocks sensitive/critical candidates.
  - Adds immune decision metadata to candidate review notes.
- `stores/slow_state_modulator_state.py`
  - Owns `memory/context/slow_state_modulator_state.json` as a compatibility
    runtime state store.
- `ops/validation/memory_structured_p0_triage.py`
  - Registers slow-state JSON as `compat_store_owner_exists`.

## Tests Added

- `tests/test_cross_domain_runtime_integration.py`
  - Runtime context includes turn triage for short continue commands.
  - Runtime context includes slow state for low-energy scenes.
  - Memory candidate extraction records immune gate metadata.
  - Sensitive immune candidates are blocked before storage.
- `tests/test_slow_state_modulator_state_store.py`
  - Slow-state store boundary and invalid JSON fallback.

## Validation

- Runtime integration focused:
  - `.\.venv\Scripts\python.exe -m pytest tests\test_cross_domain_runtime_integration.py tests\test_runtime_context.py tests\test_memory_event_time_provenance.py tests\test_memory_immune_gate.py tests\test_turn_triage_gate.py tests\test_slow_state_modulator.py tests\test_response_error_loop.py -q`
  - 44 passed
- Live sidecar nearby validation:
  - `.\.venv\Scripts\python.exe tests\smoke\voice\pre_draft_turn_classifier_smoke.py`
  - pass
  - `.\.venv\Scripts\python.exe tests\smoke\voice\dynamic_life_posture_smoke.py`
  - pass
  - `.\.venv\Scripts\python.exe -m pytest tests\test_dialogue_curiosity_bridge_injection.py -q`
  - 50 passed
- Boundary repair validation:
  - `.\.venv\Scripts\python.exe -m pytest tests\test_slow_state_modulator_state_store.py tests\test_slow_state_modulator.py tests\test_memory_structured_p0_triage.py tests\test_boundary_readiness_audit.py tests\test_cross_domain_runtime_integration.py -q`
  - 19 passed
- Full tests:
  - `.\.venv\Scripts\python.exe -m pytest tests -q`
  - 649 passed
- Quick smoke:
  - `.\.venv\Scripts\python.exe smoke_run.py --group quick --timeout-seconds 180 --json`
  - ok=true
- Diff whitespace check:
  - `git diff --check -- <cross-domain touched files>`
  - pass, with existing CRLF warnings on touched tracked files.

## Completed Cross-Domain Mechanisms

- Research ledger / registry:
  - `XINYU-CROSS-DOMAIN-SYNAESTHESIA.md`
  - `stores/cross_domain_synaesthesia_registry.json`
- Medical triage:
  - `xinyu_turn_triage_gate.py`
  - Runtime prompt integration complete.
- Control theory:
  - `xinyu_response_error_loop.py`
  - Post-reply classification feeds slow state.
- Immune danger theory:
  - `xinyu_memory_immune_gate.py`
  - Memory candidate extraction integration complete.
- Allostasis / slow variables:
  - `xinyu_slow_state_modulator.py`
  - Runtime context and live sidecar integration complete.
  - Store boundary added.
- Ecology / gardening:
  - `xinyu_module_ecology_audit.py`
  - Advisory audit provider complete.

## Direct Effect

- Short commands such as "continue/start/next" now have a tested route to
  pending work context in runtime prompt material.
- Visible response failures now become classified feedback signals instead of
  loose prompt patches.
- Memory candidates now pass a danger gate before storage.
- Fatigue/correction/relationship pressure can persist briefly and decay.
- Cleanup now has an ecology audit vocabulary before merge/archive/delete.

## Remaining Risks

- The module ecology audit is advisory and has not yet been run across the full
  dirty worktree for a reviewed kept/merged/archived/deleted table.
- Desktop typecheck/build was not rerun because no desktop source files were
  changed in this batch; quick smoke did cover desktop life/metabolism smoke.
- The worktree was already very dirty before this batch. No git commit was made.

## Recovery Point

Start from:

`D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`

Highest-value next command:

`.\.venv\Scripts\python.exe -m pytest tests -q`

Optional next batch:

Run `xinyu_module_ecology_audit.py` over a curated list of active modules and
produce a reviewed kept/merged/archived/deleted table. Do not delete anything
without archive/delete reference audit evidence.
