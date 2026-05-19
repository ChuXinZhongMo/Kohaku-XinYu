# Contributing

Use small, reviewable commits and keep private runtime state out of the repo.

## Commit Style

Use conventional, scoped subjects:

- `feat: ...`
- `fix: ...`
- `refactor: ...`
- `test: ...`
- `docs: ...`
- `chore: ...`

Prefer commits that each answer one question:

- what behavior changed
- what boundary was tightened
- what files moved or were archived
- what validation proves it

## Before A Pull Request

Run the relevant checks:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe smoke_run.py --group quick --timeout-seconds 180 --json

cd D:\XinYu\XinYu_Desktop
npm run typecheck
npm run build
```

Do not include:

- secrets or `.env` files
- private memory/runtime/log files
- owner-supplied material bodies
- unknown-license third-party source snapshots
