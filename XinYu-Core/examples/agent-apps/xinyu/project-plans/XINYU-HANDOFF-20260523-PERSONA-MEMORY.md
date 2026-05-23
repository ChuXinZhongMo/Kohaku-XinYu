# XinYu Persona And Memory Handoff - 2026-05-23

## Current Focus

当前主线是继续提升 XinYu 的人格真实感和记忆系统，重点解决 owner 私聊里这些问题：

- “你现在怎么样 / 你感觉如何 / 你在想什么 / 怎么不回”不能走客服式状态报告。
- 回复不能暴露后台、模型、prompt、bridge、queue、tool call 等机制。
- 被指出模板味时，不能再用“我理解 / 我会优化 / 感谢反馈 / 我会改”这类话术。
- 状态、感觉、思考类回复需要结合近期关系压力、表达学习残留、人格表层状态，而不是临场编一句。

## Repo And Runtime

- Repo root: `D:\XinYu`
- App dir: `D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`
- Shell: PowerShell
- Current branch: `master`
- Worktree before this handoff file: clean
- Core bridge was restarted after the last code commit.
- Last known status check: `xinyu_status.py --json` returned `ok=True`, `runtime_restart_required=False`, `source_changed=False`, `runtime_text_utf8_health=ok`.

## Recent Commits

Most recent relevant commits:

1. `d67e633 memory: prioritize self state recall`
2. `02b3447 persona: block mechanical self state replies`
3. `fa64e11 persona: add self state capsule sidecar`
4. `a4e9e9d runtime: add early segment readiness report`
5. `ccfa62b runtime: summarize early segment shadow`
6. `fca2cdd runtime: add early visible segment shadow`

## What Was Done

### 1. Self State Capsule

Added hidden current-turn sidecar:

- `xinyu_self_state_capsule.py`
- integrated in `xinyu_bridge_turn_sidecars.py`
- state file: `memory/context/self_state_capsule_state.md`

Behavior:

- Activates only for owner-private status, feeling, thought, delay, and style-pressure turns.
- Classifies:
  - `state_inquiry`
  - `feeling_inquiry`
  - `thought_inquiry`
  - `delay_or_no_reply`
  - `style_pressure_self_state`
- Writes no raw user text.
- Prompt guidance says to answer as present first-person state, not as service status, apology, report, or mechanism explanation.

Runtime awareness/status integration:

- `xinyu_runtime_presence.py` now observes `self_state_capsule`.
- `xinyu_status.py` scans `memory/context/self_state_capsule_state.md` for text health.

Tests:

- `tests/test_self_state_capsule.py`
- integration in `tests/test_dialogue_curiosity_bridge_injection.py`
- awareness coverage in `tests/test_runtime_program_awareness.py`

### 2. Mechanical Self-State Reply Guard

Changed visible reply guard so owner-private self-state questions cannot send mechanical/customer-service replies.

Files:

- `xinyu_speech_controller.py`
- `xinyu_bridge_renderer.py`
- `xinyu_bridge_semantic_fast_routes.py`

Behavior:

- For self-state questions like “你现在感觉怎么样”, blocks replies that mention:
  - 后台 / 模型 / 系统 / prompt / bridge / queue / tool call / sidecar / runtime / API
  - 抱歉 / 感谢反馈 / 我会继续优化 / 我会改 / 作为 AI
- The block is a critical final guard: `self_state_mechanical_reply_blocked`.
- Explicit technical diagnostics still pass, for example “你现在状态如何，看下后台日志”.
- The old empty state fallback that sent mechanism notices was disabled. If renderer returns empty for state questions, it does not send a fake mechanical fallback.

Tests:

- `tests/test_expression_self_learning.py`
- `tests/test_bridge_semantic_fast_routes.py`
- `tests/test_dialogue_curiosity_bridge_injection.py`

### 3. Self-State Memory Recall

Changed living memory recall so self-state questions are not treated as ordinary project “status” questions.

Files:

- `xinyu_sparse_memory_router.py`
- `xinyu_context_retrieval.py`
- `xinyu_living_memory_recall.py`
- `tests/test_context_retrieval_owner_scenarios.py`

