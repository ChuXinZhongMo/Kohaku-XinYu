# XinYu Validation Matrix

Date: 2026-05-07
Scope: behavior-preserving refactor gates for the local XinYu runtime.

## How To Run

Run commands from:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
```

Use the local venv when present:

```powershell
.\.venv\Scripts\python.exe <command>
```

Every loop still starts with repository-level checks from `D:\XinYu`:

```powershell
git diff --check
git status --short --branch
```

For Python code changes, also compile the changed Python files:

```powershell
.\.venv\Scripts\python.exe -m py_compile <changed-python-files>
```

## Capability Gates

| Capability | Primary commands | When required | Current coverage |
| --- | --- | --- | --- |
| Bridge startup/probe | `bridge_probe_smoke.py`; `bridge_session_cleanup_smoke.py`; `smoke_run.py --group deployment` | Any core bridge route, auth, session, startup, or dependency change | Covered |
| Desktop REST | `xinyu_desktop_rest_smoke.py` | Any `/desktop/*` REST handler or desktop snapshot change | Covered |
| Desktop WS/events | `xinyu_desktop_ws_smoke.py`; `xinyu_desktop_events_smoke.py` | Any desktop event bus, websocket, or event route change | Covered |
| Desktop life/metabolism/proactive | `xinyu_desktop_life_state_smoke.py`; `xinyu_desktop_metabolism_ticket_smoke.py`; `xinyu_desktop_proactive_smoke.py` | Any desktop-facing life state, metabolism, or proactive state change | Covered |
| QQ Gateway transport | `xinyu_qq_gateway_smoke.py`; `xinyu_qq_review_smoke.py` | Any `xinyu_qq_gateway.py` or QQ adapter extraction | Covered, no real outbound |
| QQ outbox | `qq_outbox_smoke.py`; `check_sent_index.py <adapter_msg_id>` for a known local test/live id; `python -m pytest tests\test_gateway_ack_spool.py::test_sent_reply_index_lookup_by_adapter_message_id -q` when no adapter id is available | Any outbox claim/send/ack/index change | Covered, no real outbound |
| Codex delegation | `codex_delegate_smoke.py`; `codex_delegation_reality_smoke.py` | Any Codex request, delegation, or material contract change | Covered |
| Codex completion outbox | `codex_completion_outbox_smoke.py`; `codex_report_material_smoke.py` | Any completion report or outbox handling change | Covered |
| Learning ingest | `bridge_learning_ingest_smoke.py`; `.\.venv\Scripts\python.exe -m pytest tests\test_learning_closed_loop.py -q` | Any `/learning/*`, ingest scope, or learning write wrapper change | Covered |
| Learning library/source chain | `learning_library_smoke.py`; `learning_quality_smoke.py`; `source_learning_chain_smoke.py`; `smoke_run.py --group learning` | Any learning quality, library, source material, or controlled source path change | Covered |
| Service boundaries | `service_boundary_smoke.py`; plus the capability smoke for the touched service | Any extracted boundary helper, service wrapper, or transport sender contract change | Covered for pure boundary contracts |
| Memory/state helpers | `state_io_smoke.py`; `memory_event_sourcing_smoke.py`; `private_thought_events_smoke.py`; `smoke_run.py --group memory` | Any state helper, event/projection, or memory-sidecar change | Covered for existing helper; broader state governance still pending |
| Persona/voice behavior | `persona_contract_absence_smoke.py`; `personality_evolution_smoke.py`; `live_voice_card_smoke.py`; `pre_draft_turn_classifier_smoke.py`; `xinyu_speech_controller_smoke.py`; `smoke_run.py --group voice` | Any renderer, prompt assembly, voice, or final speaking-controller change | Covered; avoid changing semantics |
| Runtime security/local scope | `bridge_auth_smoke.py`; `runtime_security_smoke.py`; `local_scope_smoke.py`; `smoke_run.py --group privacy` | Any auth, token, loopback, path scope, or local file access change | Covered |
| v1 compatibility | `.\.venv\Scripts\python.exe -m pytest tests\test_v1_canary_readiness.py tests\v1\test_bridge_compatibility.py tests\v1\test_hybrid_router.py -q`; `xinyu_v1_owner_simple_canary_smoke.py` | Any v1 shadow/canary/gateway/routing compatibility change | Covered, review-only canary |
| Long-run readiness | `runtime_readiness_smoke.py --offline`; `long_run_status.py`; from `D:\XinYu`: `python diagnostics\check_xinyu_health.py --json`; `python diagnostics\check_xinyu_health.py --json --write-ledger`; `python diagnostics\check_xinyu_health.py --json --recent-window-minutes 0` for historical-tail comparison | Any deployment, runtime readiness, live health, or long-run status change | Covered for health collection, recent-window scanning, and runtime ledger; live health can still be degraded |

## Refactor Slice Gates

| Slice | Minimum validation |
| --- | --- |
| Documentation-only | `git diff --check`; `git status --short --branch` |
| New Python helper without runtime wiring | `git diff --check`; `python -m py_compile <helper>` |
| Core bridge module extraction | `python -m py_compile xinyu_core_bridge.py <new-module>`; `bridge_probe_smoke.py`; relevant capability smoke |
| Bridge auth boundary | `python -m py_compile xinyu_bridge_auth.py xinyu_bridge_http.py bridge_auth_smoke.py`; `bridge_auth_smoke.py`; `bridge_probe_smoke.py`; `runtime_security_smoke.py` |
| Bridge context boundary | `python -m py_compile xinyu_bridge_context.py xinyu_core_bridge.py bridge_context_smoke.py`; `bridge_context_smoke.py`; focused prompt-signature pytest; `bridge_probe_smoke.py` |
| Bridge session boundary | `python -m py_compile xinyu_bridge_session.py xinyu_core_bridge.py bridge_session_smoke.py bridge_session_cleanup_smoke.py`; `bridge_session_smoke.py`; `bridge_session_cleanup_smoke.py`; `bridge_probe_smoke.py` |
| Bridge value helper boundary | `python -m py_compile xinyu_bridge_values.py xinyu_core_bridge.py bridge_values_smoke.py`; `bridge_values_smoke.py`; `bridge_probe_smoke.py` |
| Desktop service extraction | `python -m py_compile xinyu_core_bridge.py <new-module>`; `xinyu_desktop_rest_smoke.py`; `xinyu_desktop_ws_smoke.py`; `xinyu_desktop_events_smoke.py`; `bridge_probe_smoke.py` |
| Codex service extraction | `python -m py_compile xinyu_core_bridge.py <new-module>`; `codex_delegate_smoke.py`; `codex_completion_outbox_smoke.py`; `bridge_probe_smoke.py` |
| Learning service extraction | `python -m py_compile xinyu_core_bridge.py <new-module>`; `bridge_learning_ingest_smoke.py`; `python -m pytest tests\test_learning_closed_loop.py -q`; `bridge_probe_smoke.py` |
| Chat service boundary | `python -m py_compile xinyu_core_bridge.py xinyu_chat_service.py chat_service_smoke.py`; `chat_service_smoke.py`; `bridge_probe_smoke.py`; focused chat/session pytest |
| Service-boundary smoke | `python -m py_compile service_boundary_smoke.py xinyu_qq_sender.py xinyu_desktop_service.py xinyu_chat_service.py xinyu_codex_service.py xinyu_learning_service.py`; `service_boundary_smoke.py`; plus touched capability smoke |
| State service helper | `python -m py_compile state_service.py`; `state_io_smoke.py`; `promise_followup_state_smoke.py`; `xinyu_desktop_proactive_smoke.py` for proactive request state; `autonomous_state_smoke.py` for autonomous projection state; any focused test added for the helper |
| QQ runtime trace state | `python -m py_compile state_service.py xinyu_qq_gateway.py qq_runtime_trace_smoke.py`; `state_io_smoke.py`; `qq_runtime_trace_smoke.py`; `xinyu_qq_gateway_smoke.py`; `xinyu_qq_review_smoke.py` |
| QQ runtime JSON state | `python -m py_compile state_service.py xinyu_qq_gateway.py qq_recent_sticker_state_smoke.py`; `state_io_smoke.py`; `qq_recent_sticker_state_smoke.py`; `xinyu_qq_gateway_smoke.py`; `xinyu_qq_review_smoke.py` |
| Group shadow state | `python -m py_compile state_service.py xinyu_group_shadow_observer.py group_shadow_state_smoke.py`; `state_io_smoke.py`; `group_shadow_state_smoke.py`; `xinyu_qq_gateway_smoke.py` |
| QQ trust/outbox extraction | `python -m py_compile xinyu_qq_gateway.py <new-module>`; `qq_trust_policy_smoke.py` for trust policy helpers; `xinyu_qq_gateway_smoke.py`; `xinyu_qq_review_smoke.py`; `qq_outbox_smoke.py`; sent-index lookup via `check_sent_index.py <adapter_msg_id>` or the focused pytest fallback |
| QQ config/sender/command extraction | `python -m py_compile xinyu_qq_gateway.py <new-module>`; `xinyu_qq_config_smoke.py` for route derivation and `GatewayConfig`; `qq_config_helpers_smoke.py` for config parsing helpers; `xinyu_qq_gateway_smoke.py`; `xinyu_qq_review_smoke.py` |
| QQ server extraction | `python -m py_compile xinyu_qq_server.py xinyu_qq_gateway.py xinyu_qq_server_smoke.py`; `xinyu_qq_server_smoke.py`; `xinyu_qq_gateway_smoke.py`; `xinyu_qq_review_smoke.py` |
| QQ attachment material extraction | `python -m py_compile xinyu_qq_attachment_resolver.py xinyu_qq_gateway.py qq_attachment_material_smoke.py`; `qq_attachment_material_smoke.py`; `xinyu_qq_gateway_smoke.py`; `xinyu_qq_review_smoke.py` |
| QQ core client extraction | `python -m py_compile xinyu_qq_core_client.py xinyu_qq_gateway.py qq_core_client_smoke.py`; `qq_core_client_smoke.py`; `xinyu_qq_gateway_smoke.py`; `python -m pytest tests\test_gateway_ack_spool.py -q` |
| QQ model extraction | `python -m py_compile xinyu_qq_models.py xinyu_qq_gateway.py qq_models_smoke.py`; `qq_models_smoke.py`; `xinyu_qq_gateway_smoke.py`; `python -m pytest tests\test_gateway_ack_spool.py -q` |
| QQ CLI extraction | `python -m py_compile xinyu_qq_cli.py xinyu_qq_gateway.py qq_cli_smoke.py`; `qq_cli_smoke.py`; `xinyu_qq_gateway_smoke.py` |
| QQ sticker semantics extraction | `python -m py_compile xinyu_qq_sticker_semantics.py xinyu_qq_gateway.py qq_sticker_semantics_smoke.py`; `qq_sticker_semantics_smoke.py`; `xinyu_qq_gateway_smoke.py`; `xinyu_qq_review_smoke.py` |
| QQ forward context extraction | `python -m py_compile xinyu_qq_forward_context.py xinyu_qq_gateway.py qq_forward_context_smoke.py`; `qq_forward_context_smoke.py`; `xinyu_qq_gateway_smoke.py`; `xinyu_qq_review_smoke.py` |
| QQ rich context extraction | `python -m py_compile xinyu_qq_rich_context.py xinyu_qq_gateway.py qq_rich_context_smoke.py`; `qq_rich_context_smoke.py`; `xinyu_qq_gateway_smoke.py`; `xinyu_qq_review_smoke.py` |
| QQ gateway compatibility constants | `python -m py_compile xinyu_qq_gateway.py qq_gateway_constants_smoke.py`; `qq_gateway_constants_smoke.py`; `xinyu_qq_gateway_smoke.py`; `xinyu_qq_review_smoke.py` |
| v1 canary gate extraction | `python -m py_compile xinyu_v1_canary_readiness.py <new-module>`; `python -m pytest tests\test_v1_canary_readiness.py tests\v1\test_bridge_compatibility.py tests\v1\test_hybrid_router.py -q` |
| Long-run diagnostic addition | `python -m py_compile diagnostics\check_xinyu_health.py`; `diagnostics\check_xinyu_health.py --json`; `diagnostics\check_xinyu_health.py --json --write-ledger`; `diagnostics\check_xinyu_health.py --json --recent-window-minutes 0`; `long_run_status.py` |

## Missing Or Weak Gates

- `state_io_smoke.py` covers the shared state helper contract; caller-specific projection migrations still need their feature smoke.
- `service_boundary_smoke.py` covers the first extracted pure contracts, but future boundary modules still need their own focused tests as they are split.
- Current live health can still report `warn` from expected workspace dirtiness such as the intentionally untracked user plan file; as of 2026-05-08 10:41, the default 120-minute `recent_exceptions` signal was `ok` with `hits=0`.

## Red Lines During Validation

- Do not run real QQ outbound tests.
- Do not enable or widen v1 real traffic.
- Do not edit runtime `memory/` body files as part of validation.
- Do not treat missing live NapCat availability as permission to fake a pass; use offline gates and record the skip.
