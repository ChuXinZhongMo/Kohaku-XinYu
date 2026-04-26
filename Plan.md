# XinYu Repository Consolidation Plan

This plan tracks the work needed to turn this repository from a KohakuTerrarium
source snapshot with a XinYu app into a clearly presented XinYu project.

## Principles

- Keep XinYu runnable.
- Do not commit local secrets, logs, QQ runtime data, or live memory state.
- Do not delete the vendored KohakuTerrarium source until XinYu has a clean
  dependency path.
- Move in small commits that can be reviewed and reverted independently.

## Phase 1 - Project Identity

Status: completed

- [x] Replace root `README.md` with a XinYu-facing overview.
- [x] Replace root `ROADMAP.md` with a XinYu roadmap.
- [x] Add this `Plan.md` as the execution plan.
- [x] Add a short upstream-framework note so the vendored source snapshot is
  intentional instead of confusing.
- [x] Replace GitHub issue / PR templates that still speak as KohakuTerrarium.
- [x] Replace upstream framework CI with a lightweight XinYu syntax and privacy
  check.
- [x] Disable or rewrite release automation that is meant for upstream
  KohakuTerrarium publishing.

## Phase 2 - Bring QQ Adapter Into The Repository

Status: completed

- [x] Add `integrations/astrbot/`.
- [x] Copy the XinYu AstrBot shell plugin source into the integration directory.
- [x] Copy install / start / stop scripts that are useful for local operation.
- [x] Copy shell smoke-test tools.
- [x] Exclude shell logs, live AstrBot data, caches, and local secrets.
- [x] Link the integration from the root README and XinYu app README.

## Phase 3 - Repository Structure Cleanup

Status: pending

- [ ] Identify upstream examples and docs that are not needed for XinYu.
- [ ] Decide whether to keep, archive, or remove unrelated upstream material.
- [ ] Keep framework source required by XinYu's local runtime.
- [ ] Add a dependency extraction plan if XinYu should later consume
  KohakuTerrarium as a package instead of carrying a source snapshot.

## Phase 4 - Runtime Polish

Status: pending

- [ ] Add a single startup checklist for Core + AstrBot + NapCat.
- [ ] Add a single recovery checklist for proactive QQ delivery.
- [ ] Make `xinyu_status.py` the canonical health command in all docs.
- [ ] Keep smoke checks green after every bridge or integration change.

## Phase 5 - Release Marker

Status: pending

- [ ] Tag `v0.1.0` after docs, integration layout, and privacy boundaries are
  stable.
- [ ] Add release notes describing what is real, what is local-only, and what is
  still experimental.

## Current Execution Scope

This pass executed Phase 1 and the safe parts of Phase 2.

The cleanup that could remove or move upstream framework files is intentionally
left for a later pass because XinYu still depends on the local framework source.
