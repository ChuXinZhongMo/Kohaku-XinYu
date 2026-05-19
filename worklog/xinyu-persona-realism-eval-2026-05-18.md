# XinYu Persona Realism Eval - 2026-05-18

Status: applied as persona/live-human evaluation batch.

## Batch Scope

- Capability group: persona realism / live-human-feel regression boundary.
- Goal: add a synthetic evaluation set so future persona tuning can be tested
  against concrete failure categories.

## Completed

- Added `xinyu_persona_realism_eval.py`.
  - Defines synthetic cases:
    - tired owner
    - owner asks for less tool-like speech
    - disappointment without stable personality rewrite
    - technical work stays technical
    - long gap return
    - human-like boundary without false biology
  - Flags:
    - rolecard language
    - false biology claim
    - internal state leak
    - theatrical persona performance
    - emotion treated as fact
    - too long
    - technical work emotionalized
    - generic tool-flat phrasing
- Added `tests/test_persona_realism_eval.py`.
- Added `tests/smoke/voice/persona_realism_eval_smoke.py`.

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile xinyu_persona_realism_eval.py tests\smoke\voice\persona_realism_eval_smoke.py
.\.venv\Scripts\python.exe -m pytest tests\test_persona_realism_eval.py
.\.venv\Scripts\python.exe tests\smoke\voice\persona_realism_eval_smoke.py
git diff --check -- XinYu-Core/examples/agent-apps/xinyu/xinyu_persona_realism_eval.py XinYu-Core/examples/agent-apps/xinyu/tests/test_persona_realism_eval.py XinYu-Core/examples/agent-apps/xinyu/tests/smoke/voice/persona_realism_eval_smoke.py
```

Results:

- Focused pytest: 4 passed.
- Persona realism eval smoke: passed.
- Diff check: clean.

## Direct Impact

- Persona tuning now has a small testable boundary instead of relying only on
  subjective feel.
- The eval set uses synthetic examples only; no raw private chat is read.
- The boundary keeps XinYu more natural without letting replies become roleplay,
  false biology claims, or internal variable dumps.

## Not Changed

- No runtime reply generation behavior was changed in this batch.
- No stable personality memory was rewritten.
- No git commit was made.

## Next Batch

Add a read-only memory/library/cases boundary audit that scans paths and small
metadata only, without printing private memory bodies.
