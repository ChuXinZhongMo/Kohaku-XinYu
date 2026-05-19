# Public Data Replay

This is the local calibration path for running open dialogue data through XinYu's contextual self loop.

The replay does not call an LLM, does not send messages, and does not write raw user text to replay traces. It normalizes public records into user-turn samples, runs contextual scene selection and contextual recall, then writes observable calibration summaries.

## Recommended Sources

- `cases/conversation/public_dataset_registry.json` is the target source registry for priority, license status, trust role, and first-batch eligibility; the loader still falls back to legacy `data/conversation_experience/public_dataset_registry.json`.
- `RuiSumida/LUFY`: long-dialogue memory, selective forgetting, recall evidence.
- `FrontierLab/ChMap-Data`: Chinese memory-aware proactive dialogue.
- `thu-coai/CDial-GPT` / LCCC-base: Chinese internet short-reply rhythm, low-weight and local-research only.
- `DailyDialog`: daily scene coverage; non-commercial/share-alike terms.
- `facebook/empathetic_dialogues`: emotion scene reference; non-commercial terms.
- `alexa/Topical-Chat`: human-human topic transition reference.
- `NaturalConv`: Chinese topic-driven multi-turn conversation; blocked until local license terms are reviewed.
- `allenai/WildChat`: real user input distribution only, not assistant style.
- `lmsys/lmsys-chat-1m`: broad real user prompt distribution only; blocked until the dataset license agreement is accepted.
- `anthropics/hh-rlhf`: optional boundary calibration backlog, not XinYu voice material.

Keep raw public datasets under the dataset library, with legacy fallback still supported:

```text
library/datasets/
data/external/
```

Do not commit the original dataset files. Public examples should be converted only into abstract reviewed case cards; they must not become owner relationship memory, stable personality memory, or forced SQL reply rules.

## Supported Local Formats

- `.jsonl` / `.ndjson`
- `.json`
- `.parquet` when `pyarrow` is installed
- directories containing those files

The adapter recognizes common Hugging Face shapes:

- `conversation`, `conversations`, `messages`, `dialogue`, `turns`, `history`
- turn fields such as `role`, `from`, `speaker`, `content`, `value`, `text`
- direct text fields such as `prompt`, `instruction`, `query`, `question`, `input`, `user_text`

## Run

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe xinyu_contextual_self_replay.py `
  --root . `
  --dataset lufy `
  --dataset-name lufy `
  --limit 100
```

Optional initiative dry run:

```powershell
.\.venv\Scripts\python.exe xinyu_contextual_self_replay.py `
  --root . `
  --dataset chmap `
  --dataset-name chmapdata `
  --limit 200 `
  --run-initiative
```

`--run-initiative` still uses dry-run delivery only.

## Import Abstract Public Case Cards

After a small public sample is placed under `library/datasets/` or legacy `data/external/`, convert it into abstract, pending conversation-experience cards with:

```powershell
.\.venv\Scripts\python.exe tools\conversation_experience_cases.py import-public `
  --dataset-id lufy `
  --dataset lufy `
  --limit 50
```

Use `--dry-run` first when inspecting a new source. The import report contains case ids, hashes, tags, and counts only; it does not echo raw user text. Public cards default to `pending` or `disabled` according to the registry and require manual review before matching.

## Outputs

- `runtime/contextual_self_replay_trace.jsonl`
- `runtime/contextual_self_replay_summary.json`
- `memory/context/contextual_self_replay_state.md`
- normal contextual self and recall traces:
  - `runtime/contextual_self_loop_trace.jsonl`
  - `runtime/contextual_recall_trace.jsonl`
  - `runtime/contextual_self_observatory.json`

Use `scene_match_rate` only when records include `expected_scene`. Public datasets usually do not, so the main early signals are scene distribution, recall sparsity, and initiative gate posture.

Additional calibration signals:

- `retrieval_pressure_counts`: how often a turn asks for none/low/medium/high contextual retrieval without changing the scene label.
- `high_pressure_recall_admitted_count`: how much compact recall was admitted for high-pressure turns.
- `evidence_like_sample_count`: weakly labeled samples with evidence metadata such as `evidence_turn_ids`.
- `evidence_like_sample_recall_rate`: share of evidence-like samples that admitted at least one recall item.
- `evidence_like_pressure_detected_rate`: share of evidence-like samples whose hidden retrieval pressure reached medium or high.
- `high_pressure_no_evidence_count`: high retrieval pressure turns with no admitted recall evidence.
- `high_pressure_weak_evidence_count`: high retrieval pressure turns with some recall, but not enough to support confident history-dependent answering.
- `high_pressure_usable_evidence_count`: high retrieval pressure turns with enough compact recall to answer from evidence without overclaiming.

For LUFY-style rows, `evidence_turn_ids` is treated as a weak signal that the question depends on prior dialogue. It does not force `current_scene` to `memory_review`; it only helps measure whether hidden retrieval pressure is being detected and served.

`evidence_sufficiency` is written by the contextual recall layer as `none`, `weak`, or `usable`. It drives hidden answer discipline only: high pressure with none/weak evidence should avoid inventing missing history, while high pressure with usable evidence can answer from recalled previews.

## Answer Discipline Log Shadow Replay

The answer-discipline log shadow replay is for local sanitized interaction traces. It does not call an LLM, does not send messages, and does not write stable memory. Reports store hashes, derived classifications, expectations, and gate counts only.

Ignored local directories:

```text
data/replay/private/
data/replay/sanitized/
```

Committed fixtures must stay tiny and synthetic. Use:

```text
tests/fixtures/answer_discipline_log_replay_sample.jsonl
```

Supported fields:

- text: `user_text`, `text`, `content`, `message`, `prompt`, `query`
- role: `role`, `sender`, `from`, `speaker`
- sequence: `session_id`, `conversation_id`, `sequence_id`, `thread_id`
- optional expectations:
  - `expected_retrieval_pressure`
  - `expected_evidence_sufficiency`
  - `expected_answer_discipline`
  - `seed_kind`

Run:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe xinyu_answer_discipline_trial.py `
  --root . `
  --run-id local-log-shadow `
  --log-shadow-replay `
  --log-source .\tests\fixtures\answer_discipline_log_replay_sample.jsonl `
  --strict-gate
```

Output:

- `runtime/answer_discipline_log_shadow_replay_report.json`

Gate signals:

- `turns_loaded`
- `optional_expectations_match`
- `high_no_evidence_turns_guarded`
- `ordinary_turns_do_not_inherit_callback_pressure`

## Latest Local Run

2026-05-14 local public replay used only ignored files under `data/external/`:

- `lufy-qa-rows.json`
- `lufy-turns-rows.json`
- `chmap-dialogue-rows.json`
- `wildchat-rows.json`

Result summary:

- sample_count: 87
- dataset_counts: ChMap 25, LUFY QA 25, LUFY turns 12, WildChat 25
- LLM calls: blocked
- source mode: local_file_only
- raw user text in trace: blocked
- evidence_like_pressure_detected_rate: 1.0
- evidence_like_sample_recall_rate: 1.0
- mismatches: none

Conversation-experience DB after import:

- total cases: 105
- public_pattern cases: 86
- public pending: 62
- public disabled: 23

Remote downloads for DailyDialog, EmpatheticDialogues, and LCCC-base are still blocked by network timeout. Keep those sources in the plan, but do not pretend they have been landed.
