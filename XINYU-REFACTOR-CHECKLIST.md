# XinYu Refactor Checklist

Date: 2026-05-07

## Guardrails

- [ ] Do not change persona semantics.
- [ ] Do not edit long-term memory body content.
- [ ] Do not perform real QQ outbound tests.
- [ ] Do not expand v1 real traffic.
- [ ] Do not bulk-format unrelated files.
- [ ] Do not delete `runtime`, `memory`, `Autonomy`, or `Local-Scope`.
- [ ] Do not use `git reset --hard`.
- [ ] Do not overwrite user parallel edits.

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

- [ ] Add `XINYU-VALIDATION-MATRIX.md`.
- [ ] Map Bridge startup to smoke command.
- [ ] Map Desktop REST/WS/events to smoke commands.
- [ ] Map QQ Gateway and outbox to smoke commands.
- [ ] Map Codex delegation and completion outbox to smoke commands.
- [ ] Map Learning ingest and closed-loop tests to commands.
- [ ] Map Memory/state to commands.
- [ ] Map v1 compatibility to commands.
- [ ] Map Long-run health to command or mark missing.

## Core Bridge Slices

- [ ] Extract Desktop service boundary.
- [ ] Extract Codex service boundary.
- [ ] Extract Learning service boundary.
- [ ] Extract state write helpers.
- [ ] Extract v1 canary gate.
- [ ] Extract chat service boundary.

## QQ Gateway Slices

- [ ] Extract trust policy.
- [ ] Extract outbox dispatcher.
- [ ] Extract sender helpers.
- [ ] Extract command router helpers.
- [ ] Preserve OneBot payload compatibility.
- [ ] Preserve no-real-outbound-test rule.

## State And Operations

- [ ] Add state write audit.
- [ ] Add `state_service.py` helper seed.
- [ ] Add long-run operations document.
- [ ] Add read-only health diagnostic script.

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
