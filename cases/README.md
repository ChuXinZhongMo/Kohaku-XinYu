# XinYu Cases

Reviewed dialogue and behavior cases belong here eventually.

Current live code still reads case data from:

- `XinYu-Core/examples/agent-apps/xinyu/data/conversation_experience/`
- `XinYu-Core/examples/agent-apps/xinyu/tests/fixtures/`

Compatibility loaders now resolve workspace-level `cases/conversation/` first,
then fall back to the legacy live path. Do not hard-delete the legacy path until
imports, tests, and fixture loaders no longer reference it.

Rules:

- Cases are advisory behavior hints, not stable memory.
- Owner-private cases must stay private and redacted when used in tests.
- Public dataset cases must not mutate owner-private relationship memory.
