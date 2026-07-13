# Acceptance Addendum: Codex P0/P1 Review Fixes

date: 2026-06-03
executor: Claude (Opus 4.8)
reviewer: Codex / 5.5
follows: CLAUDE-ACCEPTANCE-PRIVATE-ECOSYSTEM-WIRING-2026-06-03.md

All four Codex items implemented and verified. Summary + verification below.

## P0-1 — Autonomous browser observe no longer bypasses the plugin gate

- `xinyu_private_ecosystem.py` no longer imports or calls `run_browser_action` /
  `create_browser_engine` (verified by grep → CLEAN).
- `explore_browser_readonly` now routes through the external_plugin_call chain
  via a new reusable helper `run_private_ecosystem_native_call(root, plugin_id,
  capability, args, context)` in `xinyu_bridge_external_plugin_routes.py`:
  `external_plugin_runtime_allowed` (enabled/proactive/installed) →
  `evaluate_external_call` (owner_private/proactive/reason/approval) → native
  executor.
- Context is `owner_private=True, proactive=True, reason="owner-approved
  read-only page observation"`.
- Capability used is `navigate_readonly` (added to the plugin as
  read_only + proactive); interactive `navigate` stays approval-gated.
- Goal still appears only when `private_browser.enabled` AND `allowed_urls`
  non-empty. Any failed gate (plugin disabled, proactive disabled, owner-private,
  approval, sensitive page, empty whitelist) → held and journaled as
  `action_blocked` (not `action_executed`).
- No click/fill/submit/computer autonomous path exists.
- Tests (`tests/test_private_ecosystem_autobrowse.py`): goal absent w/o whitelist;
  blocked when plugin disabled; blocked when proactive disabled; executes with
  plugin+whitelist (offline simulated); sensitive URL blocked; no-whitelist holds;
  stable_memory_write_count == 0.

## P0-2 — Grant route hardened

`xinyu_bridge_private_ecosystem_routes.py::_sanitize_grant_patch`:
- `owner_private_autonomous_share`: daily_limit clamped ≤ 8; cooldown_minutes
  floored ≥ 30; max_message_chars clamped ≤ 800; quiet_hours cannot be cleared
  (empty → rejected); only enabled/paused/quiet_hours_override booleans allowed.
- `private_browser`: enabled/read_only/allowed_urls only;
  `single_step_actions` rejected (never settable via the normal route).
- `computer_control`: entire section rejected (enable / single-step need a
  dedicated owner-approved mode, not this route).
- Unknown keys and unknown sections → dropped and surfaced in
  `rejected_keys`. Empty sanitized patch → HTTP 400.
- Tests (`tests/test_bridge_private_ecosystem_routes.py`): clamps share limits;
  rejects empty quiet_hours; rejects browser single_step; rejects
  computer_control; rejects unknown key.

## P1 — Edge default engine

`xinyu_browser_engine_playwright.py`:
- `root = Path(root).resolve()`.
- `_effective_channel`: honors an explicit channel; otherwise falls back to
  system Edge (`msedge`) when bundled Chromium cannot serve the requested mode
  (headless-aware: detects the missing `chromium_headless_shell` build).
- `chromium_sandbox=True` set explicitly. Launch args are only
  `--no-first-run --no-default-browser-check`. No remote-debugging-port, no
  remote-allow-origins, no disable-web-security, no stealth/anti-bot.
- Tests: explicit-channel honored + root resolved; Edge fallback when Chromium
  unusable (`tests/test_private_ecosystem_live_engines.py`); live loopback
  observation over 127.0.0.1, no external net
  (`tests/test_private_browser_engine_playwright.py`).

## P1 — Desktop browser action boundary

- `/desktop/private-browser/action` now reuses the SAME chain
  (`run_private_ecosystem_native_call`) — single execution path for autonomy and
  cockpit. Owner context is `owner_private=True, proactive=False, approved=<payload>`.
- Documented behavior: token + owner-private cockpit service; blocked with
  `plugin_disabled` when the xinyu_private_browser plugin is not enabled.
- Tests: blocked when plugin disabled; read-only works when plugin enabled
  (offline simulated); click blocked without approval (`approval_required`);
  invalid action → 400.

## Verification results

```
# new private-ecosystem suite + external plugin routes
pytest ... test_private_ecosystem*.py test_owner_private_share.py test_private_browser*.py `
  test_computer_control.py test_desktop_private_ecosystem_snapshot.py test_bridge_private_ecosystem_routes.py `
  test_bridge_external_plugin_routes.py   →  77 passed
# dossier focused regression
pytest ... test_self_action_*.py test_desktop_self_action_snapshot.py test_self_action_queue_store.py `
  test_autonomous_outward_action.py test_stage12_long_term_evaluation.py test_stage13_self_narrative.py `
  test_autonomy_loop_report.py   →  62 passed
# Desktop
npm run build   →  pass (tsc --noEmit + vite build)
```

- Kernel grep for direct engine calls: CLEAN.
- `xinyu_status` `private_ecosystem` check: **green**.

## xinyu_status total ok=False — explanation (unchanged from prior report)

Failing checks are `stage12_long_term_evaluation`, `autonomy_decision_chain`,
`action_feedback_coverage`. The first two are 24h-window rolling staleness
(`stage12` reason `recall=no_samples`, `live_loop=needs_check` — no fresh owner
QQ sample since the date advanced to 2026-06-03); `action_feedback_coverage` was
red at baseline. None touch private-ecosystem code. Recovers when the owner
sends a fresh private message.

## Constraints honored

- Did NOT modify live grants to expand permissions this round.
- Did NOT open computer_control.
- Did NOT fill autonomous `allowed_urls`.
- Note on prior live state (owner-intended, from earlier turns):
  `owner_private_autonomous_share.enabled=true`, `private_browser.enabled=true`
  (read_only, allowed_urls empty). With the new chain, autonomous browsing on
  live additionally requires the xinyu_private_browser external plugin to be
  enabled (it is OFF), so live autonomous browsing remains fully blocked.

## Residual / for Codex decision

- Bundled Playwright Chromium headless_shell still not downloaded (CDN blocked);
  Edge is the default headless engine via auto-fallback + env. Fetch later with
  `playwright install chromium-headless-shell` on an unblocked network.
- Desktop has no free-text "observe URL" button yet; browser actions are driven
  by the bridge route / CLI. The kill-switch (pause/resume share) button is wired.
