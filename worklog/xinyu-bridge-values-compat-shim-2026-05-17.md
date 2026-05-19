# XinYu Bridge Values Compatibility Shim - 2026-05-17

Status: applied as one compatibility-shim batch.

## Batch Scope

- Capability group: bridge compatibility helpers.
- Goal: restore the old `_optional_int` compatibility import expected by the
  bridge values smoke while keeping `xinyu_bridge_values.py` as the canonical
  helper owner.

## Completed

- Updated `xinyu_core_bridge.py`.
  - Added `from xinyu_bridge_values import optional_int as _optional_int`.
  - No bridge behavior or payload shape was changed.

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile xinyu_core_bridge.py xinyu_bridge_values.py
.\.venv\Scripts\python.exe tests\smoke\bridge\bridge_values_smoke.py
```

Results:

- Bridge values smoke: passed.

## DoD Impact

- A known compatibility smoke failure is removed.
- `xinyu_bridge_values.py` remains the canonical helper module.
- `xinyu_core_bridge.py` keeps legacy `_...` helper names as shims for existing
  callers and smokes.

## Remaining

- Run full validation set:
  - full pytest
  - quick smoke
  - required desktop typecheck/build
- Write final kept / merged / archived / deleted / remaining risks audit.

## Next Batch

Run the final validation gate and write the final reduction audit if the gate is
green.
