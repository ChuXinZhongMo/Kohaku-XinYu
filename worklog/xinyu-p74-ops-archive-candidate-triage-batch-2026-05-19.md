# XinYu P74 Ops Archive Candidate Triage Batch - 2026-05-19

## Scope

Batch: ops archive candidate triage after P73.

Goal: classify the 19 ops archive candidates before any doc/tool move.

## Completed

- Added ops triage report:
  - `ops/reports/module_ecology_ops_archive_triage_2026-05-19.md`
- Classified all 19 ops candidates into:
  - `keep_doc`
  - `archive_doc`
  - `merge_into_index`

## Triage Summary

- ops_candidates: 19
- keep_doc: 8
- archive_doc: 6
- merge_into_index: 5

Direct effect:

- Manual operator wrappers are not blindly archived just because they have no
  source references.
- Generated/legacy docs now have an explicit archive/merge action.
- No files were moved or deleted.

## Validation

- Classification row count:
  - 19
- `.\.venv\Scripts\python.exe -m pytest tests\test_module_ecology_audit.py -q`
  - 16 passed
- `git diff --check -- ops/reports/module_ecology_ops_archive_triage_2026-05-19.md`
  - pass

Inherited latest full validation from P73:

- `.\.venv\Scripts\python.exe -m pytest tests -q`
  - 661 passed
- `.\.venv\Scripts\python.exe smoke_run.py --group quick --timeout-seconds 180 --json`
  - ok=true

## Remaining

- 182 lab archive candidates remain untriaged.
- The 6 core `archive_ready` candidates and 6 ops `archive_doc` candidates are
  still classifications only; no file movement has happened.
- The 5 ops `merge_into_index` candidates need summary extraction before any
  archive move.

## Recovery Point

Start from:

`D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`

Highest-value next batch:

Triage lab archive candidates by source family, not one by one:

- learning/self_found external snapshots
- project-plans stale plans
- stale tests with zero imports
- owner-supplied extracted artifacts
