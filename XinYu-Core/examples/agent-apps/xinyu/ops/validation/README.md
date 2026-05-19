# Validation

Operator-run validation harnesses live here. They may call the local bridge or
write test reports, but they are not part of the live turn path.

- `live_chat_regression_baseline.py` runs local bridge chat cases and writes regression summaries under runtime output.
- `long_run_status.py` audits milestone status, required docs/scripts, selected gate states, and known smoke residue markers. The app-root `long_run_status.py` is only a compatibility wrapper.
- `sync_memory_seeds.py` checks portable seed memory and can apply it to local ignored memory when explicitly requested.
- `boundary_readiness_audit.py` aggregates memory/store/queue/event/trace/orphan boundary validators and source-reference audits into one metadata-only readiness report.
- `commit_readiness_audit.py` aggregates change packages, boundary readiness, and archive/delete decisions into one metadata-only commit-readiness report.
- `validate_memory_library_manifest.py` validates the redacted memory/library/case/data boundary manifest without reading file contents.
- `validate_scaffold.py` validates config, prompt, plugin, and required memory scaffold paths.
- `validate_inner_framework.py` validates the deterministic inner-framework manifest.
