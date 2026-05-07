# XinYu 24h Refactor Task Queue

Date: 2026-05-07
Workspace: D:\XinYu

## Baseline

- Branch: `master`
- Current HEAD: `5d07dcb Initial private XinYu protective snapshot`
- Initial dirty state: untracked `XINYU-24H-WORK-PLAN.md` supplied as run instructions.
- Live app root: `XinYu-Core/examples/agent-apps/xinyu/`
- Core bridge: `xinyu_core_bridge.py` at 7150 lines.
- QQ gateway: `xinyu_qq_gateway.py` at 4246 lines.
- Existing smoke files in app root: 157 `*smoke*.py` files.
- Existing pytest files under app `tests/`: 32 files.

## P0

- [x] Record baseline task queue.
- [x] Create progress log for loop-by-loop execution.
- [x] Create refactor checklist.
- [x] Create validation matrix mapping capability areas to exact commands.
- [x] Identify missing validation coverage and add it to this queue.
- [ ] Extract one low-risk responsibility from `xinyu_core_bridge.py`.
- [ ] Create state write audit.

## P1

- [ ] Extract Desktop service boundary from the core bridge without route or payload changes.
- [ ] Extract Codex service boundary from the core bridge without output format changes.
- [ ] Extract Learning service boundary from the core bridge without write format changes.
- [ ] Introduce `state_service.py` helper surface for atomic writes and JSONL append.
- [ ] Extract QQ trust policy from `xinyu_qq_gateway.py`.
- [ ] Extract QQ outbox dispatcher from `xinyu_qq_gateway.py`.

## P2

- [ ] Extract QQ sender helpers.
- [ ] Extract QQ command router helpers.
- [ ] Isolate v1 canary gate decisions.
- [ ] Add long-run health diagnostics.
- [ ] Add chat service boundary after validation coverage is solid.
- [ ] Add root long-run operations document.
- [ ] Add read-only `diagnostics/check_xinyu_health.py`.
- [ ] Add narrow tests for future service-boundary helpers as they are extracted.

## P3

- [ ] Full memory migration.
- [ ] Full event/projection state rewrite.
- [ ] Full chat pipeline rewrite.
- [ ] Desktop UI large refactor.
- [ ] v1 real traffic expansion.

## Stop Conditions To Watch

- Memory body content changes.
- Need for real QQ outbound testing.
- Unexpected route or payload shape changes.
- Unexpected v1 real traffic expansion.
- Bridge startup regression that cannot be rolled back.
- Repeated validation failure without a smaller safe slice.
- User parallel edits in files touched by the current loop.
