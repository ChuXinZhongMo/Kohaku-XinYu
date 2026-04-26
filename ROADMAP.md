# XinYu Roadmap

This roadmap describes XinYu's own direction. KohakuTerrarium is the underlying
runtime framework, but this repository is now organized around XinYu.

## v0.1 - Local Working System

Status: shipped locally

- XinYu core app lives under `examples/agent-apps/xinyu/`.
- Local environment file is separated into `xinyu.local.env`.
- Core bridge exposes health, probe, chat, proactive, and ack endpoints.
- Proactive QQ dispatch uses explicit claim / ack semantics.
- AstrBot shell can send a claimed proactive message through NapCat / OneBot.
- `xinyu_status.py` checks the local Core + AstrBot + NapCat stack.
- Runtime secrets, logs, and memory state are excluded from Git.

## v0.2 - Repository Consolidation

Status: in progress

- Make the GitHub repository read as XinYu first.
- Keep vendored KohakuTerrarium source clearly marked as an implementation
  dependency.
- Bring the AstrBot shell plugin source into `integrations/astrbot/`.
- Replace upstream issue templates and release automation.
- Keep local runtime docs focused on XinYu commands and recovery paths.

## v0.3 - Long-Run Stability

Status: planned

- Harden Core bridge restart behavior.
- Make status checks stricter around stale proactive dispatch state.
- Add a single operator command for "start everything, then verify".
- Add a single operator command for "stop everything cleanly".
- Expand smoke tests for repeated proactive cycles and failed-send retries.

## v0.4 - Memory Review And Safety

Status: planned

- Add clearer owner approval records for self-iteration changes.
- Separate durable memory from temporary runtime traces more cleanly.
- Add memory review tools that summarize proposed changes before they persist.
- Keep private memory local by default.

## v0.5 - Operator UI

Status: exploratory

- Build a small local dashboard for:
  - Core bridge health
  - AstrBot / NapCat connection status
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
