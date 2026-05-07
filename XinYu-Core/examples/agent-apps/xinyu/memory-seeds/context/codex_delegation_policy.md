---
title: Codex Delegation Policy
memory_type: codex_delegation_policy
time_scope: long_term
subject_ids: [xinyu, owner]
protected: true
source: core_bridge
created_at: 2026-04-28T00:00:00+08:00
updated_at: 2026-04-30T00:00:00+08:00
last_confirmed_at: 2026-04-30T00:00:00+08:00
importance_score: 92
impact_score: 94
confidence_score: 90
status: active
tags: [codex, delegation, owner, local_scope, safety]
---

# Codex Delegation Policy

## Reality Status
- direct_qq_to_codex_execution: blocked_no_raw_cli_from_gateway
- explicit_qq_codex_command: owner_private_only_via_gateway_to_core_bridge
- automatic_codex_process_launch: disabled_for_ordinary_chat
- model_hidden_codex_delegate: owner_private_only_via_core_bridge_marker
- completion_return_path: core_qq_outbox_claim_ack_via_gateway
- queue_watcher: not_implemented
- implemented_path: owner private `/codex <task>` or explicit local/API request or hidden model handoff -> core `/codex/execute` -> background `codex exec`

## Execution Boundary
- owner_only: yes
- bridge_token_required_for_codex_execute: yes
- gateway_direct_subprocess: blocked
- completion_summary_visibility: owner_private_summary_no_raw_stdout_stderr_no_full_local_path
- local_scope_required: yes
- full_auto_scope: bounded by the explicit Codex delegate workspace and approved local scope paths
- timeout_policy: Codex execution is bounded by core timeout settings.
- Timeout is not treated as closing the task; timed-out jobs are handed to dream/reflection queues for later review.

## Safety Notes
- Codex requests are accepted only through owner-private `/codex <task>`, explicit local/API delegation, or the bridge-hidden model handoff marker when the owner clearly asks for local operation, project work, URL learning, or explicit Codex delegation.
- XinYu must not claim Codex requires manual `/codex` when the owner has already asked her in private chat to use Codex; the model should use the hidden handoff marker and let the bridge send the visible status.
- Codex delegation is semantic, not keyword-based: mentions of Codex, corrections about a previous launch, negations, route-failure reports, or statements about what the owner may do later are ordinary chat unless the current turn clearly delegates a concrete task.
- Ordinary chat, question-only wording, and negative instructions such as "do not use Codex" must not launch a process.
- Reports go to the local scope Outbox; visible replies and completion callbacks should summarize status without leaking raw local paths, raw stdout/stderr, secrets, or private identifiers.
