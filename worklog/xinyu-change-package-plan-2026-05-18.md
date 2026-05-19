# XinYu Change Package Plan

Generated from `git status --short` paths only.
It does not read or print private memory, raw QQ content, tokens, or secrets.

- total_entries: 755
- package_count: 8
- review_order: P00, P01, P02, P03, P04, P05, P06, P07

## Packages

### P00 docs-worklogs-plans
- risk: low
- count: 48
- intent: Keep plans, runbooks, and human audit notes reviewable apart from code behavior.
- handling: Review for accuracy and encoding; no runtime behavior should depend on this package.
- groups:
  - docs: 48
- status:
  - modified: 25
  - untracked: 23
- validation:
  - `git diff --check`
- examples:
  - `XinYu-Core/examples/agent-apps/xinyu/CHANGELOG-XINYU.md`
  - `XinYu-Core/examples/agent-apps/xinyu/CURRENT-REFACTOR-PLAN.md`
  - `XinYu-Core/examples/agent-apps/xinyu/DEPLOYMENT-STATUS-RUNBOOK.md`
  - `XinYu-Core/examples/agent-apps/xinyu/EXECUTION-ORDER.md`
  - `XinYu-Core/examples/agent-apps/xinyu/IMPLEMENTATION-NEXT.md`
  - `XinYu-Core/examples/agent-apps/xinyu/INDEX.md`
  - `XinYu-Core/examples/agent-apps/xinyu/LONG-RUN-AUDIT.md`
  - `XinYu-Core/examples/agent-apps/xinyu/PROMPT-TUNING.md`
  - `XinYu-Core/examples/agent-apps/xinyu/README.md`
  - `XinYu-Core/examples/agent-apps/xinyu/RUNBOOK.md`

### P01 ops-validation-tools
- risk: medium
- count: 171
- intent: Keep validation, smoke, and operational tooling together.
- handling: Run focused pytest for each new tool and regenerate reports from the CLI.
- groups:
  - ops: 171
- status:
  - deleted: 3
  - modified: 6
  - untracked: 162
- validation:
  - `.\.venv\Scripts\python.exe -m pytest tests\test_git_change_group_audit.py tests\test_git_change_package_plan.py tests\test_memory_library_cases_audit.py -q`
  - `.\.venv\Scripts\python.exe smoke_run.py --group quick --restore-after --timeout-seconds 300`
- examples:
  - `.gitignore`
  - `XinYu-Core/examples/agent-apps/xinyu/config.yaml`
  - `XinYu-Core/examples/agent-apps/xinyu/long_run_status.py`
  - `XinYu-Core/examples/agent-apps/xinyu/run_local_xinyu.py`
  - `XinYu-Core/examples/agent-apps/xinyu/smoke_run.py`
  - `XinYu-Core/examples/agent-apps/xinyu/sync_memory_seeds.py`
  - `XinYu-Core/examples/agent-apps/xinyu/validate_inner_framework.py`
  - `XinYu-Core/examples/agent-apps/xinyu/validate_scaffold.py`
  - `diagnostics/check_xinyu_health.py`
  - `XinYu-Core/examples/agent-apps/xinyu/ops/`

### P02 tests-smokes-regression
- risk: medium
- count: 96
- intent: Keep regression coverage changes separate from implementation changes.
- handling: Run the targeted tests first, then the full app test suite before accepting.
- groups:
  - tests: 96
- status:
  - modified: 10
  - untracked: 86
- validation:
  - `.\.venv\Scripts\python.exe -m pytest tests -q`
- examples:
  - `XinYu-Core/examples/agent-apps/xinyu/tests/conftest.py`
  - `XinYu-Core/examples/agent-apps/xinyu/tests/test_dialogue_curiosity_bridge_injection.py`
  - `XinYu-Core/examples/agent-apps/xinyu/tests/test_dialogue_curiosity_review.py`
  - `XinYu-Core/examples/agent-apps/xinyu/tests/test_expression_self_learning.py`
  - `XinYu-Core/examples/agent-apps/xinyu/tests/test_learning_closed_loop.py`
  - `XinYu-Core/examples/agent-apps/xinyu/tests/test_memory_sync_recent_context.py`
  - `XinYu-Core/examples/agent-apps/xinyu/tests/test_runtime_context.py`
  - `XinYu-Core/examples/agent-apps/xinyu/tests/test_runtime_program_awareness.py`
  - `XinYu-Core/examples/agent-apps/xinyu/tests/v1/test_emotion_state_machine.py`
  - `XinYu-Core/examples/agent-apps/xinyu/tests/v1/test_v1_smoke_contract.py`

### P03 core-runtime-services-stores
- risk: high
- count: 150
- intent: Review live runtime behavior, memory recall, persona runtime, services, and stores as one behavior package.
- handling: Require focused tests plus full pytest and quick smoke; avoid mixing unrelated cleanup here.
- groups:
  - core: 143
  - services: 4
  - stores: 3
- status:
  - deleted: 2
  - modified: 103
  - untracked: 45
- validation:
  - `.\.venv\Scripts\python.exe -m pytest tests -q`
  - `.\.venv\Scripts\python.exe smoke_run.py --group quick --restore-after --timeout-seconds 300`
