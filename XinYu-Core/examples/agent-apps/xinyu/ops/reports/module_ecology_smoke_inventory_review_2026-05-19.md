# XinYu Smoke Inventory Review - 2026-05-19

Scope: review the stale smoke candidates from
`ops/reports/module_ecology_archive_candidates_2026-05-19.md`.

Privacy note: this review uses smoke file paths and `smoke_run.py` manifests
only. It does not read or print memory, runtime, QQ payload, library, cases, or
data bodies.

## Summary

- stale smoke candidates: 53
- covered by `smoke_run.SMOKE_GROUPS`: 0
- uncovered by grouped smoke manifests: 53
- archive-ready now: 0

## Family Counts

- bridge: 23
- codex: 1
- desktop: 2
- dialogue: 1
- initiative: 5
- life: 1
- qq: 16
- qq/integration: 1
- runtime: 1
- voice: 2

## Status Vocabulary

- `covered_by_smoke_run`: listed in the canonical grouped smoke manifest.
- `manual_only_or_archive_review`: not listed in `SMOKE_GROUPS`; keep as a
  manual diagnostic until replaced by grouped smoke or pytest evidence.
- `archive_ready`: safe to archive after a direct replacement is identified.

## Decision

All 53 candidates are currently `manual_only_or_archive_review`.

Reason: none are listed in the canonical `SMOKE_GROUPS` manifest, but absence
from the grouped manifest is not enough evidence to delete a diagnostic script.
The next cleanup step should either move important scripts into a named smoke
group, convert their assertions into pytest coverage, or archive them with a
replacement note.

## Items

| Path | Family | Status | Evidence |
| --- | --- | --- | --- |
| `tests/smoke/bridge/bridge_bootstrap_smoke.py` | bridge | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/bridge/bridge_cli_smoke.py` | bridge | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/bridge/bridge_codex_aliases_smoke.py` | bridge | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/bridge/bridge_context_smoke.py` | bridge | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/bridge/bridge_debug_prompt_dump_smoke.py` | bridge | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/bridge/bridge_desktop_actions_smoke.py` | bridge | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/bridge/bridge_desktop_projection_smoke.py` | bridge | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/bridge/bridge_desktop_service_aliases_smoke.py` | bridge | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/bridge/bridge_desktop_state_text_smoke.py` | bridge | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/bridge/bridge_errors_smoke.py` | bridge | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/bridge/bridge_learning_sidecars_smoke.py` | bridge | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/bridge/bridge_loop_thread_smoke.py` | bridge | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/bridge/bridge_memory_snapshot_smoke.py` | bridge | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/bridge/bridge_null_input_smoke.py` | bridge | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/bridge/bridge_payload_attachment_smoke.py` | bridge | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/bridge/bridge_payload_policy_smoke.py` | bridge | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/bridge/bridge_promises_smoke.py` | bridge | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/bridge/bridge_recent_sticker_reply_smoke.py` | bridge | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/bridge/bridge_reply_bubbles_smoke.py` | bridge | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/bridge/bridge_reply_text_smoke.py` | bridge | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/bridge/bridge_session_smoke.py` | bridge | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/bridge/bridge_state_text_smoke.py` | bridge | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/bridge/bridge_trusted_search_smoke.py` | bridge | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/codex/xinyu_tool_artifact_hygiene_smoke.py` | codex | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/desktop/xinyu_desktop_events_smoke.py` | desktop | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/desktop/xinyu_desktop_ws_smoke.py` | desktop | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/dialogue/group_shadow_state_smoke.py` | dialogue | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/initiative/automation_bridge_live_turn_smoke.py` | initiative | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/initiative/autonomous_state_smoke.py` | initiative | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/initiative/impulse_soup_smoke.py` | initiative | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/initiative/proactivity_scorer_smoke.py` | initiative | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/initiative/xinyu_tinykernel_shadow_smoke.py` | initiative | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/life/dream_journal_export_smoke.py` | life | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/qq/integration/qq_recent_sticker_state_smoke.py` | qq/integration | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/qq/qq_attachment_material_smoke.py` | qq | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/qq/qq_cli_smoke.py` | qq | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/qq/qq_config_helpers_smoke.py` | qq | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/qq/qq_core_client_smoke.py` | qq | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/qq/qq_forward_context_smoke.py` | qq | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/qq/qq_gateway_constants_smoke.py` | qq | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/qq/qq_gateway_utils_smoke.py` | qq | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/qq/qq_models_smoke.py` | qq | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/qq/qq_normalizer_aliases_smoke.py` | qq | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/qq/qq_rich_context_smoke.py` | qq | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/qq/qq_sticker_semantics_smoke.py` | qq | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/qq/qq_trust_aliases_smoke.py` | qq | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/qq/qq_trust_config_persistence_smoke.py` | qq | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/qq/qq_trust_policy_smoke.py` | qq | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/qq/xinyu_qq_config_smoke.py` | qq | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/qq/xinyu_qq_server_smoke.py` | qq | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/runtime/runtime_failure_freshness_smoke.py` | runtime | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/voice/xinyu_visible_state_hygiene_smoke.py` | voice | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |
| `tests/smoke/voice/xinyu_visible_text_sanitizer_smoke.py` | voice | manual_only_or_archive_review | not listed in `SMOKE_GROUPS`; keep as manual diagnostic until replaced by grouped smoke or pytest evidence |

## Direct Effect

- Prevents accidental deletion of uncovered diagnostic smoke scripts.
- Narrows the next cleanup batch to a concrete decision:
  choose which manual smokes become grouped smoke, which become pytest tests,
  and which can be archived with replacement notes.
- Leaves runtime behavior unchanged.

## Next Batch

Review plan candidates separately:

- stale `project-plans/*.md`: extract active plan index, then archive old plans
  with a manifest.
- `learning/self_found` snapshots: archive by snapshot folder after confirming
  no active source-material references.
- `learning/owner_supplied`: hold until owner-supplied material boundary is
  explicit.
