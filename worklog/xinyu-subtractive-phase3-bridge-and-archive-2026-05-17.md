# XinYu Subtractive Phase 3 - Bridge Thinning And Archive - 2026-05-17

Status: active batch.

## Scope

This batch continues the subtractive refactor after the ops manual move:

- extract route-only logic out of `xinyu_core_bridge.py`
- keep the public bridge method names as compatibility delegates
- archive constant-only manifest files that no longer have live imports

## External Plugin Route Extraction

Added:

- `XinYu-Core/examples/agent-apps/xinyu/xinyu_bridge_external_plugin_routes.py`
- `XinYu-Core/examples/agent-apps/xinyu/tests/test_bridge_external_plugin_routes.py`

Changed:

- `xinyu_core_bridge.py` now delegates:
  - `external_plugin_manifest`
  - `external_plugin_config`
  - `external_plugin_install`
  - `external_plugin_call`
- `smoke_run.py` quick py-compile now includes `xinyu_bridge_external_plugin_routes.py`.

Rationale:

The external plugin gateway is route orchestration. It depends on `xinyu_dir`,
`_closed`, `_sessions`, and `codex_execute`, but it does not need ownership of
the full core bridge class.

Validation passed:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -B -m py_compile xinyu_bridge_external_plugin_routes.py xinyu_core_bridge.py xinyu_bridge_http.py smoke_run.py tests/test_bridge_external_plugin_routes.py
.\.venv\Scripts\python.exe -B -m pytest -q tests/test_bridge_external_plugin_routes.py tests/test_action_status_reply.py
```

Result:

```text
9 passed
```

## Desktop Self-Action Route Extraction

Added:

- `XinYu-Core/examples/agent-apps/xinyu/xinyu_bridge_desktop_self_action_routes.py`

Changed:

- `xinyu_core_bridge.py` now keeps the historical methods as thin delegates:
  - `desktop_self_action_approval`
  - `_desktop_attach_self_action_patch_executor`
  - `_desktop_self_action_pending_item`
  - `_desktop_self_action_approval_reply`
- `smoke_run.py` quick py-compile now includes `xinyu_bridge_desktop_self_action_routes.py`.

Rationale:

Desktop self-action approval is a route family. It only needs `_closed`,
`xinyu_dir`, `desktop_snapshot({})`, and `codex_execute(...)`; keeping it inside
the core bridge class made the class harder to scan without owning core turn
behavior.

Validation passed:

```powershell
.\.venv\Scripts\python.exe -B -m py_compile xinyu_bridge_desktop_self_action_routes.py xinyu_core_bridge.py xinyu_bridge_http.py smoke_run.py
.\.venv\Scripts\python.exe -B -m pytest -q tests/test_self_action_approval_controls.py tests/test_desktop_self_action_snapshot.py tests/test_self_action_gateway.py tests/test_self_action_patch_executor.py
.\.venv\Scripts\python.exe tests/smoke/initiative/self_action_gateway_smoke.py
.\.venv\Scripts\python.exe tests/smoke/initiative/self_action_patch_executor_smoke.py
```

Results:

```text
21 passed
Self action gateway smoke passed
Self action patch executor smoke passed
```

## QQ Reply/Forward Context Extraction

Added:

- `XinYu-Core/examples/agent-apps/xinyu/xinyu_qq_gateway_context_enrichment.py`

Changed:

- `xinyu_qq_gateway.py` now delegates reply-file learning, reply context, and
  forward context helper methods to the new module while preserving method names
  on `NativeQQGateway`.
- `smoke_run.py` quick py-compile now includes `xinyu_qq_gateway_context_enrichment.py`.

Rationale:

The QQ gateway had a dense helper block for reply/forward enrichment near the
class top. Moving the implementation to a focused module reduces gateway
surface area while leaving direct smoke calls intact.

Validation passed:

```powershell
.\.venv\Scripts\python.exe -B -m py_compile xinyu_qq_gateway_context_enrichment.py xinyu_qq_gateway.py smoke_run.py
.\.venv\Scripts\python.exe -B -m pytest -q tests/test_dialogue_curiosity_bridge_injection.py -k "qq_forward_context_sidecar or qq_image_context_sidecar or qq_low_information_sticker_sidecar"
.\.venv\Scripts\python.exe tests/smoke/qq/qq_forward_context_smoke.py
.\.venv\Scripts\python.exe tests/smoke/qq/integration/xinyu_qq_gateway_smoke.py
.\.venv\Scripts\python.exe tests/smoke/qq/integration/qq_runtime_trace_smoke.py
.\.venv\Scripts\python.exe tests/smoke/qq/qq_rich_context_smoke.py
.\.venv\Scripts\python.exe tests/smoke/bridge/bridge_recent_sticker_reply_smoke.py
```

Results:

```text
3 passed, 47 deselected
XinYu QQ forward context smoke passed
xinyu_qq_gateway_smoke: ok
QQ runtime trace smoke passed
XinYu QQ rich context smoke passed
XinYu bridge recent sticker reply smoke passed
```

## QQ Visible Dispatch Extraction

Added:

- `XinYu-Core/examples/agent-apps/xinyu/xinyu_qq_visible_dispatch.py`
- `XinYu-Core/examples/agent-apps/xinyu/tests/test_qq_visible_dispatch.py`

Changed:

- `xinyu_qq_gateway.py` delegates visible reply normalization, bubble send
  aggregation, direct-send shadow records, outbox-send shadow records, and
  combined OneBot action response handling to the new module.
- `smoke_run.py` quick py-compile now includes `xinyu_qq_visible_dispatch.py`.

Rationale:

Visible send dispatch is QQ adapter boundary logic. It should sit next to the
QQ transport helpers instead of inside the gateway's event preparation and
dispatch class body.

Validation passed:

```powershell
.\.venv\Scripts\python.exe -B -m py_compile xinyu_qq_visible_dispatch.py xinyu_qq_gateway.py smoke_run.py tests/test_qq_visible_dispatch.py
.\.venv\Scripts\python.exe -B -m pytest -q tests/test_qq_visible_dispatch.py tests/test_visible_send_shadow.py tests/test_visible_reply_guard_plugin.py tests/test_visible_persona_voice.py
.\.venv\Scripts\python.exe tests/smoke/qq/integration/xinyu_qq_gateway_smoke.py
.\.venv\Scripts\python.exe tests/smoke/qq/qq_outbox_smoke.py
.\.venv\Scripts\python.exe tests/smoke/qq/qq_outbox_route_alias_smoke.py
.\.venv\Scripts\python.exe tests/smoke/qq/integration/qq_runtime_trace_smoke.py
```

Results:

```text
16 passed
xinyu_qq_gateway_smoke: ok
QQ outbox smoke passed
XinYu QQ outbox route alias smoke passed
QQ runtime trace smoke passed
```

## Metabolism Route Extraction

Added:

- `XinYu-Core/examples/agent-apps/xinyu/xinyu_bridge_metabolism_routes.py`

Changed:

- `xinyu_core_bridge.py` keeps the historical `life_metabolism_ticket_*`
  methods as thin delegates.
- `smoke_run.py` quick py-compile now includes `xinyu_bridge_metabolism_routes.py`.

Rationale:

Metabolism tickets are an HTTP/Desktop route family. They need `xinyu_dir`,
`self_choice_store`, `_desktop_publish_event(...)`, and
`_wake_metabolism_runner()`, but not ownership of the main turn loop.

Validation passed:

```powershell
.\.venv\Scripts\python.exe -B -m py_compile xinyu_bridge_metabolism_routes.py xinyu_core_bridge.py xinyu_bridge_http.py smoke_run.py
.\.venv\Scripts\python.exe tests/smoke/life/metabolism_bridge_smoke.py
.\.venv\Scripts\python.exe tests/smoke/life/metabolism_http_smoke.py
```

Results:

```text
Metabolism bridge smoke passed
Metabolism HTTP smoke passed
```

## Utility Route Extraction

Added:

- `XinYu-Core/examples/agent-apps/xinyu/xinyu_bridge_utility_routes.py`
- `XinYu-Core/examples/agent-apps/xinyu/tests/test_bridge_utility_routes.py`

Changed:

- `xinyu_core_bridge.py` keeps these historical method names as delegates:
  - `probe`
  - `review_inbox_command`
  - `message_ack`
  - `goldmark_mark_request`
- `smoke_run.py` quick py-compile now includes `xinyu_bridge_utility_routes.py`.

Rationale:

These methods are route wrappers for diagnostics, review inbox commands,
message ack registration, and Goldmark mark requests. They do not own the main
turn loop, memory recall, or persona behavior.

Validation passed:

```powershell
.\.venv\Scripts\python.exe -B -m py_compile xinyu_bridge_utility_routes.py xinyu_core_bridge.py xinyu_bridge_http.py smoke_run.py tests/test_bridge_utility_routes.py
.\.venv\Scripts\python.exe -B -m pytest -q tests/test_bridge_utility_routes.py tests/test_goldmark_mark.py tests/test_gateway_ack_spool.py
.\.venv\Scripts\python.exe tests/smoke/tools/xinyu_review_inbox_smoke.py
.\.venv\Scripts\python.exe tests/smoke/qq/qq_core_client_smoke.py
.\.venv\Scripts\python.exe tests/smoke/qq/xinyu_qq_config_smoke.py
.\.venv\Scripts\python.exe tests/smoke/bridge/bridge_errors_smoke.py
```

Results:

```text
14 passed
xinyu_review_inbox_smoke ok
QQ core client smoke passed
XinYu QQ config smoke passed
XinYu bridge errors smoke passed
```

## Diagnostics Move

Moved root-level operator diagnostics to:

```text
XinYu-Core/examples/agent-apps/xinyu/ops/diagnostics/
```

Files:

- `check_runtime_env.py`
- `check_sent_index.py`
- `mark_smoke_test.py`

Added:

- `ops/diagnostics/_diagnostic_paths.py`
- `ops/diagnostics/README.md`

Updated references:

- `INDEX.md`
- `VALIDATION-INDEX.md`
- `STRUCTURE-NOTES.md`
- `EXECUTION-ORDER.md`
- `CHANGELOG-XINYU.md`

Rationale:

These scripts are operator checks and inspection tools. They should stay
available, but they are not live runtime modules and should not crowd the app
root.

Validation passed:

```powershell
.\.venv\Scripts\python.exe -B -m py_compile ops/diagnostics/_diagnostic_paths.py ops/diagnostics/check_runtime_env.py ops/diagnostics/check_sent_index.py ops/diagnostics/mark_smoke_test.py
.\.venv\Scripts\python.exe ops/diagnostics/check_sent_index.py --help
.\.venv\Scripts\python.exe ops/diagnostics/mark_smoke_test.py --help
.\.venv\Scripts\python.exe ops/diagnostics/mark_smoke_test.py --json
.\.venv\Scripts\python.exe ops/diagnostics/check_sent_index.py nonexistent-adapter-id --json
```

## Probe Move

Moved longer operator-run probes to:

```text
XinYu-Core/examples/agent-apps/xinyu/ops/probes/
```

Files:

- `life_memory_visible_probe.py`
- `memory_lived_pressure_arc.py`
- `long_lived_session_harness.py`

Added:

- `ops/probes/_probe_paths.py`
- `ops/probes/README.md`

Updated references:

- `VALIDATION-INDEX.md`
- `IMPLEMENTATION-NEXT.md`
- `RUNTIME-VALIDATION-NOTES.md`
- `long_run_status.py`
- `STRUCTURE-NOTES.md`

Rationale:

These scripts are longer validation harnesses, including no-restore probes.
They stay available, but they should be visibly outside the live app root.

Validation passed:

```powershell
.\.venv\Scripts\python.exe -B -m py_compile ops/probes/_probe_paths.py ops/probes/life_memory_visible_probe.py ops/probes/memory_lived_pressure_arc.py ops/probes/long_lived_session_harness.py long_run_status.py
.\.venv\Scripts\python.exe ops/probes/life_memory_visible_probe.py --help
.\.venv\Scripts\python.exe ops/probes/memory_lived_pressure_arc.py --help
.\.venv\Scripts\python.exe ops/probes/long_lived_session_harness.py --help
```

The probes were not executed in this batch because they are long/no-restore
validation surfaces. Run them with `--restore-after` where supported unless the
goal is to inspect lived memory changes directly.

## Memory Reduction Contract

Added:

- `XinYu-Core/examples/agent-apps/xinyu/MEMORY-REDUCTION-RULES.md`

Changed:

- `INDEX.md`
- `STRUCTURE-NOTES.md`
- `VALIDATION-INDEX.md`

Rationale:

The biology/neuroscience review is useful only if it becomes an engineering
constraint. The new project contract turns it into seven rules: compact
indexes, goal-lane recall, gated stable writes, emotion as modulation, event
compression, active forgetting, and dream/replay non-factuality.

## Root Tool Moves

Moved additional root-level operator tools out of the app root:

- `dialogue_curiosity_review.py` -> `ops/diagnostics/dialogue_curiosity_review.py`
- `live_chat_regression_baseline.py` -> `ops/validation/live_chat_regression_baseline.py`

Added:

- `ops/validation/_validation_paths.py`
- `ops/validation/README.md`

Rationale:

These scripts are inspection or validation surfaces. They may read runtime
diagnostic outputs or call the local bridge, but they do not own live turn
behavior and should not crowd the root module namespace.

Validation passed:

```powershell
.\.venv\Scripts\python.exe -B -m py_compile ops/diagnostics/_diagnostic_paths.py ops/diagnostics/dialogue_curiosity_review.py ops/validation/_validation_paths.py ops/validation/live_chat_regression_baseline.py tests/test_dialogue_curiosity_review.py tests/test_live_chat_regression_baseline.py
.\.venv\Scripts\python.exe -B -m pytest -q tests/test_dialogue_curiosity_review.py tests/test_live_chat_regression_baseline.py
.\.venv\Scripts\python.exe ops/diagnostics/dialogue_curiosity_review.py --help
.\.venv\Scripts\python.exe ops/validation/live_chat_regression_baseline.py --help
```

Result:

```text
3 passed
```

Moved scaffold validators out of the app root:

- `validate_scaffold.py` -> `ops/validation/validate_scaffold.py`
- `validate_inner_framework.py` -> `ops/validation/validate_inner_framework.py`

Updated references in:

- `long_run_status.py`
- `custom/ai_self_iteration_review_engine.py`
- `INDEX.md`
- `VALIDATION-INDEX.md`
- `EXECUTION-ORDER.md`
- `IMPLEMENTATION-NEXT.md`
- `LONG-RUN-AUDIT.md`
- `CHANGELOG-XINYU.md`
- `ops/validation/README.md`

Validation passed:

```powershell
.\.venv\Scripts\python.exe -B -m py_compile ops/validation/_validation_paths.py ops/validation/validate_scaffold.py ops/validation/validate_inner_framework.py long_run_status.py custom/ai_self_iteration_review_engine.py
.\.venv\Scripts\python.exe ops/validation/validate_scaffold.py
.\.venv\Scripts\python.exe ops/validation/validate_inner_framework.py
.\.venv\Scripts\python.exe long_run_status.py --skip-deployment-gate
```

Moved runtime-injection diagnostic helper:

- `diagnose_runtime_injection.py` -> `ops/diagnostics/diagnose_runtime_injection.py`

Updated import users:

- `tests/smoke/voice/integration/persona_contract_absence_smoke.py`
- `tests/smoke/voice/integration/live_voice_card_smoke.py`
- `tests/smoke/voice/integration/persona_life_anchor_smoke.py`

Validation passed:

```powershell
.\.venv\Scripts\python.exe -B -m py_compile ops/diagnostics/diagnose_runtime_injection.py tests/smoke/voice/integration/persona_life_anchor_smoke.py tests/smoke/voice/integration/persona_contract_absence_smoke.py tests/smoke/voice/integration/live_voice_card_smoke.py
.\.venv\Scripts\python.exe ops/diagnostics/diagnose_runtime_injection.py --help
.\.venv\Scripts\python.exe tests/smoke/voice/integration/persona_contract_absence_smoke.py
.\.venv\Scripts\python.exe tests/smoke/voice/integration/live_voice_card_smoke.py
.\.venv\Scripts\python.exe tests/smoke/voice/integration/persona_life_anchor_smoke.py
```

Moved memory seed sync/check tool:

- `sync_memory_seeds.py` -> `ops/validation/sync_memory_seeds.py`

Updated:

- `tests/smoke/memory/seed_memory_packaging_smoke.py`
- `memory-seeds/README.md`
- `ops/validation/README.md`
- `INDEX.md`

Validation passed:

```powershell
.\.venv\Scripts\python.exe -B -m py_compile ops/validation/sync_memory_seeds.py tests/smoke/memory/seed_memory_packaging_smoke.py
.\.venv\Scripts\python.exe ops/validation/sync_memory_seeds.py
.\.venv\Scripts\python.exe tests/smoke/memory/seed_memory_packaging_smoke.py
```

Moved Goldmark dehydration CLI wrapper:

- `goldmark_dehydrate.py` -> `ops/manual/goldmark_dehydrate.py`

The live module `xinyu_goldmark_dehydrate.py` stayed in place.

Validation passed:

```powershell
.\.venv\Scripts\python.exe -B -m py_compile ops/manual/goldmark_dehydrate.py xinyu_goldmark_dehydrate.py tests/test_goldmark_dehydrate.py
.\.venv\Scripts\python.exe ops/manual/goldmark_dehydrate.py --help
.\.venv\Scripts\python.exe -B -m pytest -q tests/test_goldmark_dehydrate.py
```

Moved live-module diagnostic CLI:

- `xinyu_live_module_diagnostics.py` -> `ops/diagnostics/xinyu_live_module_diagnostics.py`

Updated:

- `README.md`
- `INDEX.md`
- `ops/diagnostics/README.md`

Validation passed:

```powershell
.\.venv\Scripts\python.exe -B -m py_compile ops/diagnostics/xinyu_live_module_diagnostics.py
.\.venv\Scripts\python.exe ops/diagnostics/xinyu_live_module_diagnostics.py --json
```

Moved AI-domain research dry-run probe:

- `xinyu_research_loop_dry_run.py` -> `ops/probes/xinyu_research_loop_dry_run.py`

Updated:

- `tests/smoke/learning/integration/research_loop_dry_run_smoke.py`
- `tests/smoke/initiative/competitive_benchmark_smoke.py`
- `ops/probes/README.md`
- `INDEX.md`

Validation passed:

```powershell
.\.venv\Scripts\python.exe -B -m py_compile ops/probes/xinyu_research_loop_dry_run.py tests/smoke/learning/integration/research_loop_dry_run_smoke.py tests/smoke/initiative/competitive_benchmark_smoke.py
.\.venv\Scripts\python.exe ops/probes/xinyu_research_loop_dry_run.py --help
.\.venv\Scripts\python.exe tests/smoke/learning/integration/research_loop_dry_run_smoke.py
.\.venv\Scripts\python.exe tests/smoke/initiative/competitive_benchmark_smoke.py
```

## Wide Validation

Passed after the route extractions, manifest archive, and memory contract
update:

```powershell
.\.venv\Scripts\python.exe smoke_run.py --group quick --restore-after --timeout-seconds 300
git diff --check
```

Results:

```text
smoke_run group=quick: ok
git diff --check: no whitespace errors; CRLF warnings only
```

Passed again after utility route extraction, QQ visible dispatch extraction,
and root tool moves:

```powershell
.\.venv\Scripts\python.exe smoke_run.py --group quick --restore-after --timeout-seconds 300
git diff --check
```

Results:

```text
smoke_run group=quick: ok
git diff --check: no whitespace errors; CRLF warnings only
```

Passed again after desktop proactive route extraction, proactive delivery route
extraction, async proactive outbox claim fix, and long-run status move:

```powershell
.\.venv\Scripts\python.exe smoke_run.py --group quick --restore-after --timeout-seconds 300
git diff --check
```

Results:

```text
smoke_run group=quick: ok
git diff --check: no whitespace errors; CRLF warnings only
```

Passed again after launch/store/service layer moves:

```powershell
.\.venv\Scripts\python.exe smoke_run.py --group quick --restore-after --timeout-seconds 300
git diff --check
```

Results:

```text
smoke_run group=quick: ok
git diff --check: no whitespace errors; CRLF warnings only
```

Passed again after moving `xinyu_chat_service.py` into `services/chat_service.py`:

```powershell
.\.venv\Scripts\python.exe smoke_run.py --group quick --restore-after --timeout-seconds 300
git diff --check
```

Results:

```text
smoke_run group=quick: ok
git diff --check: no whitespace errors; CRLF warnings only
```

## Archived Custom Manifests

Moved constant-only manifest files from `custom/` to:

```text
ops/archive/custom-manifests/2026-05-17/
```

Files:

- `maintenance_recommendation_manifest.py`
- `maintenance_dispatch_manifest.py`
- `question_pipeline_manifest.py`
- `reflection_output_manifest.py`
- `slow_reprocess_manifest.py`
- `source_gate_manifest.py`
- `memory_event_sourcing_manifest.py`

Rationale:

After the maintenance bridge collapse, these files no longer have live runtime,
config, startup, or test imports. They were archived instead of deleted because
they still document older path intent.

Reference scan:

```powershell
rg -n --glob '!runtime/**' --glob '!memory/**' --glob '!logs/**' --glob '!data/**' --glob '!ops/archive/**' "maintenance_recommendation_manifest|maintenance_dispatch_manifest|question_pipeline_manifest|reflection_output_manifest|slow_reprocess_manifest|source_gate_manifest|memory_event_sourcing_manifest" XinYu-Core/examples/agent-apps/xinyu
```

Result:

```text
no live references
```

Archived files still compile:

```powershell
$archiveFiles = Get-ChildItem -LiteralPath 'ops/archive/custom-manifests/2026-05-17' -Filter '*.py'
.\.venv\Scripts\python.exe -B -m py_compile @($archiveFiles.FullName)
```

## Desktop Proactive Route Extraction

Added:

- `xinyu_bridge_desktop_proactive_routes.py`

Thinned:

- `xinyu_core_bridge.py`

The runtime now delegates these desktop proactive route surfaces instead of
owning the full HTTP action flow inline:

- `desktop_proactive_inbox`
- `desktop_proactive_ack`
- `_record_desktop_initiative_feedback`
- `_desktop_finish_proactive_ack`
- `_desktop_approve_proactive_qq`
- `_desktop_update_proactive_request_state`

Compatibility preserved:

- `XinYuBridgeRuntime` keeps the same public/private method names.
- `XinYuBridgeRuntime._desktop_replace_frontmatter_field` and
  `XinYuBridgeRuntime._desktop_replace_list_field` remain direct aliases for
  older tests and hooks.
- `record_initiative_feedback` can still be monkeypatched through
  `xinyu_core_bridge` for existing focused tests.

Validation passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile xinyu_bridge_desktop_proactive_routes.py xinyu_core_bridge.py smoke_run.py
.\.venv\Scripts\python.exe tests\smoke\desktop\xinyu_desktop_proactive_smoke.py
.\.venv\Scripts\python.exe tests\smoke\desktop\xinyu_desktop_rest_smoke.py
.\.venv\Scripts\python.exe tests\smoke\bridge\bridge_desktop_state_text_smoke.py
.\.venv\Scripts\python.exe -m pytest -q tests\test_initiative_orchestrator.py::test_bridge_desktop_ack_records_initiative_feedback
```

