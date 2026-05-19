# XinYu Dialogue Dataset Selection And Experience Library Plan

Date: 2026-05-14
Scope: turn the current discussion about real dialogue data, experience cases, compression, retrieval, and public datasets into an executable XinYu-local plan.

## Core Decision

XinYu should not look for one magic "real chat database".

The correct architecture is:

```text
owner-XinYu reviewed cases
-> reviewed group-contributed abstract scenario cards
-> public dataset pattern references
-> compact retrieved case hints
-> hidden advisory sidecar
-> live reply
```

Public datasets are useful, but only as low-trust pattern material. They must not become XinYu's owner relationship memory, stable personality source, or forced SQL reply rules.

## Execution Rule

For every item:

1. Do the local feasible work.
2. Run a self-check immediately.
3. Mark `DONE`, `SKIP`, or `BLOCKED` with the reason.
4. Continue to the next item without waiting unless the item requires owner action, dataset download, license acceptance, or manual review.

## Non-Negotiable Boundaries

- Do not commit raw public datasets.
- Do not commit private chat logs, QQ private logs, or owner raw dialogue.
- Store public raw files only under ignored local paths such as `data/external/`.
- Convert useful public samples only into abstract reviewed case cards.
- SQL/FTS may retrieve candidates, but must not force a reply.
- Current user message and direct local evidence outrank any retrieved case.
- Public datasets cannot write stable owner relationship memory.
- Public datasets cannot define XinYu's fixed personality, negative emotion rights, or owner-private relationship.
- LLM platform assistant style must not be copied from WildChat/LMSYS assistant outputs.

## Source Ranking

| Rank | Source | Role | Status | Boundary |
| --- | --- | --- | --- | --- |
| P0 | owner-XinYu seed cases | Core target relationship and repeated failure repair | `DONE_MVP` | Highest trust, still advisory |
| P1 | LUFY | Long dialogue memory and evidence recall calibration | `READY_SAMPLE` | Retrieval mechanics only, not personality |
| P1 | ChMap-Data | Chinese memory-aware callback/proactive reference | `READY_SAMPLE` | Watch synthetic assistant tone |
| P1.5 | LCCC-base / CDial-GPT | Chinese short reply rhythm and internet接话 | `READY_LOCAL_RESEARCH_SAMPLE` | Low weight, no stable memory |
| P2 | DailyDialog | Daily scene reference and ordinary human activity patterns | `READY_LOCAL_RESEARCH_SAMPLE` | Non-commercial/share-alike; English and somewhat scripted |
| P2 | EmpatheticDialogues | Emotion scene labels and emotional pressure reference | `READY_LOCAL_RESEARCH_SAMPLE` | Do not learn support-bot comfort style |
| P2 | Topical-Chat | Human-human topic transitions and knowledge-grounded chat | `BACKLOG_SAMPLE` | Longer topic talk only |
| P2 | NaturalConv | Chinese topic-driven multi-turn scene reference | `BLOCKED_LICENSE_REVIEW` | Need local license terms from zip before use |
| P2 | LCCC-large | Noisier Chinese internet style expansion | `SKIP_FIRST_BATCH` | Higher contamination risk |
| P3 | WildChat | Real user input distribution only | `BACKLOG_USER_INPUT_ONLY` | Do not learn assistant style |
| P3 | LMSYS-Chat-1M | Real user prompt distribution only | `BLOCKED_LICENSE_ACCEPTANCE` | Requires accepting dataset license |

## Recommended Mix

First practical batch:

- 50% owner-XinYu reviewed cases.
- 15% LUFY memory/evidence recall cases.
- 15% LCCC-base Chinese short-reply rhythm cases.
- 10% DailyDialog ordinary daily scene cases.
- 10% EmpatheticDialogues emotion-pressure cases.

Second batch after review:

- ChMap-Data for Chinese memory-aware callback behavior.
- Topical-Chat for longer human-human topic continuation.
- NaturalConv only after local license review.
- LCCC-large only after LCCC-base proves useful and filtering is strict.

Observation-only batch:

