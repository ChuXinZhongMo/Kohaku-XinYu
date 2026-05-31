# XinYu Perception Event Layer

- generated_at: 2026-05-28T23:22:59+08:00
- status: pass
- result: pass
- claim_boundary: normalized input/event evidence only; does not claim consciousness

## Metrics
- event_count: 11
- source_count: 8
- event_type_count: 8
- input_event_count: 1
- qq_event_count: 4
- desktop_event_count: 1
- tool_result_event_count: 3
- system_health_event_count: 1
- file_change_event_count: 1
- visual_event_count: 0
- voice_event_count: 0
- importance_ready_count: 11
- anomaly_count: 1
- privacy_scope_count: 3
- latest_event_type: file_change
- latest_event_source: code_probe
- latest_event_ref: sha256:e58a463308f6884e

## Recent Events
### percevt-bf6d7baab93d2b0d
- event_type: tool_execution_result
- source: codex
- observed_at: 2026-05-21T20:37:25+08:00
- confidence: medium
- privacy_scope: runtime
- importance: normal
- anomaly: False
- summary: codex feedback=codex_delegate_finished result=succeeded status=observed
- evidence_ref: sha256:4cce5284d303ebac
### percevt-350fe75d25d2fd7c
- event_type: desktop_ack
- source: desktop
- observed_at: 2026-05-24T01:15:00+08:00
- confidence: medium
- privacy_scope: owner_private
- importance: normal
- anomaly: False
- summary: desktop request state status=dry_run answer=not_requested ack=dry_run
- evidence_ref: sha256:ff0487ac88b3dd18
### percevt-3aebc78ca4f61f3b
- event_type: qq_drop
- source: qq_gateway
- observed_at: 2026-05-28T17:14:22.562978+08:00
- confidence: high
- privacy_scope: owner_private
- importance: high
- anomaly: True
- summary: stale visible reply dropped reason=newer_input_before_visible_send:468->469
- evidence_ref: sha256:a4585c8c36f48b76
### percevt-14686809b8bb45e5
- event_type: owner_text_input
- source: qq
- observed_at: 2026-05-28T22:30:22.650026+08:00
- confidence: high
- privacy_scope: owner_private
- importance: high
- anomaly: False
- summary: owner private input observed stage=coalesced_wait text_len=4
- evidence_ref: sha256:6b0ccc3619b3ed79
### percevt-17f9c158820676f7
- event_type: qq_ack
- source: qq_gateway
- observed_at: 2026-05-28T22:30:39+08:00
- confidence: high
- privacy_scope: owner_private
- importance: normal
- anomaly: False
- summary: QQ ack observed route=chat
- evidence_ref: sha256:bcc6ecd3c782790e
### percevt-9452331996e2679c
- event_type: qq_ack
- source: qq
- observed_at: 2026-05-28T22:30:39+08:00
- confidence: medium
- privacy_scope: owner_private
- importance: normal
- anomaly: False
- summary: qq feedback=qq_visible_reply_ack result=delivered status=observed
- evidence_ref: actfb-e76a04518ee381cc
### percevt-ba6de00fa205f656
- event_type: system_health_change
- source: runtime_probe
- observed_at: 2026-05-28T22:30:39+08:00
- confidence: medium
- privacy_scope: runtime
- importance: normal
- anomaly: False
- summary: runtime_probe feedback=runtime_probe_ok result=running status=observed
- evidence_ref: sha256:d7cfb7a77c53c857
### percevt-11068e58695842c1
- event_type: tool_execution_result
- source: local_tool
- observed_at: 2026-05-28T23:09:48+08:00
- confidence: medium
- privacy_scope: runtime
- importance: normal
- anomaly: False
- summary: local_tool feedback=local_tool_probe_succeeded result=success status=observed
- evidence_ref: sha256:6155d6feec5e0b36
### percevt-5d64a6c0b154f847
- event_type: tool_execution_result
- source: patch_executor
- observed_at: 2026-05-28T23:09:48+08:00
- confidence: medium
- privacy_scope: runtime
- importance: normal
- anomaly: False
- summary: patch_executor feedback=patch_task_prepared result=prepared status=observed
- evidence_ref: sha256:a130da406f801f10
### percevt-3d4bf82ce10a181b
- event_type: qq_group_boundary
- source: qq_gateway
- observed_at: 2026-05-28T23:21:57.979543+08:00
- confidence: high
- privacy_scope: group
- importance: boundary
- anomaly: False
- summary: group event bounded reason=group_not_allowed
- evidence_ref: sha256:7ebaa96bfca8d0ba
### percevt-308f5722b64e9e6e
- event_type: file_change
- source: code_probe
- observed_at: 2026-05-28T23:22:59+08:00
- confidence: medium
- privacy_scope: runtime
- importance: normal
- anomaly: False
- summary: code_probe feedback=code_probe_source_changed result=source_changed status=observed
- evidence_ref: sha256:e58a463308f6884e

## Privacy Boundary
- raw_private_body_retained: false
- visible_reply_text_retained: false
- private_text_in_report: false
- stable_memory_write: blocked

## Notes
- tool_result_events_unified
- system_health_events_unified
- file_change_events_unified
- visual_events_not_connected_yet
- voice_events_not_connected_yet
- anomaly_events_ready_for_importance_judgement
- perception_events_have_source_time_privacy_confidence_and_refs
