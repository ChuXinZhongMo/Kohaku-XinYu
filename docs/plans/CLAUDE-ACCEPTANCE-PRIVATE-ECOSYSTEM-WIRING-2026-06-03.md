# Acceptance Report: Private Ecosystem → Autonomy Loop + Desktop Wiring

date: 2026-06-03
executor: Claude (Opus 4.8)
reviewer: 5.5
repo: D:\XinYu  · app root: D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
venv python: `.\.venv\Scripts\python.exe`
prior context: CLAUDE-HANDOFF-BACK-PRIVATE-ECOSYSTEM-2026-06-02.md,
CODEX-TASK-PRIVATE-ECOSYSTEM-ENABLE-2026-06-02.md

## Scope of this increment

Wire the already-built private browser + computer control into (a) the autonomy
loop (XinYu can trigger), and (b) the Desktop/bridge (owner can trigger from the
cockpit), without bypassing any existing gate.

Delivered:
1. Bridge route module `xinyu_bridge_private_ecosystem_routes.py` + runtime
   bindings + HTTP routes.
2. `external_plugin_call` native executor for the browser/computer plugins.
3. Kernel autonomous read-only browsing, bounded to an owner URL whitelist.
4. Desktop cockpit kill-switch (pause/resume share) button, full IPC chain.

## Files changed

New:
- xinyu_bridge_private_ecosystem_routes.py        (5 async routes)
- tests/test_bridge_private_ecosystem_routes.py    (9 tests)
- tests/test_private_ecosystem_autobrowse.py       (4 tests)

Modified (backend, additive):
- xinyu_core_bridge.py                 (+5 runtime delegator methods; import)
- xinyu_bridge_http.py                 (+2 GET, +3 POST routes; token-required set; dispatch)
- xinyu_bridge_external_plugin_routes.py (+native executor branch + `_execute_private_ecosystem_native`)
- xinyu_private_ecosystem.py           (+`explore_browser_readonly` goal, whitelist-gated; browser-observe executor)
- tests/test_private_ecosystem_external_plugins.py (+2 native-executor tests)

Modified (Desktop, additive):
- src/main/xinyu_gateway.ts             (+pausePrivateShare; +privateEcosystem on XinYuSnapshot)
- src/main/index.ts                     (+xinyu:pause-private-share IPC handler)
- src/preload/index.ts                  (+pausePrivateShare bridge)
- src/renderer/src/global.d.ts          (+pausePrivateShare type)
- src/renderer/src/main.tsx             (+pausePrivateShare handler + busy state + prop)
- src/renderer/src/DesktopPanels.tsx    (+pause/resume button in PrivateEcosystemPanel)

## New bridge surface (all owner-private; POST require bridge token)

- GET  /desktop/private-ecosystem/snapshot   → sanitized cockpit snapshot
- GET  /desktop/private-browser/snapshot      → browser session snapshot
- POST /desktop/private-ecosystem/pause       → kill switch (pause/resume share)
- POST /desktop/private-ecosystem/grant       → owner grant edit (whitelisted sections only)
- POST /desktop/private-browser/action        → one policy-gated browser action (real engine in a worker thread)

Gate order preserved: HTTP token (POST) → owner-private context
(`_owner_private_payload_matches`) → per-action policy in
run_browser_action (grant, sensitive-page block, approval). Computer execution
is NOT autonomous and stays grant-gated.

## How XinYu triggers (autonomy loop)

`explore_browser_readonly` goal appears **only when** `private_browser.enabled`
is true AND `private_browser.allowed_urls` (owner whitelist) is non-empty.
Default whitelist is empty → no autonomous browsing. When selected, the tick
does a read-only `navigate_readonly` of the next whitelisted URL through the
real engine (falls back to honest `simulated` if no browser binary). It never
auto-runs clicks/fills/submits or any computer action.

## Verification commands (independently runnable by 5.5)

Backend — new suite (expect 60 passed):
```
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m pytest -q tests/test_private_ecosystem.py tests/test_owner_private_share.py `
  tests/test_private_browser_control.py tests/test_computer_control.py tests/test_desktop_private_ecosystem_snapshot.py `
  tests/test_private_ecosystem_external_plugins.py tests/test_private_ecosystem_live_engines.py `
  tests/test_private_browser_engine_playwright.py tests/test_bridge_private_ecosystem_routes.py `
  tests/test_private_ecosystem_autobrowse.py
```

