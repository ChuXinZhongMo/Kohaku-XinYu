# XinYu Project Plan Index Review - 2026-05-19

Scope: review the 17 stale `project-plans/*.md` candidates from
`ops/reports/module_ecology_archive_candidates_2026-05-19.md`.

Privacy note: this review reads project-plan documents only. It does not read
or print memory, runtime, QQ payload, library, cases, or data bodies.

## Summary

- stale plan candidates: 17
- keep active: 1
- hold for encoding/boundary review: 1
- archive candidate, superseded by implementation or newer plan: 11
- archive candidate, historical handoff/audit/closeout: 4
- files moved: 0

## Decision Vocabulary

- `keep_active`: still part of the current execution direction.
- `hold_review`: do not archive until a specific boundary issue is resolved.
- `archive_candidate_superseded`: useful historical context, but replaced by
  implemented code/tests or a newer plan.
- `archive_candidate_historical`: handoff, closeout, or audit report with no
  active execution role.

## Items

| Path | Decision | Evidence | Direct effect |
| --- | --- | --- | --- |
| `project-plans/XINYU-ANSWER-DISCIPLINE-CALIBRATION-PLAN.md` | archive_candidate_superseded | `Completed Foundation` at line 32; visible guard and research layer entries marked done at lines 391 and 432-435 | keep implementation/tests as source of truth; plan can move to historical archive after a replacement note |
| `project-plans/XINYU-CLOSEOUT-AUTORUN-PLAN-2026-05-13.md` | archive_candidate_historical | dated closeout plan; scope is closeout/autorun at line 4 and status queue at line 20 | preserve as old run plan only; not active execution input |
| `project-plans/XINYU-CLOSEOUT-COMMIT-BOUNDARY-2026-05-14.md` | archive_candidate_historical | title says commit boundary report at line 1; scope says local report only at line 4 | preserve as commit-boundary history; not an active plan |
| `project-plans/XINYU-CODEX-HANDOFF-2026-05-05.md` | archive_candidate_historical | handoff dated 2026-05-05 at line 1; completed backend and desktop work sections at lines 58 and 181 | preserve as historical handoff; current worklogs supersede it |
| `project-plans/XINYU-CONVERSATION-EXPERIENCE-CASE-LIBRARY-PLAN.md` | archive_candidate_superseded | implementation plan has `DONE` markers at lines 437, 445, and 461 | keep case-library code/tests; plan can archive after linking current runtime owner |
| `project-plans/XINYU-CROSS-DOMAIN-SYNAESTHESIA-PLAN-2026-05-19.md` | keep_active | current purpose at line 3; runtime spine at line 145; scoring rule at line 191 | keep as current cross-domain synaesthesia execution plan |
| `project-plans/XINYU-DIALOGUE-DATASET-SELECTION-AND-EXPERIENCE-LIBRARY-PLAN-2026-05-14.md` | archive_candidate_superseded | older dataset/experience-library plan; phase plan starts at line 100 and overlaps the conversation experience case library track | archive after linking to current case-library/public-data reports |
| `project-plans/XINYU-EMOTION-COUNCIL-PLAN.md` | archive_candidate_superseded | design plan title at line 1; active implementation is now covered by `xinyu_emotion_council.py` and quick smoke manifest entry | keep runtime module/tests; plan can move to historical archive |
| `project-plans/XINYU-INNER-INTENTION-TO-PROACTIVE-SYSTEM-DESIGN.md` | archive_candidate_superseded | status is still `planned` at line 4; more concrete self-thought/proactive plans and runtime modules now exist | archive after linking to self-thought and proactive request loop plans |
| `project-plans/XINYU-INTRA-INSPIRED-RETRIEVAL-V2-PLAN-2026-05-15.md` | archive_candidate_superseded | status says `phase_1_3_plus_replay_implemented` at line 4 | keep canonical recall/tests; plan can archive as implemented design note |
| `project-plans/XINYU-LIFE-KERNEL-PLAN.md` | archive_candidate_superseded | old phase statuses start at lines 87 and 107; quick smoke now covers life kernel/metabolism paths | keep runtime/smoke coverage; archive plan after replacement note |
| `project-plans/XINYU-OWNER-PRIVATE-NEGATIVE-EXPRESSION-AUDIT-2026-05-14.md` | archive_candidate_historical | audit title at line 1; completed changes at line 19; verification section at line 78 | preserve as completed audit history only |
| `project-plans/XINYU-PROACTIVE-CONCRETE-REQUEST-LOOP-PLAN.md` | archive_candidate_superseded | status remains `planned` at line 4; `proactive_request_loop` is now in quick smoke manifest | keep runtime/smoke coverage; archive plan after linking current module owner |
| `project-plans/XINYU-PROACTIVITY-SCORER-SHADOW-PLAN.md` | archive_candidate_superseded | latest shadow decision section at line 272 and smoke coverage section at line 358 | keep scorer implementation/tests; archive plan as shadow-design history |
| `project-plans/XINYU-SELF-CHOICE-STORE-PLAN.md` | archive_candidate_superseded | implementation-oriented sections exist in the plan; quick smoke now covers `xinyu_self_choice_store_smoke.py` | keep store/smoke coverage; archive plan after current owner link |
| `project-plans/XINYU-SELF-THOUGHT-IDLE-LOOP-PLAN.md` | archive_candidate_superseded | status is `planned` at line 4; quick smoke now covers `self_thought_loop_smoke.py` | keep runtime/smoke coverage; archive plan after linking to current self-thought module |
| `project-plans/未完成事项-QQ接回后续接计划.md` | hold_review | file content renders as mojibake in local PowerShell, while headings indicate QQ reconnect work and recent progress | keep until encoding is normalized or a clean replacement report exists |

## Active Plan Index

Keep in active `project-plans`:

- `project-plans/XINYU-CROSS-DOMAIN-SYNAESTHESIA-PLAN-2026-05-19.md`

Hold in active `project-plans` until review:

- `project-plans/未完成事项-QQ接回后续接计划.md`

Candidates for future archive move after replacement notes:

- all rows marked `archive_candidate_superseded`
- all rows marked `archive_candidate_historical`

## Direct Effect

- The active plan surface is reduced from 17 stale candidates to 1 clear active
  plan plus 1 held encoding/boundary review item.
- Old implemented plans are no longer treated as current execution instructions.
- No files were moved or deleted in this batch.

## Next Batch

Review `learning/self_found` archive candidates at snapshot level. The goal is
to classify whole imported source snapshots, not individual copied files.
