# Task: XinYu autonomy/intention ecology

Goal: Build a bounded autonomy loop on top of relation posture: XinYu should form candidate intentions, score value/risk, choose action or restraint, write trace/state, feed a hidden prompt sidecar, and keep future proactive/memory candidates gated rather than directly sending or over-disclosing mechanisms.

## Open
- [ ] Commit or package these changes if the owner requests it.

## Done
- [x] Map existing initiative/proactive modules and choose the least invasive insertion point.
- [x] Implement deterministic `xinyu_intention_ecology.py` for candidate generation, scoring, gating, state, and trace.
- [x] Integrate intention ecology into the live reply sidecar chain without exposing internal mechanisms.
- [x] Add tests for candidate generation, action gating, feedback/trace state, and sidecar rendering.
- [x] Add replay/eval cases for autonomy, restraint, follow-up candidate, and mechanism-leak boundaries.
- [x] Run focused validation for intention ecology, relation posture, and bridge sidecar injection.
- [x] Run restart/status checks after focused validation.
- [x] Update completion notes and remaining risks.
- [x] Completed previous relation/emotion decision center foundation.

## Implementation notes
- Previous relation posture module path: `xinyu_relation_posture.py`.
- New intention ecology module path: `xinyu_intention_ecology.py`.
- Previous reply-chain insertion point reused: `xinyu_bridge_turn_sidecars.inject_live_turn_context()` after relation posture evaluation and before prompt sidecar selection/final live prompt assembly.
- Runtime state path: `memory/context/intention_ecology_state.md`.
- Runtime trace path: `runtime/intention_ecology_trace.jsonl`.
- Replay/eval path: `data/conversation_experience/relation_emotion_eval_cases.jsonl`; expanded to seven cases and imported successfully into the conversation experience DB.
- Registry entry `relation_emotion_eval_cases` now covers relation/emotion and intention ecology eval cases.
- Validation passed: `python -m py_compile xinyu_intention_ecology.py xinyu_relation_posture.py xinyu_bridge_turn_sidecars.py`.
- Validation passed: `python -m pytest -q tests/test_intention_ecology.py tests/test_relation_posture.py tests/test_dialogue_curiosity_bridge_injection.py::test_live_turn_injects_relation_posture_without_visible_mechanism_leak` -> 11 passed.
- Runtime validation passed: `start_xinyu_core_bridge.ps1 -ForceRestart -RequireVersion -HealthTimeoutSeconds 60`; `python xinyu_status.py --json` reports `ok: true`, core bridge/version/digest checks true, and restart flags false.
- This task keeps direct proactive sending disabled by default; future-active intentions are recorded as review-gated candidates only.

## Remaining risks
- Repository already contains many pre-existing modified/untracked files unrelated to this task; no commit was made.
- Memory/data artifacts under ignored paths remain local unless explicitly force-added or moved.
- Intention ecology is deterministic marker-based and conservative; future owner feedback can tune markers, scores, and gates.

## Previous task note
The previous contents tracked `XinYu relation/emotion decision center`; it is complete locally. Some memory/data artifacts are ignored by git and remain local unless explicitly force-added or moved.