Backend — dossier focused regression (expect 67 passed):
```
.\.venv\Scripts\python.exe -m pytest -q tests/test_self_action_gateway.py tests/test_self_action_approval_controls.py `
  tests/test_self_action_patch_executor.py tests/test_desktop_self_action_snapshot.py tests/test_self_action_queue_store.py `
  tests/test_bridge_external_plugin_routes.py tests/test_autonomous_outward_action.py `
  tests/test_stage12_long_term_evaluation.py tests/test_stage13_self_narrative.py tests/test_autonomy_loop_report.py
```

Bridge wiring sanity (expect "bridge modules import OK"):
```
.\.venv\Scripts\python.exe -c "import ast; ast.parse(open('xinyu_core_bridge.py',encoding='utf-8').read()); import xinyu_bridge_http, xinyu_bridge_external_plugin_routes, xinyu_bridge_private_ecosystem_routes; print('bridge modules import OK')"
```

Routes registered (expect all 5 paths printed):
```
.\.venv\Scripts\python.exe -c "import xinyu_bridge_http as h; src=open('xinyu_bridge_http.py',encoding='utf-8').read(); [print(p, p in src) for p in ['/desktop/private-ecosystem/snapshot','/desktop/private-browser/snapshot','/desktop/private-ecosystem/pause','/desktop/private-ecosystem/grant','/desktop/private-browser/action']]"
```

Status — private_ecosystem check green:
```
.\.venv\Scripts\python.exe -c "from pathlib import Path; import xinyu_status as s; print('pe_check=', {c.name:c.ok for c in s.check_state(Path('.'))}['private_ecosystem'])"
```

Live browser via Edge (part of the new suite; uses channel=msedge, loopback page, no external net) — see
tests/test_private_browser_engine_playwright.py (2 tests pass).

Desktop typecheck + build (expect both succeed):
```
cd D:\XinYu\XinYu_Desktop ; npm run build
```

## Results observed by executor

- New private-ecosystem suite: 60 passed.
- Dossier focused regression: 67 passed.
- Desktop `npm run build` (incl. `tsc --noEmit`): passed.
- Bridge modules import OK; all 5 routes present.
- `private_ecosystem` status check: green.

## Status checks that are RED but NOT from this work (do not fail acceptance)

`xinyu_status.py --json` aggregate `ok` is False due to time-windowed / pre-existing
autonomy checks unrelated to the private ecosystem:
- `stage12_long_term_evaluation` = active_needs_check — the 24h dialogue-recall
  and live-loop windows rolled stale (no fresh owner QQ sample since the date
  advanced to 2026-06-03). Documented rolling behavior; recovers when the owner
  sends a fresh private message. Reason: `recall=no_samples`,
  `live_loop=needs_check`.
- `autonomy_decision_chain` — same time-window staleness.
- `action_feedback_coverage` — pre-existing `needs_check` (red at baseline).
- Pre-existing mojibake debt in unrelated files (interaction_journal.jsonl,
  raw_events.jsonl, stage8 packet) still flagged by smoke mojibake guard.

None of these touch private-ecosystem code paths; the work added only an
additive `private_ecosystem` status section + check (green).

## Safety posture (unchanged invariants)

- No existing gate bypassed: bridge token + owner-private context + policy gates
  all enforced; QQ outbox claim/ack untouched; self-action approval queue
  untouched.
- Autonomous browsing is whitelist-bounded (owner URLs only); empty by default.
- Computer control is never autonomous; real screen capture stays grant-gated
  and OFF by default.
- Browser uses the isolated profile + Edge channel; sensitive/credential/payment
  pages blocked; form submission high-blocked; no open CDP port.
- Kill switch (`paused:true`) blocks sharing immediately and is reflected in
  status/Desktop in real time.

## Rollback

All edits are additive. To revert: delete xinyu_bridge_private_ecosystem_routes.py
and the 2 new test files; revert the additive blocks in xinyu_core_bridge.py,
xinyu_bridge_http.py, xinyu_bridge_external_plugin_routes.py,
xinyu_private_ecosystem.py, and the 6 Desktop files. Set grants
private_browser.enabled / owner_private_autonomous_share.enabled back to false.
No existing behavior was modified, so rollback restores the prior state.
