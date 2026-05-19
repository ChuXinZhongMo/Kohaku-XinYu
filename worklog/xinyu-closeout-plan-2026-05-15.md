# XinYu Remaining Work Plan

Date: 2026-05-15
Workspace: `D:\XinYu`

## Goal
Finish the remaining user-facing gaps without changing stable protocol keys, payload shapes, or long-term memory bodies.

## Execution Order

1. API profile quick switch
   - Keep the desktop API panel editable.
   - Make profile replace/apply behavior obvious in the UI.
   - Add a regression smoke for profile save/apply/restart.

2. External plugin control center
   - Keep Codex, Kohaku, and MCP as one control group in the front end.
   - Preserve enable/proactive/install controls.
   - Keep auto-install/download support for missing plugins.

3. Failover and quota fallback
   - Confirm API quota/rate-limit failures fall back to local visible reply handling.
   - Keep the primary path unchanged for normal calls.
   - Add a regression test for quota/rate-limit recovery.

4. Fast-path suppression cleanup
   - Stop `fast_path` from swallowing turns that should still get a real reply.
   - Keep only the tiny diagnostic path if it is still needed.
   - Update v1 smoke coverage to match the new route behavior.

5. Localization pass
   - Finish remaining Chinese labels and status copy.
   - Keep identifiers, IPC channel names, and JSON keys unchanged.

6. Final validation
   - `npm.cmd run typecheck`
   - `npm.cmd run build`
   - targeted Python smokes and pytest coverage for the touched paths

## Stop Conditions

- Any change to persona semantics or long-term memory body text.
- Any real QQ outbound test.
- Any change to public protocol names, JSON keys, or IPC channel names.
- Any rewrite that requires rolling back unrelated user edits.

## Progress

- Completed: fixed the `xinyu_runtime` test import path and validated failover coverage.
- Completed: kept v1 fast-path empty replies on the slow-reasoning fallback path.
- Completed: expanded the desktop API control surface and external plugin controls.
- Verified: `python -m pytest tests/test_llm_failover.py tests/v1/test_v1_smoke_contract.py -q`
- Verified: `python tests/smoke/tools/xinyu_external_plugins_smoke.py`
- Verified: `npm.cmd run typecheck`
- Verified: `npm.cmd run build`
- Completed: split the desktop right rail into a separate system-control column and raised the Electron minimum window size to avoid panel overlap.
- Verified after layout split: `npm.cmd run typecheck`
- Verified after layout split: `npm.cmd run build`
