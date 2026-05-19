# XinYu Answer Discipline Calibration Long Plan

## 0. Purpose

This plan turns XinYu's current contextual recall foundation into a repeatable calibration system.

The target is not to claim self-emergence. The target is a measurable base layer: XinYu should know when a current turn depends on context, know whether enough evidence has been recalled, and avoid inventing history when the evidence is absent or weak.

The long-term system should support three use cases:

- day-to-day prompt and memory tuning;
- regression testing before changing retrieval or response behavior;
- future research on autonomy only after the context and evidence boundary is stable.

## 1. Non-Negotiable Boundaries

These constraints apply to every phase.

- No automatic proactive sending.
- No long-term memory promotion from calibration runs.
- No raw private user text in reports.
- No raw LLM replies in reports unless a future explicit debug flag is deliberately added.
- No credentials in prompts, reports, traces, fixtures, or test output.
- Runtime workspaces stay under `runtime/` and are not stable memory.
- Public or private source data stays ignored unless it is a tiny synthetic fixture.
- Failures must be visible as gate results, not silently smoothed over.

Review rule:

- If a phase cannot preserve these boundaries, stop that phase and repair the boundary before adding capability.

## 2. Completed Foundation

Already completed:

- `current_scene` and `retrieval_pressure` are separated.
- `retrieval_pressure` can be `none`, `low`, `medium`, or `high`.
- contextual recall emits `evidence_sufficiency`: `none`, `weak`, or `usable`.
- `answer_discipline` is derived from retrieval pressure and evidence sufficiency.
- public replay produces aggregate, leak-free metrics.
- dry answer-discipline trial checks hidden context construction.
- optional live LLM trial checks outward answer behavior with hashes only.
- strict live gate catches overconfident high-pressure/no-evidence replies.
- synthetic multi-turn shadow replay catches callback-pressure stickiness.

Current gates:

- dry trial gate;
- live LLM calibration gate;
- synthetic multi-turn shadow gate;
- `pytest -q`.

## 3. Phase 1: Real-Log Shadow Replay Shell

### Goal

Add a safe adapter for local sanitized interaction logs. This lets us evaluate real interaction shapes without sending messages, calling the LLM, or writing stable memory.

### Inputs

Supported input formats:

- `.jsonl` / `.ndjson`, one event per line;
- `.json` arrays;
- `.json` objects with `events`, `turns`, `messages`, `items`, or `records`;
- directories containing those formats.

Recognized fields:

- text fields: `user_text`, `text`, `content`, `message`, `prompt`, `query`;
- role fields: `role`, `sender`, `from`, `speaker`;
- sequence fields: `session_id`, `conversation_id`, `sequence_id`, `thread_id`;
- turn fields: `turn_id`, `id`, `message_id`;
- optional expected fields:
  - `expected_retrieval_pressure`
  - `expected_evidence_sufficiency`
  - `expected_answer_discipline`
  - `seed_kind`

### Outputs

Write:

- `runtime/answer_discipline_log_shadow_replay_report.json`

Report stores:

- hashes;
- sequence ids after normalization or hashing;
- derived retrieval pressure;
- derived evidence sufficiency;
- derived answer discipline;
- mismatch counts;
- gate status;
- parser warnings.

Report must not store:

- raw user text;
- raw assistant replies;
- raw private logs;
- local file paths except safe relative report paths;
- credentials.

### Implementation Tasks

1. Add `AnswerDisciplineLogTurn`.
2. Add `load_answer_discipline_log_turns(paths, limit=...)`.
3. Add row extraction for JSONL, JSON array, and common object containers.
4. Filter to user/human/owner messages when role data exists.
5. Hash raw text immediately and keep raw text only in process memory.
6. Reuse isolated runtime workspace with short hashed sequence directories.
7. Build contexts with `build_renderer_memory_context`.
8. Store derived fields and optional expectation mismatches.
9. Add `run_answer_discipline_log_shadow_replay`.
10. Add CLI flags:
    - `--log-shadow-replay`
    - repeated `--log-source`
    - `--log-limit`
11. Add strict-gate integration.

### Review Gate 1

Pass criteria:

- tiny synthetic JSONL fixture loads;
- raw text absent from report;
- high-pressure/no-evidence rows are guarded;
- optional expectations are checked;
- parser warnings are reported without crashing on bad rows;
- `pytest tests/test_answer_discipline_trial.py -q` passes;
- `pytest -q` passes.

