# Claude Handoff-Back: XinYu Private Ecosystem

date: 2026-06-02
executor: Claude (Opus 4.8)
scope: Build the owner-private autonomy layer (Private Ecosystem) per
CLAUDE-XINYU-PRIVATE-ECOSYSTEM-DOSSIER-2026-06-02.md. Compose existing XinYu
control primitives; add narrow missing pieces. No Super-Agent-Party code copied.

## Summary

Implemented the full Private Ecosystem loop and its gates:

- Phase 1 — Private state + autonomy journal. A deterministic tick runs
  observe -> load goals -> select -> classify -> run/queue -> journal ->
  update goal -> memory candidate -> owner-share -> publish event. Low-risk
  local read-only probes auto-run; nothing else executes. No stable memory
  write, no QQ send, no browser/computer execution from a bare tick.
- Phase 2 — Owner-private autonomous share gate. Grant + kill-switch (pause),
  owner-private channel only, daily limit, cooldown, quiet hours (+owner
  override), max length, dedupe, privacy filter (secrets/paths/long-id
  redaction). Sends through the existing owner-private QQ outbox (claim/ack
  preserved), never directly.
- Phase 3/4 — Private browser control. Isolated profile only; read-only
  observation auto-allowed under grant; click/fill need approval or a
  single-step grant; form submission, credential/payment pages, and arbitrary
  JS blocked. Typed BrowserActionRecord with a structured last-action marker
  (no LAST_ACTION regex). Screenshot TTL cleanup.
- Phase 5 — Computer control. Observe-only and proposal-only run without an
  execution grant; click/type/hotkey need approval or single-step grant;
  multi-step arbitrary control disabled; never targets payment/credential/
  account-security windows. Normalized 0..1000 plane, structured markers.
- Phase 6 — Cockpit + governance. `privateEcosystem` block added to the
  existing `/desktop/snapshot`; read-only `PrivateEcosystemPanel` in the
  Desktop shell; `private_ecosystem` section + green check in xinyu_status.py;
  `xinyu_private_browser` / `xinyu_computer_control` registered as gated
  external plugins (default disabled).

Engine note (honest blocker): Playwright and screen-capture backends (mss/
pyautogui) are NOT installed on this machine (PIL/numpy are). The browser and
computer services therefore enforce all policy/records/artifacts but drive in
an honest `simulated`/`unavailable` mode — read-only observations write
artifacts under private paths; single-step actions are typed-blocked rather
than faked as success. Real driving is a documented follow-up.

## Files Changed

New backend modules (D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\):
- xinyu_private_ecosystem_journal.py        (append-only sanitized journal; `pevt-` ids)
- xinyu_private_ecosystem_grants.py         (grants single source of truth; env enables paths only)
- xinyu_private_ecosystem.py                (autonomy kernel + tick + snapshot)
- xinyu_owner_private_share.py              (owner-private share gate)
- xinyu_browser_control.py                  (private browser policy/records/artifacts/TTL)
- xinyu_computer_control.py                 (computer observe/proposal/single-step gate)

New tests:
- tests/test_private_ecosystem.py
- tests/test_owner_private_share.py
- tests/test_private_browser_control.py
- tests/test_computer_control.py
- tests/test_desktop_private_ecosystem_snapshot.py
- tests/test_private_ecosystem_external_plugins.py

Modified (additive, narrowly scoped):
- xinyu_bridge_desktop_snapshot.py   (+desktop_private_ecosystem_snapshot, +"privateEcosystem" key)
- xinyu_status.py                    (+private_ecosystem_* fields, +private_ecosystem check)
- xinyu_external_plugins.py          (+2 plugin specs, +control defaults, +install-status branch)
- XinYu_Desktop/src/renderer/src/desktopTypes.ts   (+PrivateEcosystemSnapshot type)
- XinYu_Desktop/src/renderer/src/DesktopPanels.tsx (+PrivateEcosystemPanel, rendered in MindStatePanel)

Generated runtime artifacts (from a real tick; safe/additive):
- memory/context/private_ecosystem_state.md
- runtime/private_ecosystem/{state.json,autonomy_journal.jsonl,observations.jsonl,events.jsonl}

Naming deviation: the dossier names the journal `xinyu_autonomy_journal.py`, but
that filename already holds an unrelated owner-visible thought-note renderer.
To avoid clobbering existing functionality, the journal store is
`xinyu_private_ecosystem_journal.py`.

## Runtime Status Before/After

Before (baseline, captured pre-edit):
- xinyu_status: ok=False. Failing (pre-existing): core_bridge_source_digest,
  core_bridge_runtime_source_digest, action_feedback_coverage.
- stage12: active_ready_for_stage13, ready_for_stage13=true.
- stage13: active_available_for_self_narrative.
- stage8: active_guarded (learning_trial_success_gate blocked — known debt).
- autonomy_loop_report: ok=False. Failing (pre-existing):
  qq_reply_integrity_diagnostics, multi_action_feedback_coverage.

After:
- xinyu_status: same 3 pre-existing failures, NO new failures. New
  `private_ecosystem` check = GREEN.
- autonomy_loop_report: byte-identical failure set (new_failures = []).
- stage12 / stage13 / stage8: unchanged (no regression).

## Private Ecosystem State

- rollout_state: disabled (default safe/off; a manual tick still journals locally).
- A real tick ran: selected_goal=observe_private_space, low_risk_executed=1,
  journal events {tick_started, goal_selected, action_executed}, stable
  memory writes = 0, boundaries.stable_memory_write = blocked.
