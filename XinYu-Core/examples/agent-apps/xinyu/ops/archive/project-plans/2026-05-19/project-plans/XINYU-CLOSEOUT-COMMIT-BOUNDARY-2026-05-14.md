# XinYu Closeout Commit Boundary Report

Date: 2026-05-14
Scope: local report only; no commit, stage, reset, checkout, or revert was run.

## Git Status Snapshot

- `git status --short` entries: `320`
- Modified entries: `51`
- Deleted entries: `212`
- Untracked entries: `57`
- Renamed entries: `0`
- Root moved-smoke deletions visible in status: `212`
- Untracked `tests/smoke/` directory entry is present; structure inventory counts `215` smoke files under `tests/smoke`.

## This Closeout Pass Boundary

Files directly touched or added by this closeout pass:

- `project-plans/XINYU-CLOSEOUT-AUTORUN-PLAN-2026-05-13.md`
- `project-plans/XINYU-CLOSEOUT-COMMIT-BOUNDARY-2026-05-14.md`
- `xinyu_core_bridge.py`
- `xinyu_bridge_promise_followup.py`
- `xinyu_bridge_turn_sidecars.py`
- `xinyu_bridge_proactive_context.py`
- `xinyu_bridge_health_snapshot.py`
- `xinyu_bridge_desktop_snapshot.py`

Related closeout work from this pass:

- promise follow-up bridge glue extraction
- live-turn prompt sidecar extraction
- proactive thread prompt sidecar extraction
- health snapshot and runtime health subsection extraction
- desktop snapshot and initiative metric helper extraction
- runtime source digest inclusion for the new bridge helper modules
- offline-only plan and blocked-item accounting
- smoke relocation/reference guard verification

## Conversation Experience Case Library Commit Group

Keep this as a separate review/commit group from the broader bridge extraction and smoke relocation work:

- `project-plans/XINYU-CONVERSATION-EXPERIENCE-CASE-LIBRARY-PLAN.md`
- `data/conversation_experience/seed_owner_cases.jsonl`
- `xinyu_conversation_experience_cases.py`
- `xinyu_conversation_experience_matcher.py`
- `xinyu_conversation_experience_sidecar.py`
- `tools/conversation_experience_cases.py`
- `tests/test_conversation_experience_cases.py`
- `tests/test_conversation_experience_matcher.py`
- `tests/test_conversation_experience_sidecar.py`
- `tests/test_prompt_pressure.py`
- `tests/smoke/dialogue/conversation_experience_cases_smoke.py`
- `tests/smoke/dialogue/conversation_experience_sidecar_smoke.py`
- `xinyu_bridge_turn_sidecars.py`
- `xinyu_prompt_pressure.py`
- `xinyu_core_bridge.py`

Boundary notes:

- Runtime database output under `runtime/conversation_experience/` is local generated state, not a source commit artifact.
- This group includes the sidecar integration edits in `xinyu_bridge_turn_sidecars.py`, prompt-pressure admission in `xinyu_prompt_pressure.py`, and runtime source digest inclusion in `xinyu_core_bridge.py`.
- Do not mix this group with QQ/NapCat, desktop renderer, E-drive, deployment, or public dataset import work.

## Separate Commit Groups To Consider Later

- Smoke relocation: root `*_smoke.py` deletions plus `tests/smoke/` additions.
- Conversation experience case library: modules, seed JSONL, CLI, tests, smokes, plan, and sidecar/prompt-pressure integration listed above.
- Bridge extraction: `xinyu_core_bridge.py`, `xinyu_bridge_promise_followup.py`, `xinyu_bridge_turn_sidecars.py`, and focused bridge tests.
- Closeout planning/reporting: files under `project-plans/` created or updated by this pass.
- Existing feature modules/tests: untracked modules such as code-awareness, prompt-pressure, contextual recall, recent-context guard, and their tests should be reviewed as their own commit group.
- Desktop repo changes: `D:\XinYu\XinYu_Desktop` renderer/gateway modifications are outside this core closeout patch and should stay separate.
- Broad modified docs/runtime modules: existing modifications in docs, memory/runtime modules, initiative/proactivity files, and learning files should not be mixed into the bridge extraction commit without review.

## Do Not Include In Offline Commit

- QQ/NapCat/live gateway recovery attempts.
- E drive recovery.
- Live deployment gate output.
- v1 production switch.
- Learning source promotions blocked by `review_needed`.
- Stable voice/personality/profile writes that still need owner review.

## Self-Check

- `git status --short` captured.
- Conversation experience case-library boundary added as its own commit group.
- No destructive git command used.
- Commit boundary remains advisory only; no files were staged.
