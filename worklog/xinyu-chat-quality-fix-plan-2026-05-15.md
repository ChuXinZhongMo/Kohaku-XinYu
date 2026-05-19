# XinYu Chat Quality Fix Plan

Date: 2026-05-15
Workspace: `D:\XinYu`

## Goal

Fix the live chat problems found in today's QQ conversation without changing persona memory bodies, public IPC names, or outbound QQ safety rules.

## Problems To Fix

1. Fragmented owner messages are treated as complete turns too early.
2. XinYu still replies to low-information or "I am still thinking" turns.
3. Runtime status can be polluted by stale state, causing contradictions like saying QQ is not connected while the current turn is from QQ.
4. Visible replies can leak bracketed aside/stage text, malformed casual wording, or low-value fillers.
5. Promises like "I will report tonight" need a trackable follow-up state instead of ad-hoc chat.
6. Ordinary low-risk chat is too slow when it does not need full reasoning.

## Execution Order

1. Add a segmented intent gate at the owner-private QQ ingress path.
   - Merge consecutive message fragments before core generation.
   - Classify as `wait_more`, `silent`, `ack_only`, `reply_now`, `correction`, or `task_instruction`.
   - Suppress low-information turns before generation.

2. Strengthen current-channel runtime facts.
   - If the current turn arrived through `qq_gateway`, treat QQ/private chat connectivity as live for that answer.
   - Prefer fresh gateway status over old memory/status text.

3. Add visible reply guard coverage.
   - Block or normalize bracketed stage asides.
   - Avoid sending useless fillers such as "嗯，在" when the conversation is already active.

4. Add tests.
   - Fragmented owner messages.
   - "不是，我的意思是..." correction.
   - "嗯..." / "我想想" silent cases.
   - QQ status contradiction case.
   - Visible text guard case.

5. Validate.
   - `python -m py_compile` for touched Python files.
   - Targeted pytest/smoke for QQ gateway and visible guard paths.

## Progress

### 2026-05-15 First Fix Batch

- Done: added an owner-private segmented intent gate in `xinyu_qq_gateway.py`.
- Done: low-information owner turns such as thinking/ack-only fragments are dropped before core generation, with `qq_should_reply=false` and an inbound trace drop reason.
- Done: correction and task-instruction turns are still dispatched and annotated with `qq_segmented_intent_action`.
- Done: coalesced owner fragments now get segmented intent metadata before dispatch.
- Done: live QQ current-turn metadata is added to chat payloads so stale runtime status should not override the fact that the current message arrived through QQ.
- Done: live-turn sidecars now expose segmented intent and current QQ transport facts to the core prompt.
- Done: empty visible reply fallback now stays empty instead of inserting a fixed fallback text.

Validation run:

- `python -m py_compile xinyu_qq_gateway.py xinyu_bridge_turn_sidecars.py xinyu_core_bridge.py`
- `python tests/smoke/qq/integration/xinyu_qq_gateway_smoke.py`
- `python -m pytest tests/test_dialogue_curiosity_bridge_injection.py::test_empty_visible_reply_fallback_is_disabled tests/test_dialogue_curiosity_bridge_injection.py::test_style_pressure_empty_fallback_is_disabled tests/test_dialogue_curiosity_bridge_injection.py::test_empty_visible_reply_fallback_does_not_template_short_fatigue tests/test_dialogue_curiosity_bridge_injection.py::test_empty_visible_reply_fallback_handles_explicit_fatigue_boundary -q`

Remaining:

- Measure ordinary-chat latency again after restarting with the new ingress gate and collecting fresh live QQ turns.

### 2026-05-15 Second Fix Batch

- Done: visible reply guard now removes targeted inline parenthetical narration such as short stage/action asides, while leaving ordinary parenthetical content alone.
- Done: speech-controller smoke now covers inline bracket narration detection and removal.
- Done: owner report-later instructions such as "晚上回来我要看到你的汇报" now match the existing promise follow-up path when XinYu replies with a report promise.
- Done: promised report follow-up writes `promise_followup_state.md` and queues through the existing `promise_followup` QQ outbox path instead of staying as a bare chat promise.

Validation run:

- `python -m py_compile xinyu_speech_controller.py xinyu_core_bridge.py`
- `python tests/smoke/voice/xinyu_speech_controller_smoke.py`
- `python -m pytest tests/test_dialogue_curiosity_bridge_injection.py::test_promised_followup_queues_owner_private_completion tests/test_dialogue_curiosity_bridge_injection.py::test_promised_followup_ignores_completed_review_reply tests/test_dialogue_curiosity_bridge_injection.py::test_promised_followup_status_check_queues_completion tests/test_dialogue_curiosity_bridge_injection.py::test_promised_followup_report_instruction_queues_completion -q`
- `python tests/smoke/qq/integration/xinyu_qq_gateway_smoke.py`

## Stop Conditions

- Any real QQ outbound test.
- Any change to persona semantics or long-term memory body text.
- Any destructive filesystem or git operation.
- Any broad rewrite of `xinyu_core_bridge.py` or `xinyu_qq_gateway.py` beyond the targeted ingress/guard paths.
