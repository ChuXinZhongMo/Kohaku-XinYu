# XinYu Trace Schema

This document lists the public-safe trace fields used by the current operator and research artifacts. Trace examples must not contain raw private chat text, full QQ IDs, tokens, or local paths.

## Turn Route Trace

Path:

```text
runtime/turn_route_trace.jsonl
```

Fields:

- `observed_at`: local ISO timestamp.
- `turn_id`: generated turn id; safe to share only if no external id is embedded.
- `stage`: route stage such as `turn_started`, `pre_model_routes_started`, `route_decided`, `model_inject_timeout`, `route_finished`, or `intervention_applied`.
- `route`: `undecided`, `semantic_fast`, `slow_live`, `owner_intervention`, or another bounded route label.
- `status`: `running`, `ok`, `accepted`, `timeout`, `error`, `applied`, or `rejected`.
- `elapsed_ms`: optional elapsed milliseconds.
- `notes`: short sanitized machine notes.
- `source`, `message_type`, `session_hash`, `user_hash`, `group_hash`: scoped payload metadata, hashed where needed.

## Proactive Lifecycle Trace

Path:

```text
runtime/proactive_request_trace.jsonl
```

Fields:

- `event_kind`: `proactive_request_evaluated`, `proactive_candidate_previewed`, `proactive_candidate_claimed`, `proactive_claim_blocked`, `proactive_ack_recorded`, `proactive_ack_rejected`, or `proactive_owner_reply_closed`.
- `event_time`: local ISO timestamp.
- `request_id`: generated proactive request id.
- `status`: current request status.
- `kind`, `source`, `focus_kind`: coarse source labels.
- `reason`, `urgency`, `risk`, `owner_relevance`, `channel`, `expiration`: candidate audit fields.
- `delivery_level`: `state_only`, `preview_only`, `queue_owner_private`, or `claim_ack`.
- `claim_id`, `claim_status`, `ack_status`, `adapter_status`: dispatch lifecycle state.
- `candidate_hash`: hash of the candidate text, never the text itself.
- `notes`: short sanitized machine notes.

## Runtime Presence Trace

Path:

```text
runtime/self_presence_trace.jsonl
```

Fields are coarse process and turn continuity facts: event kind, observed time, bridge process, active sessions, turn status, Codex status, and sanitized notes.

## Public Sharing Rules

- Prefer scenario-generated traces under `failure-scenarios/examples/`.
- Replace local paths with `<local_path>` or `<xinyu_dir>`.
- Replace full account IDs with hashes or counts.
- Do not include raw `memory/` files in public reports.
