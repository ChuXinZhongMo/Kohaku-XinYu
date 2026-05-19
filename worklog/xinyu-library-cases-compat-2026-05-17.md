# XinYu Library/Cases Compatibility Pass - 2026-05-17

Status: applied as a safe boundary-layer change. This pass did not move or
read private memory, QQ logs, runtime traces, or raw owner conversation content.

## Purpose

Keep reducing XinYu's path sprawl by routing reviewed cases and public/reference
datasets through canonical boundaries:

- `cases/conversation/` for reviewed conversation behavior cases.
- `library/datasets/` for external/public datasets.
- legacy app-local `data/conversation_experience/` and `data/external/` only as
  compatibility fallbacks.

## Applied Changes

- Updated `xinyu_storage_paths.py` so workspace-level canonical `cases/` and
  `library/` paths win before legacy app-local paths when the runtime root is
  the app directory.
- Kept legacy fallback intact for old installs and current live data.
- Made public dataset alias resolution stop at the first matching source tier,
  preventing canonical and legacy copies of the same dataset from both being
  loaded.
- Allowed `tools/conversation_experience_cases.py import-public` to resolve
  `--dataset-id` without an explicit `--dataset` argument.
- Allowed `xinyu_contextual_self_replay.py` to resolve `--dataset-name` without
  an explicit `--dataset` argument.
- Added tests for canonical-priority source resolution and dataset-id-only
  imports/replays.

## Boundary Notes

- No raw dataset rows are committed by this change.
- `library/datasets/README.md` remains the placeholder for external dataset
  placement.
- Actual movement of `data/external/` or `data/conversation_experience/` should
  wait until registry files and fixtures have migrated and full validation is
  green.
