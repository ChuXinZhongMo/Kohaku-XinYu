# Xinyu

Early-stage scaffold for Xinyu, a memory-centered emerging self built on KohakuTerrarium.

## Current State

This example currently provides:

- a controller prompt centered on continuity, memory, time, and relationship
- an output prompt for restrained, human-like outward expression
- a first-pass memory directory with core self, narrative, emotion, relationship, and context files
- specialized writer subagents for emotion, relationship, and self-narrative updates
- specialized writer subagents for emotion, relationship, self-narrative, reflection, and dream updates
- a dedicated archive writer for compression and dormancy
- a dedicated time writer for explicit reality-time anchoring
- an explicit real-time anchor file
- an explicit runtime rhythm file for maintenance cadence
- an explicit maintenance trigger plan
- a runtime plugin that injects current real time into each LLM call
- minimal reflection and dream logs

## Navigation

Use:

- `INDEX.md` for the full map
- `RUNBOOK.md` for operational use
- `smoke_run.py` for repeatable first-turn validation
- `manual_inner_sync.py` for inner-memory validation without full runtime dependence
- `manual_slow_reprocess.py` for reflection / dream / archive validation without full runtime dependence
- `VALIDATION-INDEX.md` for validation flow
- `STRUCTURE-NOTES.md` for file-layer understanding
- `CHANGELOG-XINYU.md` for evolution history
- `NAMING-CONVENTIONS.md` for id and file consistency
- `STATE-OF-XINYU.md` for current engineering status
- `EXECUTION-ORDER.md` for staged implementation flow

## Suggested Reading Order

If you are new to this scaffold, read in this order:

1. `README.md`
2. `INDEX.md`
3. `STRUCTURE-NOTES.md`
4. `RUNBOOK.md`
5. `TEST-SCENARIOS.md`
6. `WRITER-ROUTING.md`
7. `MEMORY-LINKS.md`
8. `FAILURE-MODES.md`
9. `PROMPT-TUNING.md`
10. `EXPLORATION-LOOP.md`
11. `SECOND-STAGE-ROADMAP.md`
12. `SESSION-REVIEW.md`
13. `FIRST-RUN-PLAN.md`
14. `RUNTIME-PRIORITIES.md`
15. `VALIDATION-INDEX.md`
16. `CHANGELOG-XINYU.md`
17. `NAMING-CONVENTIONS.md`
18. `STATE-OF-XINYU.md`
19. `EXECUTION-ORDER.md`
20. `OPEN-QUESTIONS.md`
21. `QUESTION-TO-VALIDATION.md`

## Current Limitations

This is still a scaffold.

Not implemented yet:

- active dream processing loop
- reflection scheduling policy
- structured forgetting/compression
- automated external exploration loop
- automatic live timestamp refresh and stronger runtime time-anchor injection
- runtime plugin behavior still needs real session validation
- structured archive/dormancy policy beyond the initial scaffold

## Local Runtime Note

On the current machine used for implementation:

- `python` exists
- `kt` is not currently available in `PATH`
- this repository copy does not include Python packaging metadata like `pyproject.toml`
- the supported runtime path is now `run_local_xinyu.py` / `run_local_xinyu.ps1`

So the shortest supported path is:

1. create a local virtual environment
2. install `requirements-minimal.txt`
3. set `XINYU_API_KEY` or create `xinyu.local.env`
4. run Xinyu through the local-source launcher

This avoids the missing package metadata problem and keeps runtime validation focused on the Xinyu scaffold itself.

## Next Steps

- add runtime writer behavior and test the routing quality
- add specialized reflection and dream writer paths
- add archive policy and compression heuristics
- add structured memory templates for additional people
- add time-aware update mechanics and live timestamp refresh

## Suggested Early Runtime Strategy

- keep the default interaction loop simple
- let the controller decide when a writer is necessary
- prefer scheduled reflection over aggressive background churn
- treat dream updates as rare and explicitly separate from factual memory

## Lightweight Validation

Before full runtime validation, you can run:

```bash
python validate_scaffold.py
```

This checks prompt references, plugin module references, memory roots, and required scaffold files without needing the full runtime environment.

For inner-framework validation without relying on the full runtime path:

```bash
python validate_inner_framework.py
python manual_inner_sync.py --user "今晚我没有想把话都说完，我只是想让你记住这种安静。"
python manual_slow_reprocess.py --show-state
```

To check whether the local machine is actually ready for deeper runtime validation:

```bash
python check_runtime_env.py
```

## Minimal Local Runtime

From the `xinyu` directory:

```powershell
.\bootstrap_minimal_env.ps1
.\run_local_xinyu.ps1 -ApiKey "your-key"
```

Repeatable smoke validation:

```bash
python smoke_run.py --message "你好，心玉。"
```

Or place your key in:

```text
xinyu.local.env
```

using the template:

```text
xinyu.local.env.example
```

Default compatible endpoint:

```text
http://llm.ciallo.date:2095/v1
```

Or directly:

```bash
python run_local_xinyu.py --mode cli
```
