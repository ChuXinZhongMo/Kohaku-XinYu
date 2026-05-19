# XinYu Delete Archive Reference Audit - 2026-05-17

Status: evidence batch applied; no broad deletion was expanded.

## Batch Scope

- Capability group: ops/delete/archive evidence.
- Goal: prove the large pre-existing deleted root wrappers have migrated or
  archived counterparts, and fix any live stale references to old root script
  names.

## Scout Evidence

Current deleted Python files under `XinYu-Core/examples/agent-apps/xinyu`:

```text
root_smoke: 212
diagnostic_validation: 9
manual_ops: 15
probe: 4
custom_manifest: 7
total: 247
```

Counterpart scan:

```text
counterpart_present=247
counterpart_missing=0
```

Representative mappings:

```text
ai_domain_source_smoke.py -> tests/smoke/learning/integration/ai_domain_source_smoke.py
check_runtime_env.py -> ops/diagnostics/check_runtime_env.py
custom/maintenance_dispatch_manifest.py -> ops/archive/custom-manifests/2026-05-17/maintenance_dispatch_manifest.py
goldmark_dehydrate.py -> ops/manual/goldmark_dehydrate.py
life_memory_visible_probe.py -> ops/probes/life_memory_visible_probe.py
```

Reference scan:

```text
Total code/config hits outside tests/smoke/runtime/logs: 143
Potential live non-doc/non-ops hits before fix: 3
Potential live non-doc/non-ops hits after fix: 0
```

The remaining 143 name hits are migrated paths, docs/plans/status records, or
ops references, not old root script execution references.

## Applied Changes

- Updated `xinyu_voice_promotion_gate.py` so `AFFECTED_SMOKES` points at
  migrated smoke paths:
  - `tests/smoke/voice/voice_learning_smoke.py`
  - `tests/smoke/voice/chinese_voice_guard_smoke.py`
  - `tests/smoke/voice/integration/real_conversation_quality_smoke.py`
- Updated `tests/smoke/voice/voice_calibration_promotion_smoke.py` to assert
  the new migrated smoke paths.

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile xinyu_voice_promotion_gate.py tests\smoke\voice\voice_calibration_promotion_smoke.py
.\.venv\Scripts\python.exe tests\smoke\voice\voice_calibration_promotion_smoke.py
git diff --check -- XinYu-Core/examples/agent-apps/xinyu/xinyu_voice_promotion_gate.py XinYu-Core/examples/agent-apps/xinyu/tests/smoke/voice/voice_calibration_promotion_smoke.py
```

Results:

- Voice calibration promotion smoke: passed.
- Diff check: whitespace clean; only CRLF normalization warning for
  `xinyu_voice_promotion_gate.py`.

## Not Changed

- No additional root wrappers were deleted in this batch.
- No runtime state, raw QQ logs, private memory bodies, or secrets were printed.
- No git commit was made.

## Remaining

- The worktree still records the 247 root deletions until the owner eventually
  asks for a commit.
- Some docs still mention old root filenames as historical records; these are
  not live execution paths.
- A final closeout audit still needs a compact kept/merged/archived/deleted
  table.

## Next Batch

Refresh module classification with the new recall-adjacent roles and delete
audit evidence, then continue to storage boundary cleanup or final audit gaps.
