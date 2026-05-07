# XinYu Next 24h Task Queue

Date: 2026-05-07

## Stop-Gap First

- [ ] Triage `diagnostics\check_xinyu_health.py --json` critical `recent_exceptions`.
- [ ] Triage v1 shadow tail errors before any canary scope change.
- [ ] Decide whether health diagnostic exception scanning needs a narrower time window or structured error ledger.

## P0

- [x] Extract Codex service boundary from `xinyu_core_bridge.py`.
- [x] Extract Learning service boundary from `xinyu_core_bridge.py`.
- [x] Migrate one low-risk projection writer to `state_service.py`.
- [x] Add a focused state-service caller smoke for the migrated writer.

## P1

- [ ] Extract QQ sender helpers from `xinyu_qq_gateway.py`.
- [ ] Reduce QQ command router shims in `xinyu_qq_gateway.py`.
- [ ] Extract Desktop REST/snapshot methods after health triage.

## P2

- [ ] Add chat service boundary.
- [ ] Add narrower long-run health history/checkpoint ledger.
- [ ] Add service-boundary unit tests for new bridge modules.

## Red Lines Remain

- [ ] No persona semantic edits.
- [ ] No long-term memory body edits.
- [ ] No real QQ outbound tests without owner approval.
- [ ] No v1 real traffic expansion without owner approval.
- [ ] No runtime/memory/Autonomy/Local-Scope deletion.