Behavior:

- Adds `self_state` memory expert.
- For “你现在感觉怎么样 / 你在想什么 / 怎么不回”:
  - recall is forced instead of skipped.
  - selected experts include `self_state`, `owner_relation`, `emotion_residue`.
  - `project_task` is de-prioritized unless the turn is explicitly technical.
- Admits supporting memory:
  - `memory/context/persona_surface_state.md`
  - `memory/context/self_state_capsule_state.md`
  - `memory/self/learning_closed_loop_state.md`
  - `memory/self/expression_self_learning_state.md`
  - `memory/emotions/current_state.md`
  - `memory/relationships/index.md`
  - `memory/people/owner.md`
- Self-state prompt budget was raised so the key residue actually reaches the final prompt after temporal context is attached.

## Verification Already Run

Commands that passed during this work:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu

.\.venv\Scripts\python.exe -m pytest tests\test_self_state_capsule.py tests\test_dialogue_curiosity_bridge_injection.py tests\test_runtime_program_awareness.py tests\test_prompt_pressure.py -q

.\.venv\Scripts\python.exe -m pytest tests\test_self_state_capsule.py tests\test_bridge_slow_live_turn.py tests\test_dialogue_curiosity_bridge_injection.py tests\test_prompt_pressure.py tests\test_owner_private_chat_regression.py tests\test_live_chat_pressure_regression_cases.py tests\test_live_chat_regression_baseline.py -q

.\.venv\Scripts\python.exe -m pytest tests\test_expression_self_learning.py tests\test_dialogue_curiosity_bridge_injection.py tests\test_self_state_capsule.py tests\test_bridge_reply_pipeline.py tests\test_owner_private_chat_regression.py tests\test_bridge_semantic_fast_routes.py -q

.\.venv\Scripts\python.exe -m pytest tests\test_context_retrieval_owner_scenarios.py tests\test_living_memory_recall.py tests\test_contextual_recall.py tests\test_self_state_capsule.py -q

