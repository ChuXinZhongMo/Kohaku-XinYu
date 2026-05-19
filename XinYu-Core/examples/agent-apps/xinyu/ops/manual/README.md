# Manual Operations

This folder holds operator-only maintenance entry points that used to live in
the app root as `manual_*.py`.

These scripts are not part of the live turn path. Run them from the app root
with an explicit path, for example:

```powershell
.\.venv\Scripts\python.exe ops\manual\manual_inner_sync.py --help
```

`goldmark_dehydrate.py` also lives here because it is an operator maintenance
entry point around the live `xinyu_goldmark_dehydrate.py` module.

Do not use these scripts as automatic runtime plugins. The live maintenance
path is owned by `custom/*_bridge_plugin.py` and `smoke_run.py`.

## Registered Manual Entrances

These files are intentionally kept even when they have no runtime imports. They
are operator-only escape hatches for controlled local maintenance:

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
- `goldmark_dehydrate.py`

Keep policy:

- Manual runners stay under `ops/manual/`.
- They must be run explicitly by path.
- They must not be auto-loaded as bridge plugins.
- If a runner gains routine use, add a focused pytest or grouped smoke entry.
- If the matching engine/plugin is removed, archive the runner in the same
  batch.
