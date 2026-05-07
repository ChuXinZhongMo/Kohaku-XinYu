# XinYu Refactor Checklist

Date: 2026-05-07

## Guardrails

- [x] Do not change persona semantics.
- [x] Do not edit long-term memory body content.
- [x] Do not perform real QQ outbound tests.
- [x] Do not expand v1 real traffic.
- [x] Do not bulk-format unrelated files.
- [x] Do not delete `runtime`, `memory`, `Autonomy`, or `Local-Scope`.
- [x] Do not use `git reset --hard`.
- [x] Do not overwrite user parallel edits.

## Baseline Inventory

- [x] Root README reviewed.
- [x] Architecture notes reviewed.
- [x] 24h work plan reviewed.
- [x] Initial git status recorded.
- [x] Core bridge location identified.
- [x] QQ gateway location identified.
- [x] Existing smoke inventory sampled.
- [x] Existing pytest inventory counted.

## Validation

- [x] Add `XINYU-VALIDATION-MATRIX.md`.
- [x] Map Bridge startup to smoke command.
- [x] Map Desktop REST/WS/events to smoke commands.
- [x] Map QQ Gateway and outbox to smoke commands.
- [x] Map Codex delegation and completion outbox to smoke commands.
- [x] Map Learning ingest and closed-loop tests to commands.
- [x] Map Memory/state to commands.
- [x] Map v1 compatibility to commands.
- [x] Map Long-run health to command or mark missing.

## Core Bridge Slices

- [x] Extract Desktop event service startup/shutdown boundary.
- [ ] Extract Desktop REST/snapshot methods.
- [ ] Extract Codex service boundary.
- [ ] Extract Learning service boundary.
- [ ] Extract state write helpers.
- [ ] Extract v1 canary gate.
- [ ] Extract chat service boundary.

## QQ Gateway Slices

- [x] Extract trust policy.
- [x] Extract outbox dispatcher.
- [ ] Extract sender helpers.
- [ ] Extract command router helpers.
- [ ] Preserve OneBot payload compatibility.
- [ ] Preserve no-real-outbound-test rule.

## State And Operations

- [x] Add state write audit.
- [x] Add `state_service.py` helper seed.
- [x] Add long-run operations document.
- [x] Add read-only health diagnostic script.

## Completion Report Inputs

- [ ] Completed loops recorded.
- [ ] Commits recorded.
- [ ] Files changed recorded.
- [ ] Tests recorded.
- [ ] Failed or skipped items recorded.
- [ ] Refactors completed recorded.
- [ ] Remaining gaps recorded.
- [ ] Untouched red lines recorded.
- [ ] Rollback commands recorded.
- [ ] Next 24h recommendation recorded.