## Proactive Delivery Route Extraction

Added:

- `xinyu_bridge_proactive_delivery_routes.py`

Thinned:

- `xinyu_core_bridge.py`

The runtime now delegates these route/helper surfaces:

- `proactive`
- `proactive_ack`
- `qq_outbox_claim`
- `qq_outbox_claim_fast`
- `qq_outbox_ack`
- `qq_outbox_ack_fast`
- `_claim_proactive_for_qq_outbox`
- `_claim_proactive_for_qq_outbox_sync`
- `_ready_proactive_outbox_candidate`
- `_proactive_candidate_already_handled`
- `_record_proactive_outbound_dialogue`

Behavioral fix included:

- Fixed the async proactive outbox claim path where `message` was assigned
  under an unreachable branch, causing `UnboundLocalError` when a ready
  proactive request was claimed via `qq_outbox_claim`.

Compatibility preserved:

- `XinYuBridgeRuntime` keeps the same public/private method names.
- The HTTP handler still calls runtime methods, not the new module directly.
- Desktop delivery events and proactive outbound dialogue recording remain
  owned through runtime methods.

Validation passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile xinyu_bridge_proactive_delivery_routes.py xinyu_bridge_desktop_proactive_routes.py xinyu_core_bridge.py smoke_run.py
.\.venv\Scripts\python.exe tests\smoke\initiative\proactive_presence_smoke.py
.\.venv\Scripts\python.exe tests\smoke\desktop\xinyu_desktop_proactive_smoke.py
.\.venv\Scripts\python.exe tests\smoke\desktop\xinyu_desktop_rest_smoke.py
.\.venv\Scripts\python.exe tests\smoke\qq\qq_outbox_route_alias_smoke.py
.\.venv\Scripts\python.exe tests\smoke\qq\qq_outbox_smoke.py
.\.venv\Scripts\python.exe -m pytest -q tests\test_gateway_ack_spool.py tests\test_bridge_utility_routes.py
```

## Long-Run Status Validation Move

Moved substantive CLI:

- `long_run_status.py` -> `ops/validation/long_run_status.py`

Left compatibility wrapper:

- `long_run_status.py`

Rationale:

`long_run_status.py` is an operator validation audit, not a live runtime
module. Keeping the root wrapper preserves existing commands and smoke tests
while removing the real implementation from the app root.

Updated:

- `INDEX.md`
- `VALIDATION-INDEX.md`
- `ops/validation/README.md`

Validation passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile long_run_status.py ops\validation\long_run_status.py
.\.venv\Scripts\python.exe long_run_status.py --skip-deployment-gate
.\.venv\Scripts\python.exe ops\validation\long_run_status.py --skip-deployment-gate
```