- Visible in Desktop via /desktop/snapshot.privateEcosystem and in
  xinyu_status fields private_ecosystem_*.

## Owner-Private Share State

- Default: enabled=false (no grant) -> all share candidates HOLD; zero sends.
- With grant + owner target + limits satisfied: exactly one owner-private
  outbox message queued; dedupe suppresses repeats. Blocks proven for: no
  grant, paused, group/non-owner channel, missing owner target, quiet hours
  (unless owner override), daily limit, cooldown, empty/sensitive content.
- Secrets / local paths / long identifiers are redacted before send (verified
  the raw secret never reaches the outbox queue file).

## Browser/Computer Control State

- Browser engine: unavailable (Playwright not installed). Read-only snapshots
  run simulated and store artifacts under runtime/private_ecosystem/browser_*.
  Sensitive pages blocked; click/fill blocked without approval/grant; form
  submission high-blocked; isolated profile (uses_owner_browser_profile=false).
  Screenshot TTL cleanup verified.
- Computer backend: unavailable. Observe-only + proposal-only work without an
  execution grant; click/type blocked without approval; multi-step arbitrary
  control disabled; sensitive windows blocked. Normalized 0..1000 plane;
  structured last-action markers.
- Both registered as external plugins (default disabled; runtime_allowed ->
  plugin_disabled; read-only caps require owner-private; action caps require
  approval).

## Tests Run

- New private-ecosystem tests: 38 passed.
- Dossier 16.1 self-action/external set: test_self_action_gateway,
  test_self_action_approval_controls, test_self_action_patch_executor,
  test_desktop_self_action_snapshot, test_self_action_queue_store,
  test_bridge_external_plugin_routes, test_autonomous_outward_action — passed
  (72 passed together with the new tests).
- Dossier 16.1 autonomy/stage set: test_autonomy_loop_report,
  test_stage8_memory_review_packet, test_stage8_learning_trial_validation_packet,
  test_stage10_proactive_life_loop, test_stage12_long_term_evaluation,
  test_stage13_self_narrative, test_proactive_direct_sender — 52 passed.
- smoke_run.py --group quick: all green EXCEPT mojibake_guard_smoke (pre-existing;
  flags interaction_journal.jsonl, raw_events.jsonl,
  stage8_learning_trial_validation_packet.py + its test — none are files this
  work created or touched).
- Desktop: `npm run typecheck` pass; `npm run build` pass.

## Rollout Flags Changed

None changed from safe defaults. All remain off:
XINYU_PRIVATE_ECOSYSTEM=disabled, XINYU_PRIVATE_BROWSER=disabled,
XINYU_COMPUTER_CONTROL=disabled, XINYU_OWNER_PRIVATE_AUTONOMOUS_SHARE=disabled
(daily_limit=8, cooldown=30m, max_chars=800, max_tabs=4, screenshot_ttl=24h).
Grants file memory/context/private_ecosystem_grants.json is the authoritative
permission source; env enables code paths only, never grants permission.

## Privacy/Safety Checks

Implemented + tested: owner identity (owner_user_ids from config), owner-private
channel only, plugin enabled/installed gates, proactive capability + concrete
reason, approval/grant gates, rate limit, cooldown, quiet hours, sensitive
domain/window detection, secret/local-path/long-id redaction, screenshot TTL,
share kill switch (pause). Journal/state never carry raw owner text, secrets,
local paths, QQ payload bodies, or visible reply bodies. stable_memory_write is
hard-forced blocked everywhere; journal stable_memory_write_count = 0.

## Known Blockers (pre-existing, surfaced not hidden)

1. xinyu_status core_bridge_source_digest / runtime_source_digest red: running
   bridge digest != source digest (bridge not restarted after earlier source
   changes). Unchanged by this work.
2. xinyu_status action_feedback_coverage = needs_check (pre-existing debt).
3. autonomy_loop_report qq_reply_integrity_diagnostics +
   multi_action_feedback_coverage red (pre-existing; identical before/after).
4. smoke mojibake_guard_smoke red: U+FFFD in interaction_journal.jsonl,
   raw_events.jsonl, xinyu_stage8_learning_trial_validation_packet.py + its
   test (pre-existing mojibake debt; not in any file this work created).
5. stage8 learning_trial_success_gate blocked — known guarded state; no
   auto-promotion (intentional, per prior owner decision).

Owner actions needed to advance the new layer (none required for DoD):
- To enable owner-private sharing: set
  owner_private_autonomous_share.enabled=true in
  memory/context/private_ecosystem_grants.json (kill switch = paused:true).
- For real browser/computer driving: `pip install playwright` (+ `playwright
  install chromium`) / a screen-capture backend, then wire a real engine; keep
  CDP loopback-only with random port + per-session token.

## Rollback Plan

Not a destructive change; all edits are additive and namespaced.
- Delete the 6 new backend modules and 6 new test files listed above.
- Revert the 5 additive edits (each is a single clearly-delimited block):
  xinyu_bridge_desktop_snapshot.py, xinyu_status.py, xinyu_external_plugins.py,
  desktopTypes.ts, DesktopPanels.tsx.
- Optionally remove generated runtime artifacts under
  runtime/private_ecosystem/ and memory/context/private_ecosystem_*.{md,json}.
- No existing gates, tests, or behavior were modified, so rollback restores the
  exact baseline.
