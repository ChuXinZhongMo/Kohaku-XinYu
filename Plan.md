# XinYu Repository Consolidation Plan

This plan tracks the work needed to keep the repository presented as XinYu
instead of a generic KohakuTerrarium source snapshot.

## Principles

- Keep XinYu runnable.
- Do not commit local secrets, logs, QQ runtime data, live memory state, or local
  gateway configuration.
- Keep the vendored KohakuTerrarium source until XinYu has a clean dependency
  path.
- Keep public docs aligned with the current native QQ gateway chain.
- Move in small commits that can be reviewed and reverted independently.

## Phase 1 - Project Identity

Status: completed

- [x] Replace root `README.md` with a XinYu-facing overview.
- [x] Replace root `ROADMAP.md` with a XinYu roadmap.
- [x] Add this `Plan.md` as the execution plan.
- [x] Mark the vendored KohakuTerrarium source as an implementation dependency.
- [x] Replace GitHub issue / PR templates that still speak as upstream
  KohakuTerrarium.
- [x] Replace upstream framework CI with a lightweight XinYu syntax and privacy
  check.

## Phase 2 - QQ Runtime Chain

Status: completed

- [x] Remove the old repository-managed AstrBot integration source.
- [x] Add the native QQ gateway: `xinyu_qq_gateway.py`.
- [x] Add start / stop scripts for the native QQ gateway.
- [x] Document the current chain:
  `NapCatQQ -> xinyu_qq_gateway.py -> xinyu_core_bridge.py -> XinYu Core`.
- [x] Keep `xinyu_qq_gateway.config.json` ignored because it contains local
  runtime configuration.
- [x] Update GitHub About, README, app README, and architecture diagram.

## Phase 3 - Repository Structure Cleanup

Status: pending

- [ ] Identify upstream examples and docs that are not needed for XinYu.
- [ ] Decide whether to keep, archive, or remove unrelated upstream material.
- [ ] Keep framework source required by XinYu's local runtime.
- [ ] Add a dependency extraction plan if XinYu should later consume
  KohakuTerrarium as a package instead of carrying a source snapshot.

## Phase 3.5 - Learning Library

Status: completed

- [x] Add `examples/agent-apps/xinyu/learning/`.
- [x] Split learning material into `self_found/` and `owner_supplied/`.
- [x] Keep downloaded materials, papers, repository snapshots, extracted text,
  and private manifest data out of Git.
- [x] Add `xinyu_learning_library.py` for URL, GitHub, file, and folder intake.
- [x] Add stage support to move registered items into `source_materials`.
- [x] Add `learning_library_smoke.py`.

## Phase 4 - Runtime Polish

Status: in progress

- [x] Add a single deployment runbook for Core + native QQ gateway + NapCat.
- [x] Make `xinyu_status.py` the canonical health command in public docs.
- [x] Add `deployment_status_smoke.py` and `runtime_readiness_smoke.py`.
- [ ] Keep smoke checks green after every bridge or gateway change.
- [ ] Reduce stale historical references to the removed AstrBot chain in old
  project-plan documents.

## Phase 5 - Release Marker

Status: pending

- [ ] Tag `v0.1.0` after docs, native QQ gateway layout, and privacy boundaries
  are stable.
- [ ] Add release notes describing what is real, what is local-only, and what is
  still experimental.