## Launch And Store Layer Moves

Moved substantive launcher:

- `run_local_xinyu.py` -> `ops/launch/run_local_xinyu.py`

Left compatibility wrapper:

- `run_local_xinyu.py`

Moved substantive persistence helper:

- `state_service.py` -> `stores/state_service.py`

Left compatibility wrapper:

- `state_service.py`

Moved substantive service helper:

- `xinyu_daily_digest.py` -> `services/daily_digest.py`
- `xinyu_chat_service.py` -> `services/chat_service.py`

Left compatibility wrapper:

- `xinyu_daily_digest.py`
- `xinyu_chat_service.py`

Added:

- `ops/launch/README.md`
- `stores/__init__.py`
- `stores/README.md`
- `services/__init__.py`
- `services/README.md`

Rationale:

The local launcher is operator entrypoint code, and state_service is store IO.
Daily digest is a runtime service helper. None of these should remain as
substantive root modules while the app root is being reduced. Thin wrappers
preserve existing script paths and imports.

Validation passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile run_local_xinyu.py ops\launch\run_local_xinyu.py
.\.venv\Scripts\python.exe run_local_xinyu.py --help
.\.venv\Scripts\python.exe ops\launch\run_local_xinyu.py --help
.\.venv\Scripts\python.exe ops\diagnostics\check_runtime_env.py
.\.venv\Scripts\python.exe -m py_compile state_service.py stores\state_service.py stores\__init__.py xinyu_core_bridge.py xinyu_qq_gateway.py xinyu_bridge_desktop_proactive_routes.py
.\.venv\Scripts\python.exe tests\smoke\runtime\state_io_smoke.py
.\.venv\Scripts\python.exe tests\smoke\dialogue\recent_attachment_context_smoke.py
.\.venv\Scripts\python.exe -m py_compile xinyu_daily_digest.py services\daily_digest.py services\__init__.py xinyu_core_bridge.py xinyu_bridge_turn_sidecars.py smoke_run.py
.\.venv\Scripts\python.exe tests\smoke\tools\xinyu_daily_digest_smoke.py
.\.venv\Scripts\python.exe -m py_compile xinyu_chat_service.py services\chat_service.py xinyu_core_bridge.py smoke_run.py
.\.venv\Scripts\python.exe tests\smoke\runtime\service_boundary_smoke.py
.\.venv\Scripts\python.exe tests\smoke\initiative\chat_service_smoke.py
```

## Next

- Seven-goal closeout artifacts were added in
  `worklog/xinyu-subtractive-seven-goal-closeout-2026-05-17.md`.
- Continue future thinning only in route-sized batches:
  `xinyu_core_bridge.py`, `xinyu_qq_gateway.py`, and remaining
  `custom/*_bridge_plugin.py` pairs.
- Do not move `memory/knowledge`, `data/external`, or
  `data/conversation_experience` until loader aliases and tests are in place.
