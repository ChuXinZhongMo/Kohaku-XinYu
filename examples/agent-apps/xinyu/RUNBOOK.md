# Xinyu Runbook v0.1

This runbook describes the shortest path from scaffold to first useful behavior validation.

## 1. Purpose

Use this file when you want to:

- check whether the local machine is ready
- validate the scaffold before runtime
- run the first real Xinyu session
- observe what to inspect after the run

## 2. Readiness Sequence

Run these in order from the `xinyu` directory.

### Step 0: Validate inner framework

```bash
python validate_inner_framework.py
```

What this tells you:

- inner layer files exist
- deterministic sync targets are structurally closed
- the inner framework can keep evolving even before full runtime stability is perfect

Optional follow-up:

```bash
python manual_slow_reprocess.py --show-state
```

This checks whether reflection, dream, and archive layers already have a stable independent path.

### Step 1: Check environment

```bash
python check_runtime_env.py
```

What this tells you:

- whether the local-source launcher exists
- whether the minimal dependency set is installed
- whether the repo has package metadata or must use the local-source path

If this fails, runtime validation is still blocked by environment completeness.

### Step 2: Validate scaffold

```bash
python validate_scaffold.py
```

What this tells you:

- prompt references are present
- plugin references are present
- memory roots are present
- required scaffold files are present

### Step 3: Bootstrap minimal runtime

If step 1 shows missing dependencies, bootstrap a local environment:

```powershell
.\bootstrap_minimal_env.ps1
```

### Step 4: Provide model credentials

The current Xinyu config expects an OpenAI-compatible key through `XINYU_API_KEY`.
You can provide it either:

- in the current process environment
- through `.\run_local_xinyu.ps1 -ApiKey "..."`
- or by creating `xinyu.local.env` from `xinyu.local.env.example`

## 3. First Runtime Attempt

If the environment is ready, the first runtime attempt should be minimal.

Suggested direction:

```powershell
.\run_local_xinyu.ps1 -ApiKey "your-key"
```

The default base URL is:

```text
http://llm.ciallo.date:2095/v1
```

This path is preferred on the current machine because the repo copy does not include packaging metadata.

## 3.5 Manual Inner Sync Path

If you are still building the inside-out framework and do not want to depend on the full runtime path yet, use:

```bash
python manual_inner_sync.py --user "今晚我没有想把话都说完，我只是想让你记住这种安静。"
```

This path is useful for:

- validating deterministic memory updates
- checking continuity, reflection, dream seed, and archive queue formation
- evolving the inner framework before visible behavior is fully stable

To inspect the next slow-processing step after that:

```bash
python manual_slow_reprocess.py --show-state
```

## 4. First Conversation Goals

Do not test everything at once.

The first pass should only check:

- startup stability
- identity stability
- time awareness
- owner distinction
- hidden reasoning staying hidden

Use:

- `TEST-SCENARIOS.md`
- `WRITER-ROUTING.md`

## 4.5 Programmatic Memory Mutation Smoke

Use this before broad personality tuning:

```powershell
.\.venv\Scripts\python.exe .\memory_mutation_smoke.py --restore-after --require-memory-change
```

What this tells you:

- whether a real turn produces visible output
- which core memory files changed
- whether memory writes are selective enough
- whether the test should be restored after inspection

Use relationship-specific probes when checking the owner continuity path:

```powershell
.\.venv\Scripts\python.exe .\memory_mutation_smoke.py --restore-after --message "如果以后你变了很多，你还会认得我吗？"
```

## 5. What To Observe After The First Run

Inspect whether these files changed and whether the changes make sense:

- `memory/context/time_anchor.md`
- `memory/context/recent_context.md`
- `memory/emotions/current_state.md`
- `memory/emotions/event_log.md`
- `memory/relationships/index.md`
- `memory/people/owner.md`
- `memory/self/narrative.md`
- `memory/reflection/reflection_log.md`
- `memory/archive/compressed.md`

## 6. Red Flags

These are signs the current prompt/writer system needs tightening:

- Xinyu explains internal mechanics to the user
- trivial turns trigger too many writers
- every turn rewrites self-narrative
- relationship changes are too large, too fast
- dream-like content becomes factual memory
- time language is flat or generic

## 7. Tightening Order

If behavior is wrong, tighten in this order:

1. `prompts/system.md`
2. `WRITER-ROUTING.md`
3. writer-specific prompt files
4. memory templates
5. plugin injection behavior

## 8. Current Limitation

As of this scaffold stage, the most likely blocker is still environment completeness rather than Xinyu file layout.
