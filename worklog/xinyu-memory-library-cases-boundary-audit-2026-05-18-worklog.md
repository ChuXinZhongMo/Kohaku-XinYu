# XinYu Memory/Library/Cases Boundary Audit - 2026-05-18

Status: applied as read-only boundary audit batch.

## Batch Scope

- Capability group: memory/library/cases content boundary.
- Goal: audit where memory, public/library data, conversation cases, legacy
  fallback data, and runtime artifacts live without printing private bodies.

## Completed

- Added `ops/validation/memory_library_cases_audit.py`.
  - Scans configured boundary roots:
    - app `memory/`
    - root `cases/`
    - root `library/`
    - app `data/`
    - app `runtime/`
  - Reads only small metadata/frontmatter fields from markdown:
    - `memory_type`
    - `source`
    - `status`
    - `time_scope`
  - Does not print memory bodies, raw QQ content, or JSON/JSONL row bodies.
  - Skips runtime pytest/codex temp directories and oversized metadata files.
- Added `tests/test_memory_library_cases_audit.py`.
- Generated:
  - `D:\XinYu\worklog\xinyu-memory-library-cases-boundary-audit-2026-05-18.md`
  - `D:\XinYu\worklog\xinyu-memory-library-cases-boundary-audit-2026-05-18.json`

## Audit Result

Latest report:

- total_files: 2287
- zone counts:
  - runtime: 1815
  - memory: 307
  - memory.runtime_or_self: 124
  - memory.knowledge: 28
  - library: 5
  - legacy.library: 4
  - cases: 2
  - legacy.cases: 2
- concern counts:
  - runtime_file_has_stable_memory_frontmatter: 284
  - structured_data_inside_memory_review: 22
  - legacy_fallback_review: 6

Interpretation:

- Canonical `cases/` and `library/` exist, while app `data/` still carries
  legacy fallback rows that should not be treated as live memory.
- Runtime contains many copied memory snapshots under smoke/trial/backup
  workspaces; these are review items, not automatic delete targets.
- Several JSON/JSONL state files remain under `memory/`; these need later
  per-file decisions before any move.

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile ops\validation\memory_library_cases_audit.py
.\.venv\Scripts\python.exe -m pytest tests\test_memory_library_cases_audit.py
.\.venv\Scripts\python.exe ops\validation\memory_library_cases_audit.py --repo-root D:\XinYu --output D:\XinYu\worklog\xinyu-memory-library-cases-boundary-audit-2026-05-18.md
.\.venv\Scripts\python.exe ops\validation\memory_library_cases_audit.py --repo-root D:\XinYu --json --output D:\XinYu\worklog\xinyu-memory-library-cases-boundary-audit-2026-05-18.json
git diff --check -- XinYu-Core/examples/agent-apps/xinyu/ops/validation/memory_library_cases_audit.py XinYu-Core/examples/agent-apps/xinyu/tests/test_memory_library_cases_audit.py
```

Results:

- Focused pytest: 4 passed.
- Boundary report generation: passed.
- Diff check: clean.

## Direct Impact

- The project now has a repeatable, privacy-conscious way to see content-boundary
  drift.
- It produces review lists without automatically deleting, moving, or exposing
  private contents.

## Not Changed

- No memory, library, case, or runtime content was moved or deleted.
- No private memory bodies were printed.
- No git commit was made.

## Next Batch

Run total validation and write final five-item completion audit.
