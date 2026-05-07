# XinYu Protective Snapshot - 2026-05-07

This folder records a non-invasive protection snapshot for the local XinYu workspace.

## Contents

- `SOURCE-MANIFEST-20260507.json`: SHA256 manifest for files visible through the protective Git ignore policy.
- `xinyu-status-redacted.json`: redacted live status report from `xinyu_status.py --json`.

## Intent

This snapshot does not refactor or rewrite XinYu. It preserves the current architecture, source inventory, and live system status before any future structural work.

The manifest intentionally excludes local secrets, virtual environments, NapCat binaries, node dependencies, private memory/runtime/log state, owner-supplied learning materials, and personal local scope data.

## Live Chain At Snapshot Time

```text
XinYu Desktop -> Core Bridge 127.0.0.1:8765
QQ / NapCat -> QQ Gateway 127.0.0.1:6199 -> Core Bridge 127.0.0.1:8765
Core Bridge -> xinyu_runtime / custom engines / v1 shadow-canary / LLM
```

## Notes

- This is a local provenance and continuity artifact, not a public release package.
- Private runtime data remains ignored by Git and should not be published.
