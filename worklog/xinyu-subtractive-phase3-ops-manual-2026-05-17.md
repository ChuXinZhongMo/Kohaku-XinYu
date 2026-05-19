# XinYu Subtractive Phase 3 - Ops Manual Move - 2026-05-17

Status: complete.

## Scope

This batch reduced root-level app clutter without changing the live turn path.

Moved operator-only manual scripts from:

```text
XinYu-Core/examples/agent-apps/xinyu/manual_*.py
```

to:

```text
XinYu-Core/examples/agent-apps/xinyu/ops/manual/
```

## Moved Files

- `manual_archive_commit.py`
- `manual_archive_output.py`
- `manual_automation_bridge.py`
- `manual_consolidation.py`
- `manual_inner_cycle.py`
- `manual_inner_sync.py`
- `manual_maintenance_recommendation.py`
- `manual_question_pipeline.py`
- `manual_reflection_output.py`
- `manual_retention_gate.py`
- `manual_slow_reprocess.py`
- `manual_source_gate.py`
- `manual_source_integration_gate.py`
- `manual_source_reliability.py`

Added:

- `ops/manual/_manual_paths.py`
- `ops/manual/README.md`

## Rationale

The scripts are operator entry points, not live runtime plugins. Keeping them
under `ops/manual/` matches the subtractive target structure and makes the app
root easier to scan.

## Behavior

- Live startup, config plugin loading, QQ gateway, desktop gateway, and the core
  bridge do not import these files.
- `manual_inner_cycle.py` now calls sibling scripts in `ops/manual/`.
- The manual scripts share `_manual_paths.py` for app root, core src, and custom
  module path setup.

## Validation

Passed:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
$files = @('ops/manual/_manual_paths.py') + (Get-ChildItem -LiteralPath 'ops/manual' -Filter 'manual_*.py' | ForEach-Object { $_.FullName })
.\.venv\Scripts\python.exe -B -m py_compile @files
```

Passed:

```powershell
foreach ($file in Get-ChildItem -LiteralPath 'ops/manual' -Filter 'manual_*.py') {
  .\.venv\Scripts\python.exe -B $file.FullName --help
}
```

Result:

```text
manual help ok
```

Reference scan:

```powershell
rg -n "manual_.*\.py|ops/manual|ops\\manual" XinYu-Core\examples\agent-apps\xinyu -g "!memory/**" -g "!runtime/**" -g "!logs/**" -g "!.venv/**" -g "!__pycache__/**"
```

Remaining references are documentation and sibling calls inside
`ops/manual/manual_inner_cycle.py`.

## Next

Proceed to low-risk bridge thinning:

- extract core bridge external plugin routes
- then extract QQ gateway context enrichment or visible send wrappers
