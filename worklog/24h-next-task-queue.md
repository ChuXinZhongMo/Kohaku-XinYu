# XinYu Next 24h Task Queue

Date: 2026-05-07 / continued 2026-05-08

## 2026-05-08 Continue Queue

- [x] Add a bounded recent-exception scan window so old log tails do not keep health permanently critical.
- [x] Make recent-exception tail scans read actual file tails and ignore partial JSONL first lines.
- [x] Prevent repeated GitHub learning `stage_error` traces for candidates already marked `failed:*`.
- [ ] Reduce the remaining 120-minute `recent_exceptions` hits from warn toward ok.
- [ ] Start `xinyu_core_bridge.py` package boundary extraction with auth/context/session helpers. Auth helper boundary done; context/session still pending.
- [ ] Start `xinyu_qq_gateway.py` package boundary extraction with config/server/normalizer helpers.
- [x] Migrate another low-risk projection/runtime writer to `state_service.py`. Desktop proactive request state update now uses `atomic_write_text`.

## Stop-Gap First

- [x] Triage `diagnostics\check_xinyu_health.py --json` critical `recent_exceptions`. Diagnostic no longer counts its own ledger, v1 shadow trace, benign malformed WebSocket probe tracebacks, or JSONL `error=none` field names; current signal is `warn`.
- [x] Triage v1 shadow tail errors before any canary scope change. Tail rows were `accepted=true,error=none`; diagnostic now reports `errors=0 window=200` without changing v1 traffic.
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

- [x] No persona semantic edits.
- [x] No long-term memory body edits.
- [x] No real QQ outbound tests without owner approval.
- [x] No v1 real traffic expansion without owner approval.
- [x] No runtime/memory/Autonomy/Local-Scope deletion.