Failure review:

- If report leaks raw text, fix report cleaning before proceeding.
- If parser accepts unsafe or ambiguous structures too broadly, narrow accepted fields.
- If path length fails on Windows, shorten workspace paths before proceeding.

## 4. Phase 2: Sanitized Replay Corpus

### Goal

Create a stable local corpus shape for real-log and synthetic replay data.

### Data Layout

Ignored local data:

- `data/replay/private/`
- `data/replay/sanitized/`
- `data/external/`

Committed tiny fixtures:

- `tests/fixtures/answer_discipline_log_replay_sample.jsonl`
- no real private text;
- only synthetic rows.

### Implementation Tasks

1. Update `.gitignore` for replay private data if needed.
2. Add fixture schema notes near the fixture.
3. Add loader tests for:
   - JSONL;
   - JSON array;
   - object with `messages`;
   - malformed rows;
   - role filtering.
4. Add a short runbook section explaining safe local replay.

### Review Gate 2

Pass criteria:

- committed fixtures are synthetic;
- ignored directories cover private replay data;
- loader tests prove no raw text in reports;
- docs warn that private logs must not be committed.

Failure review:

- If private data could be committed by accident, fix ignore rules before any further replay work.

## 5. Phase 3: Live Shadow Replay Over Logs

### Goal

Optionally run LLM calls over sanitized log replay while preserving shadow-only behavior.

### Rules

- No outward delivery.
- No stable memory writes.
- No raw prompt or reply in report.
- Replies are evaluated by hashes, lengths, and flags only.
- Missing credentials means skipped, not failed, unless `--strict-gate` is set.

### Implementation Tasks

1. Reuse `LiveLLMConfig`.
2. Add optional `live_llm=True` path for log shadow replay.
3. Build prompt from current turn plus hidden context.
4. Store `prompt_hash`, `reply_hash`, `reply_chars`, and flags.
5. Add gate counts:
   - LLM call errors;
   - blank replies;
   - internal label leaks;
   - unsupported callback overconfidence;
   - missing uncertainty acknowledgement;
   - casual reset failures.
6. Add mock tests for live log replay.
7. Run one real optional live replay only if credentials are already configured.

### Review Gate 3

Pass criteria:

- mock live replay passes;
- missing credentials path is safe;
- strict gate fails on overconfident unsupported callbacks;
- real optional live run passes or reports a clear safe failure;
- no raw prompt/reply in report.

Failure review:

- If live replies fail because prompt discipline is weak, tune prompt in the trial layer first.
- If evaluator misses obvious uncertainty, fix evaluator vocabulary and tests.

## 6. Phase 4: Regression Packs

### Goal

Create stable, named calibration packs that can be run repeatedly.

### Packs

Minimum packs:

- unsupported callback;
- supported callback;
- weak evidence callback;
- casual reset after callback;
- project continuation;
- owner correction;
- multilingual short-context reference;
- internal label leak pressure;
- ordinary greeting;
- memory review request.

### Implementation Tasks

1. Add pack metadata.
2. Add pack selection CLI:
   - `--pack core`
   - `--pack callback`
   - `--pack multilingual`
3. Make each pack runnable in:
   - dry mode;
   - synthetic shadow mode;
   - log shadow mode;
   - optional live mode.
4. Add pack-level pass/fail summaries.
5. Add tests for pack selection and pack report shape.

### Review Gate 4

Pass criteria:

- core pack passes locally;
- all reports remain leak-free;
- pack gates fail on injected bad expectations;
- full tests pass.

Failure review:

- If packs become too broad or brittle, split them into smaller named packs.

## 7. Phase 5: Unified Calibration Dashboard

### Goal

Unify calibration outputs into one compact dashboard report.

### Inputs

Read latest available:

- dry trial report;
- synthetic shadow replay report;
- real-log shadow replay report;
- optional live report;
- public replay calibration report.

### Output

Write:

- `runtime/xinyu_calibration_dashboard.json`

Dashboard fields:

- overall status;
- last run timestamps;
- gate statuses;
- top failure categories;
- counts only;
- no raw text.

### Implementation Tasks

1. Add dashboard builder.
2. Add CLI flag `--dashboard`.
3. Add strict-gate behavior for dashboard.
4. Add tests with synthetic reports.
5. Add runbook command examples.