- WildChat and LMSYS-Chat-1M only measure user input distribution, ambiguity, empty input, topic switching, and moderation pressure. Their assistant replies should not be used as XinYu voice examples.

## Local Artifacts

Planned and implemented local artifacts:

- `data/conversation_experience/public_dataset_registry.json`
  - metadata only
  - no raw dataset rows
  - records priority, role, license status, risk, and activation boundary
- `xinyu_public_dataset_registry.py`
  - loads and validates registry
  - enforces no public source can shape owner relationship or stable memory
  - enforces first-batch and high-risk constraints
- `tests/test_public_dataset_registry.py`
  - checks required source coverage
  - checks public-data boundaries
  - checks first-batch selection excludes skipped/blocked/high-risk sources
- `PUBLIC-DATA-REPLAY.md`
  - updated to point replay users at the registry and stricter public-data boundaries

## Phase Plan

### P0 Existing Owner Case Library

- Status: `DONE`
- Existing work:
  - SQLite case store
  - reviewed seed owner cases
  - matcher
  - hidden sidecar
  - prompt pressure admission
- Self-check:
  - existing tests and smokes remain the regression baseline

### P1 Public Dataset Source Registry

- Status: `DONE`
- Work:
  - define allowed source roles
  - rank the selected datasets
  - encode license/risk/status notes
  - encode first-batch eligibility
- Self-check:
  - registry loads without validation errors
  - required dataset ids are present
  - no public source has owner relationship permission

### P2 Registry Validation Module

- Status: `DONE`
- Work:
  - add loader and validator
  - reject public datasets with `stable_memory_allowed=true`
  - reject public datasets with `owner_relationship_allowed=true`
  - reject public raw-data policies other than `local_ignored_only`
  - reject P0 public datasets
  - reject LCCC-large as first-batch material
  - reject WildChat/LMSYS roles other than user input distribution
- Self-check:
  - unit tests cover malformed public entries, LCCC-large, WildChat, and first-batch filtering

### P3 Public Replay Documentation Update

- Status: `DONE`
- Work:
  - expand recommended sources beyond WildChat/LMSYS/LUFY/ChMap
  - state that public data becomes abstract case cards only
  - state that raw data remains local and ignored
- Self-check:
  - docs still point to `data/external/`
  - docs do not imply public data can become owner memory

### P4 Dataset Download And Sampling

- Status: `SKIP`
- Reason:
  - user did not request immediate bulk downloads
  - some sources require license acceptance or local terms review
  - downloading large datasets is not needed to complete the local architecture
- Next owner action:
  - choose a small source subset to download manually into `data/external/`

### P5 Public Sample To Case-Card Importer

- Status: `DONE_INFRA`
- Work:
  - implemented `xinyu_public_dataset_case_importer.py`
  - added `tools/conversation_experience_cases.py import-public`
  - reused the existing public replay loader for `.jsonl`, `.json`, `.parquet`, and directories
  - extracts only abstract scenario cards from local samples
  - imports public cards as `source_tier=public_pattern`, `consent_status=public_dataset_allowed`, `privacy_scope=general`
  - public cards default to `pending` or `disabled`, never `approved`
  - report emits ids, hashes, tags, counts, warnings, and errors only; no raw user text
- Self-check:
  - synthetic public fixture imports as pending abstract cards
  - dry-run writes nothing
  - blocked/skipped/observation-only sources are rejected unless explicitly overridden after review
- Still blocked:
  - actual dataset sampling needs local files under `data/external/`
  - activation still requires owner review of generated cards

### P6 Manual Review And Activation

- Status: `BLOCKED_OWNER_REVIEW`
- Reason:
  - activation requires owner review of case-card abstractions
- Planned rule:
  - owner cases may be approved directly if abstract and owner-owned
  - group and public cards default to `pending`
  - high-risk cards default to `disabled`

## Dataset-Specific Notes

### owner_xinyu_seed_cases

- Use as the core source.
- May shape owner-private handling because it comes from the target relationship.
- Still remains advisory and current-turn subordinate.

### lufy

