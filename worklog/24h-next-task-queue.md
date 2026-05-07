# XinYu Next 24h Task Queue

Date: 2026-05-07

## Stop-Gap First

- [ ] Triage `diagnostics\check_xinyu_health.py --json` critical `recent_exceptions`.
- [ ] Triage v1 shadow tail errors before any canary scope change.
- [x] Decide whether health diagnostic exception scanning needs a narrower time window or structured error ledger. Added an opt-in structured runtime health ledger; exception-scan narrowing remains a separate triage decision.

## P0

- [x] Extract Codex service boundary from `xinyu_core_bridge.py`.
- [x] Extract Learning service boundary from `xinyu_core_bridge.py`.
- [x] Migrate one low-risk projection writer to `state_service.py`.
- [x] Add a focused state-service caller smoke for the migrated writer.

## P1

- [x] Extract QQ sender helpers from `xinyu_qq_gateway.py`.
- [x] Reduce QQ command router shims in `xinyu_qq_gateway.py`.
- [x] Extract Desktop REST/snapshot methods after health triage.

## P2

- [x] Add chat service boundary.
- [x] Add narrower long-run health history/checkpoint ledger.
- [x] Add service-boundary unit tests for new bridge modules.

## Red Lines Remain

- [ ] No persona semantic edits.
- [ ] No long-term memory body edits.
- [ ] No real QQ outbound tests without owner approval.
- [ ] No v1 real traffic expansion without owner approval.
- [ ] No runtime/memory/Autonomy/Local-Scope deletion.
