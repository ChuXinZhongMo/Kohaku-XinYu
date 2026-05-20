# Failure Scenarios

These files define sanitized, account-free regression scenarios for XinYu runtime failures.

Each scenario is a JSON file under `failure-scenarios/scenarios/` with this schema:

- `id`: stable scenario id.
- `title`: short human-readable name.
- `input_payload`: sanitized bridge payload. Do not use real QQ ids or raw private chat.
- `expected_trace_stages`: ordered route trace stages that must appear.
- `expected_health_state`: expected `/health` or operator state fields.
- `expected_visible_behavior`: accepted/reply/status expectations safe to show.
- `expected_memory_impact`: whether runtime, temporary, candidate, or approved memory may change.
- `recovery_action`: owner or runtime action that should recover or explain the failure.
- `privacy_notes`: why this scenario is safe to share.

The first runner validates schema and privacy invariants. Runtime replay can be added without changing the scenario files.
