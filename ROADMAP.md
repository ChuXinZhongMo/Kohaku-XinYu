# XinYu Project Roadmap

This root roadmap is the public-facing project plan. More detailed runtime
planning lives under `XinYu-Core/ROADMAP.md` and the worklog/report folders.

## v0.1.0 - Public Source Baseline

Status: release candidate

- Publish the source tree as XinYu-first local personal-agent infrastructure.
- Keep private runtime state, credentials, QQ payloads, local memory, and
  owner-supplied material bodies outside the public source surface.
- Document the active runtime layout, setup commands, validation baseline, and
  local operator entry points.
- Keep the Python test suite, runtime readiness smoke, QQ gateway smoke,
  desktop typecheck, and desktop build as the release-readiness baseline.

## v0.2 - Open-Source Usability

Status: planned

- Add cleaner quick-start paths for a fresh local checkout.
- Separate machine-specific setup from reusable project configuration.
- Add issue templates for bug reports, gateway failures, and documentation
  requests.
- Improve English documentation around the memory, proactive, and QQ gateway
  boundaries.
- Publish a small set of reproducible non-private demo scenarios.

## v0.3 - Long-Run Runtime Stability

Status: in progress

- Harden restart and recovery behavior across XinYu Core, native QQ gateway,
  NapCat, and the desktop shell.
- Make stale proactive dispatch state easier to detect and repair.
- Expand repeated-cycle smoke coverage for proactive delivery, failed-send
  retries, and turn-completion side effects.
- Keep `XinYu.ps1` as the canonical local operator entry point.

## v0.4 - Memory Review And Safety

Status: planned

- Improve review tools for proposed durable-memory writes.
- Keep seed memory portable without leaking private account identifiers.
- Add clearer owner-approval records for self-iteration and learning changes.
- Strengthen privacy-boundary checks before release packaging.

## v0.5 - Operator UI And Maintenance Surface

Status: exploratory

- Build a compact local dashboard for core health, QQ gateway status,
  proactive candidate state, and AI self-iteration review state.
- Keep command-line status output as the canonical source of truth.
- Add maintainer-facing diagnostics for release readiness and support reports.

## Success Signals

- Tagged releases with clear notes and validation results.
- Public issues and pull requests triaged by the maintainer.
- Reproducible local setup from public documentation.
- Tests and smoke checks covering the public runtime boundaries.
- No private runtime state or credentials in published source.