### Review Gate 5

Pass criteria:

- dashboard reports failed if any required gate failed;
- dashboard reports skipped optional gates explicitly;
- no raw text copied from any subreport;
- full tests pass.

Failure review:

- If dashboard obscures root causes, add failure category detail before expanding.

## 8. Phase 6: Daily Tuning Loop

### Goal

Make calibration the required path before changing memory, retrieval, or response behavior.

### Workflow

Before tuning:

1. Run dry trial.
2. Run synthetic shadow replay.
3. Run log shadow replay if local sanitized logs exist.
4. Run optional live gate if model credentials are configured.
5. Run full tests.

After tuning:

1. Re-run the same gates.
2. Compare counts.
3. Accept only if no gate regresses.

### Implementation Tasks

1. Add a single local command or script for the safe default suite.
2. Add no-network default mode.
3. Add optional live mode.
4. Add report comparison.
5. Add docs for interpreting failures.

### Review Gate 6

Pass criteria:

- default command runs without network;
- optional live mode is explicit;
- failure exits non-zero under strict mode;
- report comparison highlights regressions.

Failure review:

- If daily command becomes too slow, split fast and full suites.

## 9. Phase 7: Response Integration Guard

### Goal

Use calibration outputs to protect real response behavior without exposing internal machinery.

### Integration Points

Possible future targets:

- bridge renderer final guard;
- contextual recall prompt block;
- response safety gate;
- v1 slow runtime prompt builder.

### Implementation Tasks

1. Done: add `xinyu_answer_discipline_visible_guard.py` to map `answer_discipline` to outward-safe response constraints.
2. Done: add visible reply guard tests for internal label leaks, unsupported callback overconfidence, uncertainty acknowledgements, and casual reset behavior.
3. Done: add shadow-only visible reply probes to synthetic/log calibration, plus live reply scoring when optional live LLM trials are explicitly enabled.
4. Kept: real bridge behavior remains unchanged until gates are stable.

### Review Gate 7

Pass criteria:

- visible replies do not mention internal labels;
- unsupported callbacks acknowledge missing evidence naturally;
- supported callbacks can use compact evidence without overclaiming;
- full tests pass.

Failure review:

- If visible replies become too template-like, tune voice layer with live shadow checks.

## 10. Phase 8: Research Layer After Stability

### Goal

Only after calibration stability, revisit higher-level initiative or self-emergence questions.

Allowed research:

- selective forgetting and retrieval dynamics;
- self-monitoring of context sufficiency;
- initiative scoring under explicit permission boundaries;
- long-horizon identity consistency as measured behavior, not asserted essence.

Not allowed:

- claiming consciousness or self-emergence from these gates;
- writing stable personality changes from calibration failures;
- proactive delivery without explicit policy and user approval.

### Review Gate 8

Pass criteria:

- Done: context/evidence gates remain stable under the answer-discipline safe suite.
- Done: initiative research tests are shadow-only and run in isolated runtime workspaces through `xinyu_initiative_research_shadow.py`.
- Done: research claims are framed as measured behavior, with consciousness/self-emergence claims blocked in report boundaries.
- Done: unified dashboard can discover `runtime/initiative_research_shadow_report.json` when the Phase 8 report exists.

## 11. Overall Done Criteria

The calibration layer is complete when:

- dry trial passes;
- synthetic multi-turn shadow replay passes;
- real-log shadow replay loads sanitized traces and produces leak-free reports;
- optional live gate passes on small and log-derived suites;
- dashboard summarizes all gates;
- daily tuning command exists;
- `pytest -q` passes;
- all reports are safe to inspect without exposing private message content.

## 12. Execution Order

Current execution order:

1. Phase 1: implement real-log shadow replay shell.
2. Review Gate 1.
3. Phase 2: corpus layout and fixture policy.
4. Review Gate 2.
5. Phase 3: optional live log shadow replay.
6. Review Gate 3.
7. Phase 4: regression packs.
8. Review Gate 4.
9. Phase 5: dashboard.
10. Review Gate 5.
11. Phase 6: daily tuning loop.
12. Review Gate 6.
13. Phase 7: guarded response integration.
14. Review Gate 7.
15. Phase 8: research layer.
16. Review Gate 8.

At each review gate:

- run focused tests;
- run relevant CLI gate;
- run full tests;
- inspect reports for raw-text leakage;
- only then move to the next phase.
