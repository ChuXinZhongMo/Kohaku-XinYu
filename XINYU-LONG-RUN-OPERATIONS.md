# XinYu Long-Run Operations

Date: 2026-05-07

## Purpose

This document defines the minimum operating rhythm for long-running local XinYu sessions. It does not authorize real QQ outbound testing, v1 traffic expansion, memory-body rewrites, or persona semantic changes.

## Health Signals

- Bridge alive: `/health` on `127.0.0.1:8765`.
- Desktop event stream alive: TCP connect to `127.0.0.1:8766`.
- QQ gateway alive: TCP connect to `127.0.0.1:6199`.
- NapCat reachable: TCP connect to `127.0.0.1:6099`.
- Outbox backlog: pending items in `memory/context/qq_outbox_queue.json`.
- Memory/state write errors: inferred from recent logs and traces until a dedicated state-service ledger exists.
- Recent exceptions: recent `logs/` and `runtime/` text/jsonl scan.
- v1 shadow errors: tail of `runtime/v1_shadow_trace.jsonl`.
- Disk space: free workspace drive space.
- Dirty git state: `git status --short --branch`.

## Read-Only Diagnostic

Run from `D:\XinYu`:

```powershell
python diagnostics\check_xinyu_health.py
python diagnostics\check_xinyu_health.py --json
```

Use strict mode only in automation that is allowed to fail on degraded live services:

```powershell
python diagnostics\check_xinyu_health.py --strict
```

The diagnostic is read-only. It does not start services, send QQ messages, write runtime files, or modify memory.

## Operating Rhythm

- Every 30 minutes: run `diagnostics\check_xinyu_health.py --json` and inspect `warn` or `critical` signals.
- Every 2 hours: record a checkpoint with git status, latest commits, health summary, and any skipped live checks.
- Before each refactor slice: run the validation matrix gate for the touched capability.
- After each successful refactor slice: record worklog, commit, and keep rollback command available.

## Recovery Levels

| Level | Meaning | Action |
| --- | --- | --- |
| L0 Observe | All signals ok or only expected offline warnings | Continue normal loop. |
| L1 Local Degrade | One local service or trace is warning | Re-run the focused smoke and record the condition. |
| L2 Runtime Degrade | Bridge, Desktop, QQ gateway, or outbox health is warning/critical | Stop feature work and run the relevant smoke group. |
| L3 State Risk | Memory/state write errors, growing outbox backlog, or v1 shadow errors appear | Pause migrations touching state; inspect before continuing. |
| L4 Owner Confirmation Required | Real QQ outbound, memory body rewrite, persona semantic change, v1 traffic expansion, or unrecoverable bridge startup failure is needed | Stop and ask the owner. |

## Checkpoint Template

```md
## Checkpoint - YYYY-MM-DD HH:MM

- Git:
- Health status:
- Warn/critical signals:
- Tests since last checkpoint:
- Commits since last checkpoint:
- Skipped live checks:
- Next slice:
```
