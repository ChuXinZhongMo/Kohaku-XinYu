# XinYu Next 24h Task Queue

Date: 2026-05-07 / continued 2026-05-08

## 2026-05-08 Continue Queue

- [x] Add a bounded recent-exception scan window so old log tails do not keep health permanently critical.
- [x] Make recent-exception tail scans read actual file tails and ignore partial JSONL first lines.
- [x] Prevent repeated GitHub learning `stage_error` traces for candidates already marked `failed:*`.
- [x] Reduce the remaining 120-minute `recent_exceptions` hits from warn toward ok. 2026-05-08 10:41 health reports `hits=0`; overall status remains `warn` only because the user-provided plan file is intentionally untracked.
- [x] Start `xinyu_core_bridge.py` package boundary extraction with auth/context/session helpers. Auth, session, and prompt-context helper boundaries are now started.
- [x] Start `xinyu_qq_gateway.py` package boundary extraction with config/server/normalizer helpers. Config URL helper and WebSocket server helper boundaries are started; normalizer boundary already exists.
- [x] Migrate another low-risk projection/runtime writer to `state_service.py`. Desktop proactive request state update now uses `atomic_write_text`.

## 2026-05-08 Extended Queue

- [x] Migrate autonomous mind loop projection state to `state_service.py`.
- [x] Migrate QQ inbound/rich/sticker runtime trace appends to `state_service.py`.
- [x] Migrate QQ recent sticker runtime state JSON to `state_service.py`.
- [x] Migrate group shadow runtime trace and projection state to `state_service.py`.
- [x] Extract QQ Core Bridge HTTP client from `xinyu_qq_gateway.py`.
- [x] Extract QQ message/action dataclass models from `xinyu_qq_gateway.py`.
- [x] Extract QQ gateway CLI parser from `xinyu_qq_gateway.py`.
- [x] Teach health JSONL windowing to honor `recorded_at` timestamps.
- [x] Extract QQ config parsing helpers from `xinyu_qq_gateway.py`.
- [x] Move `GatewayConfig` itself into `xinyu_qq_config.py` while preserving gateway re-export compatibility.
- [x] Move QQ owner trust command markers into `xinyu_qq_trust_policy.py`.
- [x] Extract received-sticker mood semantics from `xinyu_qq_gateway.py`.
- [x] Extract QQ forward-context raw item and de-duplication helpers from `xinyu_qq_gateway.py`.
- [x] Move image-sticker detection into `xinyu_qq_sticker_semantics.py`.
- [x] Extract QQ reply/forward id parsing into `xinyu_qq_forward_context.py`.
- [x] Extract QQ attachment material builders into `xinyu_qq_attachment_resolver.py`.
- [x] Record 2026-05-08 11:37 long-run health checkpoint.
- [x] Extract QQ rich segment summary helpers into `xinyu_qq_rich_context.py`.
- [x] Re-export QQ gateway compatibility constants from their owner modules.
- [x] Extract core bridge scalar value helpers into `xinyu_bridge_values.py`.
- [x] Extract core bridge text/list helpers into `xinyu_bridge_values.py`.
- [x] Extract core bridge state text/path helpers into `xinyu_bridge_state_text.py`.
- [x] Extract core bridge desktop action label helpers into `xinyu_bridge_desktop_actions.py`.
- [x] Extract shared bridge memory snapshot helper into `xinyu_bridge_memory_snapshot.py`.
- [x] Harden action digest followup smoke freshness window after dated fixture aged past 24h.

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
