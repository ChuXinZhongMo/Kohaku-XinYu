# Private browser operator notes (Edge live)

Status: active 2026-07-13  
Audience: owner / maintainer running XinYu on the product machine  
Related: `docs/plans/CLAUDE-XINYU-PRIVATE-ECOSYSTEM-DOSSIER-2026-06-02.md`, grants under `memory/context/private_ecosystem_grants.json`

## Goal

Allowlisted **read-only** browse (GitHub only in current grants) with a **live** Edge engine, then optional owner-private share of a short observation. No open-web, no click/fill/submit.

## Prerequisites

- App venv with Playwright: `XinYu-Core/examples/agent-apps/xinyu/.venv`
- System Edge installed (`msedge.exe` under Program Files)
- Grants: `private_ecosystem.rollout_state = browser_read_only`, `private_browser.enabled`, non-empty `allowed_urls` (github.com)
- Plugin: `xinyu_private_browser` enabled + proactive in `config/external_plugins.json`
- Share: `browse_observation` is an allowed share kind (as of 2026-07-13)

## Env (`xinyu.local.env`, gitignored)

```env
XINYU_PRIVATE_BROWSER_CHANNEL=msedge
# Only when a local SOCKS proxy is actually listening:
# XINYU_PRIVATE_BROWSER_PROXY=socks5://127.0.0.1:10808
```

Notes:

- Channel is loaded by bridge via `load_local_env` on start. Restart core bridge after edits.
- A **dead** proxy makes every navigation `ERR_PROXY_CONNECTION_FAILED` and looks like “always simulated”. Prefer no proxy when direct Edge can reach GitHub; re-enable proxy only when the port is healthy.
- Verified 2026-07-13 on owner machine: Edge open + `https://github.com/` DOM without proxy; proxy `10808` was down.

## Acceptance checks

1. Restart `start_xinyu_core_bridge.ps1` (uses app `.venv`).
2. Trigger private-ecosystem tick / Desktop PE tick so `explore_browser_readonly` runs.
3. Inspect `runtime/private_ecosystem/browser_state.json`:
   - `engine` should be live / channel msedge (not forever `simulated`)
   - last action on a github allowlist URL completes with page text or artifact
4. If engine still simulated, check plugin result for `engine_open_error` (surfaced since 2026-07-13) — missing Playwright, bad channel, proxy, etc.
5. Share ledger: browse notes must not fail solely with `share_kind_not_allowed`.

## Safety (do not change casually)

- Do not empty `allowed_urls` (empty list weakens host hard-gate for manual navigate).
- Do not enable `single_step_actions` or computer control for autonomy.
- Keep `read_only: true`.