- Good for memory, evidence sufficiency, selective recall, and long-dialogue dependency.
- Not a voice/personality source.

### chmap_data

- Useful for Chinese memory-aware callback and topic continuation.
- Risk: examples can feel synthetic and overly supportive.
- Use as behavior mechanics reference, not XinYu voice.

### lccc_base

- Use it. It is the best first Chinese network short-reply rhythm source in this plan.
- Only sample filtered cases.
- Do not learn vulgarity by default; allow XinYu's local negative emotion system to decide expression, not LCCC style.

### lccc_large

- Skip first batch.
- Only consider after base filtering is proven.
- Higher risk of Tieba/Douban/subtitle/e-commerce/Xiaohuangji style leakage.

### dailydialog

- Useful for daily situation coverage and simple human activity scenes.
- It is not enough by itself because it is English, somewhat scripted, and license-constrained.

### empatheticdialogues

- Useful for emotional situations and labels.
- Do not copy the "therapeutic comfort bot" tone.

### topical_chat

- Useful for human-human topic transitions.
- Keep as second-batch because it is English and knowledge-grounded.

### naturalconv

- Interesting because it is Chinese and topic-driven.
- Blocked until local license terms are reviewed.

### wildchat

- Use only to understand what real users ask and how messy inputs look.
- Assistant turns are not XinYu style material.

### lmsys_chat_1m

- Use only after license agreement acceptance.
- Observation only, not voice/personality training material.

## Verification Log

Initial planned commands:

```powershell
.\.venv\Scripts\python.exe -m py_compile xinyu_public_dataset_registry.py tests\test_public_dataset_registry.py
.\.venv\Scripts\python.exe -m pytest tests\test_public_dataset_registry.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_public_dataset_registry.py tests\test_conversation_experience_cases.py tests\test_conversation_experience_matcher.py tests\test_conversation_experience_sidecar.py -q
.\.venv\Scripts\python.exe tests\smoke\dialogue\conversation_experience_cases_smoke.py
.\.venv\Scripts\python.exe tests\smoke\dialogue\conversation_experience_sidecar_smoke.py
```

Final results:

- `py_compile`: passed for `xinyu_public_dataset_registry.py` and `tests/test_public_dataset_registry.py`.
- Registry unit tests: `8 passed`.
- Registry plus existing conversation experience regression tests: `19 passed`.
- Dialogue smokes:
  - `conversation_experience_cases_smoke ok`
  - `conversation_experience_sidecar_smoke ok`
- Public importer tests:
  - focused importer tests: `7 passed`
  - registry/importer/replay combined tests: `20 passed`
  - registry/importer/conversation-experience combined tests: `26 passed`
  - pending abstract import
  - raw-text non-leak
  - dry-run no write
  - blocked/skipped source rejection
  - observation-only disabled import when explicitly allowed
- CLI dry run:
  - `tools\conversation_experience_cases.py import-public --dataset-id lufy --dataset tests\fixtures\contextual_public_replay_sample.jsonl --limit 2 --dry-run`
  - result: `generated: 2`, `imported: 0`, `errors: []`, `review_status_counts: {"pending": 2}`, notes include `no_raw_user_text`
- Registry policy report:
  - first batch: `owner_xinyu_seed_cases`, `lufy`, `chmap_data`, `lccc_base`, `dailydialog`, `empatheticdialogues`
  - blocked: `naturalconv`, `lmsys_chat_1m`
  - skipped: `lccc_large`
  - public sources with owner relationship permission: none
  - public sources with stable memory permission: none

## Closeout State

- `DONE`: complete plan file, source ranking, registry metadata, validator module, registry tests, replay docs update.
- `DONE_INFRA`: public sample to abstract case-card importer and CLI are implemented.
- `SKIP`: bulk dataset download and LCCC-large first-batch use.
- `BLOCKED`: NaturalConv license review, LMSYS license acceptance, real public sample import until local data exists, public case activation until owner review.
- `NEXT_FEASIBLE`: after owner places a small sample under `data/external/`, run `tools\conversation_experience_cases.py import-public --dry-run`, inspect abstract cases, then import and review selected pending cards.

