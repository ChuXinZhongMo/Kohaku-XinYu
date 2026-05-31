# XinYu System Spine

XinYu is treated as one local system with several bounded components, not as
unrelated projects.

## Required Goal Anchor

Read `docs/system/心玉最终目标.md` before changing project direction,
autonomy behavior, memory behavior, proactive behavior, or self-action behavior.
It defines the final Chinese goal: a bounded, verifiable self-generating
autonomy loop, not performative personality text or unbounded automation.

For the long-term implementation breakdown, see
`docs/system/心玉自我生成长期路线大纲.md`.

When referencing external projects, use the "外部项目借鉴准则" section in that
roadmap first. Borrow design lessons only after mapping them to a roadmap stage,
their autonomy-loop contribution, and a XinYu-native reimplementation path.
Do not copy license-restricted code into XinYu without an explicit license review.
Record every external project reference in
`docs/system/外部项目借鉴登记.md` so attribution, license notes, and adopted
ideas stay visible.

## Operator Surface

Use the root controller:

```powershell
.\XinYu.ps1 tree
.\XinYu.ps1 status
.\XinYu.ps1 start desktop
.\XinYu.ps1 stop all
.\XinYu.ps1 test core
.\XinYu.ps1 clean
```

The older launch scripts live under `scripts/` as implementation details. The
root should stay focused on `XinYu.ps1` and top-level system areas.

## Component Boundaries

- `XinYu-Core/` owns the reusable Python runtime and the active app host.
- `XinYu-Core/examples/agent-apps/xinyu/` is the active XinYu app surface:
  bridge, QQ gateway, memory/runtime boundary, tests, and local operations.
- `XinYu_Desktop/` owns the Electron desktop shell.
- `XinYu-TinyKernel/` owns the local TinyKernel service and experiments.
- `XinYu-Local-Scope/` owns local request/material staging.
- `XinYu-Autonomy/` owns owner-visible autonomy notes.
- `scripts/` owns startup, shutdown, and local operator helpers.
- `assets/` owns cases, reference library, icons, OCR fixtures, and owner-facing
  material libraries.
- `artifacts/` owns generated archives and protection snapshots.
- `runtime/deps/NapCatQQ/`, `runtime/deps/Python312/`,
  `runtime/deps/ocr-venv/`, and `runtime/deps/vision-venv/` are local runtime
  dependencies, not XinYu source modules.

Compatibility path fallbacks may still exist in launchers while old local
setups are migrated, but new resolution should prefer `runtime/deps`.

## Consolidation Rule

Do not merge live state into source. Consolidation means:

1. One operator entry point.
2. One documented system map.
3. Source, runtime state, dependencies, assets, and reports kept in separate
   bounded locations.
4. Compatibility paths preserved until callers are migrated.
