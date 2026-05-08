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
- [x] Reuse v1 canary attachment signal helper from core bridge compatibility alias.
- [x] Extract core bridge reply text normalization helper into `xinyu_bridge_reply_text.py`.
- [x] Extract core bridge bootstrap env/path helpers into `xinyu_bridge_bootstrap.py`.
- [x] Record 2026-05-08 12:17 long-run health checkpoint.
- [x] Extract QQ gateway utility helpers into `xinyu_qq_gateway_utils.py`.
- [x] Extract shared bridge learning sidecar helpers into `xinyu_bridge_learning_sidecars.py`.
- [x] Update Codex delegate smoke static marker ownership after QQ config extraction.
- [x] Extract core bridge loop thread helper into `xinyu_bridge_loop_thread.py`.
- [x] Extract core bridge CLI parser into `xinyu_bridge_cli.py`.
- [x] Extract core bridge null input adapter into `xinyu_bridge_null_input.py`.
- [x] Extract core bridge request error type into `xinyu_bridge_errors.py`.
- [x] Extract core bridge reply bubble helpers into `xinyu_bridge_reply_bubbles.py`.
- [x] Extract core bridge recent sticker reply helpers into `xinyu_bridge_recent_sticker_reply.py`.
- [x] Replace core bridge Codex static wrappers with direct service aliases.
- [x] Record 2026-05-08 12:48 long-run health checkpoint.
- [x] Extract desktop proactive state text field helpers into `xinyu_bridge_desktop_state_text.py`.
- [x] Extract desktop event projection helpers into `xinyu_bridge_desktop_projection.py`.
- [x] Migrate QQ trusted-user config persistence to `state_service.atomic_write_json`.
- [x] Migrate core debug live system prompt dump to `state_service.atomic_write_text`.
- [x] Extract core bridge promise followup text helper into `xinyu_bridge_promises.py`.
- [x] Extract core bridge critical final guard flag helper into `xinyu_bridge_renderer.py`.
- [x] Extract core bridge trusted public search policy helper into `xinyu_bridge_trusted_search.py`.
- [x] Record 2026-05-08 13:20 long-run health checkpoint.
- [x] Replace core bridge desktop limit wrapper with direct service alias.
- [x] Extract core bridge owner/trusted payload privacy policy helpers.
- [x] Extract core bridge timestamp ISO helper into `xinyu_bridge_state_text.py`.
- [x] Replace QQ trust command text wrappers with direct policy aliases.
- [x] Replace QQ outbox delivery route wrapper with direct client alias.
- [x] Replace QQ file URI path wrapper with direct attachment resolver alias.
- [x] Extract core bridge payload text helper and alias session key helper.
- [x] Record 2026-05-08 13:53 long-run health checkpoint.
- [x] Replace core bridge renderer mode wrapper with direct renderer alias.
- [x] Record 2026-05-08 18:36 long-run health checkpoint.
- [x] Replace QQ forward context wrappers with direct helper aliases.
- [x] Replace QQ CQ normalizer wrappers with direct helper aliases.
- [x] Replace QQ sticker semantics wrappers with direct helper aliases.
- [x] Replace QQ rich segment summary wrapper with direct helper alias.
- [x] Replace QQ file path detection wrapper with direct helper alias.
- [x] Replace QQ learning material data wrapper with direct helper alias.
- [x] Replace QQ sticker import material data wrapper with direct helper alias.
- [x] Replace QQ message kind normalizer wrapper with direct method alias.
- [x] Replace QQ text extraction normalizer wrapper with direct method alias.
- [x] Replace QQ sender name normalizer wrapper with direct method alias.
- [x] Replace QQ websocket parser normalizer wrapper with direct method alias.
- [x] Replace QQ OneBot action result wrapper with direct method alias.
- [x] Replace QQ pending ack spool wrapper with direct method alias.
- [x] Replace QQ acked ack spool wrapper with direct method alias.
- [x] Replace QQ sent-message ack payload wrapper with direct method alias.
- [x] Replace QQ pending ack flush wrapper with direct method alias.
- [x] Replace QQ local image file wrapper with direct method alias.
- [x] Replace QQ local file wrapper with direct method alias.
- [x] Record 2026-05-08 19:21 long-run health checkpoint.
- [x] Replace QQ sticker import payload resolver wrapper with direct method alias.
- [x] Replace QQ learning ingest payload resolver wrapper with direct method alias.
- [x] Replace QQ OneBot media resolver wrapper with direct method alias.
- [x] Replace QQ OneBot file resolver wrapper with direct method alias.
- [x] Replace QQ OneBot file URL action wrapper with direct method alias.
- [x] Replace QQ OneBot action payload wrapper with direct method alias.
- [x] Replace QQ OneBot action data wrapper with direct method alias.
- [x] Replace QQ first text field wrapper with direct resolver value alias.
- [x] Replace QQ reply file learning intent wrapper with direct resolver text alias.
- [x] Replace QQ clean CQ text wrapper with direct normalizer value alias.
- [x] Replace QQ message segments wrapper with direct normalizer event alias.
- [x] Replace QQ segment data wrapper with direct normalizer value alias.
- [x] Replace QQ effective whitelist wrapper with direct trust policy gateway alias.
- [x] Replace QQ blocked-user wrapper with direct trust policy gateway alias.
- [x] Replace QQ blocked-group wrapper with direct trust policy gateway alias.
- [x] Replace QQ trusted-user wrapper with direct trust policy gateway alias.
- [x] Replace QQ trust-level wrapper with direct trust policy gateway alias.
- [x] Replace QQ group-shadow allow-list wrapper with direct trust policy gateway alias.
- [x] Replace QQ trust-command target wrapper with direct trust policy gateway alias.
- [x] Replace QQ outbox target wrapper with direct outbox client gateway alias.
- [x] Replace QQ outbox message ack payload wrapper with direct outbox client alias.
- [x] Replace QQ outbox ack wrapper with direct outbox client alias.
- [x] Replace QQ sent-message ack record wrapper with direct outbox client alias.
- [x] Replace QQ sent-message ack send wrapper with direct outbox client alias.
- [x] Replace QQ sent visible reply ack wrapper with direct outbox client alias.

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
