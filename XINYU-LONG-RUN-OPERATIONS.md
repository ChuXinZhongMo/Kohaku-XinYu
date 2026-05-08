# XinYu Long-Run Operations

Date: 2026-05-07

## Purpose

This document defines the minimum operating rhythm for long-running local XinYu sessions. It does not authorize real QQ outbound testing, v1 traffic expansion, memory-body rewrites, or persona semantic changes.

## Health Signals

- Bridge alive: `/health` on `127.0.0.1:8765`.
- Desktop event stream alive: minimal WebSocket handshake to `127.0.0.1:8766/desktop/events`.
- QQ gateway alive: minimal WebSocket handshake to `127.0.0.1:6199`.
- NapCat reachable: minimal WebSocket handshake to `127.0.0.1:6099`.
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

`recent_exceptions` uses a 120-minute default window so old log tails do not keep a long-running session permanently degraded. Use an explicit override when investigating older traces:

```powershell
python diagnostics\check_xinyu_health.py --json --recent-window-minutes 240
python diagnostics\check_xinyu_health.py --json --recent-window-minutes 0
```

`--recent-window-minutes 0` restores the broad tail scan and is useful only for historical comparison.

Use strict mode only in automation that is allowed to fail on degraded live services:

```powershell
python diagnostics\check_xinyu_health.py --strict
```

The default diagnostic mode is read-only. It does not start services, send QQ messages, write runtime files, or modify memory.

## Health History Ledger

Long-running sessions can opt in to a compact runtime JSONL ledger:

```powershell
python diagnostics\check_xinyu_health.py --json --write-ledger
python diagnostics\check_xinyu_health.py --json --write-ledger --checkpoint
```

The default ledger path is:

```text
XinYu-Core/examples/agent-apps/xinyu/runtime/diagnostics/xinyu_health_history.jsonl
```

The ledger records the check time, overall status, signal statuses, and degraded signal details. It is runtime diagnostic history only; it is not long-term memory content and is not a substitute for owner approval on high-risk actions.

Health probes must avoid creating their own error noise. WebSocket endpoints should be checked with a valid minimal WebSocket handshake, not a raw TCP connect that leaves malformed-handshake tracebacks in `logs/xinyu_core_bridge.err.log`.

## Operating Rhythm

- Every 30 minutes: run `diagnostics\check_xinyu_health.py --json --write-ledger` and inspect `warn` or `critical` signals.
- Every 2 hours: run `diagnostics\check_xinyu_health.py --json --write-ledger --checkpoint`, then record git status, latest commits, health summary, and any skipped live checks.
- When health is degraded but the source is unclear: re-run with `--recent-window-minutes 0` to distinguish current failures from historical tail residue.
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

## Recent Checkpoint Notes

- 2026-05-08 10:41: `diagnostics\check_xinyu_health.py --json --workspace D:\XinYu` reported `recent_exceptions: ok` with `hits=0` and `v1_shadow_errors: ok`. Overall status remained `warn` because `git_state` saw the intentionally untracked user-provided `XINYU-24H-WORK-PLAN.md`.
- 2026-05-08 11:10: QQ runtime trace smokes exposed that recent-exception JSONL filtering must honor `recorded_at` row timestamps, not only file mtime. The diagnostic was updated without cleaning runtime traces.
- 2026-05-08 11:37: `.\XinYu-Core\examples\agent-apps\xinyu\.venv\Scripts\python.exe diagnostics\check_xinyu_health.py --json --workspace D:\XinYu` reported bridge, desktop WS, QQ gateway, NapCat, outbox backlog, recent exceptions, v1 shadow errors, and disk space as `ok`. Overall status was `warn` only because `git_state` saw the intentionally untracked user-provided `XINYU-24H-WORK-PLAN.md`.
- 2026-05-08 12:17: `.\XinYu-Core\examples\agent-apps\xinyu\.venv\Scripts\python.exe diagnostics\check_xinyu_health.py --json --workspace D:\XinYu` again reported bridge, desktop WS, QQ gateway, NapCat, outbox backlog, recent exceptions, v1 shadow errors, and disk space as `ok`. Outbox was `pending=0 total=72`; recent exceptions were `hits=0 scanned_files=14 window_minutes=120`; v1 shadow errors were `errors=0 window=200`; disk free space was `646.4 GB`. Overall status remained `warn` only because `git_state` saw the intentionally untracked user-provided `XINYU-24H-WORK-PLAN.md`.
- 2026-05-08 12:48: `.\XinYu-Core\examples\agent-apps\xinyu\.venv\Scripts\python.exe diagnostics\check_xinyu_health.py --json --workspace D:\XinYu` reported bridge, desktop WS, QQ gateway, NapCat, outbox backlog, recent exceptions, v1 shadow errors, and disk space as `ok`. Outbox remained `pending=0 total=72`; recent exceptions were `hits=0 scanned_files=17 window_minutes=120`; v1 shadow errors were `errors=0 window=200`; disk free space was `646.4 GB`. Overall status remained `warn` only because `git_state` saw the intentionally untracked user-provided `XINYU-24H-WORK-PLAN.md`.
- 2026-05-08 13:20: `python diagnostics\check_xinyu_health.py --json` and `python diagnostics\check_xinyu_health.py --json --write-ledger` reported bridge, desktop WS, QQ gateway, NapCat, outbox backlog, recent exceptions, v1 shadow errors, and disk space as `ok`. Outbox remained `pending=0 total=72`; recent exceptions were `hits=0 scanned_files=15 window_minutes=120`; v1 shadow errors were `errors=0 window=200`; disk free space was `646.4 GB`. The ledger write succeeded at `runtime\diagnostics\xinyu_health_history.jsonl`. Overall status remained `warn` only because `git_state` saw the intentionally untracked user-provided `XINYU-24H-WORK-PLAN.md`.
- 2026-05-08 13:53: `python diagnostics\check_xinyu_health.py --json` and `python diagnostics\check_xinyu_health.py --json --write-ledger` again reported bridge, desktop WS, QQ gateway, NapCat, outbox backlog, recent exceptions, v1 shadow errors, and disk space as `ok`. Outbox remained `pending=0 total=72`; recent exceptions were `hits=0 scanned_files=15 window_minutes=120`; v1 shadow errors were `errors=0 window=200`; disk free space was `646.4 GB`. The ledger write succeeded at `runtime\diagnostics\xinyu_health_history.jsonl`. Overall status remained `warn` only because `git_state` saw the intentionally untracked user-provided `XINYU-24H-WORK-PLAN.md`.
- 2026-05-08 18:36: `python diagnostics\check_xinyu_health.py --json` and `python diagnostics\check_xinyu_health.py --json --write-ledger` reported bridge, desktop WS, QQ gateway, NapCat, outbox backlog, recent exceptions, v1 shadow errors, and disk space as `ok`. Bridge reported `sessions=1`; outbox remained `pending=0 total=72`; recent exceptions were `hits=0 scanned_files=11 window_minutes=120`; v1 shadow errors were `errors=0 window=200`; disk free space was `646.4 GB`. The ledger write succeeded at `runtime\diagnostics\xinyu_health_history.jsonl`. Overall status remained `warn` only because `git_state` saw the intentionally untracked user-provided `XINYU-24H-WORK-PLAN.md`.

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