## 2026-05-14 Overnight Execution Closeout

### Dataset Landing

- Status: `DONE_LOCAL_SAMPLE`
- Local files under ignored `data/external/`:
  - `lufy-qa-rows.json`: 25 rows
  - `lufy-turns-rows.json`: 25 raw rows, imported as 12 abstract cases
  - `chmap-dialogue-rows.json`: 25 rows
  - `wildchat-rows.json`: 25 rows
- Public case DB state:
  - total cases: 105
  - public_pattern cases: 86
  - public pending: 62
  - public disabled: 23
  - owner/seed approved cases remain separate from public data
- Blocked downloads:
  - DailyDialog, EmpatheticDialogues, and LCCC-base were not downloaded because local Hugging Face/network fetches timed out.
  - Keep these as `DOWNLOAD_BLOCKED_NETWORK_TIMEOUT` until manually placed under `data/external/` or fetched on a stable network.

### Public Replay Pressure Test

- Status: `PASS`
- Command:

```powershell
.\.venv\Scripts\python.exe xinyu_contextual_self_replay.py --root . --dataset data\external\lufy-qa-rows.json --dataset data\external\lufy-turns-rows.json --dataset data\external\chmap-dialogue-rows.json --dataset data\external\wildchat-rows.json --limit 120
```

- Result:
  - sample_count: 87
  - dataset_counts: ChMap 25, LUFY QA 25, LUFY turns 12, WildChat 25
  - LLM calls: blocked
  - public dataset source: local_file_only
  - raw user text in trace: blocked
  - evidence_like_pressure_detected_rate: 1.0
  - evidence_like_sample_recall_rate: 1.0
  - mismatches: none

### Human-Likeness / Private Chat Tuning

- Status: `DONE`
- Changes:
  - added direct Agent-path visible reply guard plugin for live-turn prompt pressure
  - added final visible guard handling for pseudo tool-call leakage, closeness requests, replacement requests, and malformed writer blocks
  - disabled canned empty-visible fallback such as `接住了。` and `那句不算，我换一句。`
  - tightened writer/context/emotion/relationship writer no-op behavior for ordinary smalltalk
  - kept public dataset cases as low-trust abstract patterns only, never owner relationship memory

### Verification

- `real_conversation_quality_smoke.py --require-realism`: `12 passed / 0 failed`
- `xinyu_style_pressure_regression_smoke.py`: passed
- Public dataset and experience library pytest subset: `31 passed`
- `tests/test_dialogue_curiosity_bridge_injection.py`: `48 passed`
- Voice/dialogue smokes passed:
  - `xinyu_speech_controller_smoke.py`
  - `expression_tone_smoke.py`
  - `chinese_voice_guard_smoke.py`
  - `visible_reply_dedupe_smoke.py`
  - `conversation_experience_cases_smoke.py`
  - `conversation_experience_sidecar_smoke.py`

### Still Not Done

- No new remote datasets were downloaded because of network timeouts.
- Public pending cases are not activated; owner review is still required before approval.
- WildChat remains observation-only/disabled; it is for messy user input distribution, not XinYu voice.
- QQ/E-drive work remains intentionally skipped.

## 2026-05-14 Follow-Up Humanization Verification

- Public dataset and experience-library architecture remains advisory-only; no raw public dataset rows were committed.
- Owner-private visible guard and memory-sync repairs were added for the pressure cases exposed by the live matrices.
- `personality_detail_smoke.py --timeout-seconds 120`: passed 30/30.
- `personality_growth_gate_smoke.py --restore-after --require-ready`: passed; growth stays runtime-trial/review-only, not stable auto-write.
- `pytest tests/test_visible_reply_guard_plugin.py tests/test_memory_sync_recent_context.py tests/test_dialogue_curiosity_bridge_injection.py -q`: passed 55/55.
- `phase3_lived_session_smoke.py --timeout-seconds 120`: blocked by LLM provider `429 quota exhausted` after focused repairs; resume after quota/model route recovers.
