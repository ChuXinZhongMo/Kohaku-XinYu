# XinYu Module Ecology Lab Archive Family Triage

Generated from metadata-only module ecology output. It does not read or print
memory, runtime, QQ payload, owner-supplied document bodies, library, cases, or
data bodies.

## Summary

- source_report: `ops/reports/module_ecology_archive_candidates_2026-05-19.md`
- lab_candidates: 105
- learning/self_found: 33
- learning/owner_supplied: 2
- project-plans: 17
- tests/smoke: 53

## Family Decisions

- `learning/self_found/*` | count=33 | classification=archive_family_ready | evidence=external/self-found snapshots with zero live refs/tests; archive by source snapshot folder, not individual file
- `learning/owner_supplied/*` | count=2 | classification=hold_owner_supplied_review | evidence=owner-supplied extracted artifacts; do not archive/delete until owner-supplied material boundary is reviewed
- `project-plans/*` | count=17 | classification=merge_into_plan_index | evidence=stale plan docs with zero live refs/tests; extract still-current decisions into active plan/worklog index before archive
- `tests/smoke/*` | count=53 | classification=smoke_inventory_review | evidence=smoke scripts with zero live refs/tests; compare against `smoke_run.py` groups before archive because smoke scripts are often invoked by name

## Notes

- Pytest-collected `tests/test_*.py` files and `tests/conftest.py` are no
  longer treated as stale lab assets; the audit now recognizes test runner
  collection as an activity signal.
- This report is family-level classification only. It does not move, delete, or
  rewrite any lab artifact.
