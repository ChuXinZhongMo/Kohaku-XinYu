# XinYu Roadmap

This roadmap describes XinYu's own direction. KohakuTerrarium remains the
underlying runtime framework snapshot, but this repository is organized around
XinYu.

This root roadmap is the public-facing project plan. Detailed runtime plans and
audit trails live under `examples/agent-apps/xinyu/` and the worklog/report
folders.

## v0.1.0 - Public Source Baseline

Status: release candidate

- Publish the source tree as XinYu-first local personal-agent infrastructure.
- Keep private runtime state, credentials, QQ payloads, local memory, and
  owner-supplied material bodies outside the public source surface.
- Document the active runtime layout, setup commands, validation baseline, and
  local operator entry points.
- Keep the Python test suite, runtime readiness smoke, QQ gateway smoke,
  desktop typecheck, and desktop build as the release-readiness baseline.

## v0.1 - Local Working System

Status: shipped locally

- XinYu core app lives under `examples/agent-apps/xinyu/`.
- Local environment file is separated into `xinyu.local.env`.
- Core bridge exposes health, probe, chat, proactive, ack, learning, and
  maintenance endpoints.
- Proactive QQ dispatch uses explicit claim / ack semantics.
- Native QQ gateway receives NapCat / OneBot events and forwards normalized
  turns to XinYu Core.
- `xinyu_status.py` checks the local Core + native QQ gateway + NapCat stack.
- Runtime secrets, logs, runtime traces, local gateway config, and memory state
  are excluded from Git.
- Local learning library separates self-found material from owner-supplied
  material.

## v0.2 - Repository Presentation

Status: shipped

- Make the GitHub repository read as XinYu first.
- Keep vendored KohakuTerrarium source clearly marked as an implementation
  dependency.
- Remove stale repository-managed AstrBot integration paths.
- Replace upstream issue templates and release automation.
- Update GitHub About, topics, README, app README, runbook, CI, and architecture
  diagram for the native QQ gateway chain.

## v0.3 - Long-Run Stability

Status: in progress

- Harden Core bridge restart behavior.
- Keep native QQ gateway restart behavior simple and observable.
- Make status checks stricter around stale proactive dispatch state.
- Keep `Start-XinYu-QQ.ps1` as the practical one-command local startup path.
- Keep `deployment_status_smoke.py` and `runtime_readiness_smoke.py` green.
- Expand smoke tests for repeated proactive cycles and failed-send retries.
- Add runtime scheduling around `xinyu_learning_library.py` so approved learning
  requests can download materials without manual shell commands.

## v0.4 - Memory Review And Safety

Status: planned

- Add clearer owner approval records for self-iteration changes.
- Separate durable memory from temporary runtime traces more cleanly.
- Add memory review tools that summarize proposed changes before they persist.
- Keep private memory local by default.
- Keep seed memory portable without leaking private account identifiers.

## v0.5 - Operator UI

Status: exploratory

- Build a small local dashboard for:
  - Core bridge health
  - native QQ gateway / NapCat connection status
  - proactive candidate state
  - last claim / ack result
  - AI self-iteration review state
- Keep the command-line status tool as the canonical source of truth.

## Not Yet Goals

- Public multi-user bot hosting.
- Group chat memory writes.
- Automatic public source learning from QQ messages.
- Cloud deployment of private memory.
- Removing the vendored framework source before XinYu has a clean dependency
  path.

## Success Signals

- Tagged releases with clear notes and validation results.
- Public issues and pull requests triaged by the maintainer.
- Reproducible local setup from public documentation.
- Tests and smoke checks covering the public runtime boundaries.
- No private runtime state or credentials in published source.