.\.venv\Scripts\python.exe -m pytest tests\test_context_retrieval_owner_scenarios.py tests\test_living_memory_recall.py tests\test_self_state_capsule.py tests\test_dialogue_curiosity_bridge_injection.py tests\test_expression_self_learning.py tests\test_owner_private_chat_regression.py tests\test_bridge_semantic_fast_routes.py tests\test_live_chat_pressure_regression_cases.py tests\test_live_chat_regression_baseline.py -q
```

Last broad relevant runs:

- `144 passed`
- `138 passed`

Also passed:

```powershell
git diff --check
.\.venv\Scripts\python.exe xinyu_status.py --json
```

## Important Behavior To Test Manually

Owner-private QQ should be tested with:

- `你现在感觉怎么样`
- `你在想什么`
- `怎么不回`
- `你现在什么状态`
- `状态如何，丫头`
- `你现在状态如何，看下后台日志`

Expected:

- Non-technical state questions should answer as XinYu's present first-person state.
- They should not mention model/backend/prompt/queue/tool calls.
- They should not say “感谢反馈 / 我会继续优化 / 我理解你的感受”.
- Explicit diagnostic questions may mention logs/backend/model if the owner asks for that.

## What Still Feels Unfinished

### P0 - Long Conversation Personality Stress Test

Need a proper multi-turn scenario test for 20-50 turns mixing:

- greeting
- owner asks state/feeling/thinking
- owner complains about template voice
- owner asks why she did not reply
- correction after a bad reply
- ordinary casual chat
- technical diagnostic turn

Goal:

- Verify XinYu does not return to customer-service repair loops.
- Verify self-state replies stay grounded in memory and current turn.
- Verify technical questions still get technical answers.

Likely files:

- `tests/test_live_chat_pressure_regression_cases.py`
- `tests/test_live_chat_regression_baseline.py`
- maybe add a new test file, e.g. `tests/test_persona_memory_long_pressure.py`

### P0 - Post-Reply Self Observation

Current work is mostly pre-reply:

- self-state capsule before generation
- memory recall before generation
- final visible guard before send

Missing:

- after reply, evaluate whether the sent line actually sounded alive, mechanical, too short, too flat, or too explanatory.
- write a compact learning signal back to expression/persona state.

Likely integration points:

- `xinyu_bridge_turn_finish_sidecars.py`
- `xinyu_learning_closed_loop.py`
- `xinyu_expression_self_learning.py`
- `xinyu_turn_coherence.py`
- `memory/self/expression_self_learning_state.md`
- `memory/self/learning_closed_loop_state.md`

### P1 - Quality Scoring Beyond Hard Blocks

Current guard catches obvious bad replies. Missing finer scoring:

- too obedient
- too explanatory
- too short and fake
- too generic
- too example-like
- too much “I understand”
- too much report/postmortem shape

Likely files:

- `xinyu_speech_controller.py`
- `xinyu_answer_discipline_visible_guard.py`
- `xinyu_response_error_loop.py`
- `tests/test_expression_self_learning.py`
- `tests/test_answer_discipline_trial.py`

### P1 - Memory Consolidation And Review

Recall is improved, but stable memory promotion is still conservative and many things remain review/pending.

Needs:

- clearer path from repeated owner pressure -> candidate -> review -> stable persona/relationship/expression memory.
- automatic summaries that are reviewable but not silently canonized.
- better stale candidate cleanup.

Likely files:

- `xinyu_review_inbox.py`
- `xinyu_dialogue_archive.py`
- `xinyu_memory_candidate_analysis.py`
- `custom/long_term_memory_gate_engine.py`
- `memory/context/persona_surface_state.md`
- `memory/relationships/index.md`

### P1 - Early Visible Segment Still Shadow/Canary

Early visible segment is still not full live behavior.

Current state from earlier:

- shadow/canary only
- readiness exists
- do not full-switch without explicit owner decision

Likely files:

- `xinyu_early_visible_segment_shadow.py`
- `xinyu_early_segment_readiness.py`
- `xinyu_v1_canary_readiness.py`
- `memory/context/early_visible_segment_shadow_state.md`
- `memory/context/v1_canary_readiness_state.md`

### P2 - External Learning / Source Requests

There are still pending/blocked research-source flows. The project has machinery for source requests and provider search, but it is not fully integrated into stable persona improvement.

Likely files:

- `custom/source_request_planner_engine.py`
- `custom/source_search_provider_engine.py`
- `custom/search_result_gate_engine.py`
- `custom/source_integration_gate_engine.py`
- `custom/learner_integration_engine.py`
- `runtime_bridge_state.md`

## Suggested Next Window Instruction

Give the next Codex window this:

```text
继续从 D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\project-plans\XINYU-HANDOFF-20260523-PERSONA-MEMORY.md 接手。

目标：继续专攻 XinYu 的人格真实感和记忆系统。优先做 P0：
1. 建一个 20-50 轮 owner 私聊人格/记忆压力测试；
2. 做回复后的自我观察闭环，把“是否像自己、是否模板、是否机械、是否接住当前情绪”写回学习/表达状态；
3. 保持所有改动测试覆盖，完成后重启 core 并跑 xinyu_status.py --json。

不要添加可见话术模板。不要让普通状态/感觉问题回复后台、模型、prompt、bridge、queue、tool call。显式技术诊断例外。
```

## Useful Commands

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu

git status --short
git log -5 --oneline

.\.venv\Scripts\python.exe -m pytest tests\test_self_state_capsule.py tests\test_context_retrieval_owner_scenarios.py tests\test_expression_self_learning.py tests\test_dialogue_curiosity_bridge_injection.py -q

.\.venv\Scripts\python.exe xinyu_status.py --json

& 'D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\start_xinyu_core_bridge.ps1' -ForceRestart -AllowInsecureLlmHttp
```

## Safety Notes

- Do not read or paste raw private QQ logs unless explicitly necessary.
- Do not add visible canned reply templates.
- Hidden sidecars and guards are acceptable.
- Stable personality/owner relationship writes should remain review-gated unless the owner explicitly approves.
- Work with existing dirty changes if present; do not reset or revert user changes.