- examples:
  - `XinYu-Core/examples/agent-apps/xinyu/custom/ai_self_iteration_gate_bridge_plugin.py`
  - `XinYu-Core/examples/agent-apps/xinyu/custom/ai_self_iteration_gate_engine.py`
  - `XinYu-Core/examples/agent-apps/xinyu/custom/ai_self_iteration_review_bridge_plugin.py`
  - `XinYu-Core/examples/agent-apps/xinyu/custom/ai_self_iteration_review_engine.py`
  - `XinYu-Core/examples/agent-apps/xinyu/custom/archive_commit_bridge_plugin.py`
  - `XinYu-Core/examples/agent-apps/xinyu/custom/archive_output_bridge_plugin.py`
  - `XinYu-Core/examples/agent-apps/xinyu/custom/automation_bridge_plugin.py`
  - `XinYu-Core/examples/agent-apps/xinyu/custom/autonomous_search_activation_bridge_plugin.py`
  - `XinYu-Core/examples/agent-apps/xinyu/custom/autonomous_search_activation_engine.py`
  - `XinYu-Core/examples/agent-apps/xinyu/custom/consolidation_bridge_plugin.py`

### P04 adapters-bridges-io
- risk: high
- count: 27
- intent: Review bridge, QQ, desktop action, and external I/O boundaries separately from core logic.
- handling: Validate route contracts and smoke flows without printing tokens, QQ payload bodies, or private memory.
- groups:
  - adapters: 27
- status:
  - modified: 13
  - untracked: 14
- validation:
  - `.\.venv\Scripts\python.exe -m pytest tests -q`
  - `.\.venv\Scripts\python.exe smoke_run.py --group quick --restore-after --timeout-seconds 300`
- examples:
  - `XinYu-Core/examples/agent-apps/xinyu/xinyu_bridge_action_routes.py`
  - `XinYu-Core/examples/agent-apps/xinyu/xinyu_bridge_cli.py`
  - `XinYu-Core/examples/agent-apps/xinyu/xinyu_bridge_desktop_actions.py`
  - `XinYu-Core/examples/agent-apps/xinyu/xinyu_bridge_desktop_state_text.py`
  - `XinYu-Core/examples/agent-apps/xinyu/xinyu_bridge_http.py`
  - `XinYu-Core/examples/agent-apps/xinyu/xinyu_bridge_renderer.py`
  - `XinYu-Core/examples/agent-apps/xinyu/xinyu_bridge_session.py`
  - `XinYu-Core/examples/agent-apps/xinyu/xinyu_bridge_state_text.py`
  - `XinYu-Core/examples/agent-apps/xinyu/xinyu_qq_command_router.py`
  - `XinYu-Core/examples/agent-apps/xinyu/xinyu_qq_core_client.py`

### P05 desktop-shell
- risk: medium
- count: 16
- intent: Keep Electron/main/preload/renderer changes in one frontend package.
- handling: Run desktop typecheck and build from D:\XinYu\XinYu_Desktop.
- groups:
  - desktop: 16
- status:
  - modified: 15
  - untracked: 1
- validation:
  - `npm run typecheck`
  - `npm run build`
- examples:
  - `XinYu_Desktop/src/main/index.ts`
  - `XinYu_Desktop/src/main/qq_environment.ts`
  - `XinYu_Desktop/src/main/xinyu_gateway.ts`
  - `XinYu_Desktop/src/preload/index.ts`
  - `XinYu_Desktop/src/renderer/public/xinyu-noise.svg`
  - `XinYu_Desktop/src/renderer/src/DesktopPanels.tsx`
  - `XinYu_Desktop/src/renderer/src/EnvironmentValve.tsx`
  - `XinYu_Desktop/src/renderer/src/desktopModel.ts`
  - `XinYu_Desktop/src/renderer/src/desktopTypes.ts`
  - `XinYu_Desktop/src/renderer/src/global.d.ts`

### P06 memory-data-review-only
- risk: high
- count: 5
- intent: Review memory, library, cases, seeds, and legacy data boundaries without exposing private content bodies.
- handling: Do not auto-delete or move private data. Use boundary audit reports and make per-file decisions.
- groups:
  - memory-data: 5
- status:
  - modified: 1
  - untracked: 4
- validation:
  - `.\.venv\Scripts\python.exe ops\validation\memory_library_cases_audit.py --repo-root D:\XinYu --output D:\XinYu\worklog\xinyu-memory-library-cases-boundary-audit-2026-05-18.md`
- examples:
  - `XinYu-Core/examples/agent-apps/xinyu/memory-seeds/README.md`
  - `XinYu-Core/examples/agent-apps/xinyu/data/`
  - `XinYu-Core/memory/`
  - `cases/`
  - `library/`

### P07 archive-delete-candidates
- risk: medium
- count: 242
- intent: Review removed or archived smoke/manual/diagnostic files as cleanup candidates.
- handling: Confirm references are gone before accepting deletion; never restore or delete by bulk command.
- groups:
  - archive/delete: 242
- status:
  - deleted: 242
- validation:
  - `rg "<candidate module/function>" D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`
- examples:
  - `XinYu-Core/examples/agent-apps/xinyu/ai_domain_source_smoke.py`
  - `XinYu-Core/examples/agent-apps/xinyu/ai_self_iteration_gate_smoke.py`
  - `XinYu-Core/examples/agent-apps/xinyu/ai_self_iteration_review_bridge_smoke.py`
  - `XinYu-Core/examples/agent-apps/xinyu/ai_self_iteration_review_smoke.py`
  - `XinYu-Core/examples/agent-apps/xinyu/archive_commit_smoke.py`
  - `XinYu-Core/examples/agent-apps/xinyu/archive_queue_trace_smoke.py`
  - `XinYu-Core/examples/agent-apps/xinyu/async_exploration_smoke.py`
  - `XinYu-Core/examples/agent-apps/xinyu/automation_bridge_live_turn_smoke.py`
  - `XinYu-Core/examples/agent-apps/xinyu/autonomous_search_activation_smoke.py`
  - `XinYu-Core/examples/agent-apps/xinyu/autonomous_state_smoke.py`
